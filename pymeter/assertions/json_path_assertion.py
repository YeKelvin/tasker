#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : json_assertion.py.py
# @Time    : 2020/2/17 16:39
# @Author  : Kelvin.Ye
from pymeter.assertions.assertion import Assertion
from pymeter.assertions.assertion import AssertionResult
from pymeter.elements.element import TestElement
from pymeter.samplers.sample_result import SampleResult
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class JsonPathAssertion(Assertion, TestElement):
    JSONPATH = 'JsonPathAssertion__jsonpath'
    EXPECTED_VALUE = 'JsonPathAssertion__expected_value'

    @property
    def jsonpath(self):
        return self.get_property_as_str(self.JSONPATH)

    @property
    def expected_value(self):
        return self.get_property_as_str(self.EXPECTED_VALUE)

    def do_assert(self, json_str):
        pass

    def get_result(self, result: SampleResult) -> AssertionResult:
        assertion_result = AssertionResult(self.name)
        response_data = result.response_data

        return assertion_result