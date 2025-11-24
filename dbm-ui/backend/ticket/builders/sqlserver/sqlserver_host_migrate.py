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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import (
    BaseSQLServerHATicketFlowBuilder,
    SQLServerBaseOperateDetailSerializer,
)
from backend.ticket.builders.sqlserver.sqlserver_cluster_migrate import SQLServerClusterMigrateResourceParamBuilder
from backend.ticket.constants import TicketType


class SQLServerHostMigrateDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        origin_ip = serializers.JSONField(help_text=_("源主机信息"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )


class SQLServerHostMigrateResourceParamBuilder(SQLServerClusterMigrateResourceParamBuilder):
    pass


class SQLServerHostMigrateParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.ha_switch_scene
    validator = None


@builders.BuilderFactory.register(TicketType.SQLSERVER_HOST_MIGRATE)
class SQLServerHostMigrateFlowBuilder(BaseSQLServerHATicketFlowBuilder):
    serializer = SQLServerHostMigrateDetailSerializer
    inner_flow_builder = SQLServerHostMigrateParamBuilder
    inner_flow_name = _("SQLServer 整机迁移")
    resource_batch_apply_builder = SQLServerHostMigrateResourceParamBuilder
