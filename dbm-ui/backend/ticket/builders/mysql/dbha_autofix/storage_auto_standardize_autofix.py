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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import TicketType


class StorageAutoStandardizeAutofixDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField()
    bk_biz_id = serializers.IntegerField()
    ip = serializers.IPAddressField()
    cluster_id = serializers.IntegerField()
    # port_list = serializers.ListField(serializers.IntegerField())
    # check_id = serializers.IntegerField()
    # machine_type = serializers.CharField()


class StorageAutoStandardizeAutofixInnerFlowBuilder(builders.FlowParamBuilder):
    controller = MySQLController.storage_auto_standardize_autofix_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.MYSQL_STORAGE_STANDARDIZE_AUTOFIX, is_apply=True)
class StorageAutoStandardizeAutofixFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = StorageAutoStandardizeAutofixDetailSerializer
    inner_flow_builder = StorageAutoStandardizeAutofixInnerFlowBuilder
    inner_flow_name = _("MySQL 存储自愈自动重标准化")
    default_need_itsm = False
    default_need_manual_confirm = False

    @property
    def need_itsm(self):
        return False
