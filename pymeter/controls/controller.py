#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : controller.py
# @Time    : 2020/2/28 16:01
# @Author  : Kelvin.Ye
from pymeter.elements.element import TestElement
from pymeter.samplers.sampler import Sampler


class Controller(TestElement):

    @property
    def done(self):
        """是否已完成"""
        raise NotImplementedError

    def next(self) -> Sampler:
        """返回下一个Sampler，末尾返回None"""
        raise NotImplementedError

    def initialize(self):
        """在迭代开始时调用以初始化控制器"""
        raise NotImplementedError

    def trigger_end_of_loop(self):
        """在控制器上触发循环结束条件"""
        raise NotImplementedError

    def add_iteration_listener(self):
        raise NotImplementedError

    def remove_iteration_listener(self):
        raise NotImplementedError


class IteratingController:
    """迭代控制器"""

    def start_next_loop(self) -> None:
        """开始下一个迭代"""
        raise NotImplementedError

    def break_loop(self) -> None:
        """中断循环"""
        raise NotImplementedError