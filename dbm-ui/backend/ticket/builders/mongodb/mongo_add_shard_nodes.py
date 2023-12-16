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
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBAddShardNodesDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AddShardNodesDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        add_shard_nodes = serializers.CharField(help_text=_("扩容shard节点数"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    infos = serializers.ListSerializer(help_text=_("扩容shard节点数申请信息"), child=AddShardNodesDetailSerializer())

    def validate(self, attrs):
        return attrs


class MongoDBAddShardNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        pass


class MongoDBAddShardNodesResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        super().format()
        # 扩容shard节点数对亲和性没有要求，但是需要新机器和集群在同一个城市
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = id__cluster[info["cluster_id"]]
            info["resource_spec"]["shard_nodes"].update(location_spec={"city": cluster.region, "sub_zone_ids": []})

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            machine_specs = self.format_machine_specs(next_flow.details["ticket_data"]["resource_spec"])
            next_flow.details["ticket_data"].update(machine_specs=machine_specs)


@builders.BuilderFactory.register(TicketType.MONGODB_ADD_SHARD_NODES, is_apply=True)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBAddShardNodesDetailSerializer
    inner_flow_builder = MongoDBAddShardNodesFlowParamBuilder
    inner_flow_name = _("MongoDB 扩容shard节点数执行")
    resource_batch_apply_builder = MongoDBAddShardNodesResourceParamBuilder
