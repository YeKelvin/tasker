#!/usr/bin python3
# @File    : arguments.py
# @Time    : 2021-07-05 13:44:20
# @Author  : Kelvin.Ye
from pymeter.elements.element import ConfigTestElement
from pymeter.elements.element import TestElement
from pymeter.elements.property import CollectionProperty
from pymeter.elements.property import TestElementProperty


class Argument(TestElement):

    # 参数名称
    ARGUMENT_NAME = 'Argument__name'

    # 参数值
    ARGUMENT_VALUE = 'Argument__value'

    # 参数描述
    ARGUMENT_DESCRIPTION = 'Argument__desc'

    # 参数元数据，其实就是输出str时用来连接name和value的符号，e.g. name=value
    ARGUMENT_SYMBOL = 'Argument__symbol'

    def __init__(self, name: str = None, value: str = None, desc: str = None, symbol: str = '='):
        super().__init__()
        self.name = name
        self.value = value
        self.desc = desc
        self.symbol = symbol

    @property
    def name(self):
        return self.get_property_as_str(self.ARGUMENT_NAME)

    @name.setter
    def name(self, value):
        self.set_property(self.ARGUMENT_NAME, value)

    @property
    def value(self):
        return self.get_property_as_str(self.ARGUMENT_VALUE)

    @value.setter
    def value(self, value):
        self.set_property(self.ARGUMENT_VALUE, value)

    @property
    def desc(self):
        return self.get_property_as_str(self.ARGUMENT_DESCRIPTION)

    @desc.setter
    def desc(self, value):
        self.set_property(self.ARGUMENT_DESCRIPTION, value)

    @property
    def symbol(self):
        return self.get_property_as_str(self.ARGUMENT_SYMBOL)

    @symbol.setter
    def symbol(self, value):
        self.set_property(self.ARGUMENT_SYMBOL, value)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        symbol = self.symbol
        return (
            '{\n'
            f'  "name"{symbol} "{self.name}",\n'
            f'  "value"{symbol} "{self.value}",\n'
            f'  "desc"{symbol} "{self.desc}"\n'
            '}'
        )


class Arguments(ConfigTestElement):

    ARGUMENTS = 'Arguments__arguments'

    def __init__(self):
        super().__init__()
        self.add_property(self.ARGUMENTS, CollectionProperty(self.ARGUMENTS))

    @property
    def arguments(self) -> list[Argument]:
        return self.get_property(self.ARGUMENTS).get_obj()

    def add(self, name=None, value=None, desc=None, symbol='='):
        self.add_argument(Argument(name, value, desc, symbol))

    def add_argument(self, arg: Argument):
        prop = TestElementProperty(arg.name, arg)
        if self.running_version:
            self.set_temporary(prop)
        self.arguments.append(arg)

    def to_dict(self) -> dict:
        return {arg.name: arg.value for arg in self.arguments}

    def to_list(self) -> list[Argument]:
        return self.arguments

    def get(self, name: str) -> Argument:
        return next((arg for arg in self.arguments if arg.name == name), None)

    def has(self, name: str) -> bool:
        return any(arg.name == name for arg in self.arguments)

    def remove(self, name: str):
        if argument := self.get(name):
            self.arguments.remove(argument)

    def remove_argument(self, argument: Argument):
        if argument in self.arguments:
            self.arguments.remove(argument)

    def clear(self):
        self.arguments.clear()
