#!/usr/bin python3
# @File    : http_sampler.py
# @Time    : 2020/2/13 16:14
# @Author  : Kelvin.Ye
from typing import Final
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from httpx import Response
from loguru import logger

from pymeter.configs.arguments import Arguments
from pymeter.configs.httpconfigs import HTTPFileArgument
from pymeter.configs.httpconfigs import HTTPHeaderManager
from pymeter.configs.httpconfigs import SessionManager
from pymeter.samplers.http_constants import HTTP_STATUS_CODE
from pymeter.samplers.sample_result import SampleResult
from pymeter.samplers.sampler import Sampler


class HTTPSampler(Sampler):

    # 请求类型
    REQUEST_TYPE: Final = 'HTTP'

    # 请求URL
    URL: Final = 'HTTPSampler__url'

    # 请求方法
    METHOD: Final = 'HTTPSampler__method'

    # 请求头管理器
    HEADERS: Final = 'HTTPSampler__headers'

    # 查询参数
    PARAMS: Final = 'HTTPSampler__params'

    # 表单参数
    FORMS: Final = 'HTTPSampler__forms'

    # 文件参数
    FILES: Final = 'HTTPSampler__files'

    # 请求主体
    DATA: Final = 'HTTPSampler__data'

    # 请求内容编码
    ENCODING: Final = 'HTTPSampler__encoding'

    # 跟随重定向
    FOLLOW_REDIRECTS: Final = 'HTTPSampler__follow_redirects'

    # 请求连接超时时间
    CONNECT_TIMEOUT: Final = 'HTTPSampler__connect_timeout'

    # 等待响应超时时间
    RESPONSE_TIMEOUT: Final = 'HTTPSampler__response_timeout'

    # 运行策略
    RUNNING_STRATEGY: Final = 'HTTPSampler__running_strategy'

    @property
    def url(self) -> str:
        return self.get_property_as_str(self.URL)

    @property
    def path(self) -> str:
        return urlparse(self.url).path

    @property
    def method(self) -> str:
        return self.get_property_as_str(self.METHOD)

    @property
    def header_manager(self) -> HTTPHeaderManager:
        return self.get_property(self.HEADERS).get_obj()

    @property
    def headers(self) -> dict:
        hm = self.header_manager
        return hm.headers_as_dict if hm else {}

    @property
    def query_manager(self) -> Arguments:
        return self.get_property(self.PARAMS).get_obj()

    @property
    def querys(self) -> dict:
        args = self.query_manager
        return args.to_dict() if isinstance(args, Arguments) else {}

    @property
    def form_manager(self) -> Arguments:
        return self.get_property(self.FORMS).get_obj()

    @property
    def forms(self) -> dict:
        args = self.form_manager
        return args.to_dict() if isinstance(args, Arguments) else {}

    @property
    def file_manager(self) -> Arguments:
        return self.get_property(self.FILES).get_obj()

    @property
    def files(self) -> list[HTTPFileArgument]:
        args = self.file_manager
        return args.to_list() if isinstance(args, Arguments) else []

    @property
    def data(self) -> str:
        return self.get_property_as_str(self.DATA)

    @property
    def encoding(self) -> str:
        return self.get_property_as_str(self.ENCODING) or 'utf-8'

    @property
    def follow_redirects(self) -> bool:
        return self.get_property_as_bool(self.FOLLOW_REDIRECTS)

    @property
    def connect_timeout(self) -> float:
        return self.get_property_as_float(self.CONNECT_TIMEOUT)

    @property
    def response_timeout(self) -> float:
        return self.get_property_as_float(self.RESPONSE_TIMEOUT)

    def __init__(self, name: str = None):
        super().__init__(name=name)
        self.content_type = None
        self.session_manager = None
        self.payload_decoded = None

    def initialize(self):
        if not self.content_type:
            self.init_content_type()

    def init_content_type(self):
        header_manager = self.header_manager
        if not header_manager:
            return

        header = header_manager.get_header('content-type')
        if not header:
            return

        # 缓存 content-type
        self.content_type = header.value.lower()
        # 添加 boundary
        if 'multipart/form-data' in self.content_type:
            header.value = f'multipart/form-data; boundary=--{uuid4().hex}'

    def sample(self) -> SampleResult:  # sourcery skip: extract-method
        # 初始化必要数据
        self.initialize()

        result = SampleResult()
        result.sample_name = self.name
        result.sample_desc = self.desc
        result.request_url = self.url
        result.sample_start()

        try:
            if self.session_manager and self.session_manager.session:
                impl = self.session_manager.session
            else:
                impl = httpx

            res: Response = impl.request(
                method=self.method,
                url=self.url,
                headers=self.encoded_each(self.headers),
                params=self.get_query_params(),
                data=self.get_body_data(),
                files=self.get_form_data(),
                cookies=None,
                timeout=self.get_timeout(),
                follow_redirects=self.follow_redirects
            )
            res.encoding = self.encoding
            rescontent = res.read().decode(res.encoding)

            # logger.debug(
            #     f'HTTP请求:[ {self.name} ]\n'
            #     f'REQUEST: \n'
            #     f'{res.request.method} {res.request.url}\n'
            #     f'{res.request.content.decode(res.encoding)}\n'
            #     f'RESPONSE({res.status_code}):\n'
            #     f'{rescontent}'
            # )

            result.success = res.is_success
            result.request_data = self.get_payload(res)
            result.request_decoded = self.payload_decoded
            result.request_headers = self.decode_each(dict(res.request.headers))
            result.response_data = rescontent or str(res.status_code)
            result.response_code = res.status_code
            result.response_message = HTTP_STATUS_CODE.get(res.status_code)
            result.response_headers = dict(res.headers)
            result.response_cookies = dict(res.cookies)
        except Exception as err:
            logger.exception('Exception Occurred')
            result.error = True
            result.success = False
            result.response_data = str(err)
            result.response_code = 500
            result.response_message = 'PyMeterException'
        finally:
            result.sample_end()

        return result

    def get_query_params(self) -> dict:
        querys = self.querys
        if querys:
            decoded = [f'{name}={value}' for name, value in querys.items()]
            self.payload_decoded = (
                f'{self.method} {self.url}\n\n{self.method} DATA:\n' +'\n'.join(decoded)
            )
        return querys

    def get_body_data(self) -> bytes:
        if self.content_type:
            if 'x-www-form-urlencoded' in self.content_type:
                return self.get_form_urlencoded()
            if 'multipart/form-data' in self.content_type:
                return None

        return data.encode(encoding=self.encoding) if (data := self.data) else None

    def get_body_str(self) -> str:
        body = self.get_body_data()
        return body.decode(self.encoding) if body else ''

    def get_form_urlencoded(self) -> bytes:
        forms = self.forms
        if forms:
            decoded = [f'{name}={value}' for name, value in forms.items()]
            self.payload_decoded = (
                f'{self.method} {self.url}\n\n{self.method} DATA:\n' + '\n'.join(decoded)
            )
        return self.urlencode(forms)


    def get_form_data(self) -> dict:
        # sourcery skip: dict-comprehension, remove-redundant-pass
        # 非 multipart/form-data 时返回None
        if not self.content_type:
            return None
        if 'multipart/form-data' not in self.content_type:
            return None

        files = {}
        decoded = []
        for item in self.files:
            if item.argtype == 'text':
                files[item.name] = (None, item.value.encode(encoding=self.encoding))
                decoded.append(f'{item.name}={item.value}')
            else:
                # 暂时不支持文件
                pass
        if decoded:
            self.payload_decoded = f'{self.method} {self.url}\n\n{self.method} DATA:\n' + '\n'.join(decoded)

        return files

    def get_timeout(self) -> tuple:
        return (
            (self.connect_timeout or 0, self.response_timeout or 0)
            if (self.connect_timeout and self.response_timeout)
            else None
        )

    def get_payload(self, res: Response) -> str:
        # res.url 是转码后的值，如果包含中文，就看不懂了，因为这里是为了展示数据
        req = res.request
        url = f'{req.method} {req.url}'
        payload = ''

        if body := req.read():
            body = body.decode(encoding=res.encoding) if isinstance(body, bytes) else body
            payload = f'\n\n{req.method} DATA:\n{body}'

        return url + payload

    def add_test_element(self, el) -> None:
        """@override"""
        if isinstance(el, HTTPHeaderManager):
            self.set_header_manager(el)
        elif isinstance(el, SessionManager):
            self.set_session_manager(el)
        else:
            super().add_test_element(el)

    def set_header_manager(self, new_manager: HTTPHeaderManager):
        if header_manager := self.header_manager:
            new_manager = header_manager.merge(new_manager)

        self.set_property(self.HEADERS, new_manager)

    def get_header_manager(self):
        headers = self.header_manager
        if headers is None:
            headers = HTTPHeaderManager()
            self.set_header_manager(headers)
        return headers

    def set_session_manager(self, manager: SessionManager):
        self.session_manager = manager

    def urlencode(self, args: dict):
        payload = [f'{name}={value}' for name, value in args.items()]
        return '&'.join(payload).encode(encoding=self.encoding)

    def encoded_each(self, args: dict):
        for name, value in args.items():
            args[name] = (value or '').encode(encoding=self.encoding)
        return args

    def decode_each(self, args: dict):
        for name, value in args.items():
            args[name] = value.decode(encoding=self.encoding) if isinstance(value, bytes) else value
        return args
