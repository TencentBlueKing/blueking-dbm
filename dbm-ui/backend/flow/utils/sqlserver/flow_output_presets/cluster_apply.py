# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

------------------------------------------------------------------------------

SQLServer 集群交付类摘要预设（继承 MySQL 预设、仅覆盖命名空间）。

模块职责：
  - 为 SQLServer 单据（SqlserverSingleApplyFlow / SqlserverHAApplyFlow 等）提供"每套集群一行"
    的集群部署 / 交付摘要字段契约。
  - 直接继承 :class:`backend.flow.utils.mysql.flow_output_presets.ClusterApplySummarySerializer`，
    字段契约、幂等主键 `cluster_domain_and_port` 全部沿用，避免跨 DB 类型的重复定义。
  - 仅覆盖 `table_name = "sqlserver_cluster_apply"` 与 `table_display_name`，让 FlowSummary
    在同一 pipeline 内与 mysql / spider 的交付摘要分表存放，前端渲染时自然区分。

设计要点 / 数据源 / 调用通道：
  - 使用方通过 `from backend.flow.utils.sqlserver.flow_output_presets import SqlserverClusterApplySummarySerializer`
    引用，禁止深路径 import。
  - SQLServer 组件（SqlserverClusterApplySummaryComponent）在 pipeline 的"录入 db_meta"节点
    之后调用 `FlowOutputHandler(SqlserverClusterApplySummarySerializer).insert_data(root_id, items)`
    完成写入。

边界：
  - SQLServer 场景下 **clb_ip / clb_domain 恒为空字符串**（SQLServer 产品无 CLB 入口），
    调用方应始终把这两个字段留空，不改字段契约。
  - `readonly_domain_and_port` 字段在 SQLServer 场景承载 SqlserverHA 的 "slave_domain:port"
    （主从端口对齐）；SqlserverSingle 场景无只读入口，字段留空。
  - 其他字段 / 幂等语义与 MySQL 预设一致，详见父类 docstring。
"""

from django.utils.translation import gettext as _

from backend.flow.utils.mysql.flow_output_presets import ClusterApplySummarySerializer


class SqlserverClusterApplySummarySerializer(ClusterApplySummarySerializer):
    """SQLServer 集群交付摘要（每集群主入口一行）。

    功能说明：
      - 继承 MySQL 的 :class:`ClusterApplySummarySerializer`，字段结构 / 幂等主键完全沿用，
        仅覆盖 `table_name` 与 `table_display_name` 以独立命名空间落入 FlowSummary；
      - 字段顺序即前端表头顺序，第一个字段 `cluster_domain_and_port`（形如 "c1.example.db:1433"）
        同时作为行主键，重复写入走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构，与父类完全一致）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口 `"domain:port"`，作为主键
      - readonly_domain_and_port (str, 可空, 默认 ""): SqlserverHA 的只读入口 `"slave_domain:port"`；
        SqlserverSingle 场景留空
      - clb_ip (str, 可空, 默认 ""): SQLServer 场景无 CLB，调用方应恒传 ""
      - clb_domain (str, 可空, 默认 ""): SQLServer 场景无 CLB，调用方应恒传 ""
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染

    输出：
      - 写入 FlowSummary.summary 中 `table_name="sqlserver_cluster_apply"` 的表 values；
        每次调用产出的 dict 会按主键合并进该表 values 数组。

    边界：
      - cluster_domain_and_port 为空 / 缺失 -> is_valid 抛 ValidationError（沿用父类字段约束）。
      - 相同 cluster_domain_and_port 的重复写入 -> 依赖 FlowOutputHandler.insert_data 主键合并
        分支覆盖旧行，`values` 长度不变（重试幂等）。
      - CLB 字段在 SQLServer 场景无意义：契约不变（允许空字符串），调用方负责始终留空；
        相关约束不在 Serializer 层强制，避免破坏父类 MySQL 场景的字段契约。
    """

    #: 表名（sqlserver 命名空间下唯一，前缀 sqlserver_）；与 mysql_cluster_apply 分表存放
    table_name: str = "sqlserver_cluster_apply"
    #: 前端表格展示名
    table_display_name: str = _("SQLServer 集群交付信息")
