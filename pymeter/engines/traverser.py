#!/usr/bin python3
# @File    : traverser
# @Time    : 2020/2/25 15:06
# @Author  : Kelvin.Ye
from collections import deque
from typing import Generic
from typing import TypeVar

from loguru import logger

from pymeter.assertions.assertion import Assertion
from pymeter.controls.controller import Controller
from pymeter.controls.transaction import TransactionController
from pymeter.controls.transaction import TransactionSampler
from pymeter.elements.element import ConfigElement
from pymeter.elements.element import TestElement
from pymeter.engines.interface import LoopIterationListener
from pymeter.engines.interface import NoConfigMerge
from pymeter.engines.interface import NoThreadClone
from pymeter.engines.interface import SampleListener
from pymeter.engines.interface import TestCompilerHelper
from pymeter.engines.interface import TransactionConfig
from pymeter.engines.interface import TransactionListener
from pymeter.processors.post import PostProcessor
from pymeter.processors.prev import PrevProcessor
from pymeter.samplers.sampler import Sampler
from pymeter.timers.timer import Timer
from pymeter.tools.logical_operator import calculate_condition
from pymeter.workers.package import SamplePackage
from pymeter.workers.worker import Worker


# 调试日志开关
DEBUG = False

# 定义泛型
T = TypeVar('T')


def pretty_output_stack(list):
    output = ['[', '\n']
    index = ' ' * 4
    for i in list:
        output.extend((index, str(i), ',\n'))
    output.append(']')
    return ''.join(output)

class HashTreeTraverser:

    def add_node(self, node, subtree) -> None:
        """添加节点时的处理"""
        raise NotImplementedError

    def subtract_node(self) -> None:
        """移除节点时的处理（递归回溯）"""
        raise NotImplementedError

    def process_path(self) -> None:
        """到达路径末端时的处理"""
        raise NotImplementedError


class TreeSearcher(HashTreeTraverser):

    FOUND = 'found'

    def __init__(self, target: object):
        self.target = target
        self.result = None

    def add_node(self, node, subtree) -> None:
        if subtree.get(self.target):
            raise RuntimeError(self.FOUND)

    def subtract_node(self) -> None:
        """@override"""
        pass

    def process_path(self) -> None:
        """@override"""
        pass


class ConvertToString(HashTreeTraverser):

    def __init__(self):
        self.string = ['{']
        self.spaces = []
        self.depth = 0

    def add_node(self, node, subtree) -> None:
        """@override"""
        self.depth += 1
        self.string.append('\n')
        self.string.append(self.__get_spaces())
        self.string.append(str(node))
        self.string.append(' {')

    def subtract_node(self) -> None:
        """@override"""
        self.string.append('\n')
        self.string.append(self.__get_spaces())
        self.string.append('}')
        self.depth -= 1

    def process_path(self) -> None:
        """@override"""
        pass

    def __get_spaces(self):
        if len(self.spaces) < self.depth * 2:
            while len(self.spaces) < self.depth * 2:
                self.spaces.append('  ')
        elif len(self.spaces) > self.depth * 2:
            self.spaces = self.spaces[:self.depth * 2]
        return ''.join(self.spaces)

    def __str__(self):
        self.string.append('\n}')
        return ''.join(self.string)

    def __repr__(self):
        return self.__str__()


class SearchByClass(HashTreeTraverser, Generic[T]):

    def __init__(self, search_class: T):
        self.objects_of_class = []
        self.subtrees = {}
        self.search_class = search_class

    @property
    def count(self) -> int:
        return len(self.objects_of_class)

    def get_search_result(self) -> list[T]:
        return self.objects_of_class

    def get(self, node: object):
        return self.subtrees.get(node)

    def add_node(self, node, subtree) -> None:
        """@override"""
        if isinstance(node, self.search_class):
            self.objects_of_class.append(node)
            from pymeter.engines.hashtree import HashTree
            tree = HashTree()
            tree.put(node, subtree)
            self.subtrees[node] = tree

    def subtract_node(self) -> None:
        """@override"""
        pass

    def process_path(self) -> None:
        """@override"""
        pass


class TreeCloner(HashTreeTraverser):
    """克隆 HashTree，默认情况下跳过实现 NoThreadClone 的节点"""

    def __init__(self, enable_no_clone: bool = True):
        from pymeter.engines.hashtree import HashTree
        self.new_tree = HashTree()
        self.tree_path = []
        self.enable_no_clone = enable_no_clone

    def get_cloned_tree(self):
        return self.new_tree

    def add_node(self, node, subtree) -> None:
        """@override"""
        clone = not (self.enable_no_clone and isinstance(node, NoThreadClone))
        cloned_node = node.clone() if isinstance(node, TestElement) and clone else node
        self.new_tree.add_key_by_treepath(self.tree_path, cloned_node)
        self.tree_path.append(cloned_node)

    def subtract_node(self) -> None:
        """@override"""
        if self.tree_path:
            del self.tree_path[-1]

    def process_path(self) -> None:
        """@override"""
        pass


