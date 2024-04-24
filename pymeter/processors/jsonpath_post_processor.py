#!/usr/bin python3
# @File    : jsonpath_post_processor.py
# @Time    : 2022/9/27 10:56
# @Author  : Kelvin.Ye
from typing import Final

from loguru import logger
from orjson import JSONDecodeError

from pymeter.processors.post import PostProcessor
from pymeter.utils.json_util import json_path
from pymeter.utils.json_util import to_json
from pymeter.workers.context import ContextService


class JsonPathPostProcessor(PostProcessor):

    # 变量作用域
    VARIABLE_SCOPE ='JsonPathPostProcessor__variable_scope'

    # 变量名称
    VARIABLE_NAME: Final = 'JsonPathPostProcessor__variable_name'

    # JsonPath 表达式
    JSONPATH: Final = 'JsonPathPostProcessor__jsonpath'

    # 列表随机
    LIST_RANDOM: Final = 'JsonPathPostProcessor__list_random'

    # 默认值
    DEFAULT_VALUE: Final = 'JsonPathPostProcessor__default_value'

    @property
    def variable_scope(self):
        """变量作用域

        LOCAL:  局部变量
        GLOBAL: 全局变量
        """
        return self.get_property_as_str(self.VARIABLE_SCOPE, 'LOCAL')

    @property
    def variable_name(self):
        return self.get_property_as_str(self.VARIABLE_NAME)

    @property
    def jsonpath(self):
        return self.get_property_as_str(self.JSONPATH)

    @property
    def list_random(self):
        return self.get_property_as_bool(self.LIST_RANDOM)

    @property
    def default_value(self):
        return self.get_property_as_str(self.DEFAULT_VALUE)

    def process(self) -> None:
        ctx = ContextService.get_context()

        varname = self.variable_name
        jsonpath = self.jsonpath

        if not varname:
            logger.warning(
                f'线程:[ {ctx.thread_name} ] '
                f'请求:[ {ctx.current_sampler.name} ] '
                f'处理器:[ {self.name} ] 警告: 变量名称为空，请修改写后重试'
            )
            return

        if not jsonpath:
            logger.warning(
                f'线程:[ {ctx.thread_name} ] '
                f'请求:[ {ctx.current_sampler.name} ] '
                f'处理器:[ {self.name} ] 警告: JsonPath为空，请修改写后重试')
            return

        # noinspection PyBroadException
        try:
            if response_data := ctx.previous_result.response_data:
                # 将提取值放入变量
                actualvalue = self.extract(response_data, jsonpath)
                if actualvalue is not None:
                    logger.info(
                        f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] Json提取成功\n'
                        f'表达式:[ {jsonpath} ]\n'
                        f'变量名:[ {varname} ]\n'
                        f'变量值:[ {actualvalue} ]'
                    )
                else:
                    logger.info(
                        f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] Json提取失败\n'
                        f'表达式:[ {jsonpath} ]\n'
                        f'变量名:[ {varname} ]\n'
                        f'变量值:[ {actualvalue} ]'
                    )
                self.put(ctx, varname, actualvalue)
            # 设置默认值
            elif self.default_value:
                logger.info(
                    f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] Json提取为空，赋予默认值\n'
                    f'变量名:[ {varname} ]\n'
                    f'变量值:[ {self.default_value} ]'
                )
                self.put(ctx, varname, self.default_value)
        except Exception:
            logger.exception('Exception Occurred')
            # 设置默认值
            if self.default_value:
                logger.info(
                    f'线程:[ {ctx.thread_name} ] 请求:[ {ctx.current_sampler.name} ] Json提取异常，赋予默认值\n'
                    f'变量名:[ {jsonpath} ]\n'
                    f'变量值:[ {self.default_value} ]'
                )
                self.put(ctx, jsonpath, self.default_value)

    def extract(self, json, jsonpath):
        """提取jsonpath"""
        try:
            value = json_path(json, jsonpath, self.list_random)
        except JSONDecodeError:
            value = ''

        if isinstance(value, dict | list):
            return to_json(value)
        if isinstance(value, int | float):
            return str(value)
        if isinstance(value, bool):
            return 'true' if value else 'false'

        return value if value is not None else 'null'

    def put(self, ctx, key, value):
        if self.variable_scope == 'LOCAL':
            ctx.variables.put(key, value)
        elif self.variable_scope == 'GLOBAL':
            ctx.properties.put(key, value)
        else:
            raise ValueError('作用域错误')
