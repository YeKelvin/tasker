#!/usr/bin python3
# @File    : standard_engine
# @Time    : 2020/1/24 23:31
# @Author  : Kelvin.Ye
import gc
import logging

from loguru import logger

from pymeter.elements.element import TestElement
from pymeter.engines.engine import Engine
from pymeter.engines.interface import TestCollectionListener
from pymeter.engines.traverser import SearchByClass
from pymeter.listeners.result_collector import ResultCollector
from pymeter.tools.exceptions import StopTestError
from pymeter.workers.context import ContextService
from pymeter.workers.setup_worker import SetupWorker
from pymeter.workers.teardown_worker import TeardownWorker
from pymeter.workers.test_worker import TestWorker


class StandardEngine(Engine):

    def _run(self, *args, **kwargs) -> None:
        """运行脚本的主体"""
        # 测试开始
        logger.info('开始运行脚本')

        # 上下文存储引擎和全局变量
        ctx = ContextService.get_context()
        ctx.engine = self
        ctx.variables.update(self.properties)
        # loguru注入trace_id和socket_id
        ContextService.init_loguru()
        # 上下文标记开始运行
        ContextService.start_test()

        # 查找 TestCollectionListener 对象
        collection_listener_searcher = SearchByClass(TestCollectionListener)
        self.collection_tree.traverse(collection_listener_searcher)

        # 遍历执行 TestCollectionListener
        self._notify_collection_listeners_of_start(collection_listener_searcher)

        # 存储 TestCollection 子代节点(非 TestWorker 节点)
        collection_component_list = self.collection_tree.index(0).list()
        self._remove_workers(collection_component_list)  # 删除 TestWorker 节点
        self._add_level(collection_component_list)       # 添加层级

        # 查找 SetupWorker / TestWorker / TeardownWorker 对象
        setup_worker_searcher = SearchByClass(SetupWorker)
        test_worker_searcher = SearchByClass(TestWorker)
        teardown_worker_searcher = SearchByClass(TeardownWorker)

        # 遍历查找
        self.collection_tree.traverse(setup_worker_searcher)
        self.collection_tree.traverse(test_worker_searcher)
        self.collection_tree.traverse(teardown_worker_searcher)

        ContextService.clear_total_threads()
        worker_total = 0

        # 运行SetUpWorker
        worker_total += self._process_setup_worker(setup_worker_searcher, collection_component_list)
        gc.collect()
        # 运行TestWorker
        worker_total += self._process_test_worker(test_worker_searcher, collection_component_list)
        gc.collect()
        # 运行TeardownWorker
        worker_total += self._process_teardown_worker(teardown_worker_searcher, collection_component_list)
        gc.collect()

        if worker_total == 0:
            logger.warning('集合不存在 #有效用例#')

        # 遍历执行 TestCollectionListener
        self._notify_collection_listeners_of_end(collection_listener_searcher)

        # DEBUG时输出结果
        if logger.level == logging.DEBUG:
            result_collector_searcher = SearchByClass(ResultCollector)
            self.collection_tree.traverse(result_collector_searcher)
            result_collectors = result_collector_searcher.get_search_result()
            for result_collector in result_collectors:
                logger.debug(f'取样结果:\n{result_collector.__dict__}')

        # 测试结束
        ContextService.end_test()
        logger.info('脚本运行完成')

    def _process_setup_worker(self, setup_worker_searcher, collection_component_list):
        if not setup_worker_searcher.count:
            return 0

        logger.info('开始处理 #前置用例#')
        worker_count = 0
        setup_worker_iter = iter(setup_worker_searcher.get_search_result())
        while self.running:
            try:
                setup_worker: SetupWorker = next(setup_worker_iter)
                worker_count += 1
                worker_name = setup_worker.name
                logger.info(f'用例:[ {worker_name} ] 初始化第 {worker_count} 个 #前置用例#')
                self._start_worker(setup_worker, worker_count, setup_worker_searcher, collection_component_list)

                # 需要顺序执行时，则等待当前线程执行完毕再继续下一个循环
                if self.sequential:
                    logger.info(f'用例:[ {worker_name} ] 等待当前 #前置用例# 执行完成')
                    setup_worker.wait_threads_stopped()
                    gc.collect()
            except StopIteration:
                logger.info('所有 #前置用例# 已启动')
                break

        logger.info('等待所有 #前置用例# 执行完成')
        self._wait_workers_stopped()
        self.workers.clear()  # The workers have all completed now
        ContextService.clear_total_threads()
        logger.info('所有 #前置用例# 已执行完成')
        return worker_count

    def _process_test_worker(self, test_worker_searcher, collection_component_list):
        if not test_worker_searcher.count:
            return 0

        logger.info(f'开始 #{"串行" if self.sequential else "并行"}# 处理 #用例#')
        worker_count = 0
        test_worker_iter = iter(test_worker_searcher.get_search_result())
        while self.running:
            try:
                test_worker: TestWorker = next(test_worker_iter)
                if isinstance(test_worker, SetupWorker | TeardownWorker):
                    continue
                worker_count += 1
                worker_name = test_worker.name
                logger.info(f'用例:[ {worker_name} ] 初始化第 {worker_count} 个 #用例#')
                self._start_worker(test_worker, worker_count, test_worker_searcher, collection_component_list)

                # 需要顺序执行时，则等待当前线程执行完毕再继续下一个循环
                if self.sequential:
                    logger.info(f'用例:[ {worker_name} ] 等待当前 #用例# 执行完成')
                    test_worker.wait_threads_stopped()
                    gc.collect()
            except StopIteration:
                logger.info('所有 #用例# 已启动')
                break

        if worker_count > 0:
            if not self.running:
                logger.info('测试已停止，不再启动剩余的 #用例# ')
            if not self.sequential:
                logger.info('等待所有 #用例# 执行完成')

        logger.info('等待所有 #用例# 执行完成')
        self._wait_workers_stopped()
        self.workers.clear()  # The workers have all completed now
        ContextService.clear_total_threads()
        logger.info('所有 #用例# 已执行完成')
        return worker_count

    def _process_teardown_worker(self, teardown_worker_searcher, collection_component_list):
        if not teardown_worker_searcher.count:
            return 0

        logger.info('开始处理 #后置用例#')
        worker_count = 0
        teardown_worker_iter = iter(teardown_worker_searcher.get_search_result())
        while self.running:
            try:
                teardown_worker: TeardownWorker = next(teardown_worker_iter)
                worker_count += 1
                worker_name = teardown_worker.name
                logger.info(f'用例:[ {worker_name} ] 初始化第 {worker_count} 个 #后置用例#')
                self._start_worker(teardown_worker, worker_count, teardown_worker_searcher, collection_component_list)

                # 需要顺序执行时，则等待当前线程执行完毕再继续下一个循环
                if self.sequential:
                    logger.info(f'用例:[ {worker_name} ] 等待当前 #后置用例# 完成')
                    teardown_worker.wait_threads_stopped()
                    gc.collect()
            except StopIteration:
                logger.info('所有 #后置用例# 已启动')
                break

        logger.info('等待所有 #后置用例# 执行完成')
        self._wait_workers_stopped()
        self.workers.clear()  # The workers have all completed now
        ContextService.clear_total_threads()
        logger.info('所有 #后置用例# 已执行完成')
        return worker_count

    def _start_worker(
        self,
        worker: TestWorker,
        worker_count: int,
        worker_searcher: SearchByClass,
        collection_component_list: list
    ) -> None:
        """启动TestWorker

        Args:
            worker:                      TestWorker
            worker_count:                TestWorker 总计（这里指序号，每启动一个 Gourp + 1）
            worker_searcher:             SearchByClass[TestWorker]
            collection_component_list:   TestCollection 子代节点（非 TestWorker 节点）

        Returns:
            None

        """
        try:
            number_of_threads = worker.number_of_threads
            worker_name = worker.name

            # 将 Collection 层的组件节点（非 TestWorker 节点）添加至 TestWorker
            worker_tree = worker_searcher.get(worker)
            worker_tree.add_key(worker).add_keys(collection_component_list)
            logger.info(f'用例:[ {worker_name} ] 线程数:[ {number_of_threads} ] 启动 #用例#')

            # 存储当前 TestWorker，用于后续管理线程（启动、停止或循环）
            self.workers.append(worker)
            worker.start(worker_count, worker_tree, self)
        except StopTestError:
            logger.info('停止运行')

    def _wait_workers_stopped(self) -> None:
        """等待所有线程执行完成"""
        for worker in self.workers:
            worker.wait_threads_stopped()

    @staticmethod
    def _notify_collection_listeners_of_start(searcher: SearchByClass) -> None:
        """遍历调用 TestCollectionListener

        Args:
            searcher: SearchByClass[TestCollectionListener]

        Returns: None

        """
        logger.debug('遍历触发 TestCollectionListener 的开始事件')
        listeners = searcher.get_search_result()
        for listener in listeners:
            listener.collection_started()

    @staticmethod
    def _notify_collection_listeners_of_end(searcher: SearchByClass) -> None:
        """遍历调用 TestCollectionListener

        Args:
            searcher: SearchByClass[TestCollectionListener]

        Returns: None

        """
        logger.debug('遍历触发 TestCollectionListener 的结束事件')
        listeners = searcher.get_search_result()
        for listener in listeners:
            listener.collection_ended()

    @staticmethod
    def _remove_workers(elements: list) -> None:
        """遍历删除 TestWorker 节点

        Args:
            elements: TestCollection 子代节点的列表

        Returns: None

        """
        # 复制 elements 后遍历
        for node in elements[:]:
            if isinstance(node, TestWorker) or not isinstance(node, TestElement):
                elements.remove(node)

    @staticmethod
    def _add_level(elements: list[TestElement]) -> None:
        for node in elements:
            if node.level is None:
                node.level = 1
