#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : gateway_sign.py
# @Time    : 2021-08-17 19:31:29
# @Author  : Kelvin.Ye
import hashlib
import time
from typing import Final

from pymeter.functions.function import Function
from pymeter.samplers.http_sampler import HTTPSampler
from pymeter.utils.json_util import from_json
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class GatewaySign(Function):

    REF_KEY: Final = '__GatewaySign'

    def execute(self):
        log.debug(f'start execute function:[ {self.REF_KEY} ]')

        # 获取当前 HttpSampler 对象
        http_sampler = self.current_sampler
        if not isinstance(http_sampler, HTTPSampler):
            log.error('__GatewaySign() 函数目前仅支持在 HTTPSampler 下使用')
            return 'error'

        data = http_sampler.data
        if data:
            # 反序列化 body
            data = from_json(http_sampler.data)
        else:
            # body 为空时初始化一个空 dict
            data = {}

        # 从 headers 中提取 requestTm 和 deviceId
        header_manager = http_sampler.header_manager
        request_tm_header = header_manager.get_header('requestTm')
        device_id_header = header_manager.get_header('deviceId')

        request_tm = None
        device_id = None

        if request_tm_header:
            request_tm = request_tm_header.value
        else:
            request_tm = str(int(time.time() * 1000))
            header_manager.add_header('requestTm', request_tm)

        if device_id_header:
            device_id = device_id_header.value
        else:
            device_id = 'powered.by.pymeter'
            header_manager.add_header('deviceId', device_id)

        # 将 requestTm 和 deviceId 添加到 body 中
        data['requestTm'] = request_tm
        data['deviceId'] = device_id

        # 请求加签
        return self.sign(data)

    def set_parameters(self, params: list):
        log.debug(f'start to set function parameters:[ {self.REF_KEY} ]')

        # 校验函数参数个数
        self.check_parameter_count(params, 0)

    def sign(self, data: dict):
        # 根据首字母排序
        data = dict(sorted(data.items(), key=lambda x: x[0]))

        # 遍历参数加签
        buffer = []
        for key, value in data.items():
            self.traverse(buffer, key, value)

        # 签名去掉最后一个多余的符号
        signature = (''.join(buffer))[:-1]
        log.debug(f'signature:[ {signature} ]')

        if not signature:
            return ''

        # md5加密
        return hashlib.md5(signature.encode(encoding='UTF-8')).hexdigest()

    def traverse(self, buffer: list, key, value):
        if isinstance(value, dict):
            buffer.append(f'{key}={self.traverse_dict(value)}&')
        elif isinstance(value, list):
            buffer.append(f'{key}={self.traverse_list(value)}&')
        else:
            buffer.append(f'{key}={value}&')

    def traverse_dict(self, value: dict):
        if not value:
            return '{}'

        # 根据首字母排序
        sorted_dict = dict(sorted(value.items(), key=lambda x: x[0]))
        buffer = ['{']
        for key, value in sorted_dict.items():
            self.traverse(buffer, key, value)

        return (''.join(buffer))[:-1] + '}'

    def traverse_list(self, value: list):
        if not value:
            return '[]'

        buffer = ['[']
        for item in value:
            if isinstance(item, dict):
                buffer.append(self.traverse_dict(item))
            elif isinstance(value, list):
                buffer.append(self.traverse_list(value))
            else:
                buffer.append(item)
            buffer.append(',')

        return (''.join(buffer))[:-1] + ']'


if __name__ == '__main__':
    json = {
        'c11': '3',
        'b11': '2',
        'd11': '4',
        'a11': '1',
    }
    s = sorted(json.items(), key=lambda x: x[0])
    print(s)
    print(type(s))
    print(dict(s))
    print(type(dict(s)))