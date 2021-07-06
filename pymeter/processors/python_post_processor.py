#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : python_post.py
# @Time    : 2020/2/17 16:29
# @Author  : Kelvin.Ye
from typing import Final

from pymeter.elements.element import TestElement
from pymeter.processors.post import PostProcessor
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class PythonPostProcessor(PostProcessor, TestElement):
    SOURCE: Final = 'PythonPostProcessor__source'

    def process(self) -> None:
        exec(self.get_property_as_str(self.SOURCE), {}, locals())