#!/usr/bin python3
# @Module  : tools
# @File    : python_security.py
# @Time    : 2024-07-10 14:12:24
# @Author  : Kelvin.Ye
from pymeter.tools.exceptions import ForbiddenPythonError


def check_security(code):
    # 禁用 os
    if 'import os' in code or 'from os' in code:
        raise ForbiddenPythonError('os')
    # 禁用 sys
    if 'import sys' in code or 'from sys' in code:
        raise ForbiddenPythonError('sys')
    # 禁用 shutil
    if 'import shutil' in code or 'from shutil' in code:
        raise ForbiddenPythonError('shutil')
    # 禁用 sysconfig
    if 'import sysconfig' in code or 'from sysconfig' in code:
        raise ForbiddenPythonError('sysconfig')
    # 禁用 subprocess
    if 'import subprocess' in code or 'from subprocess' in code:
        raise ForbiddenPythonError('subprocess')
    # 禁用 pathlib
    if 'import pathlib' in code or 'from pathlib' in code:
        raise ForbiddenPythonError('pathlib')
    # 禁用 platform
    if 'import platform' in code or 'from platform' in code:
        raise ForbiddenPythonError('platform')
    # 禁用 tempfile
    if 'import tempfile' in code or 'from tempfile' in code:
        raise ForbiddenPythonError('tempfile')
    # 禁用 importlib
    if 'import importlib' in code or 'from importlib' in code:
        raise ForbiddenPythonError('importlib')
