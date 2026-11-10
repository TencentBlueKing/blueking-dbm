# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Redis 集群画像 DispatchTask —— Redis 家族画像消费者。

模块职责：
    - 定义 :class:`RedisPortraitReportTask`：所有 Redis / Tendis 架构共用
      :class:`RedisClusterPortraitGenerator`（落 ``db_type=redis``）
    - 通过 ``@register_dispatch_task`` 注册到 ``PortraitQueue`` 的 ``cluster_portrait`` namespace

设计要点：
    - 全部通用链路已下沉到 :class:`PortraitReportTaskBase`；本类保持薄壳
"""
from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.registry import register_dispatch_task
from backend.db_periodic_task.local_tasks.cluster_portrait_report.base_portrait_task import PortraitReportTaskBase
from backend.db_periodic_task.local_tasks.cluster_portrait_report.config import RedisPortraitReportConfig
from backend.db_report.portrait.generator import ClusterPortraitGenerator, RedisClusterPortraitGenerator
from backend.dbm_aiagent.agent.constants import DBMAgentCode


@register_dispatch_task(
    config_cls=RedisPortraitReportConfig,
    metadata={
        "agent_code": str(DBMAgentCode.REDIS_PORTRAIT_CLUSTER),
        "db_type": "redis",
    },
)
class RedisPortraitReportTask(PortraitReportTaskBase):
    """Redis 集群画像 DispatchTask 消费者。

    使用方式：
        由 dispatch worker 自动调用；定时任务 ``generate_cluster_portrait_report``
        负责选集群 + 与其他画像 Task 交错 ``task.submit``。

    线程安全：是（继承基类无状态特性）
    """

    config_cls = RedisPortraitReportConfig

    def resolve_generator(self, cluster: Cluster) -> ClusterPortraitGenerator:
        return RedisClusterPortraitGenerator()


__all__ = ("RedisPortraitReportTask",)
