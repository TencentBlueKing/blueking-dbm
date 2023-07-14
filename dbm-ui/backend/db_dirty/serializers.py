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

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.constants import INT_MAX
from backend.db_dirty.mock import DIRTY_MACHINE_LIST
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Spec
from backend.db_services.dbresource.constants import ResourceOperation
from backend.db_services.dbresource.mock import RECOMMEND_SPEC_DATA, RESOURCE_LIST_DATA, SPEC_DATA
from backend.db_services.ipchooser.serializers.base import QueryHostsBaseSer
from backend.ticket.constants import TicketStatus, TicketType


class QueryDirtyMachineSerializer(serializers.Serializer):
    ip_list = serializers.CharField(help_text=_("过滤的主机IP列表，以逗号分隔"), required=False)
    ticket_id = serializers.IntegerField(help_text=_("过滤的单据ID"), required=False)
    task_id = serializers.CharField(help_text=_("过滤的任务ID"), required=False)
    ticket_type = serializers.ChoiceField(help_text=_("过滤的单据类型"), choices=TicketType.get_choices(), required=False)
    operator = serializers.CharField(help_text=_("操作人"), required=False)

    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)

    def validate(self, attrs):
        if "ip_list" in attrs:
            attrs["ip_list"] = attrs["ip_list"].split(",")

        return attrs


class QueryDirtyMachineResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": DIRTY_MACHINE_LIST}


class DeleteDirtyMachineSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("待转移的主机ID列表"))
