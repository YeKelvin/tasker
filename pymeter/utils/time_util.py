#!/usr/bin python3
# @File    : time_util
# @Time    : 2020/3/9 15:20
# @Author  : Kelvin.Ye
import time

from datetime import datetime
from datetime import timedelta
from datetime import timezone


DEFAULE_STRFTIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def strftime_now(fmt: str = DEFAULE_STRFTIME_FORMAT) -> str:
    """获取当前时间并格式化为时间字符串"""
    return datetime.now().strftime(fmt)


def timestamp_now() -> float:
    """获取时间戳（从UTC时间 1970年1月1日 0点 到现在的秒值）"""
    return time.time()


def timestamp_to_strftime(timestamp: float, fmt: str = DEFAULE_STRFTIME_FORMAT):
    """时间戳转时间字符串

    Args:
        timestamp:  时间戳
        fmt:        时间格式

    """
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def strftime_to_timestamp(strftime: str, fmt: str = DEFAULE_STRFTIME_FORMAT) -> int:
    """时间字符串转毫秒级时间戳

    Args:
        strftime:   时间字符串
        fmt:        时间格式

    """
    return int(time.mktime(time.strptime(strftime, fmt)) * 1000)


def change_strftime_format(strftime: str, old_fmt: str, new_fmt: str = DEFAULE_STRFTIME_FORMAT) -> str:
    """更改时间字符串的格式

    Args:
        strftime:   时间字符串
        old_fmt:    旧格式
        new_fmt:    新格式

    """
    return datetime.strptime(strftime, old_fmt).strftime(new_fmt)


def microsecond_to_h_m_s(microsecond: int) -> str:
    """毫秒转换为时分秒"""
    s, ms = divmod(microsecond, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h == 0 and m == 0 and s == 0:
        return '%dms' % ms
    if h == 0 and m == 0:
        return '%02ds:%dms' % (s, ms)
    if h == 0:
        return '%02dm:%02ds' % (m, s)

    return '%02dh:%02dm:%02ds' % (h, m, s)


def microsecond_to_m_s(microsecond: int) -> str:
    """毫秒转换为时分秒"""
    s, ms = divmod(microsecond, 1000)
    m, s = divmod(s, 60)
    if m == 0 and s == 0:
        return '%dms' % ms
    if m == 0:
        return '%02ds:%dms' % (s, ms)

    return '%02dm:%02ds' % (m, s)


def timestmp_to_utc8_datetime(timestmp):
    """时间戳转北京时间的 datetime 对象"""
    return datetime.fromtimestamp(timestmp, tz=timezone(timedelta(hours=8)))
