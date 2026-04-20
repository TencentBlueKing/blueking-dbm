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


class MySQLBackupLogInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    backup_id = serializers.CharField(help_text=_("备份 ID"), default=None, required=False)
    rollback_time = serializers.DateTimeField(
        help_text=_("Rollback time in ISO 8601 format (e.g. '2026-01-08T16:33:38+08:00'). "),
        default=None,
        required=False,
    )
    start_time = serializers.DateTimeField(
        help_text=_("Start of the query time range in ISO 8601 format (e.g. '2026-01-08T16:33:38+08:00'). "),
        default=None,
        required=False,
    )
    end_time = serializers.DateTimeField(
        help_text=_("Start of the query time range in ISO 8601 format (e.g. '2026-01-08T16:33:38+08:00'). "),
        default=None,
        required=False,
    )


class MySQLBackupLogOutputSerializer(serializers.Serializer):
    backup_infos = serializers.ListSerializer(child=serializers.DictField(), help_text=_("备份信息列表"))
