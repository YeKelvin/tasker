#!/usr/bin python3
# @File    : sampler.py
# @Time    : 2020/1/24 23:47
# @Author  : Kelvin.Ye
from pymeter.elements.element import TestElement


class Sampler(TestElement):

    # 元素配置
    CONFIG = 'Sampler__config'

    @property
    def config(self):
        default = {
            'components': {
                # 类型: [1前置，2后置，3断言]，级别: [0空间，1集合，2工作线程，3控制器]
                'include': {"type": [], "level": []},
                'exclude': {"type": [], "level": []},
                # 倒序执行: [1前置，2后置，3断言]
                'reverse': []
            }
        }
        _config_ = self.get_property(self.CONFIG).get_obj()
        return _config_ or default

    def sample(self):
        raise NotImplementedError
