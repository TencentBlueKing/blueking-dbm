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
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(help_text=_("集群ID")))
        current_shard_nodes_num = serializers.IntegerField(help_text=_("当前shard节点数"))
        add_shard_nodes_num = serializers.IntegerField(help_text=_("扩容shard节点数"))
        node_replica_count = serializers.IntegerField(help_text=_("单机部署实例数"))
        shards_num = serializers.IntegerField(help_text=_("扩容shard分片数"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    infos = serializers.ListSerializer(help_text=_("扩容shard节点数申请信息"), child=AddShardNodesDetailSerializer())

    def validate(self, attrs):
        cluster_ids = list(itertools.chain(*[info["cluster_ids"] for info in attrs["infos"]]))
        clusters = Cluster.objects.filter(id__in=cluster_ids)

        # 校验集群类型一致
        self.validate_cluster_same_attr(clusters, attrs=["cluster_type"])

        return attrs


class MongoDBAddShardNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.increase_node

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBAddShardNodesResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        super().format()
        # 扩容shard节点数对亲和性没有要求，但是需要新机器和集群在同一个城市
        cluster_ids = [cluster_id for info in self.ticket_data["infos"] for cluster_id in info["cluster_ids"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = id__cluster[info["cluster_ids"][0]]
            info["resource_spec"]["shard_nodes"].update(location_spec={"city": cluster.region, "sub_zone_ids": []})

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            # 将infos内容对info进行ClusterTpye分类
            cluster_ids = [cluster_id for info in self.ticket_data["infos"] for cluster_id in info["cluster_ids"]]
            id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
            mongo_type__apply_infos: Dict[str, List] = defaultdict(list)
            for info in next_flow.details["ticket_data"]["infos"]:
                info["resource_spec"] = self.format_machine_specs_info(info["resource_spec"])
                info["add_shard_nodes"] = info.pop("shard_nodes")
                cluster = id__cluster[info["cluster_ids"][0]]
                info["db_version"] = cluster.major_version
                cluster_type = cluster.cluster_type
                if cluster_type == ClusterType.MongoShardedCluster.value:
                    info["cluster_id"] = info.pop("cluster_ids")[0]
                mongo_type__apply_infos[cluster_type].append(info)

            next_flow.details["ticket_data"]["infos"] = mongo_type__apply_infos


@builders.BuilderFactory.register(TicketType.MONGODB_ADD_SHARD_NODES, is_apply=True)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBAddShardNodesDetailSerializer
    inner_flow_builder = MongoDBAddShardNodesFlowParamBuilder
    inner_flow_name = _("MongoDB 扩容shard节点数执行")
    resource_batch_apply_builder = MongoDBAddShardNodesResourceParamBuilder
