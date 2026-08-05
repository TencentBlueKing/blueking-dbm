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
from collections import defaultdict
from typing import Dict, List

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import AppCache, Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
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


class MongoDBShardAddShardNodesDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ShardAddShardNodesDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
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
    infos = serializers.ListSerializer(help_text=_("扩容shard节点数申请信息"), child=ShardAddShardNodesDetailSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return attrs


class MongoDBShardAddShardNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.increase_node

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBShardAddShardNodesResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def find_same_ip_shards(self, shard_name_ip_map):
        ip_pattern_to_shards = defaultdict(list)
        for shard_name, ip_list in shard_name_ip_map.items():
            sorted_ip_tuple = tuple(sorted(ip_list))
            ip_pattern_to_shards[sorted_ip_tuple].append(shard_name)

        same_ip_shards = {tuple(shards): ips for ips, shards in ip_pattern_to_shards.items()}
        return same_ip_shards

    def format(self):
        super().format()
        # 扩容shard节点数对亲和性没有要求，但是需要新机器和集群在同一个城市
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = id__cluster[info["cluster_id"]]
            tolerance = get_mongodb_cluster_tolerance(cluster.disaster_tolerance_level, "mongodb")

            group_num = info["shards_num"] // info["node_replica_count"]
            old_shard_nodes = info["resource_spec"].pop("shard_nodes")
            old_shard_nodes["count"] = old_shard_nodes["count"] // group_num

            inst_filter = Q(
                instance_role__in=[role for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]],
                cluster=cluster,
                machine_type=MachineType.MONGODB,
            )
            insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)
            shard_name_inst_map: Dict[str, List] = defaultdict(list)
            shard_name_ip_map: Dict[str, List] = defaultdict(list)
            for inst in insts:
                shard_name_inst_map[inst_id__shard[inst.id]].append(inst.machine)
                shard_name_ip_map[inst_id__shard[inst.id]].append(inst.machine.ip)

            same_ip_shards = self.find_same_ip_shards(shard_name_ip_map)

            index = 0
            for shard_names_t in same_ip_shards:
                role = f"mongodb_{index}"
                info[f"shards_{index}"] = list(shard_names_t)
                info["resource_spec"][role] = old_shard_nodes
                exclusive_hosts = shard_name_inst_map[shard_names_t[0]]
                self.patch_common_affinity(
                    info,
                    role=role,
                    cluster=cluster,
                    exclusive_hosts=exclusive_hosts,
                    tolerance=tolerance,
                )
                index += 1

    def get_current_shard_names(self, index, key_name):
        rollback_flow = self.ticket.current_flow()
        infos = rollback_flow.details["infos"]
        return infos[index][key_name] if infos[index].get(key_name) else []

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            for index, info in enumerate(next_flow.details["ticket_data"]["infos"]):
                info["add_shard_nodes"] = []
                group_num = info["shards_num"] // info["node_replica_count"]
                for num in range(group_num):
                    shards = self.get_current_shard_names(index, f"shards_{num}")
                    info["add_shard_nodes"].append({"shards": shards, "mongodb": info.pop(f"mongodb_{num}")})


@builders.BuilderFactory.register(
    TicketType.MONGODB_SHARD_ADD_SHARD_NODES, is_apply=True, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBShardAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBShardAddShardNodesDetailSerializer
    inner_flow_builder = MongoDBShardAddShardNodesFlowParamBuilder
    inner_flow_name = _("MongoDB 分片集群扩容shard节点数执行")
    resource_batch_apply_builder = MongoDBShardAddShardNodesResourceParamBuilder
