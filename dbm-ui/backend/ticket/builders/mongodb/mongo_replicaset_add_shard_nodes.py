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

from backend.db_meta.enums import MachineType
from backend.db_meta.models import AppCache
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import get_mongodb_cluster_tolerance
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBReplicaAddShardNodesDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AddShardNodesDetailSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(help_text=_("集群ID")))
        db_version = serializers.CharField(help_text=_("集群版本"))
        current_shard_nodes_num = serializers.IntegerField(help_text=_("当前shard节点数"))
        add_shard_nodes_num = serializers.IntegerField(help_text=_("扩容shard节点数"))
        node_replica_count = serializers.IntegerField(help_text=_("单机部署实例数"))
        shards_num = serializers.IntegerField(help_text=_("当前集群分片数"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    cluster_type = serializers.CharField(help_text=_("集群版本"))
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    infos = serializers.ListSerializer(help_text=_("扩容shard节点数申请信息"), child=AddShardNodesDetailSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return attrs


class MongoDBReplicaAddShardNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.increase_node

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBReplicaAddShardNodesResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="shard_nodes",
            remain_machine_type=MachineType.MONGODB,
            tolerance=get_mongodb_cluster_tolerance,
            tolerance_type="mongodb",
        )

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            for info in next_flow.details["ticket_data"]["infos"]:
                info["add_shard_nodes"] = info.pop("shard_nodes")


@builders.BuilderFactory.register(
    TicketType.MONGODB_REPLICA_ADD_SHARD_NODES, is_apply=True, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBReplicaAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBReplicaAddShardNodesDetailSerializer
    inner_flow_builder = MongoDBReplicaAddShardNodesFlowParamBuilder
    inner_flow_name = _("MongoDB 副本集扩容shard节点数执行")
    resource_batch_apply_builder = MongoDBReplicaAddShardNodesResourceParamBuilder
