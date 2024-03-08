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
from backend.ticket.builders.mongodb.mongo_backup import MongoDBBackupFlowParamBuilder
from backend.ticket.constants import TicketType


class MongoDBScaleUpDownDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ScaleUpDownDetailSerializer(serializers.Serializer):
        shard_num = serializers.IntegerField(help_text=_("集群分片数"), required=False)
        shard_machine_group = serializers.IntegerField(help_text=_("机器组数"))
        shard_node_count = serializers.IntegerField(help_text=_("集群每分片节点数"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("集群容量变更申请信息"), child=ScaleUpDownDetailSerializer())

    def validate(self, attrs):
        # 校验count = 机器组数 * 集群分片节点数
        for info in attrs["infos"]:
            mongo_count = info["resource_spec"]["mongodb"]["count"]
            if info["shard_machine_group"] * info["shard_node_count"] != mongo_count:
                raise serializers.ValidationError(
                    _("请保证申请机器数{} = 机器组数{} * 集群分片节点数{}").format(
                        mongo_count, info["shard_machine_group"], info["shard_node_count"]
                    )
                )

        return attrs


class MongoDBScaleUpDownFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        MongoDBBackupFlowParamBuilder.add_cluster_type_info(self.ticket_data["infos"])


class MongoDBScaleUpDownResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 获取每个集群的分片数和节点数，以此作为mongodb的资源申请规格
        for info in self.ticket_data["infos"]:
            resource_spec = info["resource_spec"]
            shard_machine_group, shard_node_count = info["shard_machine_group"], info["shard_node_count"]
            self.format_mongo_resource_spec(resource_spec, shard_machine_group, shard_node_count)

        # 集群容量变更亲和性需要和集群亲和性保持一致
        self.patch_info_affinity_location()
        super().format()

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            cluster_ids = [info["cluster_id"] for info in next_flow.details["ticket_data"]["infos"]]
            id__cluster = Cluster.objects.filter(id__in=cluster_ids)

            mongo_type__apply_infos: Dict[str, List] = defaultdict(list)
            for info in next_flow.details["ticket_data"]["infos"]:
                # 格式化mongodb节点信息和machine_specs规格信息
                self.format_mongo_node_infos(info)
                info["machine_specs"] = self.format_machine_specs(info["resource_spec"])
                # 补充集群信息
                cluster = id__cluster[info["cluster_id"]]
                info["db_version"] = cluster.major_version
                info["disaster_tolerance_level"] = cluster.disaster_tolerance_level
                # 根据mongo集群类型归类
                mongo_type__apply_infos[cluster.cluster_type].append(info)

            next_flow.details["ticket_data"]["infos"] = mongo_type__apply_infos


@builders.BuilderFactory.register(TicketType.MONGODB_SCALE_UPDOWN, is_apply=True)
class MongoDBScaleUpDownFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBScaleUpDownDetailSerializer
    inner_flow_builder = MongoDBScaleUpDownFlowParamBuilder
    inner_flow_name = _("MongoDB 集群容量变更执行")
    resource_batch_apply_builder = MongoDBScaleUpDownResourceParamBuilder
