# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class _Section_Inputs:
    """分组：MCP 工具的输入字段。

    本组职责
        定义 `sqlserver_get_stored_procedure` MCP 工具的入参契约：
        按精确坐标（cluster_domain + dbname + schema.proc）单次获取
        SQLServer 单个存储过程的【完整原始 T-SQL 定义体】，专用于静态风险分析。
    本组类
        - SQLServerProcedureDefinitionInputSerializer
    边界
        - 本工具不提供枚举/模糊匹配/批量；调用方必须已确切知道 SP 名称；
        - procedure 支持 'schema.proc' 或 'proc'（缺省 schema=dbo）；
        - 不接受任何写操作语义；只读访问 sys.sql_modules / sys.procedures。
    """


class SQLServerProcedureDefinitionInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dbname = serializers.CharField(
        help_text=_("业务库名（区分实际承载该 SP 的数据库；不允许为系统库 master/msdb/model/tempdb 之外的拼写错误）"),
    )
    procedure = serializers.CharField(
        help_text=_(
            "存储过程名称，支持两种形式："
            "1) 'schema.proc' 显式指定 schema；"
            "2) 'proc' 缺省 schema=dbo。"
            "调用前必须已确切知道该名称（本工具不做枚举/模糊匹配/批量）。"
            "如需分析多个 SP，请多次调用本工具"
        ),
    )
    max_definition_chars = serializers.IntegerField(
        required=False,
        default=200000,
        min_value=10000,
        max_value=500000,
        help_text=_("定义体字符数硬上限；超出则 status=too_large 且 definition=null（不截断，避免风险分析失真）。" "默认 200000，最大 500000"),
    )
    address = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
        help_text=_("可选实例地址 ip:port；不传时缺省走 master"),
    )


class _Section_Output:
    """分组：MCP 工具的顶层输出（扁平结构）。

    本组职责
        定义对外返回的最外层结构。单次只查 1 个 SP，因此**不再嵌套 results 数组**，
        将所有字段拍平到顶层，便于 LLM 解析。
    本组类
        - SQLServerProcedureDefinitionOutputSerializer
    边界
        - status 是流程控制核心字段，调用方必须先看 status：
            * ok         -> definition 字段为 SP 原文
            * not_found  -> 该 SP 不存在
            * encrypted  -> SP 用了 WITH ENCRYPTION，无法解析
            * too_large  -> 定义体超过 max_definition_chars，未返回 definition
            * error      -> RPC 或其他异常
        - definition 是 sys.sql_modules.definition 原文，**不做任何脱敏**，
          可能包含硬编码凭据/密钥/IP；仅用于分析，不可直接回显给最终用户；
        - modify_date 用于"祖传代码"风险信号识别；
        - definition_total_chars / line_count 体量信号 + LLM 上下文消耗预估。
    """


class SQLServerProcedureDefinitionOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际命中的实例 ip:port"))
    role = serializers.CharField(help_text=_("实例内部角色，例如 master/slave"))
    dbname = serializers.CharField(help_text=_("业务库名（调用方原样回传）"))
    procedure = serializers.CharField(help_text=_("SP 名称（调用方原样回传，便于对账）"))

    status = serializers.ChoiceField(
        choices=["ok", "not_found", "encrypted", "too_large", "error"],
        help_text=_(
            "查询状态："
            "ok=已成功获取定义体；"
            "not_found=SP 不存在；"
            "encrypted=SP 使用了 WITH ENCRYPTION 加密，无法解析；"
            "too_large=定义体超过 max_definition_chars，definition 字段为 null；"
            "error=RPC/权限等异常，详见 error 字段"
        ),
    )
    error = serializers.CharField(
        help_text=_("非 ok 状态下的错误描述；ok 状态时为 null"),
        allow_null=True,
        allow_blank=True,
    )

    modify_date = serializers.CharField(
        help_text=_("SP 最近一次修改时间（来源 sys.objects.modify_date）；用于识别长期未维护的祖传代码"),
        allow_null=True,
    )
    is_encrypted = serializers.IntegerField(
        help_text=_("SP 是否启用 WITH ENCRYPTION：1=是（definition 为 null），0=否"),
    )
    definition_total_chars = serializers.IntegerField(
        help_text=_("definition 原始字符长度；可用于评估 LLM 上下文消耗"),
    )
    line_count = serializers.IntegerField(
        help_text=_("definition 行数；体量信号，超大 SP 本身是风险信号"),
    )
    definition = serializers.CharField(
        help_text=_(
            "SP 完整原始 T-SQL 定义体（来自 sys.sql_modules.definition），与 SSMS 右键 Modify 一致；"
            "**不做任何脱敏**，可能包含硬编码凭据/密钥；"
            "status != ok 时为 null"
        ),
        allow_null=True,
        allow_blank=True,
    )
    notice = serializers.CharField(
        help_text=_("使用注意事项（提示 definition 是原文，含敏感风险，仅供分析）"),
        allow_blank=True,
    )
