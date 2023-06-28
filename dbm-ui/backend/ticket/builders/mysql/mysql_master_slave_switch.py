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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MysqlMasterSlaveSwitchDetailSerializer(MySQLBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        master_ip = HostInfoSerializer(help_text=_("主库 IP"))
        slave_ip = HostInfoSerializer(help_text=_("从库 IP"))
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        super().validate_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验master和slave的关联集群是否一致
        super().validate_instance_related_clusters(
            attrs, instance_key=["master_ip"], cluster_key=["cluster_ids"], role=InstanceInnerRole.MASTER
        )
        super().validate_instance_related_clusters(
            attrs, instance_key=["slave_ip"], cluster_key=["cluster_ids"], role=InstanceInnerRole.SLAVE
        )

        return attrs


class MysqlMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_switch_scene

    def format_ticket_data(self):
        # 整个单据统一注入安全模式参数
        is_safe = self.ticket_data.pop("is_safe", True)
        for index, info in enumerate(self.ticket_data["infos"]):
            self.ticket_data["infos"][index]["is_safe"] = is_safe


@builders.BuilderFactory.register(TicketType.MYSQL_MASTER_SLAVE_SWITCH)
class MysqlMasterSlaveSwitchFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlMasterSlaveSwitchDetailSerializer
    inner_flow_builder = MysqlMasterSlaveSwitchParamBuilder
    inner_flow_name = _("主从互换执行")
    retry_type = FlowRetryType.MANUAL_RETRY

    @property
    def need_manual_confirm(self):
        return True
