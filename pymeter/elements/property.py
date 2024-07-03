#!/usr/bin python3
# @File    : property.py
# @Time    : 2020/2/16 14:16
# @Author  : Kelvin.Ye
from collections.abc import Iterable
from copy import deepcopy

from loguru import logger

from pymeter.workers.context import ContextService


class PyMeterProperty:
    def __init__(self, name: str, value: any = None):
        self.name = name
        self.value = value
        self._running_version = False

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        self._running_version = running

    def get_str(self) -> str:
        raise NotImplementedError

    def get_int(self) -> int:
        raise NotImplementedError

    def get_float(self) -> float:
        raise NotImplementedError

    def get_bool(self) -> bool:
        raise NotImplementedError

    def get_obj(self) -> any:
        raise NotImplementedError

    def recover_running_version(self, owner) -> None:
        raise NotImplementedError


class BasicProperty(PyMeterProperty):

    def __init__(self, name: str, value: str | int | float | bool = None):
        super().__init__(name, value)
        self.saved_value = None

    def get_str(self) -> str:
        return str(self.value)

    def get_int(self) -> int:
        value = self.get_str()
        return int(value) if value else 0

    def get_float(self) -> float:
        value = self.get_str()
        return float(value) if value else 0.00

    def get_bool(self) -> bool:
        value = self.get_str()
        return value.lower() == 'true'

    def get_obj(self) -> object:
        return self.value

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        PyMeterProperty.running_version = running
        self.saved_value = self.value if running else None

    def recover_running_version(self, owner) -> None:
        if self.saved_value is not None:
            self.value = self.saved_value

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()


class NoneProperty(PyMeterProperty):

    def __init__(self, name: str):
        super().__init__(name, None)

    def get_str(self) -> str:
        return ''

    def get_int(self) -> int:
        return 0

    def get_float(self) -> float:
        return 0.00

    def get_bool(self) -> bool:
        return False

    def get_obj(self) -> None:
        return None

    def recover_running_version(self, owner) -> None:
        ...


class ObjectProperty(PyMeterProperty):

    def __init__(self, name: str, value=None):
        super().__init__(name, value)
        self.saved_value = None

    def get_str(self) -> str:
        return str(self.value)

    def get_obj(self) -> object:
        return self.value

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        PyMeterProperty.running_version = running
        self.saved_value = deepcopy(self.value) if running else None

    def recover_running_version(self, owner) -> None:
        if self.saved_value is not None:
            self.value = self.saved_value


class MultiProperty(PyMeterProperty):

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        self._running_version = running
        for prop in self.iterator():
            prop.running_version = running

    def iterator(self) -> Iterable[PyMeterProperty]:
        raise NotImplementedError

    def remove(self, prop: PyMeterProperty):
        raise NotImplementedError

    def recover_running_version_of_subelements(self, owner):  # owner: TestElement
        for prop in self.iterator()[:]:
            if owner.is_temporary(prop):
                self.remove(prop)
            elif isinstance(prop, PyMeterProperty):
                prop.recover_running_version(owner)
            elif hasattr(prop, 'recover_running_version'):
                prop.recover_running_version()


class CollectionProperty(MultiProperty):

    def __init__(self, name: str, value: list[PyMeterProperty] = None):
        if value is None:
            value = []
        super().__init__(name, value)
        self.saved_value = None

    def get_str(self) -> str:
        return str(self.value)

    def get_bool(self) -> bool:
        return bool(self.value)

    def get_obj(self) -> list:
        return self.value

    def remove(self, prop: PyMeterProperty) -> None:
        self.value.remove(prop)

    def set(self, prop: PyMeterProperty) -> None:
        self.value.append(prop)

    def get(self, index: int) -> PyMeterProperty:
        return self.value[index]

    def iterator(self) -> Iterable:
        return self.value

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        MultiProperty.running_version = running
        self.saved_value = deepcopy(self.value) if running else None

    def recover_running_version(self, owner) -> None:
        if self.saved_value is not None:
            self.value = deepcopy(self.saved_value)
        self.recover_running_version_of_subelements(owner)


class TestElementProperty(MultiProperty):

    def __init__(self, name: str, value):  # value: TestElement
        super().__init__(name, value)
        self.saved_value = None

    def get_str(self) -> str:
        return str(self.value)

    def get_bool(self) -> bool:
        return bool(self.value)

    def get_obj(self):
        return self.value

    def remove(self, prop: PyMeterProperty) -> None:
        self.value.remove_property(prop.name)

    def iterator(self) -> Iterable:
        return self.value.property_iterator()

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        MultiProperty.running_version = running
        self.value.running_version = running
        self.saved_value = self.value if running else None

    def recover_running_version(self, owner) -> None:
        if self.saved_value is not None:
            self.value = self.saved_value
        self.value.recover_running_version()


class DictProperty(MultiProperty):

    def __init__(self, name: str, value: dict[str, PyMeterProperty] = None):
        if value is None:
            value = {}
        super().__init__(name, value)
        self.saved_value = None

    def get_str(self) -> str:
        return str(self.value)

    def get_bool(self) -> bool:
        return bool(self.value)

    def get_obj(self) -> dict:
        return self.value

    def remove(self, prop: PyMeterProperty) -> None:
        self.value.pop(prop.name)

    def iterator(self) -> Iterable:
        return list(self.value.values())

    @property
    def running_version(self):
        return self._running_version

    @running_version.setter
    def running_version(self, running: bool):
        MultiProperty.running_version = running
        self.saved_value = deepcopy(self.value) if running else None

    def recover_running_version(self, owner) -> None:
        if self.saved_value is not None:
            self.value = deepcopy(self.saved_value)
        self.recover_running_version_of_subelements(owner)


class FunctionProperty(PyMeterProperty):

    def __init__(self, name: str, function):  # function: CompoundVariable
        super().__init__(name)
        self.function = function
        self.cache_value = None
        self.test_iteration = -1

    @property
    def ctx(self):
        return ContextService.get_context()

    def get_raw(self) -> str:
        return self.function.raw_parameters

    def get_str(self) -> str:
        if not self.running_version:
            logger.debug(f'非运行状态, 返回函数原始文本\n{self.function.raw_parameters}')
            return self.function.raw_parameters

        iteration = self.ctx.variables.iteration if self.ctx.variables else -1

        if iteration < self.test_iteration:
            self.test_iteration = -1

        if (iteration > self.test_iteration) or (self.cache_value is None):
            logger.debug(f'元素属性:[ {self.name} ] 执行函数')
            self.test_iteration = iteration
            self.cache_value = self.function.execute()

        return self.cache_value

    def get_bool(self) -> bool:
        return self.function.has_function

    def get_obj(self) -> None:
        return None

    def recover_running_version(self, owner) -> None:
        self.cache_value = None
