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

from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import DisplayInfoSerializer, SkipToRepresentationMixin
from backend.ticket.builders.redis.base import BaseRedisInstanceTicketFlowBuilder
from backend.ticket.constants import TicketType


class RedisClusterInsMigrateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    class RedisClusterInsMigrateItemSerializer(DisplayInfoSerializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("实例迁移单据详情"), child=RedisClusterInsMigrateItemSerializer())

    def validate(self, attrs):
        return attrs


class RedisClusterInsMigrateBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_ins_migrate

    def format_ticket_data(self):
        cluster_id = self.ticket_data["infos"][0]["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)
        self.ticket_data.update(
            cluster_id=cluster.id,
            bk_cloud_id=cluster.bk_cloud_id,
            resource_spec=self.ticket_data["infos"][0]["resource_spec"],
        )


class RedisClusterInstanceApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        cluster_id = self.ticket_data["infos"][0]["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)
        self.ticket_data.update(
            cluster_id=cluster.id,
            bk_cloud_id=cluster.bk_cloud_id,
            resource_spec=self.ticket_data["infos"][0]["resource_spec"],
        )
        self.patch_info_affinity_location(roles=["backend_group"])

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            migrate_list = {
                "src_master": f'{info["old_nodes"]["master"][0]["ip"]}:{info["old_nodes"]["master"][0]["port"]}',
                "src_slave": f'{info["old_nodes"]["slave"][0]["ip"]}:{info["old_nodes"]["slave"][0]["port"]}',
                "dest_master": f'{ticket_data["nodes"]["backend_group"][0]["master"]["ip"]}',
                "dest_slave": f'{ticket_data["nodes"]["backend_group"][0]["slave"]["ip"]}',
                "resource_spec": ticket_data["resource_spec"],
            }
            info["migrate_list"] = [migrate_list]
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_INS_MIGRATE)
class RedisClusterInsMigrateBuilder(BaseRedisInstanceTicketFlowBuilder):
    serializer = RedisClusterInsMigrateDetailSerializer
    inner_flow_builder = RedisClusterInsMigrateBuilder
    resource_apply_builder = RedisClusterInstanceApplyResourceParamBuilder
    inner_flow_name = _("Redis 集群指定实例迁移")
