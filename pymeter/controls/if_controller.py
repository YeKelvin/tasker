#!/usr/bin python3
# @File    : if_controller.py
# @Time    : 2020/2/29 10:49
# @Author  : Kelvin.Ye
from typing import Final

from loguru import logger

from pymeter.controls.generic_controller import GenericController
from pymeter.tools.exceptions import NextIsNone
from pymeter.workers.context import ContextService


class IfController(GenericController):

    CONDITION: Final = 'IfController__condition'

    @property
    def condition(self) -> str:
        return self.get_property_as_str(self.CONDITION)

    @property
    def done(self):
        return False

    @done.setter
    def done(self, val: bool):
        self._done = val

    def next(self):
        """@override"""
        # We should only evaluate the condition if it is the first
        # time ( first "iteration" ) we are called.
        # For subsequent calls, we are inside the IfController,
        # so then we just pass the control to the next item inside the if control

        # 非首次时表示if运算为true，获取下一个
        if not self.first:
            return super().next()

        # 逻辑运算
        result = self.evaluate()
        if result is True:
            return super().next()

        # if-result is false, need to re-initialize indexes
        try:
            self.initialize_sub_controllers()
            return self.next_is_null()
        except NextIsNone:
            return None

    def trigger_end_of_loop(self):
        super().initialize_sub_controllers()
        super().trigger_end_of_loop()

    def evaluate(self):
        try:
            ctx = ContextService.get_context()
            condition = self.condition.strip()
            result = eval(condition, None, {'vars': ctx.variables, 'props': ctx.properties})
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] IF逻辑运算\n'
                f'if条件: {condition}\n'
                f'if结果: {result}'
            )
            return result
        except Exception:
            logger.exception('Exception Occurred')
            return False
