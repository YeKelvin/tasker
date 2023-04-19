#!/usr/bin python3
# @File    : sample_package
# @Time    : 2020/2/27 15:41
# @Author  : Kelvin.Ye
from typing import Sequence

from loguru import logger

from pymeter.assertions.assertion import Assertion
from pymeter.controls.controller import Controller
from pymeter.elements.element import ConfigElement
from pymeter.engine.interface import SampleListener
from pymeter.engine.interface import TransactionListener
from pymeter.processors.post import PostProcessor
from pymeter.processors.pre import PreProcessor
from pymeter.timers.timer import Timer


class SamplePackage:

    def __init__(
        self,
        configs: Sequence[ConfigElement] = None,
        listeners: Sequence[SampleListener] = None,
        trans_listeners: Sequence[TransactionListener] = None,
        timers: Sequence[Timer] = None,
        assertions: Sequence[Assertion] = None,
        post_processors: Sequence[PostProcessor] = None,
        pre_processors: Sequence[PreProcessor] = None,
        controllers: Sequence[Controller] = None
    ):
        self.configs = configs if configs is not None else []
        self.listeners = listeners if listeners is not None else []
        self.trans_listeners = trans_listeners if trans_listeners is not None else []
        self.timers = timers if timers is not None else []
        self.assertions = assertions if assertions is not None else []
        self.post_processors = post_processors if post_processors is not None else []
        self.pre_processors = pre_processors if pre_processors is not None else []
        self.controllers = controllers if controllers is not None else []

        self.sampler = None

    def set_running_version(self, running) -> None:
        logger.debug(f'package:[ {self.sampler} ] set running:[ {running} ]')
        for el in self.configs:
            el.running_version = running
        for el in self.pre_processors:
            el.running_version = running
        for el in self.listeners:
            el.running_version = running
        for el in self.post_processors:
            el.running_version = running
        for el in self.assertions:
            el.running_version = running
        for el in self.timers:
            el.running_version = running
        for el in self.controllers:
            el.running_version = running
        self.sampler.running_version = running

    def recover_running_version(self) -> None:
        logger.debug(f'package:[ {self.sampler} ] recover running')
        for el in self.configs:
            el.recover_running_version()
        for el in self.pre_processors:
            el.recover_running_version()
        for el in self.listeners:
            el.recover_running_version()
        for el in self.post_processors:
            el.recover_running_version()
        for el in self.assertions:
            el.recover_running_version()
        for el in self.timers:
            el.recover_running_version()
        for el in self.controllers:
            el.recover_running_version()
        self.sampler.recover_running_version()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str({
            'sampler': self.sampler,
            'configs': list(self.configs),
            'controllers': list(self.controllers),
            'listeners': list(self.listeners),
            'transactionListeners': list(self.trans_listeners),
            'timers': list(self.timers),
            'assertions': list(self.assertions),
            'pres': list(self.pre_processors),
            'posts': list(self.post_processors)
        })
