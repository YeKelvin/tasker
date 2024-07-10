#!/usr/bin python3
# @File    : runner.py
# @Time    : 2020/2/12 11:46
# @Author  : Kelvin.Ye
import time

import orjson

from gevent.event import Event
from loguru import logger
from loguru._logger import context as logurucontext

from pymeter.engines import script_service
from pymeter.engines.standard_engine import StandardEngine
from pymeter.tools.exceptions import InvalidScriptError
from pymeter.utils.json_util import to_pretty_json
from pymeter.utils.log_util import SocketIOHandler


class Runner:

    @staticmethod
    def start(
            script: str or list,
            extra: dict = None,
            throw_ex: bool = False,
            stop_event: Event = None
    ) -> None:
        """执行脚本

        Args:
            script:     脚本
            extra:      外部扩展，用于传递外部对象
            throw_ex:   是否抛出异常
            stop_event: 停止信号

        Retruns:
            None
        """
        # 校验脚本不能为空
        if not script:
            raise InvalidScriptError('脚本不允许为空')

        # 初始化extra
        if not extra:
            extra = {}

        # 配置socket日志
        socket_logger_id = None
        if 'sio' in extra and 'sid' in extra:
            socket_logger_id = logger.add(
                SocketIOHandler(extra.get('sio'), extra.get('sid')),
                level='INFO',
                format='[{time:%H:%M:%S.%f}] [{level}] {message}'
            )

        # log注入traceid和sid
        logurucontext.set({
            **logurucontext.get(),
            'traceid': extra.get('traceid'),
            'sid': extra.get('sid')
        })

        try:
            logger.debug(f'测试脚本\n{to_pretty_json(script)}')
            Runner.run(script, extra, stop_event)
        except Exception:
            logger.exception('Exception Occurred')
            if throw_ex:
                raise
        finally:
            if socket_logger_id:
                logger.remove(socket_logger_id)

    @staticmethod
    def run(script: str, extra: dict=None, stop_event: Event=None) -> None:
        # 记录时间
        now = time.time()
        ymd = time.strftime('%Y-%m-%d', time.localtime(now))
        hms = time.strftime('%H:%M:%S', time.localtime(now))

        # 加载脚本
        logger.info('开始加载脚本')
        hashtree = script_service.load_tree(script)
        logger.info('脚本加载完成')
        logger.debug(f'脚本HashTree结构:\n{hashtree}')

        # 将脚本配置到执行引擎中
        engine = StandardEngine(
            extra=extra,
            props={
                'START.MS': int(now * 1000),
                'START.YMD': ymd,
                'START.HMS': hms
            },
            stop_event=stop_event
        )
        # 配置脚本
        engine.configure(hashtree)
        # 开始执行测试
        engine.run_test()


if __name__ == '__main__':
    import pathlib
    import sys

    # 项目根目录
    rootpath = pathlib.Path(__file__).parent.parent.absolute()
    # 清空日志文件
    logpath = rootpath.joinpath('debug.log').absolute()
    if logpath.exists():
        logpath.unlink()

    # 日志配置
    fmt = '<green>[{time:%Y-%m-%d %H:%M:%S.%f}]</green> <level>[{level}] [{module}:{function}:{line}] {message}</level>'
    logger.remove()
    logger.add(
        sys.stdout,
        level='DEBUG',
        colorize=True,
        format=fmt
    )
    logger.add(
        'debug.log',
        level='DEBUG',
        diagnose=True,
        backtrace=True,
        format=fmt
    )

    # 读取脚本运行
    with open(rootpath.joinpath('scripts', 'debug.json')) as f:
        # import cProfile
        # cProfile.run('Runner.start(script)', filename='profile.out')
        script = ''.join(f.readlines())
        obj = [orjson.loads(script)]
        Runner.start(obj)
