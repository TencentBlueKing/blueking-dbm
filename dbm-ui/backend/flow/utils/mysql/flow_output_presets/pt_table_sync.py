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

mysql/spider pt-table-sync 数据修复类摘要预设。

职责：
  - 描述"每(集群, slave-ip, 库, 表) 一行"的 pt-table-sync 修复结果摘要。
  - 依托 table_primary_key = "unique_key" 走 FlowOutputHandler.insert_data 的主键合并分支，
    实现节点重试 / 同表多次修复对同一 (集群, IP, 库, 表) 记录的"后写覆盖前写"幂等语义。

数据源 / 调用通道：
  - 由 mysql pt-table-sync 流程节点在采集完 PtTableSyncContext.result 后调用：
    `FlowOutputHandler(PtTableSyncSummarySerializer).insert_data(root_id, data)`。
  - PtTableSyncContext.result 结构：{slave_ip: [{db_name, table_name, status, reason, ...}, ...]}
    需要由调用方按 (集群, ip, 库, 表) 展平为每行 dict 后交给本预设写入。

边界：
  - FlowOutputHandler.insert_data 只支持"单字段可 hash"主键，因此本预设不使用
    (cluster_domain, ip, db_name, table_name) 组合主键，而是要求调用方将四元组拼成
    单字段 unique_key（推荐格式："{cluster_domain}|{ip}|{db_name}|{table_name}"）。
    与 ClusterApplySummarySerializer.cluster_domain_and_port 同款惯例：主键字段自身作为
    一列参与前端展示，无需额外隐藏机制。
  - status / reason 直接透传 db-actuator 侧输出（例如 ok / skipped / error），本预设不做
    枚举强校验，避免与 Go 侧新增状态耦合。
  - reason 允许为空串（例如 status=ok 时无需理由）。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class PtTableSyncSummarySerializer(BaseFlowOutputSerializer):
    """mysql pt-table-sync 数据修复摘要（每 (集群, slave-ip, 库, 表) 一行）。

    功能说明：
      - 描述 pt-table-sync 对单个 (集群, slave-ip, 库, 表) 的一次修复结果，字段顺序即前端表头顺序。
      - 主键 `unique_key` 由调用方按 "{cluster_domain}|{ip}|{db_name}|{table_name}" 拼接得到；
        通过 `table_primary_key = "unique_key"` 走 FlowOutputHandler.insert_data 主键合并分支，
        实现同 (集群, ip, 库, 表) 重复写入时的"后写覆盖前写"幂等。
      - 主键字段沉在最后一列，与 ClusterApplySummarySerializer.cluster_domain_and_port
        同款惯例（主键即业务列，无需额外隐藏机制）。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain (str, 必填, 非空): 集群主域名，例如 "c1.mysql.example.db"
      - ip (str, 必填, 非空, IP): 执行修复的 slave 节点 IP，走基类 IpField 严格校验
      - db_name_table_name (str, 必填, 非空): 库.表，格式 "db_name.table_name"
      - status (str, 必填, 非空): 修复状态，透传 db-actuator 输出（ok / skipped / error 等）
      - reason (str, 可空, 默认 ""): 修复结果说明；status=ok 场景允许为空串
      - unique_key (str, 必填, 非空): 行标识，格式 "{cluster_domain}|{ip}|{db_name}|{table_name}"

    输出：
      - 写入 FlowSummary.summary 中 table_name = "mysql_pt_table_sync" 的表 values；
        每次调用产出的 dict 会按 unique_key 主键合并进该表 values 数组。

    边界：
      - cluster_domain / ip / db_name_table_name / status / unique_key 任一为空 -> is_valid
        抛 ValidationError。
      - ip 非合法 IPv4/IPv6 字面量 -> IpField 校验失败抛 ValidationError。
      - 相同 unique_key 的重复写入 -> 依赖 insert_data 主键合并分支覆盖旧行，`values` 长度不变。
      - status / reason 不做枚举校验，避免与 db-actuator 侧新增状态耦合。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_pt_table_sync"
    #: 前端表格展示名
    table_display_name: str = _("数据修复结果")
    #: 表主键：调用方需拼成 "{cluster_domain}|{ip}|{db_name}|{table_name}" 的单字段串
    #: 与 ClusterApplySummarySerializer.cluster_domain_and_port 同款惯例——
    #: 主键字段本身作为一列参与前端展示，用户可视化"这一行的唯一定位坐标"。
    table_primary_key: str = "unique_key"

    cluster_domain = serializers.CharField(help_text=_("集群主域名"), required=True, allow_blank=False)
    ip = BaseFlowOutputSerializer.IpField(help_text=_("修复节点IP"), required=True)
    db_name_table_name = serializers.CharField(help_text=_("库.表"), required=True, allow_blank=False)
    status = serializers.CharField(help_text=_("修复状态"), required=True, allow_blank=False)
    #: 修复结果说明；透传 db-actuator 的 reason 字段，前端按纯文本渲染
    reason = serializers.CharField(help_text=_("修复结果"), required=False, allow_blank=True, default="")
    #: 行唯一标识：格式 "{cluster_domain}|{ip}|{db_name}|{table_name}"；
    #: 既作为 FlowOutputHandler 主键做同行覆盖合并，也作为前端末列展示（对齐
    #: ClusterApplySummarySerializer.cluster_domain_and_port 的做法）。
    unique_key = serializers.CharField(help_text=_("行标识"), required=True, allow_blank=False)
