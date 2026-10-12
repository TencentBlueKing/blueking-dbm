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

from datetime import datetime, timedelta
from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.oracle.helpers.time_window import to_display_tz


class OracleAddrMixin(serializers.Serializer):
    """所有 Oracle MCP 工具的通用入参：bk_cloud_id 和 address 均必填。"""

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址（鉴权维度）"))


TIME_HELP = _("ISO 8601 带时区偏移，格式 YYYY-MM-DDTHH:MM:SS±HH:MM（例 '2026-11-18T11:07:34+08:00'）")


class OracleTimeWindowMixin(serializers.Serializer):
    """按绝对时间区间 [begin_time, end_time] 分析的通用入参（ASH / AWR 共用）。"""

    begin_time = serializers.CharField(help_text=_("起始时间，{fmt}").format(fmt=TIME_HELP))
    end_time = serializers.CharField(help_text=_("结束时间（晚于 begin_time），{fmt}").format(fmt=TIME_HELP))

    # 跨度上限（小时），None 表示不限制
    max_span_hours: Optional[int] = None
    span_exceeded_hint = ""

    @staticmethod
    def _parse(value: str, field: str) -> datetime:
        """解析 ISO 8601，必须带时区偏移（精确到分钟）。"""
        try:
            dt = datetime.fromisoformat(value.strip())
        except ValueError:
            dt = None
        offset = dt.utcoffset() if dt else None
        if offset is None or offset.total_seconds() % 60:
            raise serializers.ValidationError({field: _("时间必须为 ISO 8601 带时区偏移，例 '2026-11-18T11:07:34+08:00'")})
        return to_display_tz(dt.replace(microsecond=0))

    def validate(self, attrs):
        attrs = super().validate(attrs)
        begin = self._parse(attrs["begin_time"], "begin_time")
        end = self._parse(attrs["end_time"], "end_time")
        if end <= begin:
            raise serializers.ValidationError(_("end_time 必须晚于 begin_time"))
        if self.max_span_hours and end - begin > timedelta(hours=self.max_span_hours):
            raise serializers.ValidationError(
                _("时间跨度不能超过 {hours} 小时。{hint}").format(hours=self.max_span_hours, hint=self.span_exceeded_hint)
            )
        # 统一换算为展示时区并规范化为 YYYY-MM-DDTHH:MM:SS±HH:MM，与 SQL 侧 TO_TIMESTAMP_TZ 格式严格对齐
        attrs["begin_time"] = begin.isoformat()
        attrs["end_time"] = end.isoformat()
        return attrs
