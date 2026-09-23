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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.oracle import OracleController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.oracle.base import BaseOracleTicketFlowBuilder, OracleOpsBaseDetailSerializer
from backend.ticket.constants import TicketType


class OracleMasterSlaveSwitchDetailSerializer(OracleOpsBaseDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        master = HostInfoSerializer(help_text=_("主库 IP"))
        slave = HostInfoSerializer(help_text=_("从库 IP"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    is_check_process = serializers.BooleanField(help_text=_("是否检测业务连接"), default=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # 校验集群类型是否都为主从
        super().validated_cluster_type(attrs, ClusterType.OraclePrimaryStandby)
        return attrs


class OracleMasterFailOverParamBuilder(builders.FlowParamBuilder):
    controller = OracleController.oracle_master_failover_scene


@builders.BuilderFactory.register(TicketType.ORACLE_MASTER_FAIL_OVER, iam=ActionEnum.ORACLE_MANAGE)
class OracleMasterFailOverFlowBuilder(BaseOracleTicketFlowBuilder):
    serializer = OracleMasterSlaveSwitchDetailSerializer
    inner_flow_builder = OracleMasterFailOverParamBuilder
    inner_flow_name = _("ORACLE 主库故障切换")
