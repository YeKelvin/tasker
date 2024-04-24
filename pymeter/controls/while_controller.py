#!/usr/bin python3
# @File    : while_controller.py
# @Time    : 2021-08-26 18:08:15
# @Author  : Kelvin.Ye
import time
from typing import Final

import gevent
from loguru import logger

from pymeter.controls.controller import IteratingController
from pymeter.controls.generic_controller import GenericController
from pymeter.workers.context import ContextService


class WhileController(GenericController, IteratingController):

    CONDITION: Final = 'WhileController__condition'

    MAX_LOOP_COUNT: Final = 'WhileController__max_loop_count'

    TIMEOUT: Final = 'WhileController__timeout'

    DELAY: Final = 'WhileController__delay'

    @property
    def condition(self) -> str:
        return self.get_property_as_str(self.CONDITION)

    @property
    def max_loop_count(self) -> int:
        return self.get_property_as_int(self.MAX_LOOP_COUNT)

    @property
    def timeout(self) -> int:
        return self.get_property_as_int(self.TIMEOUT)

    @property
    def delay(self) -> int:
        return self.get_property_as_int(self.DELAY)

    @property
    def last_sample_ok(self) -> str:
        return self.ctx.variables.get('Coroutine__last_sample_ok')

    def __init__(self):
        super().__init__()
        self._start_time = 0
        self._break_loop = False
        self._while_result = None

    def next(self):
        """@override"""
        self.update_iteration_index(self.name, self.iter_count)
        try:
            # 如果设置了 timeout 则记录开始循环时间
            if self.iter_count == 0 and self.timeout:
                self._start_time = time.time()

            # 如果第一次进入时条件为假，则完全跳过控制器
            if self.first and self.end_of_loop(False):
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 获取下一个请求')
                self.reset_while()
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为空')
                return None

            # 获取下一个 sampler
            return super().next()
        except Exception:
            logger.exception('Exception Occurred')
        finally:
            self.update_iteration_index(self.name, self.iter_count)

    # Evaluate the condition, which can be:
    # blank or LAST = was the last sampler OK?
    # otherwise, evaluate the condition to see if it is not "false"
    # If blank, only evaluate at the end of the loop
    # Must only be called at start and end of loop
    def end_of_loop(self, loop_end: bool) -> bool:
        if self._break_loop:
            return True

        condition = self.condition.strip()
        result = False

        # 如果条件为空，在循环结束时只检查上一个 Sampler 的结果
        if loop_end and condition.isspace():
            result = self.last_sample_ok.lower() == 'false'
        elif self.max_loop_count and (self.iter_count + 1 > self.max_loop_count):
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] while超过最大循环次数，停止循环\n'
                f'while最大循环次数:[ {self.max_loop_count} ]\n'
                f'while当前循环次数:[ {self.iter_count + 1} ]'
            )
            result = False
        elif self.timeout and (elapsed := int(time.time() * 1000) - int(self._start_time * 1000)) > self.timeout:
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] while已超时，停止循环\n'
                f'while超时时间:[ {self.timeout}ms ]\n'
                f'while循环耗时:[ {elapsed}ms ]'
            )
            result = False
        else:
            result = self.evaluate(condition)  # 如果 next() 被调用，条件可能为空

        if result and self.delay:
            logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 间隔:[ {self.delay}ms ]')
            gevent.sleep(float(self.delay / 1000))

        # 此方法为是否结束循环，所以对while结果要取反
        return not result

    def next_is_null(self):
        """@override"""
        self.re_initialize()
        if self.end_of_loop(True):
            self.reset_while()
            return None

        return self.next()

    def trigger_end_of_loop(self):
        """@override"""
        super().trigger_end_of_loop()
        self.reset_while()

    def start_next_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始下一个循环')
        self.re_initialize()

    def increment_iter_count(self):
        """@override"""
        super().increment_iter_count()
        self.reset_while_result()

    def reset_while(self):
        self.reset_iter_count()
        self.reset_strat_time()
        self.reset_break_loop()
        self.reset_while_result()

    def reset_break_loop(self):
        self._break_loop = False

    def reset_strat_time(self):
        self._strat_time = 0

    def reset_while_result(self):
        self._while_result = None

    def break_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 中止循环')
        self._break_loop = True
        self.first = True
        self.reset_current()
        self.reset_iter_count()

    def iteration_start(self, source, iter_count):
        """@override"""
        self.re_initialize()
        self.reset_iter_count()

    def evaluate(self, condition: str):
        if self._while_result is not None:
            return self._while_result

        try:
            ctx = ContextService.get_context()
            result = eval(condition, None, {'vars': ctx.variables, 'props': ctx.properties})
            if not isinstance(result, bool):
                result = bool(result)
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] WHILE逻辑运算\n'
                f'while次数: 第 {self.iter_count + 1} 次\n'
                f'while条件: {condition}\n'
                f'while结果: {result}'
            )
            self._while_result = result
            return result
        except Exception:
            logger.exception('Exception Occurred')
            return False
