#!/usr/bin python3
# @File    : generic_controller
# @Time    : 2020/2/28 17:25
# @Author  : Kelvin.Ye
from collections import deque

from loguru import logger

from pymeter.controls.controller import Controller
from pymeter.engines.interface import LoopIterationListener
from pymeter.engines.interface import TestCompilerHelper
from pymeter.samplers.sampler import Sampler
from pymeter.tools.exceptions import NextIsNullException
from pymeter.workers.context import ContextService
from pymeter.workers.context import ThreadContext


class GenericController(Controller, TestCompilerHelper):
    """所有控制器的基类"""

    def __init__(self):
        super().__init__()

        # 用于 TestCompilerHelper
        self.children = []

        # GenericController::subControllersAndSamplers
        # 存储 Sampler 或 Controller
        # 由 TestCompiler 编译时通过 addElement 添加
        self.sub_elements = []

        # 存储子代控制器的 LoopIterationListener
        self.iteration_listeners = deque()

        # 控制器下当前元素的索引（Sampler 或 Controller）
        self.current = 0

        # 当前迭代次数
        self._iter_count = 0

        # 是否控制器下的第一个元素（Sampler 或 Controller）
        self._first = True

        # 是否已经完成控制器下所有的请求和迭代
        self._done = False

    @property
    def iter_count(self) -> int:
        """只读，写由 increment_iter_count 函数控制"""
        return self._iter_count

    @property
    def first(self) -> bool:
        return self._first

    @first.setter
    def first(self, val: bool):
        self._first = val

    @property
    def done(self) -> bool:
        """@override"""
        return self._done

    @done.setter
    def done(self, val: bool):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] set done:[ {val} ]')
        self._done = val

    @property
    def ctx(self) -> ThreadContext:
        return ContextService.get_context()

    def reset_current(self):
        """重置当前元素的索引"""
        self.current = 0

    def reset_iter_count(self):
        """重置当前迭代次数"""
        self._iter_count = 0

    def initialize(self):
        """初始化控制器"""
        self.done = False
        self.first = True
        self.reset_current()
        self.reset_iter_count()
        self.initialize_sub_controllers()

    def initialize_sub_controllers(self):
        """初始化子代控制器"""
        for element in self.sub_elements:
            if isinstance(element, GenericController):
                element.initialize()

    def re_initialize(self):
        """重新初始化控制器（在控制器最后一个子代元素执行完成之后调用）"""
        self.first = True
        self.increment_iter_count()
        self.reset_current()
        self.recover_running_version()

    def increment_current(self):
        self.current += 1

    def increment_iter_count(self):
        self._iter_count += 1

    def next(self) -> Sampler | None:
        """获取控制器的下一个子代元素"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 获取下一个请求')
        self.fire_iter_events()

        if self.done:
            return None

        next_sampler = None
        try:
            current_element = self.get_current_element()  # type: Sampler | Controller
            if current_element is None:
                next_sampler = self.next_is_null()
            elif isinstance(current_element, Sampler):
                next_sampler = self.next_is_sampler(current_element)
            else:
                next_sampler = self.next_is_controller(current_element)
        except NextIsNullException:
            logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为空')

        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个:[ {next_sampler} ]')
        return next_sampler

    def fire_iter_events(self):
        if self.first:
            self.fire_iteration_start()
            self.first = False

    def fire_iteration_start(self):
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 遍历触发 LoopIterationListener 的开始事件')
        for listener in self.iteration_listeners:
            listener.iteration_start(self, self.iter_count)

    def get_current_element(self):
        """根据当前索引获取元素"""
        if self.current < len(self.sub_elements):
            return self.sub_elements[self.current]

        if not self.sub_elements:
            self.done = True
            raise NextIsNullException()

        return None

    def next_is_sampler(self, sampler: Sampler) -> Sampler:
        """下一个元素是取样器时的处理方法"""
        self.increment_current()
        return sampler

    def next_is_controller(self, controller: Controller) -> Sampler:
        """下一个元素是控制器时的处理方法"""
        # 获取子代控制器的下一个请求
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为控制器')
        sampler = controller.next()
        # 子代控制器的下一个请求为空时重新获取父控制器的下一个请求
        if sampler is None:
            self.current_returned_none(controller)
            sampler = self.next()
        return sampler

    def next_is_null(self) -> None:
        """下一个元素为空时的处理方法（即没有下一个元素了）"""
        self.re_initialize()
        return None

    def current_returned_none(self, controller: Controller):
        """子代控制器的下一个请求为空时的处理方法"""
        if controller.done:
            self.remove_current_element()
        else:
            self.increment_current()

    def add_element(self, child):
        self.sub_elements.append(child)

    def add_test_element(self, child):
        if isinstance(child, Controller | Sampler):
            self.add_element(child)

    def add_test_element_once(self, child) -> bool:
        """@override from TestCompilerHelper"""
        if child not in self.children:
            self.children.append(child)
            self.add_test_element(child)
            return True
        else:
            return False

    def remove_current_element(self):
        self.sub_elements.remove(self.sub_elements[self.current])

    def add_iteration_listener(self, listener: LoopIterationListener):
        self.iteration_listeners.appendleft(listener)

    def remove_iteration_listener(self, listener: LoopIterationListener):
        self.iteration_listeners.remove(listener)

    def trigger_end_of_loop(self):
        """触发结束循环"""
        self.re_initialize()
