#!/usr/bin python3
# @File    : time.py
# @Time    : 2020/1/20 16:07
# @Author  : Kelvin.Ye
import time

from typing import Final

from loguru import logger

from pymeter.functions.function import Function


class Time(Function):

    REF_KEY: Final = '__time'

    def __init__(self):
        self.format = None

    def execute(self):
        logger.debug(f'执行函数:[ {self.REF_KEY} ]')

        timestamp = time.time()

        # 格式化时间
        if self.format:
            time_format = self.format.execute().strip()
            struct_time = time.localtime(timestamp)
            return time.strftime(time_format, struct_time)

        return str(int(timestamp * 1000))

    def set_parameters(self, params: list):
        # 校验函数实参数量
        self.check_parameter_min(params, 0)
        self.check_parameter_max(params, 1)
        # 提取参数
        self.format = params[0] if params else None
