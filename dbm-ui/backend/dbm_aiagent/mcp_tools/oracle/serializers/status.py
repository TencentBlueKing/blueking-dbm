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

from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_MAX_ROWS
from backend.dbm_aiagent.mcp_tools.oracle.serializers.basic_info import OracleAddrMixin


class CheckInstanceStatusInputSerializer(OracleAddrMixin):
    pass


class _HealthSerializer(serializers.Serializer):
    level = serializers.ChoiceField(
        choices=[("healthy", "healthy"), ("warning", "warning"), ("critical", "critical")],
        help_text=_("综合健康等级"),
    )
    reasons = serializers.ListField(child=serializers.CharField(), help_text=_("异常/告警原因列表"))


class CheckInstanceStatusOutputSerializer(serializers.Serializer):
    reachable = serializers.BooleanField(help_text=_("是否能成功建立连接并查询"))
    latency_ms = serializers.IntegerField(help_text=_("本次探活耗时（毫秒）"))
    health = _HealthSerializer()
    state = serializers.DictField(help_text=_("v$instance + v$database 关键字段"))
    sessions = serializers.DictField(help_text=_("会话数 + 会话上限 + 使用率"))


class GetAlertLogErrorsInputSerializer(OracleAddrMixin):
    minutes = serializers.IntegerField(required=False, default=120, min_value=1, max_value=4320, help_text=_("回溯分钟数"))
    limit = serializers.IntegerField(required=False, default=ORACLE_MAX_ROWS, min_value=1, max_value=ORACLE_MAX_ROWS)


class GetAlertLogErrorsOutputSerializer(serializers.Serializer):
    errors = serializers.ListField(child=serializers.DictField())
    count = serializers.IntegerField()
    minutes = serializers.IntegerField()
