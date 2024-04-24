#!/usr/bin python3
# @File    : setup_worker.py
# @Time    : 2023-06-05 18:35:46
# @Author  : Kelvin.Ye
from typing import Final

from pymeter.workers.test_worker import TestWorker


class SetupWorker(TestWorker):

    # 运行策略
    RUNNING_STRATEGY: Final = 'SetupWorker__running_strategy'

    # 请求失败时的处理逻辑
    ON_SAMPLE_ERROR: Final = 'SetupWorker__on_sample_error'

    # 线程数
    NUMBER_OF_THREADS: Final = 'SetupWorker__number_of_threads'

    # 每秒启动的线程数
    STARTUPS_PER_SECOND: Final = 'SetupWorker__startups_per_second'

    # 循环控制器
    MAIN_CONTROLLER: Final = 'SetupWorker__main_controller'
