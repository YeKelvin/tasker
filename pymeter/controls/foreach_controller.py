#!/usr/bin python3
# @File    : foreach_controller.py
# @Time    : 2021/11/12 14:42
# @Author  : Kelvin.Ye
from collections.abc import Iterable
from typing import Final

import gevent
from loguru import logger

from pymeter.controls.controller import IteratingController
from pymeter.controls.generic_controller import GenericController


class ForeachController(GenericController, IteratingController):

    FOREACH_TARGET: Final = 'ForeachController__target'

    FOREACH_ITER: Final = 'ForeachController__iter'

    OBJECT_TYPE: Final = 'ForeachController__type'

    DELAY: Final = 'ForeachController__delay'

    @property
    def foreach_target(self) -> str:
        return self.get_property_as_str(self.FOREACH_TARGET)

    @property
    def foreach_iter(self) -> str:
        return self.get_property_as_str(self.FOREACH_ITER)

    @property
    def object_type(self) -> str:
        return self.get_property_as_str(self.OBJECT_TYPE)

    @property
    def delay(self) -> int:
        return self.get_property_as_int(self.DELAY)

    @property
    def iter_count(self) -> int:
        return self._loop_count + 1

    @property
    def done(self) -> bool:
        if self._loop_count >= self._end_index:
            return True

        try:
            item = self._iter[self._loop_count]
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始第 {self._loop_count + 1} 次遍历\n'
                f'foreach当前项:{item}'
            )
            if self._target_size > 1 and isinstance(item, Iterable):
                for i, target in enumerate(self._target):
                    self.ctx.variables.put(target, item[i])
            else:
                target = self._target[0]
                self.ctx.variables.put(self._target[0], item)
        except Exception:
            logger.exception('Exception Occurred')
            return True

        return self._done

    @done.setter
    def done(self, val: bool):
        self._done = val

    def __init__(self):
        super().__init__()
        self._loop_count: int = 0
        self._break_loop: bool = False
        self._target = None
        self._target_size = None
        self._iter = None
        self._end_index = 0

    def init_foreach(self):
        # 分割目标变量
        self._target = self.foreach_target.split(',')
        self._target_size = len(self._target)

        # 移除目标变量首尾的空格
        for i, key in enumerate(self._target):
            self._target[i] = key.strip()

        # 获取迭代对象
        if self.object_type == 'OBJECT':
            self._iter = self.ctx.variables.get(self.foreach_iter, self.ctx.properties.get(self.foreach_iter))
        elif self.object_type == 'CUSTOM':
            self.exec_iter(self.foreach_iter)
        else:
            logger.error(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 对象类型:[ {self.object_type} ] '
                f'不支持的对象类型'
            )
            self.done = True
            return

        if self._iter is None:
            logger.error(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 迭代对象为None，停止遍历')
            self.done = True
            return

        if isinstance(self._iter, str):
            self.exec_iter(self._iter)

        # 判断是否为可迭代的对象
        if not isinstance(self._iter, Iterable):
            logger.error(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 迭代对象:[ {self._iter} ] '
                f'不是可迭代的对象，停止遍历'
            )
            self.done = True
            return

        iter_size = len(self._iter)
        if iter_size == 0:
            logger.error(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 迭代对象:[ {self._iter} ] '
                f'迭代对象为空，停止遍历'
            )
            self.done = True
            return

        # 字典处理
        if isinstance(self._iter, dict):
            self._iter = list(self._iter.items())

        logger.info(
            f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始FOREACH遍历\n'
            f'foreach数据:{self._iter}'
        )

        # 存储最后一个索引
        self._end_index = iter_size

    def exec_iter(self, stmt):
        exec(f'self._iter = ( {stmt} )', None, {'self': self})

    def next(self):
        """@override"""
        self.update_iteration_index(self.name, self._loop_count)
        # noinspection PyBroadException
        try:
            if self.first:
                self.init_foreach()

            if self.end_of_loop():
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 获取下一个请求')
                self.re_initialize()
                self.reset_break_loop()
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为空')
                return None

            nsampler = super().next()
            if nsampler and self.delay:
                logger.debug(
                    f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 间隔:[ {self.delay}ms ]'
                )
                gevent.sleep(float(self.delay / 1000))

            return nsampler
        except Exception:
            logger.exception('Exception Occurred')
        finally:
            self.update_iteration_index(self.name, self._loop_count)

    def trigger_end_of_loop(self):
        """@override"""
        super().trigger_end_of_loop()
        self.reset_loop_count()

    def end_of_loop(self) -> bool:
        """判断循环是否结束"""
        return self._break_loop or (self._loop_count >= self._end_index)

    def next_is_null(self):
        """@override"""
        self.re_initialize()
        if self.end_of_loop():
            self.reset_break_loop()
            self.reset_loop_count()
            return None
        return self.next()

    def increment_loop_count(self):
        self._loop_count += 1

    def reset_loop_count(self):
        self._loop_count = 0

    def re_initialize(self):
        """@override"""
        self.first = True
        self.reset_current()
        self.increment_loop_count()
        self.recover_running_version()

    def reset_break_loop(self):
        if self._break_loop:
            self._break_loop = False

    def start_next_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始下一个循环')
        self.re_initialize()

    def break_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 中止循环')
        self._break_loop = True
        self.first = True
        self.reset_current()
        self.reset_loop_count()
        self.recover_running_version()

    def iteration_start(self, source, iter_count):
        """@override"""
        self.re_initialize()
        self.reset_loop_count()
