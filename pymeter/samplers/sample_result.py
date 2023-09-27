#!/usr/bin python3
# @File    : sample_result.py
# @Time    : 2020/1/24 23:35
# @Author  : Kelvin.Ye
import time
import traceback

from loguru import logger

from pymeter.tools.advanced import transform
from pymeter.utils import json_util
from pymeter.utils import time_util
from pymeter.utils.json_util import from_json


class SampleResult:

    default_encoding = 'UTF-8'

    def __init__(self):
        self.parent = None

        self.sample_name = None
        self.sample_desc = None

        self.request_url = None
        self.request_data = None
        self.request_headers = None
        self.request_decoded = None

        self.response_data = None
        self.response_code = None
        self.response_message = None
        self.response_headers = None
        self.response_cookies = None
        self.response_decoded = None

        self.start_time = 0
        self.end_time = 0
        self.elapsed_time = 0
        self.idle_time = 0
        self.pause_time = 0
        self.connect_time = 0

        self.success = True
        self.error = False
        self.retrying = False
        self.assertions = []
        self.subresults: list[SampleResult] = []

        self.request_size = 0
        self.request_data_size = 0
        self.request_header_size = 0

        self.response_size = 0
        self.response_data_size = 0
        self.response_header_size = 0

        self.stop_worker = False
        self.stop_test = False
        self.stop_now = False

    @property
    def json(self) -> str:
        if self.error:
            return None

        try:
            obj = from_json(self.response_data)
            return transform(obj)
        except Exception:
            logger.debug(traceback.format_exc())
            return None

    @property
    def started(self) -> bool:
        return self.start_time != 0

    def to_dict(self) -> dict:
        return {
            'samplerName': self.sample_name,
            'samplerDesc': self.sample_desc,
            'requestUrl': self.request_url,
            'requestData': self.request_data,
            'requestParsedData': self.request_data,
            'requestHeaders': self.request_headers,
            'requestSize': self.request_size,
            'responseData': self.response_data,
            'responseParsedData': self.response_data,
            'responseHeaders': self.response_headers,
            'responseSize': self.response_size,
            'responseCode': self.response_code,
            'responseMessage': self.response_message,
            'success': self.success,
            'startTime': time_util.timestamp_to_strftime(self.start_time),
            'endTime': time_util.timestamp_to_strftime(self.end_time),
            'elapsedTime': self.elapsed_time,
            'assertions': [str(assertion) for assertion in self.assertions],
            'subresults': [result.to_dict() for result in self.subresults]
        }

    def sample_start(self):
        self.start_time = time.time()

    def sample_end(self):
        self.end_time = time.time()
        self.elapsed_time = int(self.end_time * 1000) - int(self.start_time * 1000)

    def add_subresult(self, subresult: 'SampleResult'):
        if not subresult:
            return

        # Extend the time to the end of the added sample
        self.end_time = max(self.end_time, subresult.end_time)

        # Include the byte count for the added sample
        self.request_size = self.request_size + subresult.request_size
        self.request_data_size = self.request_data_size + subresult.request_data_size
        self.request_header_size = self.request_header_size + subresult.request_header_size

        self.response_size = self.response_size + subresult.response_size
        self.response_data_size = self.response_data_size + subresult.response_data_size
        self.response_header_size = self.response_header_size + subresult.response_header_size

        self.subresults.append(subresult)
        subresult.parent = self

    def json_path(self, expressions, choice=False):
        return json_util.json_path(self.response_data, expressions, choice)
