#!/usr/bin python3
# @File    : retry_controller.py
# @Time    : 2021/11/29 11:25
# @Author  : Kelvin.Ye
from typing import Final

import gevent
from loguru import logger

from pymeter.controls.controller import IteratingController
from pymeter.controls.generic_controller import GenericController
from pymeter.elements.element import TestElement
from pymeter.engines.interface import LoopIterationListener
from pymeter.samplers.sampler import Sampler


class RetryController(GenericController, IteratingController, LoopIterationListener):

    # 重试次数
    RETRIES: Final = 'RetryController__retries'

    # 重试间隔
    INTERVALS: Final = 'RetryController__intervals'

    # 重试标识前缀
    FLAG_PREFIX: Final = 'RetryController__flag_prefix'

    def __init__(self):
        TestElement.__init__(self)
        GenericController.__init__(self)

        self._retry_count: int = 0
        self._break_retry: bool = False

    @property
    def retries(self) -> int:
        return self.get_property_as_int(self.RETRIES)

    @property
    def intervals(self) -> int:
        return self.get_property_as_int(self.INTERVALS)

    @property
    def flag_prefix(self) -> str:
        return self.get_property_as_str(self.FLAG_PREFIX)

    @property
    def done(self):
        """@override"""
        return self._done

    @done.setter
    def done(self, val: bool):
        """@override"""
        self.reset_break_retry()
        self._done = val

    @property
    def last_sample_ok(self) -> str:
        return self.ctx.variables.get('Coroutine__last_sample_ok')

    def next(self) -> Sampler | None:
        # noinspection PyBroadException
        try:
            if self.end_of_retry():
                self.done = True
                self.reset_break_retry()
                return None

            # 给下一个 Sampler 添加重试标识
            nsampler = super().next()
            if nsampler:
                # 延迟重试（间隔）
                if not self.first and self.intervals:
                    logger.debug(
                        f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 延迟 {self.intervals}ms 重试'
                    )
                    gevent.sleep(float(self.intervals / 1000))

                # 添加重试标识，最后一次无需添加
                nsampler.retrying = self._retry_count < self.retries - 1
                # 给重试的请求的名称添加重试标识后缀
                if self._retry_count < self.retries:
                    nsampler.retry_flag = f'[{self.flag_prefix}{self._retry_count + 1}]' if self.flag_prefix else None

            return nsampler
        except Exception:
            logger.exception('Exception Occurred')

    def next_is_null(self):
        """@override"""
        self.re_initialize()
        if self.last_sample_ok:
            logger.debug(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 请求成功, 测试通过，停止重试'
            )
            self.done = True
            return None
        if self.end_of_retry():
            self.done = True
            return None
        return self.next()

    def end_of_retry(self) -> bool:
        return self._break_retry or (self._retry_count >= self.retries)

    def increment_retry_count(self):
        self._retry_count += 1

    def reset_retry_count(self):
        self._retry_count = 0

    def reset_break_retry(self):
        if self._break_retry:
            self._break_retry = False

    def trigger_end_of_loop(self):
        """@override"""
        super().trigger_end_of_loop()
        self.reset_retry_count()

    def re_initialize(self):
        """@override"""
        self.first = True
        self.reset_current()
        self.increment_retry_count()
        self.recover_running_version()

    def start_next_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始下一个循环')
        self.re_initialize()

    def break_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 中止循环')
        self._break_retry = True
        self.first = True
        self.reset_current()
        self.reset_retry_count()
        self.recover_running_version()

    def iteration_start(self, source, iter_count):
        """@override"""
        self.re_initialize()
        self.reset_retry_count()
