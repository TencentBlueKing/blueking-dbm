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


import os

from prometheus_client import Counter, Gauge, Histogram


def decode_buckets(buckets_list):
    return [float(x) for x in buckets_list.split(",")]


def get_histogram_buckets_from_env(env_name):
    if env_name in os.environ:
        buckets = decode_buckets(os.environ.get(env_name))
    else:
        buckets = (
            0.005,
            0.01,
            0.1,
            0.5,
            1.0,
            5.0,
            10.0,
            60,
            120,
            600,
            1800,
            3600,
            float("inf"),
        )
    return buckets


# pipeline原子任务 执行失败次数计数
pipeline_node_execute_failed_total = Counter(
    name="pipeline_node_execute_failed_total",
    documentation="count pipeline node execute failed",
    labelnames=["name", "bk_biz_id", "ticket_type", "ticket_id"],
)

# pipeline原子任务 execute执行耗时
pipeline_node_execute_duration_histogram = Histogram(
    name="pipeline_node_execute_duration_histogram",
    documentation="Histogram of the time (in seconds) each pipeline node execute",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["name", "bk_biz_id", "ticket_type", "ticket_id"],
)


# pipeline原子任务 schedule执行耗时
pipeline_node_schedule_duration_histogram = Histogram(
    name="pipeline_node_schedule_duration_histogram",
    documentation="Histogram of the time (in seconds) each pipeline task schedule",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["name", "bk_biz_id", "ticket_type", "ticket_id"],
)

# pipeline原子任务 执行中计数
pipeline_node_execute_running_count = Gauge(
    name="pipeline_node_execute_running_count",
    documentation="Number of pipeline execute running count.",
    labelnames=["name", "bk_biz_id", "ticket_type", "ticket_id"],
)

# pipeline 流程树构建耗时
pipeline_tree_build_duration_histogram = Histogram(
    name="pipeline_tree_build_duration_histogram",
    documentation="Histogram of the time (in seconds) each pipeline tree build",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["bk_biz_id", "ticket_type", "ticket_id"],
)

# ticket 创建耗时
ticket_create_duration_histogram = Histogram(
    name="ticket_create_duration_histogram",
    documentation="Histogram of the time (in seconds) each ticket create",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["bk_biz_id", "ticket_type"],
)
