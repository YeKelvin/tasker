#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : traverser
# @Time    : 2020/2/25 15:06
# @Author  : Kelvin.Ye
from typing import Dict

from pymeter.controls.controller import Controller
from pymeter.controls.generic_controller import GenericController
from pymeter.elements.element import TestElement
from pymeter.elements.interface import NoConfigMerge
from pymeter.engine.interface import LoopIterationListener
from pymeter.groups.interface import NoCoroutineClone
from pymeter.groups.package import SamplePackage
from pymeter.samplers.sampler import Sampler
from pymeter.utils.log_util import get_logger


log = get_logger(__name__)


class HashTreeTraverser:

    def add_node(self, node, subtree) -> None:
        """加节点时的处理
        """
        raise NotImplementedError

    def subtract_node(self) -> None:
        """减节点时的处理（递归回溯）
        """
        raise NotImplementedError

    def process_path(self) -> None:
        """到达子叶末尾时的处理
        """
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
    """克隆HashTree，默认情况下跳过实现NoCoroutineClone的节点"""

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

    def __init__(self, group_level_elements: list):
        self.group_level_elements = group_level_elements
        self.sampler_package_saver: Dict[Sampler, SamplePackage] = {}
        self.compiled_node = []

    def configure_sampler(self, sampler) -> SamplePackage:
        """将ConfigTestElement合并至Sampler中"""
        package = self.sampler_package_saver.get(sampler)
        sampler.clear_test_element_children()
        for config in package.configs:
            if not isinstance(config, NoConfigMerge):
                sampler.add_test_element(config)
        return package

    def add_node(self, node, subtree) -> None:
        log.debug(f'开始编译节点:[ {node} ]')
        if isinstance(node, Sampler):
            self.__save_sampler_package(node, subtree)
        if isinstance(node, Controller):
            self.__compile_controller(node, subtree)

    def subtract_node(self) -> None:
        pass

    def process_path(self) -> None:
        pass

    def __save_sampler_package(self, node, subtree):
        sample_package = SamplePackage()
        # 存储Sampler的子节点
        sample_package.add(subtree.list())
        # 存储Group层的非Group节点添加至Sampler节点下
        sample_package.add(self.group_level_elements)
        self.sampler_package_saver[node] = sample_package

    def __compile_controller(self, node, subtree):
        if node in self.compiled_node:
            log.debug(f'当前节点已完成编译，无需再次编译，当前节点:[ {node} ]')
            return

        controller_level_elements = subtree.list()
        # Controller节点储存Sampler节点和Controller节点
        for element in controller_level_elements:
            log.debug(f'当前节点的子代节点:[ {element} ]')
            if isinstance(element, Sampler) or isinstance(element, Controller):
                node.add_test_element(element)

            if isinstance(element, LoopIterationListener):
                node.add_iteration_listener(element)

        # 移除Controller层的非Sampler节点和非Controller节点，用于传递到子代
        self.__remove_samplers_and_controllers(controller_level_elements)

        # 合并Group层和子代Controller层的非Sampler节点和非Controller节点
        parent_level_elements = self.group_level_elements + controller_level_elements

        # 递归编译子代节点
        compiler = TestCompiler(parent_level_elements)
        subtree.traverse(compiler)
        self.sampler_package_saver.update(compiler.sampler_package_saver)

        # 存储已编译过的Controller节点，避免递归遍历下有可能产生重复编译的问题
        self.compiled_node.extend(compiler.compiled_node)
        self.compiled_node.append(node)

    @staticmethod
    def __remove_samplers_and_controllers(elements: list):
        for element in elements[:]:
            if isinstance(element, Sampler):
                elements.remove(element)
            if isinstance(element, GenericController):
                elements.remove(element)
            if not isinstance(element, TestElement):
                elements.remove(element)


class FindTestElementsUpToRoot(HashTreeTraverser):

    def __init__(self, required_nodes: object):
        self.node_list = []
        self.required_nodes = required_nodes
        self.stop_recording = False

    def get_controllers_to_root(self) -> list:
        result = []
        node_list = self.node_list[::-1]
        for node in node_list:
            if isinstance(node, Controller):
                result.append(node)
        return result

    def add_node(self, node, subtree) -> None:
        if self.stop_recording:
            return

        if node is self.required_nodes:
            self.stop_recording = True

        self.node_list.append(node)

    def subtract_node(self) -> None:
        if self.stop_recording:
            return

        self.node_list.pop()  # 删除最后一个

    def process_path(self) -> None:
        pass