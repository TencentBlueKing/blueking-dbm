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
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBReduceMongosDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReduceMongosDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        role = serializers.CharField(help_text=_("接入层角色"), required=False, default=MachineType.MONGOS)
        reduce_spec_id = serializers.IntegerField(help_text=_("缩容接入层规格"))
        reduce_count = serializers.IntegerField(help_text=_("缩容数量"))

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListSerializer(help_text=_("缩容接入层申请信息"), child=ReduceMongosDetailSerializer())

    def validate(self, attrs):

        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]
        id__cluster = {
            cluster.id: cluster
            for cluster in Cluster.objects.prefetch_related("proxyinstance_set__machine").filter(id__in=cluster_ids)
        }

        # 校验集群类型合法性
        CommonValidate.validate_cluster_type(cluster_ids, ClusterType.MongoShardedCluster)

        for info in attrs["infos"]:
            cluster = id__cluster[info["cluster_id"]]
            mongos = cluster.proxyinstance_set
            shrink_mongos = cluster.proxyinstance_set.filter(machine__spec_id=info["reduce_spec_id"])

            # 缩容的mongos机器台数不能高于当前规格台数, 且不能为负数
            if shrink_mongos.count() <= info["reduce_count"] or info["reduce_count"] < 0:
                raise serializers.ValidationError(_("缩容的mongos机器台数不能高于当前规格台数, 且不能为负数"))

            # 缩容后的整体mongos机器数量不能小于3，且保持为奇数
            if mongos.count() - info["reduce_count"] < 3 or (mongos.count() - info["reduce_count"]) & 1:
                raise serializers.ValidationError(_("缩容后的整体mongos机器数量不能小于3，且保持为奇数"))

            # 缩容后的整体mongos需要满足集群亲和性
            machines = [s.machine for s in mongos]
            self.validate_shrink_machine_affinity(cluster, machines, info["reduce_spec_id"], info["reduce_count"])

        return attrs


class MongoDBReduceMongosFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MONGODB_REDUCE_MONGOS)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBReduceMongosDetailSerializer
    inner_flow_builder = MongoDBReduceMongosFlowParamBuilder
    inner_flow_name = _("MongoDB 缩容接入层执行")
