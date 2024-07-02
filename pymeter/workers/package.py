#!/usr/bin python3
# @File    : sample_package
# @Time    : 2020/2/27 15:41
# @Author  : Kelvin.Ye
from loguru import logger

from pymeter.assertions.assertion import Assertion
from pymeter.controls.controller import Controller
from pymeter.elements.element import ConfigElement
from pymeter.engines.interface import SampleListener
from pymeter.engines.interface import TransactionListener
from pymeter.processors.post import PostProcessor
from pymeter.processors.prev import PrevProcessor
from pymeter.timers.timer import Timer


class SamplePackage:

    def __init__(
        self,
        configs: list[ConfigElement],
        listeners: list[SampleListener],
        controllers: list[Controller],
        trans_listeners: list[TransactionListener],
        prev_processors: list[PrevProcessor],
        post_processors: list[PostProcessor],
        assertions: list[Assertion],
        timers: list[Timer]
    ):
        self.sampler = None
        self.configs = configs
        self.listeners = listeners
        self.controllers = controllers
        self.trans_listeners = trans_listeners
        self.prev_processors = prev_processors
        self.post_processors = post_processors
        self.assertions = assertions
        self.timers = timers


    def done(self):
        self.recover_running_version()

    def set_running_version(self, running: bool) -> None:
        logger.debug(f'取样包:[ {self.sampler} ] 设置running={running}')
        for el in self.configs:
            el.running_version = running
        for el in self.listeners:
            el.running_version = running
        for el in self.controllers:
            el.running_version = running
        for el in self.prev_processors:
            el.running_version = running
        for el in self.post_processors:
            el.running_version = running
        for el in self.assertions:
            el.running_version = running
        for el in self.timers:
            el.running_version = running
        self.sampler.running_version = running

    def recover_running_version(self) -> None:
        logger.debug(f'取样包:[ {self.sampler} ] 恢复运行版本')
        for el in self.configs:
            el.recover_running_version()
        for el in self.listeners:
            el.recover_running_version()
        for el in self.controllers:
            el.recover_running_version()
        for el in self.prev_processors:
            el.recover_running_version()
        for el in self.post_processors:
            el.recover_running_version()
        for el in self.assertions:
            el.recover_running_version()
        for el in self.timers:
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
            'prevs': list(self.prev_processors),
            'posts': list(self.post_processors),
            'assertions': list(self.assertions)
        })