class TestCompiler(HashTreeTraverser):

    def __init__(self, tree):
        self.stack = deque()
        self.strategy = None
        self.hashtree = tree
        self.sample_packages: dict[Sampler, SamplePackage] = {}
        self.trans_packages: dict[TransactionController, SamplePackage] = {}

    def configure_sampler(self, sampler) -> SamplePackage:
        package = self.sample_packages.get(sampler)
        package.sampler = sampler
        self.configure_with_config_elements(sampler, package.configs)
        return package

    def configure_trans_sampler(self, trans_sampler: TransactionSampler) -> SamplePackage:
        controller = trans_sampler.controller
        package = self.trans_packages.get(controller)
        package.sampler = trans_sampler
        return package

    def add_node(self, node, subtree) -> None:
        """@override"""
        if DEBUG:
            logger.debug(f'添加节点: {node}')
        self.stack.append(node)

    def subtract_node(self) -> None:
        """@override"""
        child = self.stack[-1]
        if DEBUG:
            logger.debug('回溯节点')
            logger.debug(f'堆栈大小:[ {len(self.stack)} ] 堆栈:[ {pretty_output_stack(self.stack)} ]')
            logger.debug(f'子节点:[ {child} ]')

        # 如果子节点为LoopIterationListener则将其添加至路径上所有的父控制器中
        self.track_iteration_listeners(child)

        # 配置取样包
        if isinstance(child, Sampler):
            self.save_sample_package(child)
        elif isinstance(child, TransactionController):
            self.save_trans_package(child)

        # 移除最后一个节点（当前child）
        self.stack.pop()
        if len(self.stack) == 0:
            return

        parent = self.stack[-1]
        if DEBUG:
            logger.debug(f'父节点:[ {parent} ]')

        # 添加节点层级
        if child.level is None and not isinstance(child, Controller | Sampler):
            if isinstance(parent, Worker):
                child.level = 2
            elif isinstance(parent, Controller):
                child.level = 3
            else: # Sampler
                child.level = 4

        duplicate = False
        if isinstance(parent, Controller) and isinstance(child, Sampler | Controller):
            if isinstance(parent, TestCompilerHelper):
                duplicate = not parent.add_test_element_once(child)
            else:
                parent.add_test_element(child)

        # 重复时警告
        if duplicate:
            logger.warning(f'Unexpected duplicate for {parent} and {child}')

    def process_path(self) -> None:
        """@override"""
        pass

    def track_iteration_listeners(self, child):
        if not isinstance(child, LoopIterationListener):
            return
        for i in range(len(self.stack) - 1, -1, -1):  # 倒序遍历
            item = self.stack[i]
            if item == child:
                continue
            if isinstance(item, Controller):
                item.add_iteration_listener(child)

    def save_sample_package(self, sampler):  # sourcery skip: low-code-quality
        strategy = self.get_merged_strategy(sampler.running_strategy)
        filter_rule = strategy.get('filter', {})
        reverse_order = strategy.get('reverse', [])

        configs = deque()
        controllers = deque()
        listeners = deque()
        trans_listeners = deque()
        prevs = deque()
        posts = deque()
        assertions = deque()
        timers = deque()

        if DEBUG:
            logger.debug(f'请求:[ {sampler} ] 开始配置取样包')
        for i in range(len(self.stack) - 1, -1, -1):  # 倒序遍历
            maybe_controller = self.stack[i]
            if isinstance(maybe_controller, Controller):
                controllers.append(maybe_controller)
            temp_prevs = deque()
            temp_posts = deque()
            temp_assertions = deque()
            treepath = self.hashtree.list_by_treepath([self.stack[x] for x in range(i + 1)])
            if DEBUG:
                logger.debug(f'当前索引:[ {i} ] 树路径:[ {pretty_output_stack(treepath)} ]')
            for item in treepath:
                if isinstance(item, ConfigElement) and not isinstance(item, TransactionConfig):
                    configs.append(item)
                if isinstance(item, SampleListener):
                    listeners.append(item)
                if isinstance(item, PrevProcessor) and not self.is_filtered_component(item, filter_rule):
                    temp_prevs.append(item)
                if isinstance(item, PostProcessor) and not self.is_filtered_component(item, filter_rule):
                    temp_posts.append(item)
                if isinstance(item, Assertion) and not self.is_filtered_component(item, filter_rule):
                    temp_assertions.append(item)
                if isinstance(item, Timer):
                    timers.append(item)

            prevs.extendleft(list(temp_prevs)[::-1])
            posts.extendleft(list(temp_posts)[::-1])
            assertions.extendleft(list(temp_assertions)[::-1])

        # 根据配置排序
        sorted_prevs = sorted(prevs, key=lambda x:x.level, reverse=('PREV' in reverse_order))
        sorted_posts = sorted(posts, key=lambda x:x.level, reverse=('POST' in reverse_order))
        sorted_assertions = sorted(assertions, key=lambda x:x.level, reverse=('ASSERT' in reverse_order))

        if DEBUG:
            logger.debug(f'请求:[ {sampler} ] 取样包配置完成')

        package = SamplePackage(
            list(configs),
            list(listeners),
            list(controllers),
            list(trans_listeners),
            list(sorted_prevs),
            list(sorted_posts),
            list(sorted_assertions),
            list(timers)
        )
        package.sampler = sampler
        package.set_running_version(True)
        self.sample_packages[sampler] = package

    def save_trans_package(self, trans_controller: TransactionController):  # sourcery skip: low-code-quality
        configs = deque()
        controllers = deque()
        listeners = deque()
        trans_listeners = deque()
        prevs = deque()
        posts = deque()
        assertions = deque()
        timers = deque()
        trans_configs = deque()
        trans_samplers = deque()

        if DEBUG:
            logger.debug(f'事务:[ {trans_controller} ] 开始配置取样包')
        for i in range(direct_level := len(self.stack) - 1, -1, -1):
            maybe_controller = self.stack[i]
            if isinstance(maybe_controller, Controller):
                controllers.append(maybe_controller)
            treepath = self.hashtree.list_by_treepath([self.stack[x] for x in range(i + 1)])
            if DEBUG:
                logger.debug(f'当前索引:[ {i} ] 树路径:[ {pretty_output_stack(treepath)} ]')
            for item in treepath:
                if isinstance(item, SampleListener):
                    listeners.append(item)
                if isinstance(item, Assertion):
                    assertions.append(item)
                # 添加 Transaction 直系子代
                if i == direct_level:
                    if isinstance(item, TransactionListener):
                        trans_listeners.append(item)
                    if isinstance(item, ConfigElement) and isinstance(item, TransactionConfig):
                        trans_configs.append(item)
                    # 临时存储 Transaction 直系取样器
                    if isinstance(item, Sampler):
                        trans_samplers.append(item)
        if DEBUG:
            logger.debug(f'事务:[ {trans_controller} ] 取样包配置完成')

        for sampler in trans_samplers:
            sampler_package = self.sample_packages.get(sampler)
            temp_config = deque()
            temp_config.extend(sampler_package.configs)
            temp_config.extendleft(trans_configs)
            sampler_package.configs = temp_config

        package = SamplePackage(
            list(configs),
            list(listeners),
            list(controllers),
            list(trans_listeners),
            list(prevs),
            list(posts),
            list(assertions),
            list(timers)
        )
        package.sampler = TransactionSampler(trans_controller, trans_controller.name)
        package.set_running_version(True)
        self.trans_packages[trans_controller] = package

    def get_merged_strategy(self, sampler_strategy):
        strategy = self.strategy
        if sampler_strategy and (sampler_strategy.get('filter') or sampler_strategy.get('reverse')):
            strategy = sampler_strategy
        return strategy

    def configure_with_config_elements(self, sampler: Sampler, configs: list):
        sampler.clear_test_element_children()
        for config in configs:
            if not isinstance(config, NoConfigMerge):
                sampler.add_test_element(config)

    def is_filtered_component(self, node: TestElement, filter_rule: dict):
        if not filter_rule:
            return False

        return not calculate_condition(
            rule=filter_rule,
            actual_values = {
                'TYPE': node.TYPE,
                'LEVEL': str(node.level)
            }
        )


class FindTestElementsUpToRoot(HashTreeTraverser):

    def __init__(self, node_to_find: object):
        self.stack = deque()
        self.node_to_find = node_to_find
        self.stop_recording = False

    def get_controllers_to_root(self) -> list[Controller]:
        result = []
        stack_copy = self.stack.copy()
        while len(stack_copy) > 0:
            element = stack_copy[-1]
            if isinstance(element, Controller):
                result.append(element)

            stack_copy.pop()

        return result

    def add_node(self, node, subtree) -> None:
        """@override"""
        if self.stop_recording:
            return

        if node is self.node_to_find:
            self.stop_recording = True

        self.stack.append(node)

    def subtract_node(self) -> None:
        """@override"""
        if self.stop_recording:
            return

        self.stack.pop()

    def process_path(self) -> None:
        """@override"""
        pass
