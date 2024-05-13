#!/usr/bin python3
# @File    : transaction.py
# @Time    : 2021-08-24 23:23:12
# @Author  : Kelvin.Ye
from loguru import logger

from pymeter.controls.controller import Controller
from pymeter.controls.generic_controller import GenericController
from pymeter.samplers.sample_result import SampleResult
from pymeter.samplers.sampler import Sampler


class TransactionController(GenericController):

    def __init__(self):
        super().__init__()
        self.transaction_sampler = None  # type: TransactionSampler

    def next(self):
        """@override"""
        return self.next_with_transaction_sampler()

    def next_with_transaction_sampler(self):
        # Check if transaction is done
        if self.transaction_sampler and self.transaction_sampler.done:
            logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 获取下一个请求')
            # This transaction is done
            self.transaction_sampler = None
            logger.debug(f'线程:[ {self.ctx.thread_name} ] 事务:[ {self.name} ] 事务结束')
            logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为空')
            return None

        # Check if it is the start of a new transaction
        if self.first:  # must be the start of the subtree
            logger.debug(f'线程:[ {self.ctx.thread_name} ] 事务:[ {self.name} ] 开始事务')
            self.transaction_sampler = TransactionSampler(self, self.name)

        # Sample the children of the transaction
        sub_sampler = super().next()
        self.transaction_sampler.sub_sampler = sub_sampler

        # If we do not get any sub samplers, the transaction is done
        if sub_sampler is None:
            self.transaction_sampler.set_done()

        return self.transaction_sampler

    def next_is_controller(self, controller: Controller):
        """@override"""
        logger.debug(f'线程:[ {self.ctx.thread_name} ] 控制器:[ {self.name} ] 下一个为控制器')
        sampler = controller.next()
        # 子代控制器的下一个请求为空时重新获取父控制器的下一个请求
        if sampler is None:
            self.current_returned_none(controller)
            # We need to call the super.next, instead of this.next, which is done in GenericController,
            # because if we call this.next(), it will return the TransactionSampler, and we do not want that.
            # We need to get the next real sampler or controller
            return super().next()
        else:
            return sampler

    def trigger_end_of_loop(self):
        """@override"""
        sub_sampler = self.transaction_sampler.sub_sampler
        # triggerEndOfLoop is called when error occurs to end Main Loop
        # in this case normal workflow doesn't happen, so we need
        # to notify the children of TransactionController and
        # update them with SubSamplerResult
        if isinstance(sub_sampler, TransactionSampler):
            self.transaction_sampler.add_sub_sampler_result(sub_sampler.result)

        self.transaction_sampler.set_done()
        # This transaction is done
        self.transaction_sampler = None

        super().trigger_end_of_loop()


class TransactionSampler(Sampler):

    def __init__(self, controller: TransactionController, name: str):
        super().__init__(name=name)
        self.controller = controller
        self.done = False
        self.sub_sampler = None

        self.calls = 0
        self.no_failing_samples = 0
        self.total_time = 0

        self.result = SampleResult()
        self.result.sample_name = name
        self.result.success = True
        self.result.sample_start()

    def sample(self):
        """@override"""
        raise NotImplementedError

    def add_sub_sampler_result(self, result: SampleResult):
        # Another subsample for the transaction
        self.calls += 1

        # Set Response code of transaction
        if self.no_failing_samples == 0:
            self.result.response_code = result.response_code

        # The transaction fails if any sub sample fails
        if not result.success and not result.retrying:
            self.result.success = False
            self.no_failing_samples += 1

        # Add the sub result to the transaction result
        self.result.add_subresult(result)

        # Add current time to total for later use (exclude pause time)
        self.total_time += result.elapsed_time - int(result.idle_time * 1000)

    def set_done(self):
        logger.debug(f'线程:[ {self.controller.ctx.thread_name} ] 事务:[ {self.controller.name} ] 完成事务')
        self.done = True
        self.result.elapsed_time = self.total_time
        if self.result.success:
            self.result.response_code = 200
