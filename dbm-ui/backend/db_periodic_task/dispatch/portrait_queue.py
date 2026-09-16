# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像专属 DispatchQueue —— 独立 namespace "cluster_portrait"。

模块职责：
    - 定义 :class:`PortraitQueueConfig`：画像队列的容量/并发配置容器
    - 定义 :class:`PortraitQueue`：画像 dispatch 队列实现，占用独立 Redis namespace

设计要点：
    - **与 AI queue（ai namespace）物理隔离**：独立队列容量、独立 pending/reserved
      指标、独立限流曲线，画像日常批量任务不与 Redis LLM 检查互相挤占资源；
    - `DispatchQueue` 元类会在导入时把本类注册到 ``_QUEUE_REGISTRY``，
      同 namespace 重复注册会 fail fast（重名检测由框架保证）；
    - 拥塞判定（``is_congestion_outcome``）与 AI 队列保持一致：requeue 类
      outcome 视为拥塞信号，方便复用同一套上层限流退让策略；
    - 默认字段沿用父类：``max_admitted_jobs=2000`` / ``max_reserved=10``，
      如需调整走 ``DispatchQueueSettings`` 管理端持久化，无需改代码。

边界：
    - 本模块 import 仅产生"类定义 + 元类注册"两个副作用，无 IO/DB 访问；
    - 必须由 ``backend/db_periodic_task/dispatch_queues.py`` 显式再导出，
      才能保证 Django 启动阶段真实执行注册；否则运行时才 lazy import 会晚于
      ``dispatch_execute_job`` 的路由决策，可能导致 ephemeral queue 兜底。
"""
from dataclasses import dataclass
from typing import ClassVar

from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.queue import DispatchQueue

#: 集群画像队列的 namespace 常量；作为 Redis key 前缀 + 指标标签 + 路由键
CLUSTER_PORTRAIT_NAMESPACE: str = "cluster_portrait"


@dataclass
class PortraitQueueConfig(DispatchQueueConfig):
    """集群画像队列的容量/并发配置。

    职责：
        - 声明 namespace = "cluster_portrait"，作为路由与限流隔离边界
        - 其余字段（``max_admitted_jobs`` / ``max_reserved``）沿用父类默认，
          需要按业务调优时通过 ``DispatchQueueSettings`` 持久化覆盖，不改代码

    边界：
        - namespace 一经绑定不可变（``ClassVar``），运行期任何修改都视为编程错误；
        - 与 ``AITaskQueueConfig``（namespace="ai"）严格互斥，Redis key 空间不重叠。

    线程安全：是（dataclass frozen-like 使用；`save_to_db` 由 Django ORM 保护）
    """

    #: 队列 namespace 常量；与 ``PortraitQueue.namespace`` 通过元类同步
    namespace: ClassVar[str] = CLUSTER_PORTRAIT_NAMESPACE


class PortraitQueue(DispatchQueue):
    """集群画像专属 DispatchQueue。

    职责：
        - 占用独立 Redis namespace "cluster_portrait"，与 AI 队列物理隔离
        - 复用 ``DispatchQueue`` 全部入队 / 出队 / dedupe / metrics 能力
        - 声明画像语境下的拥塞判定，用于上层退让策略

    使用方式：
        通过 ``MysqlPortraitReportTask.queue_cls = PortraitQueue`` 绑定；
        producer / worker 无需直接实例化。

    线程安全：是（无实例状态，仅使用类方法与 ClassVar）
    边界：
        - namespace 重复绑定 -> ``DispatchQueue`` 元类在 import 期 fail fast；
        - 未通过 ``dispatch_queues.py`` 显式再导出 -> 运行时可能走 ephemeral 队列。
    """

    config_cls = PortraitQueueConfig

    @classmethod
    def is_congestion_outcome(cls, outcome: DispatchOutcomeType) -> bool:
        """画像队列的拥塞判定策略。

        功能说明：
            - 与 ``AITaskQueue`` 保持一致：requeue 类 outcome 视为下游拥塞信号
            - 用于上层 producer 判定"是否需要降速 / 稍后重试"

        :param outcome: 单次 dispatch 结束后的 outcome 枚举
        :return: True 表示本次 outcome 属于拥塞类，需上层退让；False 表示非拥塞
        边界：
            - REQUEUED / REQUEUE_EXHAUSTED 视为拥塞；其余 outcome 一律非拥塞
        """
        return outcome in {
            DispatchOutcomeType.REQUEUED,
            DispatchOutcomeType.REQUEUE_EXHAUSTED,
        }


__all__ = (
    "CLUSTER_PORTRAIT_NAMESPACE",
    "PortraitQueueConfig",
    "PortraitQueue",
)
