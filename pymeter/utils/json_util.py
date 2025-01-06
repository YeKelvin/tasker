#!/usr/bin python3
# @File    : json_util.py
# @Time    : 2020/2/21 11:14
# @Author  : Kelvin.Ye
import random

import orjson

from jsonpath import jsonpath


class JsonpathExtractException(Exception):
    ...


def to_json(obj: dict | list) -> str:
    """序列化"""
    return orjson.dumps(obj).decode('utf8')

def to_pretty_json(obj: dict or list) -> str:
    """序列化"""
    return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode('utf8')


def from_json(val):
    """反序列化"""
    return orjson.loads(val)


def json_path(val, expressions, choice=False, throw=False):
    results = jsonpath(from_json(val), expressions)

    # jsonpath 没有匹配时会返回 False
    if not results:
        if throw:
            raise JsonpathExtractException
        return

    if len(results) == 1:
        result = results[0]
        if isinstance(result, list):
            return random.choice(result) if choice else result
        else:
            return result

    return random.choice(results) if choice else results
