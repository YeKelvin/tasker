#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : httpconfigs.py
# @Time    : 2020/2/17 15:41
# @Author  : Kelvin.Ye
from typing import List
from typing import Optional

import requests

from pymeter.common.exceptions import HttpCookieDuplicateException
from pymeter.common.exceptions import HttpHeaderDuplicateException
from pymeter.elements.element import ConfigTestElement
from pymeter.elements.element import TestElement
from pymeter.engine.interface import TestGroupListener
from pymeter.engine.interface import TestIterationListener
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class HTTPHeader(TestElement):

    # HTTP头部名称
    HEADER_NAME = 'Header__name'

    # HTTP头部值
    HEADER_VALUE = 'Header__value'

    @property
    def name(self):
        return self.get_property_as_str(self.HEADER_NAME)

    @name.setter
    def name(self, value):
        self.set_property(self.HEADER_NAME, value)

    @property
    def value(self):
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
        self.add_property(self.HEADERS, [])

    @property
    def headers_as_list(self) -> List[HTTPHeader]:
        return self.get_property(self.HEADERS).get_obj()

    @property
    def headers_as_dict(self) -> dict:
        headers = {}
        for header in self.headers_as_list:
            headers[header.name] = header.value
        return headers

    def merge(self, el):
        if not isinstance(el, HTTPHeaderManager):
            raise Exception(f'cannot merge type: {self} with type: {el}')

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

    def get_header(self, name: str) -> Optional[HTTPHeader]:
        for header in self.headers_as_list:
            if header.name.lower() == name.lower():
                return header
        return None

    def has_header(self, name: str) -> bool:
        for header in self.headers_as_list:
            if header.name.lower() == name.lower():
                return True
        return False

    def add_header(self, name: str, value: str) -> None:
        if self.has_header(name):
            raise HttpHeaderDuplicateException(f'header:[ {name} ] 已存在')

        header = HTTPHeader()
        header.name = name
        header.value = value
        self.headers_as_list.append(header)


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
        self.add_property(self.COOKIES, [])

    @property
    def cookies_as_list(self) -> List[HTTPCookie]:
        return self.get_property(self.COOKIES).get_obj()

    @property
    def cookies_as_dict(self) -> dict:
        cookies = {}
        for cookie in self.cookies_as_list:
            cookies[cookie.name] = cookie.value
        return cookies

    def merge(self, el):
        if not isinstance(el, HTTPCookieManager):
            raise Exception(f'cannot merge type: {self} with type: {el}')

        merged_manager = self.clone()  # type: HTTPCookieManager
        new_manager = el  # type: HTTPCookieManager

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

    def get_cookie(self, name: str) -> Optional[HTTPCookie]:
        for cookie in self.cookies_as_list:
            if cookie.name.lower() == name.lower():
                return cookie
        return None

    def has_cookie(self, name: str) -> bool:
        for cookie in self.cookies_as_list:
            if cookie.name.lower() == name.lower():
                return True
        return False

    def add_cookie(self, name: str, value: str, domain: str = None, path: str = None) -> None:
        if self.has_cookie(name):
            raise HttpCookieDuplicateException(f'cookie:[ {name} ] 已存在')

        cookie = HTTPCookie()
        cookie.name = name
        cookie.value = value
        cookie.domain = domain
        cookie.path = path
        self.cookies_as_list.append(cookie)


class SessionManager(ConfigTestElement):

    def __init__(self) -> None:
        super().__init__()
        self.session = None  # type: Optional[requests.sessions.Session]


class HTTPSessionManager(SessionManager, TestGroupListener, TestIterationListener):

    COOKIES = 'HTTPSessionManager__cookies'

    CLEAR_EACH_ITERATION = 'HTTPSessionManager__clear_each_iteration'

    @property
    def clear_each_iteration(self) -> bool:
        return self.get_property_as_bool(self.CLEAR_EACH_ITERATION)

    def group_started(self) -> None:
        log.debug('open new http session')
        self.session = requests.session()

    def group_finished(self) -> None:
        log.debug(f'close http session:[ {self.session} ]')
        self.session.close()

    def test_iteration_start(self, controller, iter: int) -> None:
        if self.clear_each_iteration and iter > 1:
            log.debug(f'close and open new http session in iteration:[ {iter} ]')
            self.session.close()
            self.session = requests.session()
