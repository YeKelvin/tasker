#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : traverser
# @Time    : 2020/2/25 15:06
# @Author  : Kelvin.Ye
from collections import deque
from typing import Dict
from typing import List

from pymeter.assertions.assertion import Assertion
from pymeter.controls.controller import Controller
from pymeter.controls.transaction import TransactionController
from pymeter.controls.transaction import TransactionSampler
from pymeter.elements.element import ConfigElement
from pymeter.elements.element import TestElement
from pymeter.engine.interface import LoopIterationListener
from pymeter.engine.interface import NoConfigMerge
from pymeter.engine.interface import NoCoroutineClone
from pymeter.engine.interface import SampleListener
from pymeter.groups.package import SamplePackage
from pymeter.processors.post import PostProcessor
from pymeter.processors.pre import PreProcessor
from pymeter.samplers.sampler import Sampler
from pymeter.timers.timer import Timer
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


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
        result = subtree.get(self.target)
        if result:
            raise RuntimeError(self.FOUND)

    def subtract_node(self) -> None:
        pass

    def process_path(self) -> None:
        pass


class ConvertToString(HashTreeTraverser):

    def __init__(self):
        self.string = ['{']
        self.spaces = []
        self.depth = 0

    def add_node(self, node, subtree) -> None:
        self.depth += 1
        self.string.append('\n')
        self.string.append(self.__get_spaces())
        self.string.append(str(node))
        self.string.append(' {')

    def subtract_node(self) -> None:
        self.string.append('\n')
        self.string.append(self.__get_spaces())
        self.string.append('}')
        self.depth -= 1

    def process_path(self) -> None:
        pass

    def __get_spaces(self):
        if len(self.spaces) < self.depth * 2:
            while len(self.spaces) < self.depth * 2:
                self.spaces.append('  ')
        elif len(self.spaces) > self.depth * 2:
            self.spaces = self.spaces[0:self.depth * 2]
        return ''.join(self.spaces)

    def __str__(self):
        self.string.append('\n}')
        return ''.join(self.string)

    def __repr__(self):
        return self.__str__()


class SearchByClass(HashTreeTraverser):

    def __init__(self, search_class: type):
        self.objects_of_class = []
        self.subtrees = {}
        self.search_class = search_class

    def get_search_result(self) -> list:
        return self.objects_of_class

    def get_subtree(self, node: object):
        return self.subtrees.get(node)

    def add_node(self, node, subtree) -> None:
        if isinstance(node, self.search_class):
            self.objects_of_class.append(node)
            from pymeter.engine.tree import HashTree
            tree = HashTree()
            tree.put(node, subtree)
            self.subtrees[node] = tree

    def subtract_node(self) -> None:
        pass

    def process_path(self) -> None:
        pass


class TreeCloner(HashTreeTraverser):
    """克隆 HashTree，默认情况下跳过实现 NoCoroutineClone 的节点"""

    def __init__(self, enable_no_clone: bool = True):
        from pymeter.engine.tree import HashTree
        self.new_tree = HashTree()
        self.tree_path = []
        self.enable_no_clone = enable_no_clone

    def get_cloned_tree(self):
        return self.new_tree

    def add_node(self, node, subtree) -> None:
        clone = not (self.enable_no_clone and isinstance(node, NoCoroutineClone))
        if isinstance(node, TestElement) and clone:
            cloned_node = node.clone()
        else:
            cloned_node = node

        self.new_tree.add_key_by_treepath(self.tree_path, cloned_node)
        self.tree_path.append(cloned_node)

    def subtract_node(self) -> None:
        if self.tree_path:
            del self.tree_path[-1]

    def process_path(self) -> None:
        pass


