#!/usr/bin python3
# @File    : foreach_controller.py
# @Time    : 2021/11/12 14:42
# @Author  : Kelvin.Ye
from collections.abc import Iterable
from typing import Final

import gevent

from loguru import logger

from pymeter.controls.controller import IteratingController
from pymeter.controls.generic_controller import GenericController


class ForeachController(GenericController, IteratingController):

    # 遍历项的变量名称，一个或多个变量名，以逗号分隔
    ITERATION_TARGET: Final = 'ForeachController__target'

    # 可迭代对象: list | dict | iterable | code
    ITERABLE_OBJ: Final = 'ForeachController__iterable'

    # 数组来源: VARIABLE | CUSTOM
    DATA_SOURCE: Final = 'ForeachController__source'

    # 延迟迭代，单位毫秒
    DELAY: Final = 'ForeachController__delay'

    @property
    def iteration_target(self) -> str:
        return self.get_property_as_str(self.ITERATION_TARGET)

    @property
    def iterable_obj(self) -> str:
        return self.get_property_as_str(self.ITERABLE_OBJ)

    @property
    def data_source(self) -> str:
        return self.get_property_as_str(self.DATA_SOURCE)

    @property
    def delay(self) -> int:
        return self.get_property_as_int(self.DELAY)

    @property
    def iter_count(self) -> int:
        return self._loop_count + 1

    @property
    def done(self) -> bool:
        if self._loop_count >= self._last_index:
            return True

        return self._done

    @done.setter
    def done(self, val: bool):
        self._done = val

    def __init__(self):
        super().__init__()

        self._loop_count: int = 0
        self._break_loop: bool = False

        self._iterable_obj: Iterable = None
        self._iter_index: int = 0
        self._last_index: int = 0

        self._target: list = None
        self._target_size: int = None

    def init_foreach(self):
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 初始化遍历数据')
        # 分割迭代项的变量
        self._target = self.iteration_target.split(',')
        # 缓存变量个数
        self._target_size = len(self._target)

        # 移除目标变量首尾的空格
        for i, key in enumerate(self._target):
            self._target[i] = key.strip()

        # 获取迭代对象
        if self.data_source == 'VARIABLE':
            self._iterable_obj = self.ctx.variables.get(
                self.iterable_obj,
                self.ctx.properties.get(self.iterable_obj)
            )
        elif self.data_source == 'CUSTOM':
            self.init_iterable_object(self.iterable_obj)
        else:
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 对象类型:[ {self.data_source} ] '
                f'不支持数组来源，无法遍历'
            )
            return True  # 表示异常 error=true

        if self._iterable_obj is None:
            logger.info(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 迭代对象为None，无法遍历')
            return True  # 表示异常 error=true

        if isinstance(self._iterable_obj, str):
            self.init_iterable_object(self._iterable_obj)

        # 判断是否为可迭代的对象
        if not isinstance(self._iterable_obj, Iterable):
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 迭代对象:[ {self._iterable_obj} ] '
                f'不是可迭代的对象，无法遍历'
            )
            return True  # 表示异常 error=true

        # 存储最后一个索引
        self._last_index = len(self._iterable_obj)
        if self._last_index == 0:
            logger.info(
                f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 迭代对象:[ {self._iterable_obj} ] '
                f'迭代对象为空，无法遍历'
            )
            return True  # 表示异常 error=true

        # 字典处理
        if isinstance(self._iterable_obj, dict):
            self._iterable_obj = list(self._iterable_obj.items())

        logger.info(
            f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始迭代数据\n'
            f'迭代数据={self._iterable_obj}'
        )

    def init_iterable_object(self, stmt):
        exec(f'self._iterable_obj = ( {stmt} )', None, {'self': self})

    def iterate_data(self):
        # 获取当前迭代项
        item = self._iterable_obj[self._iter_index]
        logger.info(
            f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始第 {self._iter_index + 1} 次迭代\n'
            f'当前迭代项={item}'
        )
        # 设置数据
        if self._target_size > 1 and isinstance(item, Iterable):
            for i, target in enumerate(self._target):
                self.ctx.variables.put(target, item[i])
        else:
            target = self._target[0]
            self.ctx.variables.put(self._target[0], item)
        # 迭代索引 +1
        self._iter_index = self._iter_index + 1

    def next(self):
        """@override"""
        self.update_iteration_index(self.name, self._loop_count)
        try:
            error = False
            # 初始化迭代数据
            if self.first and self.init_foreach():
                error = True

            # 判断迭代是否错误或已完成
            if error or self.end_of_loop():
                self.re_initialize()
                self.reset_break_loop()
                return

            # 设置当前迭代的数据
            if (self._loop_count + 1) > self._iter_index:
                self.iterate_data()

            nsampler = super().next()
            if nsampler and self.delay:
                logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 间隔:[ {self.delay}ms ]')
                gevent.sleep(float(self.delay / 1000))

            return nsampler
        except Exception:
            logger.exception('Exception Occurred')
        finally:
            self.update_iteration_index(self.name, self._loop_count)

    def trigger_end_of_loop(self):
        """@override"""
        super().trigger_end_of_loop()
        self.reset_loop_count()

    def end_of_loop(self) -> bool:
        """判断循环是否结束"""
        return self._break_loop or (self._loop_count >= self._last_index)

    def next_is_null(self):
        """@override"""
        self.re_initialize()
        if self.end_of_loop():
            self.reset_break_loop()
            self.reset_loop_count()
            return None
        return self.next()

    def increment_loop_count(self):
        self._loop_count += 1

    def reset_loop_count(self):
        self._loop_count = 0
        self._iter_index = 0

    def re_initialize(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 重新初始化控制器')
        self.first = True
        self.reset_current()
        self.increment_loop_count()
        self.recover_running_version()

    def reset_break_loop(self):
        if self._break_loop:
            self._break_loop = False

    def start_next_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 开始下一个迭代')
        self.re_initialize()

    def break_loop(self):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 中止迭代')
        self._break_loop = True
        self.first = True
        self.reset_current()
        self.reset_loop_count()
        self.recover_running_version()

    def iteration_start(self, source, iter_count):
        """@override"""
        self.re_initialize()
        self.reset_loop_count()
