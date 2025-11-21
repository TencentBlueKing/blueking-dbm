# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import socket
import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Dict, List, Union

from pipeline.core.data.base import DataObject
from pipeline.core.flow.activity import Service
from prometheus_client import Counter, Gauge, Histogram

_HOSTNAME = socket.gethostname()


def default_label_func():
    return {"hostname": _HOSTNAME}


def node_label_func(self: Service, data: DataObject, *args, **kwargs):
    # pipeline 节点维度
    node_data = data.inputs.get("global_data", {})
    _labels = {
        "name": self.name,
        "bk_biz_id": node_data.get("bk_biz_id", 0),
        "ticket_type": node_data.get("ticket_type", ""),
        "ticket_id": node_data.get("uid", ""),
    }
    return _labels


def pipeline_build_label_func(self, *args, **kwargs):
    # pipeline构建维度
    return {"bk_biz_id": self.ticket.bk_biz_id, "ticket_type": self.ticket.ticket_type, "ticket_id": self.ticket.id}


def get_labels(labels: Union[Callable, Dict], *args, **kwargs):
    """获取指标标签，支持自定义函数/字典"""
    if isinstance(labels, Callable):
        try:
            return labels(*args, **kwargs)
        except Exception:  # noqa
            return default_label_func()
    elif isinstance(labels, Dict):
        return labels

    return default_label_func()


def setup_gauge(gauges: List[Gauge], labels: Union[Callable, Dict] = None):
    """设置Gauge指标, 在函数执行前后设置，统计函数执行中计数"""

    def wrapper(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            _labels = get_labels(labels, *args, **kwargs)
            for g in gauges:
                g.labels(**_labels).inc(1)
            try:
                return func(*args, **kwargs)
            finally:
                for g in gauges:
                    g.labels(**_labels).dec(1)

        return _wrapper

    return wrapper


def setup_histogram(histograms: List[Histogram], labels: Union[Callable, Dict] = None):
    """设置Histogram指标, 在函数执行前后设置，统计函数执行事件"""

    def wrapper(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            start = time.perf_counter()
            _labels = get_labels(labels, *args, **kwargs)
            try:
                return func(*args, **kwargs)
            finally:
                for h in histograms:
                    h.labels(**_labels).observe(time.perf_counter() - start)

        return _wrapper

    return wrapper


def setup_counter(counters: List[Counter], labels: Union[Callable, Dict] = None, check: Callable = None):
    """设置Counter指标, 统计函数执行次数"""

    def wrapper(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            try:
                if not check or check(res):
                    _labels = get_labels(labels, *args, **kwargs)
                    for c in counters:
                        c.labels(**_labels).inc(1)
                return res
            except Exception:  # noqa
                return res

        return _wrapper

    return wrapper


def inc_counter(counters: List[Counter], labels: Union[Callable, Dict] = default_label_func, *args, **kwargs):
    """增加Counter指标"""
    _labels = get_labels(labels, *args, **kwargs)
    for c in counters:
        c.labels(**_labels).inc(1)


def dec_counter(counters: List[Counter], labels: Union[Callable, Dict] = default_label_func, *args, **kwargs):
    """减少Counter指标"""
    _labels = get_labels(labels, *args, **kwargs)
    for c in counters:
        c.labels(**_labels).dec(1)


@contextmanager
def observe(histogram, **labels):
    """设置Histogram指标, 用于代码片段执行时间"""
    start = time.perf_counter()
    yield
    histogram.labels(**labels).observe(time.perf_counter() - start)
