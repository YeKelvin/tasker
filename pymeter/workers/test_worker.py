#!/usr/bin python3
# @File    : test_worker.py
# @Time    : 2020/2/13 12:58
# @Author  : Kelvin.Ye
from typing import Final

import gevent
from gevent import Greenlet
from loguru import logger

from pymeter.assertions.assertion import Assertion
from pymeter.assertions.assertion import AssertionResult
from pymeter.controls.controller import IteratingController
from pymeter.controls.loop_controller import LoopController
from pymeter.controls.retry_controller import RetryController
from pymeter.controls.transaction import TransactionSampler
from pymeter.elements.element import TestElement
from pymeter.engines.hashtree import HashTree
from pymeter.engines.interface import LoopIterationListener
from pymeter.engines.interface import SampleListener
from pymeter.engines.interface import TestCompilerHelper
from pymeter.engines.interface import TestIterationListener
from pymeter.engines.interface import TestWorkerListener
from pymeter.engines.traverser import FindTestElementsUpToRoot
from pymeter.engines.traverser import SearchByClass
from pymeter.engines.traverser import TestCompiler
from pymeter.engines.traverser import TreeCloner
from pymeter.engines.variables import Variables
from pymeter.samplers.sample_result import SampleResult
from pymeter.samplers.sampler import Sampler
from pymeter.tools.exceptions import StopTestException
from pymeter.tools.exceptions import StopTestNowException
from pymeter.tools.exceptions import StopTestWorkerException
from pymeter.tools.exceptions import UserInterruptedError
from pymeter.workers.context import ContextService
from pymeter.workers.context import ThreadContext
from pymeter.workers.package import SamplePackage
from pymeter.workers.worker import LogicalAction
from pymeter.workers.worker import Worker


