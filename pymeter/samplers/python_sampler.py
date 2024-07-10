#!/usr/bin python3
# @File    : python_sampler.py
# @Time    : 2020/2/16 21:29
# @Author  : Kelvin.Ye
import traceback

from typing import Final

from loguru import logger

from pymeter.samplers.sample_result import SampleResult
from pymeter.samplers.sampler import Sampler
from pymeter.tools.exceptions import ForbiddenPythonError
from pymeter.tools.python_code_snippets import DEFAULT_LOCAL_IMPORT_MODULE
from pymeter.tools.python_code_snippets import INDENT
from pymeter.tools.python_security import check_security
from pymeter.workers.context import ContextService


class PythonSampler(Sampler):

    # 请求类型
    REQUEST_TYPE: Final = 'PYTHON'

    # 脚本内容
    SCRIPT: Final = 'PythonSampler__script'

    # 运行策略
    RUNNING_STRATEGY: Final = 'PythonSampler__running_strategy'

    @property
    def script(self) -> str:
        return self.get_property_as_str(self.SCRIPT)

    @property
    def raw_function(self):
        func = ['def function(log, ctx, vars, props, prev, result):\n' + DEFAULT_LOCAL_IMPORT_MODULE]

        content = self.script
        if not content or content.isspace():  # 脚本内容为空则生成空函数
            func.append(f'{INDENT}...\n')
        else:
            lines = content.split('\n')
            func.extend(f'{INDENT}{line}\n' for line in lines)
        func.append('self.dynamic_function = function')
        return ''.join(func)

    def sample(self) -> SampleResult:
        result = SampleResult()
        result.sample_name = self.name
        result.request_data = self.script
        result.sample_start()

        try:
            # 获取代码
            code = self.raw_function

            # 校验是否包含不允许使用的模块
            check_security(code)

            # 动态生成函数
            exec(code, {'self': self}, {'self': self})

            # 执行函数
            ctx = ContextService.get_context()
            if res := self.dynamic_function(  # noqa
                log=logger,
                ctx=ctx,
                vars=ctx.variables,
                props=ctx.properties,
                prev=ctx.previous_result,
                result=result
            ):
                result.response_data = res if isinstance(res, str) else str(res)
        except ForbiddenPythonError as m:
            result.success = False
            result.response_data = f'错误: 禁止使用 {m} 模块'
        except Exception:
            result.success = False
            result.response_data = traceback.format_exc()
        finally:
            result.sample_end()

        return result
