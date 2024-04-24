#!/usr/bin python3
# @File    : sleep_post_processor.py
# @Time    : 2022/10/17 17:05
# @Author  : Kelvin.Ye
from typing import Final

import gevent
from loguru import logger

from pymeter.processors.post import PostProcessor
from pymeter.workers.context import ContextService


class SleepPostProcessor(PostProcessor):

    # 延迟时间，单位ms
    DELAY: Final = 'SleepPostProcessor__delay'

    @property
    def delay(self):
        return self.get_property_as_str(self.DELAY)

    def process(self) -> None:
        ctx = ContextService.get_context()
        try:
            logger.info(f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] 后置等待 {self.delay} ms')
            gevent.sleep(float(self.delay) / 1000)
        except Exception:
            logger.exception('Exception Occurred')