class TestWorker(Worker, TestCompilerHelper):

    # 运行策略
    RUNNING_STRATEGY = 'TestWorker__running_strategy'

    # 请求失败时的处理逻辑
    ON_SAMPLE_ERROR = 'TestWorker__on_sample_error'

    # 线程数
    NUMBER_OF_THREADS = 'TestWorker__number_of_threads'

    # TODO: 每秒启动的线程数
    STARTUPS_PER_SECOND = 'TestWorker__startups_per_second'

    # 循环控制器
    MAIN_CONTROLLER = 'TestWorker__main_controller'

    # 默认等待线程结束时间，单位 ms
    WAIT_TO_DIE = 5 * 1000

    @property
    def on_sample_error(self) -> str:
        return self.get_property_as_str(self.ON_SAMPLE_ERROR)

    @property
    def number_of_threads(self) -> int:
        return self.get_property_as_int(self.NUMBER_OF_THREADS)

    @property
    def startups_per_second(self) -> float:
        return self.get_property_as_int(self.STARTUPS_PER_SECOND)

    @property
    def main_controller(self) -> LoopController:
        return self.get_property(self.MAIN_CONTROLLER).get_obj()

    @property
    def on_error_continue(self) -> bool:
        return self.on_sample_error == LogicalAction.CONTINUE.value

    @property
    def on_error_start_next_thread(self) -> bool:
        return self.on_sample_error == LogicalAction.START_NEXT_ITERATION_OF_THREAD.value

    @property
    def on_error_start_next_current_loop(self) -> bool:
        return self.on_sample_error == LogicalAction.START_NEXT_ITERATION_OF_CURRENT_LOOP.value

    @property
    def on_error_break_current_loop(self) -> bool:
        return self.on_sample_error == LogicalAction.BREAK_CURRENT_LOOP.value

    @property
    def on_error_stop_worker(self) -> bool:
        return self.on_sample_error == LogicalAction.STOP_WORKER.value

    @property
    def on_error_stop_test(self) -> bool:
        return self.on_sample_error == LogicalAction.STOP_TEST.value

    @property
    def on_error_stop_now(self) -> bool:
        return self.on_sample_error == LogicalAction.STOP_NOW.value

    def __init__(self):
        super().__init__()

        self.running = False
        self.worker_number = None
        self.worker_tree = None
        self.workers: list[Coroutine] = []
        self.children: list[TestElement] = []

    def start(self, worker_number, worker_tree, engine) -> None:
        """启动 TestWorker

        Args:
            worker_number:   worker编号
            worker_tree:     worker哈希树
            engine:          测试引擎

        Returns: None

        """
        self.running = True
        self.worker_number = worker_number
        self.worker_tree = worker_tree
        context = ContextService.get_context()

        for number in range(self.number_of_threads):
            if self.running:
                self.__start_new_worker(number, engine, context)
            else:
                break

        logger.info(f'开始执行第 {self.worker_number} 个 #用例#')

    @property
    def done(self):
        """Controller API"""
        return self.main_controller.done

    @done.setter
    def done(self, value):
        """Controller API"""
        self.main_controller.done = value

    def next(self) -> Sampler:
        """Controller API"""
        return self.main_controller.next()

    def initialize(self):
        """Controller API"""
        self.main_controller.initialize()

    def trigger_end_of_loop(self):
        """Controller API"""
        self.main_controller.trigger_end_of_loop()

    def add_iteration_listener(self, listener):
        """Controller API"""
        self.main_controller.add_iteration_listener(listener)

    def remove_iteration_listener(self, listener):
        """Controller API"""
        self.main_controller.remove_iteration_listener(listener)

    def start_next_loop(self):
        """Controller API"""
        self.main_controller.start_next_loop()

    def break_loop(self):
        """Controller API"""
        self.main_controller.break_loop()

    def add_test_element(self, child):
        """TestElement API"""
        self.main_controller.add_test_element(child)

    def add_test_element_once(self, child) -> bool:
        """@override from TestCompilerHelper"""
        if child not in self.children:
            self.children.append(child)
            self.add_test_element(child)
            return True
        else:
            return False

    def wait_threads_stopped(self) -> None:
        """等待所有线程停止"""
        for worker in self.workers:
            if not worker.dead:
                worker.join(self.WAIT_TO_DIE)

    def stop_threads(self) -> None:
        """停止所有线程"""
        self.running = False
        for worker in self.workers:
            worker.stop_thread()

    def kill_threads(self) -> None:
        """杀死所有线程"""
        self.running = False
        for worker in self.workers:
            worker.stop_thread()
            worker.kill()  # TODO: 重写 kill方法，添加中断时的操作

    def __start_new_worker(self, thread_number, engine, context) -> 'Coroutine':
        """创建一个线程去执行 TestWorker

        Args:
            thread_number:  线程编号
            engine:         测试引擎
            context:        测试上下文

        Returns:
            测试线程

        """
        thread = self.__make_thread(thread_number, engine, context)
        self.workers.append(thread)
        thread.start()
        return thread

    def __make_thread(self, thread_number, engine, context) -> 'Coroutine':
        """创建一个线程

        Args:
            thread_number:  线程编号
            engine:         测试引擎
            context:        测试上下文

        Returns:
            测试线程

        """
        thread_name = f'{self.name} @ w{self.worker_number}t{thread_number + 1}'
        coroutine = Coroutine(self.__clone_worker_tree())
        coroutine.init_context(context)
        coroutine.engine = engine
        coroutine.worker = self
        coroutine.thread_number = thread_number
        coroutine.thread_name = thread_name
        coroutine.compile_strategy = (
            coroutine.worker.running_strategy or coroutine.engine.collection.running_strategy
        )
        return coroutine

    def __clone_worker_tree(self) -> HashTree:
        """深拷贝 HashTree

        目的是让每个线程持有不同的节点实例，在高并发下避免相互影响的问题
        """
        cloner = TreeCloner(True)
        self.worker_tree.traverse(cloner)
        return cloner.get_cloned_tree()


