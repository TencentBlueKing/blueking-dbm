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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLClusterStandardizeDetailSerializer(MySQLBaseOperateDetailSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices())
    cluster_ids = serializers.ListField(child=serializers.IntegerField())
    departs = serializers.ListField(child=serializers.ChoiceField(choices=DeployPeripheralToolsDepart.get_choices()))
    with_deploy_binary = serializers.BooleanField()
    with_deploy_config = serializers.BooleanField()
    with_collect_sysinfo = serializers.BooleanField()
    with_bk_plugin = serializers.BooleanField()
    with_cc_standardize = serializers.BooleanField()
    with_instance_standardize = serializers.BooleanField()

    def validate(self, attrs):
        cluster_ids = attrs.get("cluster_ids")
        cluster_type = attrs.get("cluster_type")

        if Cluster.objects.filter(pk__in=cluster_ids).exclude(cluster_type=cluster_type).exists():
            raise serializers.ValidationError(_("集群类型不匹配"))


class MySQLClusterStandardizeFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.cluster_standardize


@builders.BuilderFactory.register(TicketType.MYSQL_CLUSTER_STANDARDIZE)
class MySQLClusterStandardizeFlowBuilder(TicketFlowBuilder):
    default_need_itsm = False
    default_need_manual_confirm = False
    serializer = MySQLClusterStandardizeDetailSerializer
    inner_flow_builder = MySQLClusterStandardizeFlowParamBuilder
    inner_flow_name = _("MySQL集群标准化")
    retry_type = FlowRetryType.MANUAL_RETRY
    group = DBType.MySQL
