#!/usr/bin python3
# @File    : httpconfigs.py
# @Time    : 2020/2/17 15:41
# @Author  : Kelvin.Ye
import httpx

from loguru import logger

from pymeter.configs.arguments import Argument
from pymeter.elements.element import ConfigTestElement
from pymeter.elements.element import TestElement
from pymeter.elements.property import CollectionProperty
from pymeter.engines.interface import TestIterationListener
from pymeter.engines.interface import TestWorkerListener
from pymeter.tools.exceptions import HTTPCookieDuplicateException
from pymeter.tools.exceptions import HTTPHeaderDuplicateException


class HTTPHeader(TestElement):

    # HTTP头部名称
    HEADER_NAME = 'Header__name'

    # HTTP头部值
    HEADER_VALUE = 'Header__value'

    @property
    def name(self) -> str:
        return self.get_property_as_str(self.HEADER_NAME)

    @name.setter
    def name(self, value):
        self.set_property(self.HEADER_NAME, value)

    @property
    def value(self) -> str:
        return self.get_property_as_str(self.HEADER_VALUE)

    @value.setter
    def value(self, value):
        self.set_property(self.HEADER_VALUE, value)

    def update(self, header) -> None:
        """更新value"""
        self.add_property(self.HEADER_VALUE, header.get_property(self.HEADER_VALUE))

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '{' + f'"{self.name}":"{self.value}"' + '}'


class HTTPHeaderManager(ConfigTestElement):

    HEADERS = 'HeaderManager__headers'

    def __init__(self):
        super().__init__()
        self.add_property(self.HEADERS, CollectionProperty(self.HEADERS))

    @property
    def headers_as_list(self) -> list[HTTPHeader]:
        return self.get_property(self.HEADERS).get_obj()

    @property
    def headers_as_dict(self) -> dict:
        return {header.name: header.value for header in self.headers_as_list}

    def merge(self, el):
        if not isinstance(el, HTTPHeaderManager):
            raise TypeError(f'cannot merge type: {self} with type: {el}')

        merged_manager = self.clone()  # type: HTTPHeaderManager
        new_manager = el  # type: HTTPHeaderManager

        for new_header in new_manager.headers_as_list:
            found = False
            for merged_header in merged_manager.headers_as_list:
                if merged_header.name.lower() == new_header.name.lower():
                    merged_header.update(new_header)
                    found = True
                    break

            if not found:
                merged_manager.headers_as_list.append(new_header)

        return merged_manager

    def get_header(self, name: str) -> HTTPHeader:
        return next(
            (
                header
                for header in self.headers_as_list
                if header.name.lower() == name.lower()
            ),
            None,
        )

    def has_header(self, name: str) -> bool:
        return any(
            header.name.lower() == name.lower() for header in self.headers_as_list
        )

    def add_header(self, name: str, value: str) -> None:
        if self.has_header(name):
            raise HTTPHeaderDuplicateException(f'请求头:[ {name} ] 已存在')

        header = HTTPHeader()
        header.name = name
        header.value = value
        self.headers_as_list.append(header)

    def set_header(self, name: str, value: str, force: bool=False) -> None:
        if header := self.get_header(name):
            if force:
                header.value = value
                return
            else:
                return
        else:
            header = HTTPHeader()
            header.name = name
            header.value = value
            self.headers_as_list.append(header)

    def remove_header(self, name: str) -> None:
        if header := self.get_header(name):
            self.headers_as_list.remove(header)


class HTTPCookie(TestElement):

    COOKIE_NAME = 'Cookie__name'
    COOKIE_VALUE = 'Cookie__value'
    COOKIE_DOMAIN = 'Cookie__domain'
    COOKIE_PATH = 'Cookie__path'

    @property
    def name(self):
        return self.get_property_as_str(self.COOKIE_NAME)

    @name.setter
    def name(self, val):
        self.set_property(self.COOKIE_NAME, val)

    @property
    def value(self):
        return self.get_property_as_str(self.COOKIE_VALUE)

    @value.setter
    def value(self, val):
        self.set_property(self.COOKIE_VALUE, val)

    @property
    def domain(self):
        return self.get_property_as_str(self.COOKIE_DOMAIN)

    @domain.setter
    def domain(self, val):
        self.set_property(self.COOKIE_DOMAIN, val)

    @property
    def path(self):
        return self.get_property_as_str(self.COOKIE_PATH)

    @path.setter
    def path(self, val):
        self.set_property(self.COOKIE_PATH, val)

    def update(self, cookie) -> None:
        """更新value"""
        self.add_property(self.COOKIE_VALUE, cookie.get_property(self.COOKIE_VALUE))

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '{' + f'"{self.name}":"{self.value}";"{self.domain}{self.path}"' + '}'


