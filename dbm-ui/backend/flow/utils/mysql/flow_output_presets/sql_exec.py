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

mysql/spider SQL 变更 / 执行结果类摘要预设。

职责：
  - 描述"每个实例一行"的 SQL 变更 / 执行结果（SQL 变更单、备份恢复、DDL 执行等）。
  - 通过 table_primary_key = "instance" (IP:Port) 保证节点重试对同一实例上一次 SQL 执行的重复
    上报走覆盖合并。

数据源 / 调用通道：
  - 由 mysql / spider SQL 执行类流程节点调用：
    `FlowOutputHandler(SqlExecResultSummarySerializer).insert_data(root_id, data)`。

边界：
  - instance 字段走 BaseFlowOutputSerializer.InstanceField，格式必须为 IP:Port。
  - 若同一实例执行多个 SQL 文件且需分别展示 -> 应改为组合主键或走 dynamic_key 机制，不属于本预设
    的常规使用范畴。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class SqlExecResultSummarySerializer(BaseFlowOutputSerializer):
    """mysql / spider SQL 执行结果摘要（每实例一行）。

    功能说明：
      - 描述实例级 SQL 变更 / 执行结果，供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "instance"` 让 FlowOutputHandler.insert_data 对同实例的重复
        写入走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构）：
      - instance (str, 必填, IP:Port): 实例标识，作为主键，格式由 InstanceField 强校验
      - sql_file (str, 必填, 非空): SQL 文件名或标识（如 "01_ddl.sql"）
      - status (str, 必填, 非空): 执行状态（success / failed / skipped）
      - affected_rows (int, 可空, 默认 0): 受影响行数
      - message (str, 可空, 默认 ""): 详细消息 / 错误原因
      - extra (str, 可空, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染

    输出：
      - 写入 FlowSummary.summary 中 table_name = "mysql_sql_exec_result" 的表 values。

    边界：
      - instance 非 IP:Port 格式 -> InstanceField.run_validators 抛校验异常。
      - sql_file / status 缺失或空串 -> is_valid 抛 ValidationError。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_sql_exec_result"
    #: 前端表格展示名
    table_display_name: str = _("SQL执行结果")
    #: 表主键：每实例一行，重复写入按 instance 覆盖合并
    table_primary_key: str = "instance"

    instance = BaseFlowOutputSerializer.InstanceField(help_text=_("实例(IP:Port)"), required=True, allow_blank=False)
    sql_file = serializers.CharField(help_text=_("SQL文件"), required=True, allow_blank=False)
    status = serializers.CharField(help_text=_("执行状态"), required=True, allow_blank=False)
    affected_rows = serializers.IntegerField(help_text=_("受影响行数"), required=False, default=0)
    message = serializers.CharField(help_text=_("详细消息"), allow_blank=True, default="")
    #: 单据私有展示文本兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
