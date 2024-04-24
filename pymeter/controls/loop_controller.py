#!/usr/bin python3
# @File    : loop_controller
# @Time    : 2020/2/28 17:16
# @Author  : Kelvin.Ye
from typing import Final

from loguru import logger

from pymeter.controls.controller import IteratingController
from pymeter.controls.generic_controller import GenericController
from pymeter.elements.element import TestElement
from pymeter.samplers.sampler import Sampler


class LoopController(GenericController, IteratingController):

    # 循环次数
    LOOPS: Final = 'LoopController__loops'

    # 是否无限循环
    CONTINUE_FOREVER: Final = 'LoopController__continue_forever'

    # 无限循环数
    INFINITE_LOOP_COUNT: Final = -1

    def __init__(self):
        TestElement.__init__(self)
        GenericController.__init__(self)

        self._loop_count: int = 0
        self._break_loop: bool = False

    @property
    def loops(self) -> int:
        return self.get_property_as_int(self.LOOPS)

    @property
    def continue_forever(self) -> bool:
        return self.get_property_as_bool(self.CONTINUE_FOREVER)

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, val: bool):
        self.reset_break_loop()
        self._done = val

    def next(self) -> Sampler | None:
        self.update_iteration_index(self.name, self._loop_count)
        # noinspection PyBroadException
        try:
            if self.end_of_loop():
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 获取下一个请求')
                if not self.continue_forever:
                    self.done = True
                self.reset_break_loop()
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为空')
                return None

            if self.first:
                controller_name = f'控制器:[ {self.name} ] ' if self.name else ''
                logger.info(
                    f'线程:[ {self.ctx.thread_name} ] {controller_name}开始第 {self._loop_count + 1} 次迭代'
                )

            return super().next()
        except Exception:
            logger.exception('Exception Occurred')
        finally:
            self.update_iteration_index(self.name, self._loop_count)

    def trigger_end_of_loop(self):
        """触发循环结束"""
        super().trigger_end_of_loop()
        self.reset_loop_count()

    def end_of_loop(self) -> bool:
        """判断循环是否结束"""
        return self._break_loop or (self.loops > self.INFINITE_LOOP_COUNT) and (self._loop_count >= self.loops)

    def next_is_null(self):
        self.re_initialize()
        if self.end_of_loop():
            if not self.continue_forever:
                self.done = True
            else:
                self.reset_loop_count()
            return None
        return self.next()

    def increment_loop_count(self):
        self._loop_count += 1

    def reset_loop_count(self):
        self._loop_count = 0

    def re_initialize(self):
        self.first = True
        self.reset_current()
        self.increment_loop_count()
        self.recover_running_version()

    def reset_break_loop(self):
        if self._break_loop:
            self._break_loop = False

    def start_next_loop(self):
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始下一个循环')
        self.re_initialize()

    def break_loop(self):
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 中止循环')
        self._break_loop = True
        self.first = True
        self.reset_current()
        self.reset_loop_count()
        self.recover_running_version()

    def iteration_start(self, source, iter_count):
        self.re_initialize()
        self.reset_loop_count()
