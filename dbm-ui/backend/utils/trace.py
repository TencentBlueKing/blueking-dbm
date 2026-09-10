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
import functools
import logging
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import (
    INVALID_SPAN,
    Link,
    SpanKind,
    Status,
    StatusCode,
    format_trace_id,
    get_current_span,
    set_span_in_context,
)

from backend import env

logger = logging.getLogger("root")

tracer = trace.get_tracer(__name__)


def detached_root_span(func):
    """
    丢弃上游透传的 traceparent，为视图新建一条独立的 trace。

    parentbased 采样策略下上游未采样会让本地 span 被直接 DROP，表现为日志有 trace_id 但
    APM 查不到记录。置空 parent 后由 root 分支重新决定采样，上游 trace_id 以 span link 和
    upstream.trace_id 属性保留，用于关联两侧链路。
    """

    @functools.wraps(func)
    def wrapper(self, request, *args, **kwargs):
        upstream = get_current_span().get_span_context()
        attributes = {"http.method": request.method, "http.target": request.get_full_path()}
        if upstream.is_valid:
            attributes["upstream.trace_id"] = format_trace_id(upstream.trace_id)

        with tracer.start_as_current_span(
            f"{request.method} {request.path}",
            context=set_span_in_context(INVALID_SPAN),
            kind=SpanKind.SERVER,
            links=[Link(upstream)] if upstream.is_valid else (),
            attributes=attributes,
        ) as span:
            if upstream.is_valid:
                # 本行日志自带新 trace_id，与上游 id 成对，便于从视图外的日志跳转过来
                logger.info("[trace] %s detached from %s", request.path, attributes["upstream.trace_id"])

            response = func(self, request, *args, **kwargs)
            # 抛异常时 start_as_current_span 已记录 ERROR，此处只处理正常返回
            status_code = getattr(response, "status_code", None)
            if status_code is not None:
                span.set_attribute("http.status_code", status_code)
                span.set_status(Status(StatusCode.ERROR if status_code >= 400 else StatusCode.OK))
            return response

    return wrapper


@contextmanager
def start_new_span(func):
    """
    为周期任务的每一次批次投递单独开一个 span。

    CeleryInstrumentor 投递消息前会把当前 span 注入消息头，worker 侧的子任务因此挂到本 span
    之下，而非平铺在 dispatcher 任务上。新 span 的 trace_id 与外层 celery 任务一致，
    如需另起一条 trace 参考 detached_root_span 传入 context 的做法。
    """
    if env.ENABLE_OTEL_TRACE:
        with tracer.start_as_current_span(func.__name__) as span:
            yield span
    else:
        yield
