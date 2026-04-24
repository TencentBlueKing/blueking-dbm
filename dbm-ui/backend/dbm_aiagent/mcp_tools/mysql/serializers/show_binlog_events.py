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
import re
from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

_SAFE_BINLOG_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")


class ShowBinlogEventsInputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), default=None, allow_null=True)
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    log_name = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
        help_text=_("binlog 文件名, 对应 IN 子句, 如 mysql-bin.000001, 不填则省略 IN"),
    )
    from_pos = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text=_("对应 FROM 子句的起始位点, 不填则省略 FROM"),
    )
    limit_offset = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text=_("LIMIT 的 offset, 与 limit_row_count 一起构成 LIMIT offset, row_count, 不填则使用单参数 LIMIT row_count"),
    )
    limit_row_count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        help_text=_("返回行数 row_count, 最大 100"),
    )

    def validate_log_name(self, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        if not _SAFE_BINLOG_NAME.match(value):
            raise serializers.ValidationError(_("log_name 不合法, 仅允许字母、数字、点、下划线与连字符"))
        return value


class ShowBinlogEventsOutputSerializer(serializers.Serializer):
    events = serializers.ListField(
        child=serializers.DictField(child=serializers.JSONField()),
        help_text=_("SHOW BINLOG EVENTS 结果行, 每行为列名到值的 JSON 对象, 列随 MySQL 版本可能不同"),
    )
