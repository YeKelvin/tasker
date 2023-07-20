#!/usr/bin python3
# @File    : replacer.py
# @Time    : 2021/5/30 17:11
# @Author  : Kelvin.Ye
from typing import List

from loguru import logger

from pymeter.elements.property import BasicProperty
from pymeter.elements.property import FunctionProperty
from pymeter.functions import Function
from pymeter.tools.exceptions import InvalidVariableException
from pymeter.utils.class_finder import ClassFinder
from pymeter.workers.context import ContextService


class SimpleVariable:

    def __init__(self, name: str = None):
        self.name = name

    @property
    def variables(self):
        return ContextService.get_context().variables

    @property
    def properties(self):
        return ContextService.get_context().properties

    @property
    def value(self):
        variables = self.variables or {}
        properties = self.properties or {}

        if self.name in variables:
            return variables.get(self.name)
        elif self.name in properties:
            return properties.get(self.name)
        else:
            logger.debug(f'变量:[ {self.name} ] 找不到变量，返回原始字符')
            return '${' + self.name + '}'


class CompoundVariable:
    """复合变量"""
    functions = {}

    def __init__(self, parameters: str = None):
        if not self.functions:
            self.__init_functions__()

        # 原始参数
        self.raw_parameters = None
        # 是否存在函数
        self.has_function = False
        # 动态函数
        self.dynamic = False
        # 已编译完成的组件
        self.compiled_components = []
        # 结果缓存
        self.permanent_results = None

        if parameters:
            self.set_parameters(parameters)

    def execute(self):
        """执行函数"""
        # 非动态函数时，优先返回结果缓存
        if not self.dynamic and self.permanent_results:
            logger.debug('返回缓存结果')
            return self.permanent_results

        if not self.compiled_components:
            logger.debug('已编译组件为空')
            return ''

        results = []
        # noinspection PyBroadException
        try:
            for item in self.compiled_components:
                if isinstance(item, Function):
                    result = item.execute()
                    logger.debug(f'函数:[ {item.REF_KEY} ] 执行结果:[ {result} ]')
                    results.append(result)
                elif isinstance(item, SimpleVariable):
                    value = str(item.value)
                    logger.debug(f'变量:[ {item.name} ] 实际值:[ {value} ]')
                    results.append(value)
                else:
                    results.append(item)
        except Exception as e:
            results.append(str(e))
            logger.exception('Exception Occurred')
        finally:
            results_str = ''.join(results)

        # 非动态函数时，缓存执行结果
        if not self.dynamic:
            logger.debug('非动态函数, 缓存执行结果')
            self.permanent_results = results_str

        return results_str

    def set_parameters(self, parameters: str):
        """设置函数入参"""
        self.raw_parameters = parameters
        if not parameters:
            return

        # 编译参数
        self.compiled_components = FunctionParser.compile_string(parameters)

        if len(self.compiled_components) > 1 or not isinstance(self.compiled_components[0], str):
            # logger.debug('已编译字符串中存在函数')
            self.has_function = True

        # 在首次执行时进行计算和缓存
        self.permanent_results = None

        for item in self.compiled_components:
            if isinstance(item, (Function, SimpleVariable)):
                # logger.debug('设置为动态函数')
                self.dynamic = True
                break

    @classmethod
    def get_named_function(cls, func_name):
        """根据函数名称获取函数对象"""
        if func_name in cls.functions:
            return cls.functions[func_name]()
        else:
            return SimpleVariable(func_name)

    @classmethod
    def __init_functions__(cls):
        if cls.functions:
            return

        classes = ClassFinder.find_subclasses(Function)
        for clazz in classes.values():
            if reference_key := clazz.REF_KEY:
                cls.functions[reference_key] = clazz


class StringReader:

    def __init__(self, string: str):
        self.raw = string
        self.__iter: iter = string.__iter__()

    @property
    def next(self) -> str or None:
        try:
            return self.__iter.__next__()
        except StopIteration:
            return None

    def reset(self) -> None:
        self.__iter = self.raw.__iter__()


