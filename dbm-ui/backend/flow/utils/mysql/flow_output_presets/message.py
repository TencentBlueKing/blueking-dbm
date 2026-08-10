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

mysql/spider 通用 KV 消息类摘要预设（追加型兜底）。

职责：
  - 为无法归入其他语义类别的"流水消息 / 提示 / 警告"提供兜底表结构。
  - 明确"允许重复、不做主键去重"，仅在真正追加型语义下使用。

数据源 / 调用通道：
  - 由 mysql / spider 流程节点在需要向摘要中追加一条流水日志时调用：
    `FlowOutputHandler(MessageSummarySerializer).insert_data(root_id, data)`。

边界：
  - 本预设明确 **不承诺幂等**；节点重试会产生多条相同 message 记录。若业务需要幂等，请改用
    带 `table_primary_key` 的预设（如 ClusterApplySummarySerializer / InstanceChangeSummarySerializer 等）。
  - 不适合承载结构化业务字段（如集群 / 实例信息），此类语义应走对应的专用预设。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class MessageSummarySerializer(BaseFlowOutputSerializer):
    """mysql / spider 通用 KV 消息摘要（追加型，不去重）。

    功能说明：
      - 兜底型摘要表，用于承载无法归入其他语义类别的流水消息 / 提示 / 警告。
      - **允许重复且不做主键去重**：`table_primary_key` 留空，走 FlowOutputHandler.insert_data
        的"无主键 -> 直接 extend"分支。
      - **仅在真正追加型语义下使用**；若节点会因重试等原因重复调用，请优先选择带主键的预设。

    输入参数（即 data 每一行的字段结构）：
      - level (str, 必填, 非空): 消息级别（info / warn / error）
      - message (str, 必填, 非空): 消息正文
      - context (str, 可空, 默认 ""): 附加上下文文本；前端按纯文本渲染

    输出：
      - 追加到 FlowSummary.summary 中 table_name = "mysql_message" 的表 values。

    边界：
      - level / message 缺失或空串 -> is_valid 抛 ValidationError。
      - 重复写入 -> **不去重**，会产生多条相同记录（这是本预设的预期行为）。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_message"
    #: 前端表格展示名
    table_display_name: str = _("流程消息")
    #: 追加型语义：**不设置主键**，允许重复写入
    table_primary_key: str = ""

    level = serializers.CharField(help_text=_("级别"), required=True, allow_blank=False)
    message = serializers.CharField(help_text=_("消息"), required=True, allow_blank=False)
    #: 附加上下文文本；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    context = serializers.CharField(help_text=_("上下文"), required=False, allow_blank=True, default="")
