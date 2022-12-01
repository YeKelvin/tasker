#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : json_path_post_processor.py
# @Time    : 2022/9/27 10:56
# @Author  : Kelvin.Ye
import traceback
from typing import Final

from pymeter.groups.context import ContextService
from pymeter.processors.post import PostProcessor
from pymeter.utils.json_util import json_path
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class JsonPathPostProcessor(PostProcessor):

    # 变量名称
    VARIABLE_NAME: Final = 'JsonPathPostProcessor__variable_name'

    # JsonPath 表达式
    JSONPATH: Final = 'JsonPathPostProcessor__jsonpath'

    # 列表随机
    LIST_RANDOM: Final = 'JsonPathPostProcessor__list_random'

    # 默认值
    DEFAULT_VALUE: Final = 'JsonPathPostProcessor__default_value'

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
            log.warning(f'元素: {self.name}, 警告: 变量名称为空，请修改写后重试')
            return

        if not jsonpath:
            log.warning(f'元素: {self.name}, 警告: JsonPath为空，请修改写后重试')
            return

        # noinspection PyBroadException
        try:
            if response_data := ctx.previous_result.response_data:
                # 将提取值放入变量
                actualvalue = json_path(response_data, jsonpath, self.list_random)
                ctx.variables.put(varname, actualvalue)
                if actualvalue is not None:
                    log.info(f'Json提取成功，jsonpath:[ {jsonpath} ]，变量名[ {varname} ]，变量值:[ {actualvalue} ]')
                else:
                    log.info(
                        f'Json提取失败，请检查jsonpath是否正确，'
                        f'jsonpath:[ {jsonpath} ]，变量名[ {varname} ]，变量值:[ {actualvalue} ]'
                    )
            # 设置默认值
            elif self.default_value:
                ctx.variables.put(varname, self.default_value)
                log.info(f'响应结果为空，赋予默认值，变量名[ {varname} ]，变量值:[ {self.default_value} ]')
        except Exception:
            log.error(traceback.format_exc())
            # 设置默认值
            if self.default_value:
                ctx.variables.put(jsonpath, self.default_value)
                log.info(f'Json提取异常，赋予默认值，变量名[ {jsonpath} ]，变量值:[ {self.default_value} ]')