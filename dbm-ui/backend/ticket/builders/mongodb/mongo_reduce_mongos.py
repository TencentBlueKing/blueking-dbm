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

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import AppCache, Cluster
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate, HostInfoSerializer, HostRecycleSerializer
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoOperateFlowParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBReduceMongosDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReduceMongosDetailSerializer(serializers.Serializer):
        class OldNodesSerializer(serializers.Serializer):
            mongos = serializers.ListSerializer(help_text=_("缩容mongos"), child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        role = serializers.CharField(help_text=_("接入层角色"), required=False, default=MachineType.MONGOS)
        old_nodes = OldNodesSerializer(help_text=_("缩容信息"))

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    infos = serializers.ListSerializer(help_text=_("缩容接入层申请信息"), child=ReduceMongosDetailSerializer())
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)

    def validate(self, attrs):
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]
        cluster_map = Cluster.objects.prefetch_related("proxyinstance_set__machine").in_bulk(cluster_ids)

        # 校验集群类型合法性
        CommonValidate.validated_cluster_type(cluster_ids, ClusterType.MongoShardedCluster)

        for info in attrs["infos"]:
            cluster = cluster_map[info["cluster_id"]]
            mongos_count = cluster.proxyinstance_set.count()
            info["reduce_count"] = len(info["old_nodes"]["mongos"])

            # 缩容后的整体mongos机器数量不能小于2
            if mongos_count - info["reduce_count"] < 2:
                raise serializers.ValidationError(_("缩容后的整体mongos机器数量不能小于2"))

            # 缩容后的整体mongos需要满足集群亲和性，等后续支持指定count缩容后才校验
            machines = [s.machine for s in cluster.proxyinstance_set.all()]
            shrink_ips = [node["ip"] for node in info["old_nodes"]["mongos"]]
            self.validate_shrink_ip_machine_affinity(cluster, machines, shrink_ips)

            # 缩容的mongos机器台数不能高于当前规格台数, 且不能为负数。TODO: 等支持指定规格数量缩容后，才需要这个校验
            # if mongos_count <= info["reduce_count"] or info["reduce_count"] < 0:
            #     raise serializers.ValidationError(_("缩容的mongos机器台数不能高于当前规格台数, 且不能为负数"))

        return attrs


class MongoDBReduceMongosFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.reduce_mongos

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["db_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr
        self.ticket_data["infos"] = self.add_cluster_info(self.ticket_data["infos"])
        for info in self.ticket_data["infos"]:
            info["reduce_nodes"] = info.pop("old_nodes")["mongos"]


@builders.BuilderFactory.register(TicketType.MONGODB_REDUCE_MONGOS, is_recycle=True)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBReduceMongosDetailSerializer
    inner_flow_builder = MongoDBReduceMongosFlowParamBuilder
    inner_flow_name = _("MongoDB 缩容接入层执行")
    need_patch_recycle_host_details = True
