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
import itertools
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBReduceShardNodesDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReduceMongosDetailSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(help_text=_("集群ID")))
        reduce_shard_nodes = serializers.IntegerField(help_text=_("缩容数量"))
        current_shard_nodes_num = serializers.IntegerField(help_text=_("当前shard节点数量"))
        machine_instance_num = serializers.IntegerField(help_text=_("单机部署实例数量"))
        shard_num = serializers.IntegerField(help_text=_("shard数量"))

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListSerializer(help_text=_("缩容shard节点数信息"), child=ReduceMongosDetailSerializer())

    def validate(self, attrs):
        cluster_ids = list(itertools.chain(*[info["cluster_ids"] for info in attrs["infos"]]))
        clusters = Cluster.objects.filter(id__in=cluster_ids)

        # 校验集群类型一致
        self.validate_cluster_same_attr(clusters, attrs=["cluster_type"])
        return attrs


class MongoDBReduceShardNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.reduce_node

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr
        cluster_ids = [cluster_id for info in self.ticket_data["infos"] for cluster_id in info["cluster_ids"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        mongo_type__apply_infos: Dict[str, List] = defaultdict(list)
        for info in self.ticket_data["infos"]:
            cluster = id__cluster[info["cluster_ids"][0]]
            info["db_version"] = cluster.major_version
            cluster_type = cluster.cluster_type
            if cluster_type == ClusterType.MongoShardedCluster.value:
                info["cluster_id"] = info.pop("cluster_ids")[0]
            mongo_type__apply_infos[cluster_type].append(info)

        self.ticket_data["infos"] = mongo_type__apply_infos


@builders.BuilderFactory.register(TicketType.MONGODB_REDUCE_SHARD_NODES)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBReduceShardNodesDetailSerializer
    inner_flow_builder = MongoDBReduceShardNodesFlowParamBuilder
    inner_flow_name = _("MongoDB 缩容Shard节点数执行")
