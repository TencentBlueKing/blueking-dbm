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

from backend.configuration.constants import DBType


class TzAwareDateTimeField(serializers.DateTimeField):
    def enforce_timezone(self, value):
        if value.tzinfo is None:
            raise serializers.ValidationError(_("时间必须包含时区信息, 例如: 2026-05-25T12:00:00+08:00"))
        return super().enforce_timezone(value)


class RegisterCalleePlanInputSerializer(serializers.Serializer):
    callee_mcp_id = serializers.CharField(help_text=_("被调用的 MCP 工具 operation_id"))
    params = serializers.JSONField(help_text=_("调用参数"), default=dict)
    time_window_start = TzAwareDateTimeField(help_text=_("计划生效起始时间, ISO 8601 格式且必须包含时区信息"))
    time_window_end = TzAwareDateTimeField(help_text=_("计划生效截止时间, ISO 8601 格式且必须包含时区信息"))
    max_call_count = serializers.IntegerField(help_text=_("最大调用次数"), min_value=1)
    db_type = serializers.ChoiceField(choices=DBType.get_choices(), help_text=_("db 类型"))
