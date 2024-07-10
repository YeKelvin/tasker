#!/usr/bin python3
# @File    : exception.py
# @Time    : 2019/3/15 10:48
# @Author  : Kelvin.Ye


class InvalidScriptError(Exception):
    ...


class InvalidVariableError(Exception):
    ...


class InvalidPropertyError(Exception):
    ...


class EngineError(Exception):
    ...


class ScriptParseError(Exception):
    ...


class NodeParseError(Exception):
    ...


class NextIsNone(Exception):
    ...


class StopTestWorkerError(Exception):
    ...


class StopTestError(Exception):
    ...


class StopTestNowError(Exception):
    ...


class UnsupportedOperationError(Exception):
    ...


class HTTPHeaderDuplicateError(Exception):
    ...


class HTTPCookieDuplicateError(Exception):
    ...


class FunctionError(Exception):
    ...

class UserInterruptedError(Exception):
    ...


class ForbiddenPythonError(Exception):
    ...
