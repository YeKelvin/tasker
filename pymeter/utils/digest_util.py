#!/usr/bin python3
# @File    : digest_util.py
# @Time    : 2023-06-14 15:44:41
# @Author  : Kelvin.Ye
import base64
import hashlib
import hmac

from hashlib import sha256


def md5(data: str| bytes, charset='utf-8'):
    if isinstance(data, str):
        data = data.encode(encoding=charset)
    return hashlib.md5(data).hexdigest()


def hmac_sha256(key: str| bytes, data: str| bytes, charset='utf-8') -> bytes:
    if isinstance(key, str):
        key = key.encode(charset)
    if isinstance(data, str):
        data = data.encode(charset)
    return hmac.new(key, data, digestmod=sha256).digest()


def hmac_sha256_hex(key: str| bytes, data: str| bytes, charset='utf-8') -> str:
    if isinstance(key, str):
        key = key.encode(charset)
    if isinstance(data, str):
        data = data.encode(charset)
    return hmac.new(key, data, digestmod=sha256).hexdigest().upper()


def hmac_sha256_base64(key: str| bytes, data: str| bytes, charset='utf-8') -> str:
    return base64.b64encode(hmac_sha256(key, data, charset)).decode(charset)
