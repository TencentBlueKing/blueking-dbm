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

from backend.db_meta.models.sqlserver_dts import SqlserverDtsInfo
from backend.flow.consts import SqlserverDtsMode
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class ManualTerminateSyncSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("单据ID"))

    def validate(self, attrs):
        ticket = Ticket.objects.get(id=attrs["ticket_id"])
        if ticket.ticket_type != TicketType.SQLSERVER_DATA_MIGRATE:
            raise serializers.ValidationError(_("请保证单据类型是[SQLServer 数据迁移]"))
        if ticket.details["dts_mode"] != SqlserverDtsMode.INCR:
            raise serializers.ValidationError(_("请保证迁移模式是[增量备份迁移]"))
        return attrs


class ManualTerminateSyncResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"ticket_id": 3}}


class ForceFailedMigrateSerializer(serializers.Serializer):
    dts_id = serializers.IntegerField(help_text=_("单据ID"))

    def validate(self, attrs):
        if not SqlserverDtsInfo.objects.filter(id=attrs["dts_id"]).count():
            raise serializers.ValidationError(_("迁移记录{}不存在").format(attrs["dts_id"]))
        return attrs
