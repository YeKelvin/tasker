#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : log_util.py
# @Time    : 2019/3/15 10:56
# @Author  : KelvinYe
import logging
from sendanywhere.utils import config

# 日志输出格式
FORMATTER = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s.%(funcName)s %(lineno)d] %(message)s')

# 输出到控制台
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setFormatter(FORMATTER)

# 写入日志文件
FILE_HANDLER = logging.FileHandler(config.get('log', 'name'))

# 日志级别
LEVEL = config.get('log', 'level')


def get_logger(name):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(LEVEL)
    logger.addHandler(CONSOLE_HANDLER)
    return logger