class HTTPCookieManager(ConfigTestElement):

    COOKIES = 'CookieManager__cookies'

    def __init__(self):
        super().__init__()
        self.set_property(self.COOKIES, CollectionProperty(self.COOKIES))

    @property
    def cookies_as_list(self) -> list[HTTPCookie]:
        return self.get_property(self.COOKIES).get_obj()

    @property
    def cookies_as_dict(self) -> dict:
        return {cookie.name: cookie.value for cookie in self.cookies_as_list}

    def merge(self, el):
        if not isinstance(el, HTTPCookieManager):
            raise TypeError(f'cannot merge type: {self} with type: {el}')

        merged_manager = self.clone()   # type: HTTPCookieManager
        new_manager = el                # type: HTTPCookieManager

        for new_cookie in new_manager.cookies_as_list:
            found = False
            for merged_header in merged_manager.cookies_as_list:
                if merged_header.name.lower() == new_cookie.name.lower():
                    merged_header.update(new_cookie)
                    found = True
                    break

            if not found:
                merged_manager.cookies_as_list.append(new_cookie)

        return merged_manager

    def get_cookie(self, name: str) -> HTTPCookie:
        return next(
            (
                cookie
                for cookie in self.cookies_as_list
                if cookie.name.lower() == name.lower()
            ),
            None,
        )

    def has_cookie(self, name: str) -> bool:
        return any(
            cookie.name.lower() == name.lower() for cookie in self.cookies_as_list
        )

    def add_cookie(self, name: str, value: str, domain: str = None, path: str = None) -> None:
        if self.has_cookie(name):
            raise HTTPCookieDuplicateException(f'Cookie:[ {name} ] 已存在')

        cookie = HTTPCookie()
        cookie.name = name
        cookie.value = value
        cookie.domain = domain
        cookie.path = path
        self.cookies_as_list.append(cookie)

    def set_cookie(self, name: str, value: str, domain: str = None, path: str = None) -> None:
        if cookie := self.get_cookie(name):
            cookie.name = name
            cookie.value = value
            cookie.domain = domain
            cookie.path = path
        else:
            cookie = HTTPCookie()
            cookie.name = name
            cookie.value = value
            cookie.domain = domain
            cookie.path = path
            self.cookies_as_list.append(cookie)


class SessionManager(ConfigTestElement):

    def __init__(self) -> None:
        super().__init__()
        self.session = None  # type: httpx.Client


class HTTPSessionManager(SessionManager, TestWorkerListener, TestIterationListener):

    COOKIES = 'HTTPSessionManager__cookies'

    CLEAR_EACH_ITERATION = 'HTTPSessionManager__clear_each_iteration'

    @property
    def clear_each_iteration(self) -> bool:
        return self.get_property_as_bool(self.CLEAR_EACH_ITERATION)

    def worker_started(self) -> None:
        logger.debug('创建 HTTP 会话')
        self.session = httpx.Client()

    def worker_finished(self) -> None:
        logger.debug('关闭 HTTP 会话')
        self.session.close()

    def test_iteration_start(self, controller, iter: int) -> None:
        if self.clear_each_iteration and iter > 1:
            logger.debug(f'迭代:[ {iter} ] 重置 HTTP 会话')
            self.session.close()
            self.session = httpx.Client()


class HTTPArgument(Argument):
    pass


class HTTPFileArgument(Argument):

    # 参数类型
    ARGUMENT_TYPE = 'Argument__argtype'

    # 媒体类型
    ARGUMENT_MIME_TYPE = 'Argument__mimetype'

    def __init__(
            self,
            name: str = None,
            value: str = None,
            argtype: str = None,
            mimetype: str = None,
            desc: str = None,
            symbol: str = '='
    ):
        super().__init__(name, value, desc, symbol)
        self.argtype = argtype
        self.mimetype = mimetype

    @property
    def argtype(self):
        return self.get_property_as_str(self.ARGUMENT_TYPE)

    @argtype.setter
    def argtype(self, value):
        self.set_property(self.ARGUMENT_TYPE, value)

    @property
    def mimetype(self):
        return self.get_property_as_str(self.ARGUMENT_MIME_TYPE)

    @mimetype.setter
    def mimetype(self, value):
        self.set_property(self.ARGUMENT_MIME_TYPE, value)

    def __str__(self):
        symbol = self.symbol
        return (
            '{\n'
            f'  "name"{symbol} "{self.name}",\n'
            f'  "value"{symbol} "{self.value}",\n'
            f'  "argtype"{symbol} "{self.argtype}"\n'
            f'  "mimetype"{symbol} "{self.mimetype}",\n'
            f'  "desc"{symbol} "{self.desc}"\n'
            '}'
        )
