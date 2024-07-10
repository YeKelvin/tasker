#!/usr/bin python3
# @File    : function.py
# @Time    : 2020/1/19 17:05
# @Author  : Kelvin.Ye
from pymeter.tools.exceptions import InvalidVariableError
from pymeter.workers.context import ContextService


class Function:

    REF_KEY = '__reference_key'

    @property
    def variables(self):
        return ContextService.get_context().variables

    @property
    def previous_result(self):
        return ContextService.get_context().previous_result

    @property
    def current_sampler(self):
        return ContextService.get_context().current_sampler

    def execute(self):
        raise NotImplementedError

    def set_parameters(self, params: list):
        raise NotImplementedError

    def check_parameter_count(self, params: list, count: int) -> None:
        num = len(params)
        if num != count:
            raise InvalidVariableError(
                f'{self.REF_KEY} called with wrong number of parameters. Actual: {num}. Expected: {count}.'
            )

    def check_parameter_min(self, params: list, minimum: int) -> None:
        num = len(params)
        if num < minimum:
            raise InvalidVariableError(
                f'{self.REF_KEY} called with wrong number of parameters. Actual: {num}. Expected at least: {minimum}.'
            )

    def check_parameter_max(self, params: list, maximum: int = None) -> None:
        num = len(params)
        if num > maximum:
            raise InvalidVariableError(
                f'{self.REF_KEY} called with wrong number of parameters. Actual: {num}. Expected at most: {maximum}.'
            )
