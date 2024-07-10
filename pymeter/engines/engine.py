#!/usr/bin python3
# @File    : engine.py
# @Time    : 2023-08-07 13:19:26
# @Author  : Kelvin.Ye
from gevent import Greenlet
from gevent.event import Event
from loguru import logger

from pymeter.collections.test_collection import TestCollection
from pymeter.engines.context import EngineContext
from pymeter.engines.hashtree import HashTree
from pymeter.engines.traverser import SearchByClass
from pymeter.engines.variables import Variables
from pymeter.tools.exceptions import EngineError


class Engine(Greenlet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active = False
        self.running = False
        self.collection_tree = None
        self.collection = None
        self.sequential = True
        self.workers = []
        self.context = EngineContext()
        self.extra = kwargs.get('extra', {})
        self.properties = Variables()
        self.properties.update(kwargs.get('props', {}))
        self.stop_event: Event = kwargs.get('stop_event', None)

    def run_test(self) -> None:
        """运行脚本，这里主要做异常捕获"""
        try:
            self.running = True
            self.start()  # _run()
            self.join()  # 等待主线程结束
        except EngineError as e:
            logger.error(e)
        except Exception:
            logger.exception('Exception Occurred')
        finally:
            self.running = False
            self.active = False

    def configure(self, hashtree: HashTree) -> None:
        """将脚本配置到执行引擎中"""
        # 查找脚本顶层列表中的 TestCollection 对象
        searcher = SearchByClass(TestCollection)
        hashtree.traverse(searcher)
        collections = searcher.get_search_result()

        if len(collections) == 0:
            raise EngineError('集合不允许为空')

        self.active = True
        self.collection_tree = hashtree
        self.collection = collections[0]
        self.sequential = self.collection.sequential

    def stop_test(self):
        """停止所有 TestWorker（等待当前已启动的所有的 TestWorker 执行完成且不再执行剩余的 TestWorker）"""
        self.running = False
        for worker in self.workers:
            worker.stop_threads()

    def stop_test_now(self):
        """立即停止测试（强制中断所有的线程）"""
        self.running = False
        for worker in self.workers:
            worker.kill_threads()

    def is_interrupted(self):
        return self.stop_event and self.stop_event.is_set()