class Coroutine(Greenlet):

    LAST_SAMPLE_OK: Final = 'Coroutine__last_sample_ok'

    def __init__(self, worker_tree: HashTree, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        self.next_continue = True
        self.start_time = 0
        self.end_time = 0
        self.engine = None
        self.worker = None
        self.worker_tree = worker_tree
        self.worker_main_controller = worker_tree.list()[0]
        self.thread_name = None
        self.thread_number = None
        self.variables = Variables()
        self.compile_strategy = None
        self.compiler = TestCompiler(self.worker_tree)

        # 搜索 TestWorkerListener 节点
        worker_listener_searcher = SearchByClass(TestWorkerListener)
        self.worker_tree.traverse(worker_listener_searcher)
        self.worker_listeners = worker_listener_searcher.get_search_result()

        # 搜索 TestIterationListener 节点
        test_iteration_listener_searcher = SearchByClass(TestIterationListener)
        self.worker_tree.traverse(test_iteration_listener_searcher)
        self.test_iteration_listeners = test_iteration_listener_searcher.get_search_result()

    def init_context(self, context: ThreadContext) -> None:
        """将父线程（运行 StandardEngine 的线程）的局部变量赋值给子线程的局部变量中"""
        self.variables.update(context.variables)

    def init_run(self, context: ThreadContext) -> None:
        """运行初始化

        初始化包括：
            1、给 CoroutineContext 赋值
            2、将 TestWorker 的非 Sampler/Controller 节点传递给子代
            3、编译子代节点
        """
        context.engine = self.engine
        context.worker = self.worker
        context.thread = self
        context.thread_name = self.thread_name
        context.thread_number = self.thread_number
        context.variables = self.variables
        context.variables.put(self.LAST_SAMPLE_OK, True)

        # loguru注入trace_id和socket_id
        ContextService.init_loguru()

        # 编译 TestWorker 的子代节点
        logger.debug('开始编译用例节点')
        # logger.debug(f'TestWorker的HashTree结构:\n{self.worker_tree}')
        self.compiler.strategy = self.compile_strategy
        self.worker_tree.traverse(self.compiler)
        logger.debug('用例节点编译完成')
        # logger.debug(f'TestWorker的HashTree结构:\n{self.worker_tree}')

        # 初始化 TestWorker 控制器
        self.worker_main_controller.initialize()

        # 添加 TestWorker 迭代监听器
        worker_iteration_listener = self.IterationListener(self)
        self.worker_main_controller.add_iteration_listener(worker_iteration_listener)

        # 遍历执行 TestWorkerListener
        self.__coroutine_started()

    def _run(self, *args, **kwargs):
        """执行线程的入口"""
        context = ContextService.get_context()
        self.init_run(context)
        # noinspection PyBroadException
        try:
            while self.running:
                # 获取下一个Sampler
                sampler = self.worker_main_controller.next()
                # 循环处理Sampler
                while self.running and sampler:
                    # 判断用户是否主动中断
                    if self.engine.is_interrupted():
                        raise UserInterruptedError()
                    # 处理Sampler
                    self.__process_sampler(sampler, parent=None, context=context)
                    # Sampler失败且非继续执行时，根据 on_sample_error 选项来控制迭代
                    last_sample_ok = context.variables.get(self.LAST_SAMPLE_OK)
                    if not self.next_continue or (not last_sample_ok and self.worker.on_error_continue):
                        self.__control_loop_by_logical_action(sampler, context)
                        self.next_continue = True
                        sampler = None
                    else:
                        sampler = self.worker_main_controller.next()  # 获取下一个 Sample
                # 如果主控制器标记已完成，则结束迭代
                if self.worker_main_controller.done:
                    self.running = False
                    logger.info(f'线程:[ {self.thread_name} ] 已停止，执行结束')
        except StopTestWorkerException:
            logger.debug(f'线程:[ {self.thread_name} ] 捕获异常:[ StopTestWorkerException ] 停止执行用例')
            self.stop_worker()
        except StopTestException:
            logger.debug(f'线程:[ {self.thread_name} ] 捕获异常:[ StopTestException ] 停止执行测试')
            self.stop_test()
        except StopTestNowException:
            logger.debug(f'线程:[ {self.thread_name} ] 捕获:[ StopTestNowException ] 立即停止执行')
            self.stop_now()
        except UserInterruptedError:
            logger.warning('用户主动中断，立即停止测试')
            self.stop_now()
        except Exception:
            logger.exception('Exception Occurred')
        finally:
            logger.info(f'线程:[ {self.thread_name} ] 已执行完成')
            self.__coroutine_finished()  # 遍历执行 TestWorkerListener
            context.clear()
            ContextService.remove_context()

    def __coroutine_started(self) -> None:
        """线程开始时的一系列操作

        包括：
            1、ContextService 统计线程数
            2、遍历执行 TestWorkerListener
        """
        ContextService.incr_number_of_threads()
        logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 TestWorkerListener 的开始事件')
        for listener in self.worker_listeners:
            listener.worker_started()

    def __coroutine_finished(self) -> None:
        """线程结束时的一系列操作

        包括：
            1、ContextService 统计线程数
            2、遍历执行 TestWorkerListener
        """
        logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 TestWorkerListener 的完成事件')
        for listener in self.worker_listeners:
            listener.worker_finished()
        ContextService.decr_number_of_threads()

    def __control_loop_by_logical_action(self, sampler: Sampler, context: ThreadContext) -> None:
        # 重试失败的 Sampler
        if self.is_retrying_sampler(sampler):
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，重试当前请求')
            self.__trigger_loop_logical_action_on_parent_controllers(sampler, context, self.__continue_on_retry)

        # 错误时开始下一个 TestWorker 循环
        elif self.worker.on_error_start_next_thread:
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，开始下一个主循环')
            self.__trigger_loop_logical_action_on_parent_controllers(sampler, context, self.__continue_on_main_loop)

        # 错误时开始下一个当前控制器循环
        elif self.worker.on_error_start_next_current_loop:
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，开始下一个当前循环')
            self.__trigger_loop_logical_action_on_parent_controllers(sampler, context, self.__continue_on_current_loop)

        # 错误时中断当前控制器循环
        elif self.worker.on_error_break_current_loop:
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，中止当前循环')
            self.__trigger_loop_logical_action_on_parent_controllers(sampler, context, self.__break_on_current_loop)

        # 错误时停止线程
        elif self.worker.on_error_stop_worker:
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，停止主线程')
            self.stop_worker()

        # 错误时停止测试
        elif self.worker.on_error_stop_test:
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，停止测试')
            self.stop_test()

        # 错误时立即停止测试（中断所有线程）
        elif self.worker.on_error_stop_now:
            logger.debug(f'线程:[ {self.thread_name} ] 最后一次请求失败，立即停止测试')
            self.stop_now()

    def __trigger_loop_logical_action_on_parent_controllers(
            self,
            sampler: Sampler,
            context: ThreadContext,
            loop_logical_action
    ):
        real_sampler = self.__find_real_sampler(sampler)

        if not real_sampler:
            raise RuntimeError(f'Got null subSampler calling findRealSampler for:[ {sampler} ]')

        # 查找父级 Controllers
        path_to_root_traverser = FindTestElementsUpToRoot(real_sampler)
        self.worker_tree.traverse(path_to_root_traverser)

        loop_logical_action(path_to_root_traverser)

        # When using Start Next Loop option combined to TransactionController.
        # if an error occurs in a Sample (child of TransactionController)
        # then we still need to report the Transaction in error (and create the sample result)
        if isinstance(sampler, TransactionSampler) and sampler.done:
            transaction_package = self.compiler.configure_trans_sampler(sampler)
            self.__do_end_transaction_sampler(sampler, transaction_package, None, context)

    def is_retrying_sampler(self, sampler: Sampler):
        return (
            getattr(sampler, 'retrying', False) or  # noqa
            (
                isinstance(sampler, TransactionSampler) and  # noqa
                getattr(self.__find_real_sampler(sampler), 'retrying', False)  # noqa
            )  # noqa
        )

    def __find_real_sampler(self, sampler: Sampler):
        real_sampler = sampler
        while isinstance(real_sampler, TransactionSampler):
            real_sampler = real_sampler.sub_sampler
        return real_sampler

    def __process_sampler(
            self,
            current: Sampler,
            parent: Sampler,
            context: ThreadContext
    ) -> SampleResult:
        """执行 Sampler"""
        logger.debug(f'线程:[ {self.thread_name} ] 当前请求:[ {current} ]')

        transaction_result = None
        transaction_sampler = None
        transaction_package = None

        if isinstance(current, TransactionSampler):
            transaction_sampler = current
            transaction_package = self.compiler.configure_trans_sampler(transaction_sampler)

            # 检查事务是否已完成
            if current.done:
                transaction_result = self.__do_end_transaction_sampler(
                    transaction_sampler,
                    transaction_package,
                    parent,
                    context
                )
                # 事务已完成，Sampler 无需继续执行
                current = None
            else:
                # 事务开始时，遍历执行 TransactionListener
                if transaction_sampler.calls == 0:
                    logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 TransactionListener 的开始事件')
                    for listener in transaction_package.trans_listeners:
                        listener.transaction_started()
                # 获取 Transaction 直接子代
                prev = current
                current = transaction_sampler.sub_sampler
                # 如果 Transaction 直接子代还是 Transaction，则递归执行
                if isinstance(current, TransactionSampler):
                    result = self.__process_sampler(current, prev, context)  # 递归处理
                    context.set_current_sampler(prev)
                    current = None  # 当前 Sampler 为事务，无需继续执行
                    if result:
                        transaction_sampler.add_sub_sampler_result(result)

        # 执行 Sampler 和 SamplerPackage，不包含 TransactionSampler
        if current:
            self.__execute_sample_package(current, transaction_sampler, transaction_package, context)

        # 线程已经停止运行但事务未生成结果时，手动结束事务
        if (
            not self.running  # noqa
            and transaction_result is None  # noqa
            and transaction_sampler is not None  # noqa
            and transaction_package is not None  # noqa
        ):
            transaction_result = self.__do_end_transaction_sampler(
                transaction_sampler,
                transaction_package,
                parent,
                context
            )

        return transaction_result

    def __execute_sample_package(
            self,
            sampler: Sampler,
            transaction_sampler: TransactionSampler,
            transaction_package: SamplePackage,
            context: ThreadContext
    ) -> None:
        """执行请求"""
        # 上下文存储当前sampler
        context.set_current_sampler(sampler)
        # 获取sampler对应的package
        package = self.compiler.configure_sampler(sampler)

        # 执行前置处理器
        self.__run_prev_processors(package.prev_processors)
        # 执行时间控制器
        self.__run_timers(package.timers)

        # 执行请求
        result = None
        if self.running:
            result = self.__do_sampling(sampler, context, package.listeners)

        if not result:
            package.done()
            return

        # 设置为上一个结果
        context.set_previous_result(result)

        # 执行后置处理器
        self.__run_post_processors(package.post_processors)

        # 执行断言
        self.__check_assertions(package.assertions, result, context)

        # 添加重试标识，标识来自 RetryController
        retrying = getattr(sampler, 'retrying', False)
        if retrying:
            result.retrying = True
        if retryflag := getattr(sampler, 'retry_flag', None):
            result.sample_name = f'{result.sample_name} {retryflag}' if retryflag else result.sample_name

        # 遍历执行 SampleListener
        logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 SampleListener 的发生事件')
        sample_listeners = self.__get_sample_listeners(package, transaction_package, transaction_sampler)
        for listener in sample_listeners:
            listener.sample_occurred(result)

        package.done()

        # Add the result as subsample of transaction if we are in a transaction
        if transaction_sampler:
            transaction_sampler.add_sub_sampler_result(result)

        # 检查是否需要停止线程或测试
        if result.stop_worker or (not result.success and self.worker.on_error_stop_worker):
            logger.info(f'线程:[ {self.thread_name} ] 用户手动设置停止测试组')
            self.stop_thread()
        if result.stop_test or (not result.success and self.worker.on_error_stop_test):
            logger.info(f'线程:[ {self.thread_name} ] 用户手动设置停止测试')
            self.stop_test()
        if result.stop_now or (not result.success and self.worker.on_error_stop_now):
            logger.info(f'线程:[ {self.thread_name} ] 用户手动设置立即停止测试')
            self.stop_now()
        if not result.success:
            self.next_continue = False

    def __do_sampling(self, sampler: Sampler, context: ThreadContext, listeners: list) -> SampleResult:
        """执行Sampler"""
        sampler.context = context

        # 遍历执行 SampleListener
        logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 SampleListener 的开始事件')
        for listener in listeners:
            listener.sample_started(sampler)

        result = None
        try:
            logger.info(f'线程:[ {self.thread_name} ] 请求:[ {sampler.name} ] 开始请求')
            result = sampler.sample()
        except Exception as err:
            logger.exception('Exception Occurred')
            if not result:
                result = SampleResult()
                result.sample_name = sampler.name
            result.response_data = str(err)
        finally:
            # 遍历执行 SampleListener
            logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 SampleListener 的结束事件')
            for listener in listeners:
                listener.sample_ended(result)

            return result

    def __do_end_transaction_sampler(
            self,
            transaction_sampler: TransactionSampler,
            transaction_package: SamplePackage,
            parent: Sampler,
            context: ThreadContext
    ) -> SampleResult:
        logger.debug(
            f'线程:[ {self.thread_name} ] 事务:[ {transaction_sampler} ] 父元素:[ {parent} ] 结束事务'
        )

        # 上下文存储当前sampler（事务）
        context.set_current_sampler(transaction_sampler)

        # Get the transaction sample result
        result = transaction_sampler.result

        # Check assertions for the transaction sample
        self.__check_assertions(transaction_package.assertions, result, context)

        #  Notify listeners with the transaction sample result
        if not isinstance(parent, TransactionSampler):
            # 遍历执行 SampleListener
            logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 SampleListener 的发生事件')
            for listener in transaction_package.listeners:
                listener.sample_occurred(result)

        # 遍历执行 TransactionListener
        logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 TransactionListener 的结束事件')
        for listener in transaction_package.trans_listeners:
            listener.transaction_ended()

        # 标记事务已完成
        transaction_package.done()
        return result

    def __run_timers(self, timers: list):
        total_delay = 0
        for timer in timers:
            delay = timer.delay()
            total_delay = total_delay + delay
        if total_delay > 0:
            gevent.sleep(float(total_delay / 1000))

    def __get_sample_listeners(
            self,
            sample_package: SamplePackage,
            transaction_package: SamplePackage,
            transaction_sampler: TransactionSampler
    ) -> list[SampleListener]:
        sampler_listeners = sample_package.listeners
        # Do not send subsamples to listeners which receive the transaction sample
        if transaction_sampler:
            only_subsampler_listeners = []
            for listener in sample_package.listeners:
                # 检查在 TransactionListenerList 中是否有重复的 listener
                found = any(trans is listener for trans in transaction_package.listeners)
                if not found:
                    only_subsampler_listeners.append(listener)

            sampler_listeners = only_subsampler_listeners

        return sampler_listeners

    def __continue_on_retry(self, path_to_root_traverser) -> None:
        """Sampler 失败时，继续 Sampler 的父控制器循环"""
        controllers_to_reinit = path_to_root_traverser.get_controllers_to_root()
        for parent_controller in controllers_to_reinit:
            if isinstance(parent_controller, TestWorker):
                parent_controller.start_next_loop()
            elif isinstance(parent_controller, RetryController):
                parent_controller.start_next_loop()
                break
            else:
                parent_controller.trigger_end_of_loop()

    def __continue_on_main_loop(self, path_to_root_traverser) -> None:
        """Sampler 失败时，继续 TestWorker 控制器的循环"""
        controllers_to_reinit = path_to_root_traverser.get_controllers_to_root()
        for parent_controller in controllers_to_reinit:
            if isinstance(parent_controller, TestWorker):
                parent_controller.start_next_loop()
            else:
                parent_controller.trigger_end_of_loop()

    def __continue_on_current_loop(self, path_to_root_traverser) -> None:
        """Sampler 失败时，继续 Sampler 的父控制器循环"""
        controllers_to_reinit = path_to_root_traverser.get_controllers_to_root()
        for parent_controller in controllers_to_reinit:
            if isinstance(parent_controller, TestWorker):
                parent_controller.start_next_loop()
            elif isinstance(parent_controller, IteratingController):
                parent_controller.start_next_loop()
                break
            else:
                parent_controller.trigger_end_of_loop()

    def __break_on_current_loop(self, path_to_root_traverser) -> None:
        """Sampler 失败时，中断 Sampler 的父控制器循环"""
        controllers_to_reinit = path_to_root_traverser.get_controllers_to_root()
        for parent_controller in controllers_to_reinit:
            if isinstance(parent_controller, TestWorker):
                parent_controller.break_loop()
            elif isinstance(parent_controller, IteratingController):
                parent_controller.break_loop()
                break
            else:
                parent_controller.trigger_end_of_loop()

    def _notify_test_iteration_listeners(self) -> None:
        """遍历执行 TestIterationListener"""
        logger.debug(f'线程:[ {self.thread_name} ] 遍历触发 TestIterationListener 的开始事件')
        self.variables.iteration += 1
        for listener in self.test_iteration_listeners:
            listener.test_iteration_start(self.worker_main_controller, self.variables.iteration)
            if isinstance(listener, TestElement):
                listener.recover_running_version()

    def stop_thread(self) -> None:
        self.running = False

    def stop_worker(self) -> None:
        logger.info(f'线程:[ {self.thread_name} ] 停止主线程发起')
        self.worker.stop_threads()

    def stop_test(self) -> None:
        logger.info(f'线程:[ {self.thread_name} ] 停止测试')
        self.running = False
        if self.engine:
            self.engine.stop_test()

    def stop_now(self) -> None:
        logger.info(f'线程:[ {self.thread_name} ] 立即停止测试')
        self.running = False
        if self.engine:
            self.engine.stop_test_now()

    def __run_prev_processors(self, prev_processors: list) -> None:
        """执行前置处理器"""
        for prev_processor in prev_processors:
            logger.debug(f'线程:[ {self.thread_name} ] 前置处理器:[ {prev_processor.name} ] 正在运行中')
            prev_processor.process()

    def __run_post_processors(self, post_processors: list) -> None:
        """执行后置处理器"""
        for post_processor in post_processors:
            logger.debug(f'线程:[ {self.thread_name} ] 后置处理器:[ {post_processor.name} ] 正在运行中')
            post_processor.process()

    def __check_assertions(self, assertions: list[Assertion], result: SampleResult, context: ThreadContext) -> None:
        """断言取样结果"""
        for assertion in assertions:
            logger.debug(f'线程:[ {self.thread_name} ] 断言器:[ {assertion.name} ] 正在运行中')
            self.__process_assertion(assertion, result)

        logger.debug(
            f'线程:[ {self.thread_name} ] 请求:[ {result.sample_name} ] 设置变量 LAST_SAMPLE_OK={result.success}'
        )
        # 存储取样结果
        context.variables.put(self.LAST_SAMPLE_OK, result.success)

    def __process_assertion(self, assertion: Assertion, sample_result: SampleResult) -> None:
        """执行断言"""
        assertion_result = None
        try:
            assertion_result = assertion.get_result(sample_result)
        except AssertionError as e:
            logger.debug(f'线程:[ {self.thread_name} ] 请求:[ {sample_result.sample_name} ] 断言器: {e}')
            assertion_result = AssertionResult(sample_result.sample_name)
            assertion_result.failure = True
            assertion_result.message = str(e)
        except RuntimeError as e:
            logger.error(f'线程:[ {self.thread_name} ] 请求:[ {sample_result.sample_name} ] 断言器: {e}')
            assertion_result = AssertionResult(sample_result.sample_name)
            assertion_result.error = True
            assertion_result.message = str(e)
        except Exception as e:
            logger.error(f'线程:[ {self.thread_name} ] 请求:[ {sample_result.sample_name} ] 断言器: {e}')
            logger.exception('Exception Occurred')
            assertion_result = AssertionResult(sample_result.sample_name)
            assertion_result.error = True
            assertion_result.message = str(e)
        finally:
            sample_result.success = (
                sample_result.success and not assertion_result.error and not assertion_result.failure
            )
            sample_result.assertions.append(assertion_result)

    class IterationListener(LoopIterationListener):
        """Coroutine 内部类，用于在 TestWorker 迭代开始时触发所有实现类的开始动作"""

        def __init__(self, parent: 'Coroutine'):
            self.parent = parent

        def iteration_start(self, source, iter) -> None:
            self.parent._notify_test_iteration_listeners()
