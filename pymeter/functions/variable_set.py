#!/usr/bin python3
# @Module  : functions
# @File    : variable_set.py
# @Time    : 2024-03-11 17:41:56
# @Author  : Kelvin.Ye
from typing import Final

from loguru import logger

from pymeter.functions.function import Function
from pymeter.workers.context import ContextService


class VariableSet(Function):

    REF_KEY: Final = '__setvar'

    def __init__(self):
        self.name = None
        self.value = None

    def execute(self):
        logger.debug(f'执行函数:[ {self.REF_KEY} ]')

        name = self.name.execute().strip()
        value = self.value.execute().strip()

        ctx = ContextService.get_context()
        ctx.variables.put(name, value)
        logger.info(
            f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] 函数:[ __setvar ] 设置局部变量\n'
            f'变量名:[ {name} ]\n'
            f'变量值:[ {value} ]'
        )

        return value

    def set_parameters(self, params: list):
        # 校验函数实参数量
        self.check_parameter_count(params, 2)
        # 提取参数
        self.name = params[0]
        self.value = params[1]
