#!/usr/bin python3
# @File    : test_element.py
# @Time    : 2020/1/24 23:48
# @Author  : Kelvin.Ye
from collections import deque
from collections.abc import Iterable
from copy import deepcopy

from pymeter.elements.property import BasicProperty
from pymeter.elements.property import MultiProperty
from pymeter.elements.property import NoneProperty
from pymeter.elements.property import ObjectProperty
from pymeter.elements.property import PyMeterProperty
from pymeter.elements.property import TestElementProperty
from pymeter.tools.exceptions import InvalidPropertyException


class TestElement:

    # 组件名称
    NAME = 'TestElement__name'

    # 组件备注
    DESC = 'TestElement__desc'

    def __init__(self, name: str = None):
        self._running_version = False
        self.level = None
        self.context = None
        self.properties = {}      # type: dict[str, PyMeterProperty]
        self.temporarys = None    # type: deque | None
        name and self.set_property(self.NAME, name)

    @property
    def name(self) -> str:
        return self.get_property_as_str(self.NAME)

    @property
    def desc(self) -> str:
        return self.get_property_as_str(self.DESC)

    @name.setter
    def name(self, val: str) -> None:
        self.set_property(self.NAME, val)

    @desc.setter
    def desc(self, val: str) -> None:
        self.set_property(self.DESC, val)

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running):
        self._running_version = running
        for prop in self.property_iterator():
            prop.running_version = running

    def recover_running_version(self) -> None:
        for prop in list(self.properties.values()):
            if self.is_temporary(prop):
                self.remove_property(prop.name)
                self.remove_temporary(prop)
            else:
                prop.recover_running_version(self)

        self.clear_temporary()

    def set_property(self, key: str, value: any) -> None:
        if not key:
            raise InvalidPropertyException('键名不能为空')

        if self.running_version and not isinstance(prop := self.get_property(key), NoneProperty):
            prop.value = value
            return

        if (self.running_version and isinstance(self.get_property(key), NoneProperty)) or (not self.running_version):
            if isinstance(value, TestElement):
                self.add_property(key, TestElementProperty(key, value))
            elif isinstance(value, object):
                self.add_property(key, ObjectProperty(key, value))
            elif value is None:
                self.add_property(key, NoneProperty(key))
            else:
                self.add_property(key, BasicProperty(key, value))

    def add_property(self, key: str, prop: PyMeterProperty) -> None:
        if self.running_version:
            self.set_temporary(prop)
        else:
            self.remove_temporary(prop)

        self.properties[key] = prop

    def get_property(self, key: str, default: any = None) -> PyMeterProperty:
        if default:
            return self.properties.get(key, default)

        return self.properties.get(key, NoneProperty(key))

    def get_property_as_str(self, key: str, default: str = None) -> str:
        prop = self.get_property(key)
        return default if prop is None or isinstance(prop, NoneProperty) else prop.get_str()

    def get_property_as_int(self, key: str, default: int = None) -> int:
        prop = self.get_property(key)
        return default if prop is None or isinstance(prop, NoneProperty) else prop.get_int()

    def get_property_as_float(self, key: str, default: float = None) -> float:
        prop = self.get_property(key)
        return default if prop is None or isinstance(prop, NoneProperty) else prop.get_float()

    def get_property_as_bool(self, key: str, default: bool = None) -> bool:
        prop = self.get_property(key)
        return default if prop is None or isinstance(prop, NoneProperty) else prop.get_bool()

    def remove_property(self, key) -> None:
        self.properties.pop(key)

    def add_test_element(self, element: 'TestElement') -> None:
        """Merge in"""
        for key, value in element.items():
            self.add_property(key, value)

    def clear_test_element_children(self) -> None:
        """清除所有使用 #add_test_element(TestElement) 方法合并的元素的属性"""
        ...

    def list(self):
        return list(self.properties.keys())

    def items(self):
        return self.properties.items()

    def property_iterator(self) -> Iterable[PyMeterProperty]:
        return self.properties.values()

    def clone(self) -> 'TestElement':
        """克隆副本，如果子类有 property 以外的属性，请在子类重写该方法"""
        cloned_element = self.__class__()  # 实例化一个新的对象
        cloned_element.level = self.level
        cloned_element.properties = deepcopy(self.properties)
        cloned_element.running_version = self.running_version
        return cloned_element

    def clear(self) -> None:
        """清空属性"""
        self.properties.clear()

    def is_temporary(self, prop) -> bool:
        if self.temporarys is None:
            return False
        else:
            return prop in self.temporarys

    def set_temporary(self, prop) -> None:
        if self.temporarys is None:
            self.temporarys = deque()

        self.temporarys.append(prop)
        # 虽然 TestElementProperty 正在实现 MultiProperty，但它的工作方式不同。
        # 它不会像 MultiProperty 那样一一合并内部属性。
        # 因此我们不能将 TestElementProperty 的封闭属性标记为临时。
        if isinstance(prop, MultiProperty) and not isinstance(prop, TestElementProperty):
            for prop in prop.iterator():
                self.set_temporary(prop)

    def remove_temporary(self, prop):
        if self.temporarys is not None:
            self.temporarys.remove(prop)

    def clear_temporary(self):
        if self.temporarys is not None:
            self.temporarys.clear()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"<'{self.name}' ({type(self).__name__} @ {id(self)})>"


class ConfigElement:

    def add_config_element(self, el: 'ConfigElement'):
        raise NotImplementedError


class ConfigTestElement(ConfigElement, TestElement):

    def add_config_element(self, el: ConfigElement):
        raise NotImplementedError
