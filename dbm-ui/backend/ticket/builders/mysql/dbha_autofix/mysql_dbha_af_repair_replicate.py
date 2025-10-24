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

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MySQLDBHAAFRepairReplicateDetailSerializer(MySQLBaseOperateDetailSerializer):
    class MySQLDBHAAFRepairReplicateInfoSerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField()
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        new_master_address = serializers.CharField(help_text=_("master ip:port"))
        new_master_log_file = serializers.CharField()
        new_master_log_pos = serializers.IntegerField()
        old_master_address = serializers.CharField()
        ro_slave_addresses = serializers.ListField(child=serializers.CharField(), help_text=_("slave ip:port 列表"))
        check_id = serializers.IntegerField()

    infos = serializers.ListField(child=MySQLDBHAAFRepairReplicateInfoSerializer())


class MySQLDBHAAFRepairReplicateInnerFlowBuilder(builders.FlowParamBuilder):
    controller = MySQLController.dbha_autofix_repair_replicate_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.MYSQL_DBHA_AF_REPAIR_REPLICATE, is_apply=True)
class MySQLDBHAAFRepairReplicateFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLDBHAAFRepairReplicateDetailSerializer
    inner_flow_builder = MySQLDBHAAFRepairReplicateInnerFlowBuilder
    inner_flow_name = _(TicketType.MYSQL_DBHA_AF_REPAIR_REPLICATE)
    default_need_itsm = False
    default_need_manual_confirm = False

    @property
    def need_itsm(self):
        return False
