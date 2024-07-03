#!/usr/bin python3
# @File    : test_collection.py
# @Time    : 2023-06-27 14:41:45
# @Author  : Kelvin.Ye
from typing import Final

from pymeter.collections.collection import Collection


class TestCollection(Collection):

    # 运行策略
    RUNNING_STRATEGY: Final = 'TestCollection__running_strategy'

    # 顺序执行 worker
    SEQUENTIAL: Final = 'TestCollection__sequential'

    # 延迟启动 worker ，单位ms
    DELAY: Final = 'TestCollection__delay'

    @property
    def sequential(self):
        return self.get_property_as_bool(self.SEQUENTIAL)

    @property
    def delay(self):
        return self.get_property_as_int(self.DELAY)
