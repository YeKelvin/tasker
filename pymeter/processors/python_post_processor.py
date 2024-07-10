#!/usr/bin python3
# @File    : python_post.py
# @Time    : 2020/2/17 16:29
# @Author  : Kelvin.Ye
from typing import Final

from loguru import logger

from pymeter.processors.post import PostProcessor
from pymeter.tools.exceptions import ForbiddenPythonError
from pymeter.tools.python_code_snippets import DEFAULT_LOCAL_IMPORT_MODULE
from pymeter.tools.python_code_snippets import INDENT
from pymeter.workers.context import ContextService


class PythonPostProcessor(PostProcessor):

    # 脚本内容
    SCRIPT: Final = 'PythonPostProcessor__script'

    @property
    def script(self) -> str:
        return self.get_property_as_str(self.SCRIPT)

    @property
    def raw_function(self):
        func = [
            'def function(log, ctx, args, vars, props, result, sampler):\n',
            DEFAULT_LOCAL_IMPORT_MODULE
        ]

        content = self.script
        if not content or content.isspace():  # 脚本内容为空则生成空函数
            func.append(f'{INDENT}...\n')
        else:
            lines = content.split('\n')
            func.extend(f'{INDENT}{line}\n' for line in lines)
        func.append('self.dynamic_function = function')
        return ''.join(func)

    def process(self) -> None:
        try:
            # 获取代码
            code = self.raw_function

            # 禁止使用os模块
            if 'import os' in code:
                raise ForbiddenPythonError()

            # 动态生成函数
            exec(self.raw_function, {'self': self}, {'self': self})

            # 执行函数
            ctx = ContextService.get_context()
            self.dynamic_function(  # noqa
                log=logger,
                ctx=ctx,
                args=ctx.arguments,
                vars=ctx.variables,
                props=ctx.properties,
                result=ctx.previous_result,
                sampler=ctx.current_sampler
            )
        except ForbiddenPythonError:
            logger.error(f'线程:[ {ContextService.get_context().thread_name} ] 脚本:[ {self.name} ] 禁止使用 os 模块')
        except Exception:
            logger.exception('Exception Occurred')
