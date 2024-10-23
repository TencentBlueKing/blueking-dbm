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
import logging
from contextlib import contextmanager

from opentelemetry.trace import get_tracer

from backend import env

logger = logging.getLogger(__name__)


@contextmanager
def start_new_span(func):
    """
    开启一个新的span，同时也会生成新的 trace ID
    为了解决削峰执行周期任务时，trace_id 都是同一个的问题
    """
    if env.ENABLE_OTEL_TRACE:
        logger.error("Start a new span")
        with get_tracer(__name__).start_as_current_span(func.__name__) as span:
            logger.error("Span is active with trace ID:", span.get_span_context().trace_id)
            yield span
    else:
        yield
