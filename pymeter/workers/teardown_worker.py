#!/usr/bin python3
# @File    : teardown_worker.py
# @Time    : 2023-06-05 18:36:25
# @Author  : Kelvin.Ye
from typing import Final

from pymeter.workers.test_worker import TestWorker


class TearDownWorker(TestWorker):

    # 运行策略
    RUNNING_STRATEGY: Final = 'TearDownWorker__running_strategy'

    # 取样器失败时的处理逻辑
    ON_SAMPLE_ERROR: Final = 'TearDownWorker__on_sample_error'

    # 线程数
    NUMBER_OF_THREADS: Final = 'TearDownWorker__number_of_threads'

    # 每秒启动的线程数
    STARTUPS_PER_SECOND: Final = 'TearDownWorker__startups_per_second'

    # 循环控制器
    MAIN_CONTROLLER: Final = 'TearDownWorker__main_controller'