class TestCompiler(HashTreeTraverser):

    PAIRING: list = []

    @classmethod
    def initialize(cls):
        cls.PAIRING.clear()

    def __init__(self, tree):
        self.stack = deque()

        self.sampler_config_dict: Dict[Sampler, SamplePackage] = {}
        self.transaction_controller_config_dict: Dict[TransactionController, SamplePackage] = {}

        self.test_tree = tree

    def configure_sampler(self, sampler) -> SamplePackage:
        log.debug(f'configure sampler:[ {sampler} ]')
        package = self.sampler_config_dict.get(sampler)
        package.sampler = sampler
        self.__configure_with_config_elements(sampler, package.configs)
        return package

    def configure_transaction_sampler(self, transaction_sampler: TransactionSampler) -> SamplePackage:
        log.debug(f'configure transaction sampler:[ {transaction_sampler} ]')
        controller = transaction_sampler.transaction_controller
        package = self.transaction_controller_config_dict.get(controller)
        package.sampler = transaction_sampler
        return package

    def done(self, package) -> None:
        log.debug('SamplerPackage Done')
        package.recover_running_version()

    def add_node(self, node, subtree):
        """@override"""
        self.stack.append(node)

    def subtract_node(self):
        """@override"""
        log.debug(f'subtracting node, stack size:[ {len(self.stack)} ]')
        child = self.stack[-1]
        log.debug(f'current child:[ {child} ]')
        self.__track_iteration_listeners(self.stack)
        if isinstance(child, Sampler):
            self.__save_sampler_configs(child)
        elif isinstance(child, TransactionController):
            self.__save_transaction_controller_configs(child)

        self.stack.pop()
        if len(self.stack) > 0:
            parent = self.stack[-1]
            duplicate = False
            if isinstance(parent, Controller) and (isinstance(child, Sampler) or isinstance(child, Controller)):
                pair = self.ObjectPair(parent, child)
                # TODO: 加锁
                if pair not in self.PAIRING:
                    parent.add_test_element(child)
                    self.PAIRING.append(pair)
                else:
                    duplicate = True

            if duplicate:
                log.warn(f'Unexpected duplicate for {parent} and {child}')

    def process_path(self) -> None:
        """@override"""
        pass

    def __configure_with_config_elements(self, sampler: Sampler, configs: list):
        sampler.clear_test_element_children()
        for config in configs:
            if not isinstance(config, NoConfigMerge):
                sampler.add_test_element(config)

    def __track_iteration_listeners(self, stack):
        child = stack[-1]
        if isinstance(child, LoopIterationListener):
            for item in stack[::-1]:
                if item == child:
                    log.debug(f'tracking iteration listeners, current item:[ {item} ] is child:[ {child} ] skip')
                    continue
                if isinstance(item, Controller):
                    log.debug(
                        f'tracking iteration listeners, current item:[ {item} ] add iteration listener:[ {child} ]'
                    )
                    item.add_iteration_listener(child)

    def __save_sampler_configs(self, sampler):
        configs = []
        controllers = []
        listeners = []
        timers = []
        assertions = []
        pres = []
        posts = []
        for i in range(len(self.stack) - 1, -1, -1):
            self.__add_direct_parent_controllers(controllers, self.stack[i - 1])
            inner_pres = []
            inner_posts = []
            inner_assertions = []
            # log.debug(f'i={i}')
            # log.debug([x for x in range(0, i)])
            # log.debug(f'[self.stack[x] for x in range(0, i)]={[self.stack[x] for x in range(0, i)]}')
            for item in self.test_tree.list_by_treepath([self.stack[x] for x in range(0, i)]):
                if isinstance(item, ConfigElement):
                    configs.append(item)
                elif isinstance(item, SampleListener):
                    listeners.append(item)
                elif isinstance(item, Timer):
                    timers.append(item)
                elif isinstance(item, Assertion):
                    inner_assertions.append(item)
                elif isinstance(item, PostProcessor):
                    inner_posts.append(item)
                elif isinstance(item, PreProcessor):
                    inner_pres.append(item)

                assertions.extend(inner_assertions)
                pres.extend(inner_pres)
                posts.extend(inner_posts)

        package = SamplePackage(configs, listeners, timers, assertions, posts, pres, controllers)
        package.sampler = sampler
        package.set_running_version(True)
        self.sampler_config_dict[sampler] = package

    def __save_transaction_controller_configs(self, trans_controller: Controller):
        configs = []
        controllers = []
        listeners = []
        timers = []
        assertions = []
        pres = []
        posts = []
        for i in range(len(self.stack) - 1, -1, -1):
            self.__add_direct_parent_controllers(controllers, self.stack[i - 1])
            for item in self.test_tree.list_by_treepath([self.stack[x] for x in range(0, i)]):
                if isinstance(item, SampleListener):
                    listeners.append(item)
                elif isinstance(item, Assertion):
                    assertions.append(item)

        package = SamplePackage(configs, listeners, timers, assertions, posts, pres, controllers)
        package.sampler = TransactionSampler(trans_controller, trans_controller.name)
        package.set_running_version(True)
        self.transaction_controller_config_dict[trans_controller] = package

    def __add_direct_parent_controllers(self, controllers: list, maybe_controller):
        if isinstance(maybe_controller, Controller):
            controllers.append(maybe_controller)

    class ObjectPair:

        def __init__(self, parent, child) -> None:
            self.parent = parent
            self.child = child

        def __eq__(self, other):
            return id(self) == id(other)

        def __hash__(self):
            return id(self.parent) + id(self.child)


class FindTestElementsUpToRoot(HashTreeTraverser):

    def __init__(self, node_to_find: object):
        self.nodes = []
        self.node_to_find = node_to_find
        self.stop_recording = False

    def get_controllers_to_root(self) -> List[Controller]:
        result = []
        nodes = self.nodes[::-1]  # 反向排序
        for node in nodes:
            if isinstance(node, Controller):
                result.append(node)
        return result

    def add_node(self, node, subtree) -> None:
        if self.stop_recording:
            return

        if node is self.node_to_find:
            self.stop_recording = True

        self.nodes.append(node)

    def subtract_node(self) -> None:
        if self.stop_recording:
            return

        log.debug(f'subtracting node, nodes size = {len(self.nodes)}')
        self.nodes.pop()  # 删除最后一个

    def process_path(self) -> None:
        pass
