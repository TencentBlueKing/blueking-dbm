# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像生成器 - MySQL 子类（薄壳）。

模块职责：
    - 声明 MySQL 集群画像生成器所属 DB 类型与画像智能体 code
    - 复用 :class:`ClusterPortraitGenerator` 的默认 prompt 模板与 build_content 实现

设计要点：
    - 本子类**仅声明 3 个类属性**：``db_type / agent_code / dimension_enum``；
      不重写 :meth:`build_content` / :attr:`PROMPT_TEMPLATE` / :meth:`parse_response`
    - 若未来 MySQL 画像 prompt 需要新增占位（例如 spider 层节点数），
      优先重写 :meth:`ClusterPortraitGenerator.get_extra_context` 注入即可；
      再进一步定制才考虑覆盖 :attr:`PROMPT_TEMPLATE` 或重写 :meth:`build_content`

边界：
    - 本模块 import **不产生任何除"定义类"以外的副作用**
    - 服务 :attr:`DBType.MySQL` 和 :attr:`DBType.TenDBCluster`（后者复用同一套
      agent_code / dimension_enum，仅 ``db_type`` 不同，落库区分）
"""
from backend.configuration.constants import DBType
from backend.db_report.portrait.generator.base import ClusterPortraitGenerator
from backend.db_report.portrait.mysql_dimensions import MysqlPortraitDimensionCode
from backend.dbm_aiagent.agent.constants import DBMAgentCode


class MysqlClusterPortraitGenerator(ClusterPortraitGenerator):
    """MySQL 集群画像生成器。

    职责：
        - 声明 MySQL 画像所属 db_type、使用的智能体 code、允许的维度枚举类型
        - prompt 组装 / AI 调用 / 结果解析 / 落库全部复用基类

    使用方式（调用方明确知道 db_type，直接 import 本子类调用其 ``run()``）::

        from backend.db_report.portrait.generator import MysqlClusterPortraitGenerator

        result = MysqlClusterPortraitGenerator().run(
            cluster=cluster, report_from=t0, report_to=t1, dimensions=None, operator="system",
        )

    线程安全：是（无实例状态）
    边界：
        - dimensions 必须是 :class:`MysqlPortraitDimensionCode` 成员；否则被基类
          :meth:`ClusterPortraitGenerator._validate_inputs` 拦截为 :class:`PortraitInvalidParamException`
    """

    #: 本子类所属 DB 类型：MySQL
    db_type: DBType = DBType.MySQL

    #: 本 db_type 使用的画像智能体 code；见 ``DBMAgentCode.MYSQL_PORTRAIT_CLUSTER = "ai-c-report"``
    agent_code: DBMAgentCode = DBMAgentCode.MYSQL_PORTRAIT_CLUSTER

    #: 允许的维度枚举类型（类型级引用，非枚举成员本身）；基类用它做 dimensions 参数的 isinstance 校验
    dimension_enum = MysqlPortraitDimensionCode


class TendbClusterClusterPortraitGenerator(ClusterPortraitGenerator):
    """TenDBCluster 集群画像生成器。

    职责：
        - 声明 TenDBCluster 画像所属 db_type、使用的智能体 code、允许的维度枚举类型
        - prompt 组装 / AI 调用 / 结果解析 / 落库全部复用基类

    设计要点：
        - 与 :class:`MysqlClusterPortraitGenerator` 的唯一区别是 ``db_type = DBType.TenDBCluster``，
          使落库 ``ClusterPortraitReport.db_type`` 记录为 ``"tendbcluster"`` 而非 ``"mysql"``
        - agent_code 复用 ``MYSQL_PORTRAIT_CLUSTER``（"ai-c-report"）：该 agent 的 system_prompt
          定位为通用"DBM 集群画像分析师"，按 (bk_biz_id, cluster_domain) 经 MCP 工具查数据，
          不写死 MySQL；MCP 工具已覆盖 TenDBCluster 数据源
        - dimension_enum 复用 :class:`MysqlPortraitDimensionCode`：TenDBCluster 的巡检维度
          （TENDBCLUSTER_META_CHECK / MYSQL_CHECKSUM_CHECK 等）本就挂在该枚举下

    使用方式::

        from backend.db_report.portrait.generator import TendbClusterClusterPortraitGenerator

        result = TendbClusterClusterPortraitGenerator().run(
            cluster=cluster, report_from=t0, report_to=t1, dimensions=None, operator="system",
        )

    线程安全：是（无实例状态）
    """

    #: 本子类所属 DB 类型：TenDBCluster
    db_type: DBType = DBType.TenDBCluster

    #: 复用通用集群画像智能体（ai-c-report）；其 system_prompt 不限 DB 类型
    agent_code: DBMAgentCode = DBMAgentCode.MYSQL_PORTRAIT_CLUSTER

    #: 复用 MySQL 维度枚举；TenDBCluster 维度现状挂在此枚举下
    dimension_enum = MysqlPortraitDimensionCode
