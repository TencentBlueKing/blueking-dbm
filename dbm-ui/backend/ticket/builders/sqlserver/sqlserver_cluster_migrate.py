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

from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import (
    BaseSQLServerHATicketFlowBuilder,
    SQLServerBaseOperateDetailSerializer,
    SQLServerBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class SQLServerClusterMigrateDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )


class SQLServerClusterMigrateResourceParamBuilder(SQLServerBaseOperateResourceParamBuilder):
    def format(self):
        super().format()
        for info in self.ticket_data["infos"]:
            cluster = Cluster.objects.filter(id=info["cluster_ids"][0]).first()
            for role in info["resource_spec"]:
                self.patch_common_affinity(
                    info,
                    role=role,
                    cluster=cluster,
                    exclusive_hosts=[],
                    tolerance=0,
                )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            if "backend_group" in info:
                backend_group = info.pop("backend_group")[0]
                info["new_hosts"] = [backend_group[role] for role in backend_group]

        next_flow.save(update_fields=["details"])


class SQLServerClusterMigrateParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.sqlserver_cluster_migrate_for_ins_scene
    validator = SqlserverController.sqlserver_cluster_migrate_for_ins_scene.validator


@builders.BuilderFactory.register(TicketType.SQLSERVER_CLUSTER_MIGRATE)
class SQLServerClusterMigrateFlowBuilder(BaseSQLServerHATicketFlowBuilder):
    serializer = SQLServerClusterMigrateDetailSerializer
    inner_flow_builder = SQLServerClusterMigrateParamBuilder
    inner_flow_name = _("SQLServer 集群迁移")
    resource_batch_apply_builder = SQLServerClusterMigrateResourceParamBuilder