class FunctionParser:

    @staticmethod
    def compile_string(source: str) -> List:
        reader = StringReader(source)
        result = []
        buffer = []
        previous = ''
        # logger.debug(f'start compiling str, source:[ {source} ]')
        while True:
            current = reader.next
            if current is None:  # end of reader
                # logger.debug('end of reader')
                break
            if current == '\\':  # 匹配 "\" 转义符
                previous = current
                current = reader.next
                if current is None:  # end of reader
                    # logger.debug('end of reader')
                    break
                # 保留 "\"，除非当前字符是 "$" 或 "\"
                # 注意：此方法用于解析函数参数，因此必须将 "，" 视为特殊的字符
                if current != '$' and current != ',' and current[0] != '\\':
                    buffer.append(previous)
                previous = ''
                buffer.append(current)
            elif current == '{' and previous == '$':  # 匹配 "${" 占位符前缀
                # logger.debug('found a "${"')
                buffer = buffer[:-1]
                if len(buffer) > 0:  # 保存 "${" 占位符前的字符串
                    before_placeholder_str = ''.join(buffer)
                    # logger.debug(f'save the string before the placeholder: {before_placeholder_str}')
                    result.append(before_placeholder_str)
                    buffer.clear()
                result.append(FunctionParser.__make_function(reader))
                previous = ''
            else:
                buffer.append(current)
                previous = current

        if len(buffer) > 0:
            result.append(''.join(buffer))

        if not result:
            result.append('')

        return result

    @staticmethod
    def __make_function(reader: StringReader) -> Function or str:
        buffer = []
        previous = ''
        while True:
            current = reader.next
            if current is None:  # end of reader
                # logger.debug('end of reader')
                break
            if current == '\\':
                current = reader.next
                if current is None:  # end of reader
                    # logger.debug('end of reader')
                    break
                previous = ''
                buffer.append(current)
            elif current == '(' and previous != '':
                func_name = ''.join(buffer)
                # logger.debug(f'function reference key: {func_name}')
                function = CompoundVariable.get_named_function(func_name)
                if isinstance(function, Function):
                    function.set_parameters(FunctionParser.__parse_params(reader))
                    current = reader.next
                    if current is None or current != '}':
                        raise InvalidVariableException(f'expected }} after {func_name} function call in {reader.raw}')
                    return function
                else:  # 函数不存在，按普通字符处理
                    buffer.append(current)
            elif current == '}':  # 变量 或者没有参数的函数
                func_name = ''.join(buffer)
                # logger.debug(f'function reference key:[ {func_name} ]')
                function = CompoundVariable.get_named_function(func_name)
                if isinstance(function, Function):  # 确保调用 set_parameters()
                    function.set_parameters([])
                buffer.clear()
                return function
            else:
                buffer.append(current)
                previous = current

        str_buffer = ''.join(buffer)
        logger.warning(f'may be invalid function string: {str_buffer}')
        return str_buffer

    @staticmethod
    def __parse_params(reader: StringReader) -> List[CompoundVariable]: # sourcery skip: low-code-quality
        result = []
        buffer = []
        previous = ''
        function_recursion = 0
        parent_recursion = 0
        while True:
            current = reader.next
            if current is None:  # end of reader
                # logger.debug('end of reader')
                break
            if current == '\\':
                buffer.append(current)  # Store the \
                current = reader.next
                if current is None:  # end of reader
                    # logger.debug('end of reader')
                    break
                previous = ''
                buffer.append(current)
            elif current == ',' and function_recursion == 0:
                param_str = ''.join(buffer)
                # logger.debug(f'parameter str: {param_str}')
                param = CompoundVariable(param_str)
                buffer.clear()
                result.append(param)
            elif current == ')' and function_recursion == 0 and parent_recursion == 0:
                # 检测 function name，防止生成空字符串作为参数
                if not buffer and not result:
                    return result
                # 正常退出
                param_str = ''.join(buffer)
                # logger.debug(f'raw parameter: {param_str}')
                param = CompoundVariable(param_str)
                buffer.clear()
                result.append(param)
                return result
            elif current == '{' and previous == '$':
                buffer.append(current)
                previous = current
                function_recursion += function_recursion
            elif current == '}' and function_recursion > 0:
                buffer.append(current)
                previous = current
                function_recursion -= function_recursion
            elif current == ')' and function_recursion == 0 and parent_recursion > 0:
                buffer.append(current)
                previous = current
                parent_recursion -= parent_recursion
            elif current[0] == '(' and function_recursion == 0:
                buffer.append(current)
                previous = current[0]
                parent_recursion += parent_recursion
            else:
                buffer.append(current)
                previous = current

        # 退出，未匹配到参数列表结束符 ")"
        str_buffer = ''.join(buffer)
        logger.warning(f'may be invalid function string: {str_buffer}')
        var = CompoundVariable()
        var.set_parameters(str_buffer)
        result.append(var)
        return result


class ValueReplacer:

    @staticmethod
    def replace_values(key: str, source: str) -> BasicProperty:
        master_function = CompoundVariable()
        master_function.set_parameters(source)
        if master_function.has_function:
            return FunctionProperty(key, master_function)
        return BasicProperty(key, source)