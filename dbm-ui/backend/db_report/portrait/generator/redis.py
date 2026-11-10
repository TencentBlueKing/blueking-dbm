# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像生成器 - Redis 子类（薄壳）。

模块职责：
    - 声明 Redis 集群画像生成器所属 DB 类型与画像智能体 code（``ai-rds-portrait``）
    - 复用 :class:`ClusterPortraitGenerator` 的默认 prompt 模板与 build_content 实现

设计要点：
    - 本子类**仅声明 3 个类属性**：``db_type / agent_code / dimension_enum``；
      ``ai-rds-portrait`` 背后的 redis-portrait-generator skill 按 (bk_biz_id, cluster_domain)
      自行拉取维度汇总，输出 ``[ai_result]{...}[ai_result]`` 契约，与基类默认解析器对齐

边界：
    - 本模块 import **不产生任何除"定义类"以外的副作用**
    - 覆盖 :meth:`ClusterType.redis_cluster_types` 下全部 Redis / Tendis 架构，统一落 ``db_type=redis``
"""
from backend.configuration.constants import DBType
from backend.db_report.portrait.generator.base import ClusterPortraitGenerator
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.dbm_aiagent.agent.constants import DBMAgentCode


class RedisClusterPortraitGenerator(ClusterPortraitGenerator):
    """Redis 集群画像生成器。

    职责：
        - 声明 Redis 画像所属 db_type、使用的智能体 code、允许的维度枚举类型
        - prompt 组装 / AI 调用 / 结果解析 / 落库全部复用基类

    使用方式::

        from backend.db_report.portrait.generator import RedisClusterPortraitGenerator

        result = RedisClusterPortraitGenerator().run(
            cluster=cluster, report_from=t0, report_to=t1, dimensions=None, operator="system",
        )

    线程安全：是（无实例状态）
    边界：
        - dimensions 必须是 :class:`RedisPortraitDimensionCode` 成员；否则被基类
          :meth:`ClusterPortraitGenerator._validate_inputs` 拦截为 :class:`PortraitInvalidParamException`
    """

    #: 本子类所属 DB 类型：Redis
    db_type: DBType = DBType.Redis

    #: 本 db_type 使用的画像智能体 code；见 ``DBMAgentCode.REDIS_PORTRAIT_CLUSTER = "ai-rds-portrait"``
    agent_code: DBMAgentCode = DBMAgentCode.REDIS_PORTRAIT_CLUSTER

    #: 允许的维度枚举类型；基类用它做 dimensions 参数的 isinstance 校验
    dimension_enum = RedisPortraitDimensionCode
