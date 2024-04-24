#!/usr/bin python3
# @File    : sleep_prev_processor.py
# @Time    : 2022/10/17 17:06
# @Author  : Kelvin.Ye
from typing import Final

import gevent
from loguru import logger

from pymeter.processors.prev import PrevProcessor
from pymeter.workers.context import ContextService


class SleepPrevProcessor(PrevProcessor):

    # 延迟时间，单位ms
    DELAY: Final = 'SleepPrevProcessor__delay'

    @property
    def delay(self):
        return self.get_property_as_str(self.DELAY)

    def process(self) -> None:
        ctx = ContextService.get_context()
        try:
            logger.info(f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] 前置等待 {self.delay} ms')
            gevent.sleep(float(self.delay) / 1000)
        except Exception:
            logger.exception('Exception Occurred')
