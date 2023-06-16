#!/usr/bin python3
# @File    : context
# @Time    : 2019/3/15 9:39
# @Author  : Kelvin.Ye
from gevent.local import local as CoroutineLocal

from pymeter.utils import time_util
from pymeter.workers.variables import Variables


class ThreadContext:

    @property
    def properties(self) -> dict:
        return getattr(self.engine, 'properties', {})

    @property
    def extra(self) -> dict:
        return getattr(self.engine, 'extra', {})

    def __init__(self):
        self.variables = Variables()
        self.engine = None
        self.worker = None
        self.thread = None
        self.thread_number = None
        self.thread_name = None
        self.current_sampler = None
        self.previous_sampler = None
        self.previous_result = None

    def clear(self):
        self.variables = None
        self.worker = None
        self.thread = None
        self.thread_number = None
        self.current_sampler = None
        self.previous_sampler = None
        self.previous_result = None

    def set_current_sampler(self, sampler):
        self.previous_sampler = self.current_sampler
        self.current_sampler = sampler

    def set_previous_result(self, result):
        self.previous_result = result


class ContextService:

    local = CoroutineLocal()

    @classmethod
    def get_context(cls) -> ThreadContext:
        if not hasattr(cls.local, 'thread_context'):
            setattr(cls.local, 'thread_context', ThreadContext())
        return cls.local.thread_context

    @classmethod
    def remove_context(cls) -> None:
        if hasattr(cls.local, 'thread_context'):
            del cls.local.thread_context

    @classmethod
    def replace_context(cls, ctx) -> None:
        setattr(cls.local, 'thread_context', ctx)

    @classmethod
    def start_test(cls):
        engine_ctx = cls.get_context().engine.context
        if engine_ctx.test_start == 0:
            engine_ctx.number_of_threads_actived = 0
            engine_ctx.test_start = time_util.timestamp_now()
            cls.get_context().properties.put('TESTSTART.MS', engine_ctx.test_start)

    @classmethod
    def end_test(cls):
        engine_ctx = cls.get_context().engine.context
        engine_ctx.test_start = 0

    @classmethod
    def incr_number_of_threads(cls):
        """增加活动线程的数量"""
        engine_ctx = cls.get_context().engine.context
        engine_ctx.number_of_threads_actived += 1
        engine_ctx.number_of_threads_started += 1

    @classmethod
    def decr_number_of_threads(cls):
        """减少活动线程的数量"""
        engine_ctx = cls.get_context().engine.context
        engine_ctx.number_of_threads_actived -= 1
        engine_ctx.number_of_threads_finished += 1

    @classmethod
    def add_total_threads(cls, worker_number):
        engine_ctx = cls.get_context().engine.context
        engine_ctx.total_threads += worker_number

    @classmethod
    def clear_total_threads(cls):
        engine_ctx = cls.get_context().engine.context
        engine_ctx.total_threads = 0
        engine_ctx.number_of_threads_started = 0
        engine_ctx.number_of_threads_finished = 0