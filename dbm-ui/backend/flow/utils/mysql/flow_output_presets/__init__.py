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

mysql/spider 单据流程输出预设 Serializer 统一入口。

职责：
  - 按"输出语义"归类共享 BaseFlowOutputSerializer 子类，供 mysql/spider 全量单据在流程节点摘要
    (FlowSummary.summary) 中复用，避免"每单据一 Serializer 子类"的膨胀。
  - 所有预设的 table_name 命名空间统一以 "mysql_" 或 "spider_" 前缀开头，防止与其他 DB 类型冲突。
  - 提供"通过 table_primary_key 天然幂等"的能力：依托现有 FlowOutputHandler.insert_data 的主键合并
    分支，令流程节点重试对同主键的二次写入走覆盖而非追加。

数据源 / 调用通道：
  - 使用方通过 `from backend.flow.utils.mysql.flow_output_presets import XxxSerializer` 引用，
    禁止深路径 import。
  - 使用方调用 `FlowOutputHandler(XxxSerializer).insert_data(root_id, data)` 完成写入。

边界：
  - 本目录仅提供"表 schema 声明 + 主键约定"，不修改 backend/flow/utils/base/flow_output.py 内的
    BaseFlowOutputSerializer / FlowOutputHandler 任何逻辑。
  - "追加型"预设（如 MessageSummarySerializer）明确不做主键去重，允许重复写入。
"""

from backend.flow.utils.mysql.flow_output_presets.auth_result import AuthResultSummarySerializer
from backend.flow.utils.mysql.flow_output_presets.cluster_apply import ClusterApplySummarySerializer
from backend.flow.utils.mysql.flow_output_presets.instance_change import (
    InstanceChangeAction,
    InstanceChangeSummarySerializer,
)
from backend.flow.utils.mysql.flow_output_presets.message import MessageSummarySerializer
from backend.flow.utils.mysql.flow_output_presets.precheck import PrecheckResultSummarySerializer
from backend.flow.utils.mysql.flow_output_presets.sql_exec import SqlExecResultSummarySerializer

__all__ = [
    "ClusterApplySummarySerializer",
    "InstanceChangeSummarySerializer",
    "AuthResultSummarySerializer",
    "PrecheckResultSummarySerializer",
    "SqlExecResultSummarySerializer",
    "MessageSummarySerializer",
    "InstanceChangeAction",
]
