#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : aes.py
# @Time    : 2022/10/12 18:21
# @Author  : Kelvin.Ye
from typing import Final

from pymeter.functions.function import Function
from pymeter.utils import aes_util as aes_cryptor
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class AES(Function):

    REF_KEY: Final = '__AES'

    def __init__(self):
        self.plaintext = None
        self.key = None
        self.plaintext_encode_type = None
        self.block_size = None
        self.mode = None

    def execute(self):
        log.debug(f'start execute function:[ {self.REF_KEY} ]')

        plaintext = self.plaintext.execute().strip()
        key = self.key.execute().strip()
        plaintext_encode_type = self.plaintext_encode_type.execute().strip() if self.plaintext_encode_type else 'base64'
        block_size = self.block_size.execute().strip() if self.block_size else '16'
        mode = self.mode.execute().strip() if self.mode else 'ECB'

        result = aes_cryptor.encrypt(plaintext, key, plaintext_encode_type, block_size, mode)
        log.debug(f'function:[ {self.REF_KEY} ] result:[ {result} ]')

        return result

    def set_parameters(self, params: list):
        log.debug(f'start to set function parameters:[ {self.REF_KEY} ]')

        # 校验函数参数个数
        self.check_parameter_min(params, 2)
        self.check_parameter_max(params, 4)
        # 提取参数
        self.plaintext = params[0]
        self.key = params[1]
        self.plaintext_encode_type = params[2] if len(params) > 2 else None
        self.block_size = params[3] if len(params) > 3 else None
        self.mode = params[4] if len(params) > 4 else None