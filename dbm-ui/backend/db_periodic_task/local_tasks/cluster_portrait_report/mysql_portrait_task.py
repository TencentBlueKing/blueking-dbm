# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL 集群画像 DispatchTask —— 收敛 MySQL 家族的专属知识。

模块职责：
    - 定义 :class:`MysqlPortraitReportTask`：MySQL 家族（TenDBSingle / TenDBHA /
      TenDBCluster）的画像消费者
    - 通过 ``@register_dispatch_task`` 注册到 ``PortraitQueue`` 的 ``cluster_portrait`` namespace
    - MySQL 专属逻辑只有一处：按 ``cluster.cluster_type`` 派发生成器
      （TenDBCluster 用 tendbcluster 生成器，其余用 mysql 生成器）

设计要点：
    - 全部通用链路已下沉到 :class:`PortraitReportTaskBase`；本类保持薄壳；
    - worker 唯一动作是调 :meth:`ClusterPortraitGenerator.run`，agent_code 由生成器
      自身声明（``MysqlClusterPortraitGenerator.agent_code = MYSQL_PORTRAIT_CLUSTER``），
      本类不感知；
    - :func:`_select_mysql_generator` 收敛 TenDBCluster / 其余 的派发规则，
      未来若 MySQL 家族新增 cluster_type 只需在此函数追加一行判断。

边界：
    - 覆盖的 cluster_type：TenDBSingle / TenDBHA / TenDBCluster；
    - producer 侧过滤后的 cluster_type 之外的类型不会到达 execute，
      :func:`_select_mysql_generator` 兜底返回 MySQL 生成器（防御性）。
"""
import logging

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.registry import register_dispatch_task
from backend.db_periodic_task.local_tasks.cluster_portrait_report.base_portrait_task import PortraitReportTaskBase
from backend.db_periodic_task.local_tasks.cluster_portrait_report.config import MysqlPortraitReportConfig
from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport
from backend.db_report.portrait.generator import (
    ClusterPortraitGenerator,
    MysqlClusterPortraitGenerator,
    TendbClusterClusterPortraitGenerator,
)
from backend.dbm_aiagent.agent.constants import DBMAgentCode

logger = logging.getLogger("root")


def _select_mysql_generator(cluster_type: str) -> ClusterPortraitGenerator:
    """按 MySQL 家族 cluster_type 选择对应 db_type 的画像生成器实例。

    功能说明：
        - TenDBCluster -> :class:`TendbClusterClusterPortraitGenerator`（落 db_type=tendbcluster）
        - 其余（TenDBSingle / TenDBHA）-> :class:`MysqlClusterPortraitGenerator`（落 db_type=mysql）

    :param cluster_type: ``Cluster.cluster_type`` 字段值（例如 "tendbcluster" / "tendbha"）
    :return: 对应的画像生成器实例
    边界：
        - 不识别的 cluster_type 落回默认 MySQL 生成器（防御性兜底；producer 侧已过滤）
    """
    if cluster_type == ClusterType.TenDBCluster.value:
        return TendbClusterClusterPortraitGenerator()
    return MysqlClusterPortraitGenerator()


@register_dispatch_task(
    config_cls=MysqlPortraitReportConfig,
    metadata={
        "agent_code": str(DBMAgentCode.MYSQL_PORTRAIT_CLUSTER),
        "db_type": "mysql",
    },
)
class MysqlPortraitReportTask(PortraitReportTaskBase):
    """MySQL 集群画像 DispatchTask 消费者。

    职责：
        - 继承 :class:`PortraitReportTaskBase` 的通用执行链路（execute 唯一动作是调 ``generator.run()``）
        - 只填 MySQL 家族的一处专属知识：按 ``cluster.cluster_type`` 选生成器

    使用方式：
        由 dispatch worker 自动调用；定时任务 ``generate_mysql_cluster_portrait_report``
        负责选集群 + ``task.submit``。

    线程安全：是（继承基类无状态特性）
    边界：见 :class:`PortraitReportTaskBase` docstring；本子类不新增行为约束。
    """

    #: 绑定 MySQL 家族的 task 配置；@register_dispatch_task 会同步 task_key / queue_namespace 到 config_cls
    config_cls = MysqlPortraitReportConfig

    def resolve_generator(self, cluster: Cluster) -> ClusterPortraitGenerator:
        """MySQL 家族内部按 cluster_type 二次派发。

        :param cluster: 已从 DB 拉起的 :class:`Cluster` 实例
        :return: :class:`ClusterPortraitGenerator` 实例；agent_code 由生成器自身声明
        边界：见 :func:`_select_mysql_generator` 说明
        """
        return _select_mysql_generator(cluster.cluster_type)


# 便于 producer 从本模块直接引用（避免绕道 model 模块）
__all__ = (
    "MysqlPortraitReportTask",
    "ClusterPortraitReport",
)
