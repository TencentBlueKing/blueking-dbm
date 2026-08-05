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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.models import AppCache, Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import get_mongodb_cluster_tolerance
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.builders.mongodb.mongo_backup import MongoDBBackupFlowParamBuilder
from backend.ticket.constants import TicketType


class MongoDBScaleUpDownDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ScaleUpDownDetailSerializer(serializers.Serializer):
        shards_num = serializers.IntegerField(help_text=_("集群分片数"), required=False)
        shard_machine_group = serializers.IntegerField(help_text=_("机器组数"))
        shard_node_count = serializers.IntegerField(help_text=_("集群每分片节点数"))
        db_version = serializers.CharField(help_text=_("DB版本"))
        disaster_tolerance_level = serializers.ChoiceField(
            help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
        )
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        cluster_type = serializers.CharField(help_text=_("集群类型"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_nodes = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("集群容量变更申请信息"), child=ScaleUpDownDetailSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
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
    controller = MongoDBController.scale_cluster

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr
        MongoDBBackupFlowParamBuilder.add_cluster_type_info(self.ticket_data["infos"])


class MongoDBScaleUpDownResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 获取每个集群的分片数和节点数，以此作为mongodb的资源申请规格
        for info in self.ticket_data["infos"]:
            resource_spec = info["resource_spec"]
            shard_machine_group, shard_node_count = info["shard_machine_group"], info["shard_node_count"]
            self.format_mongo_resource_spec(resource_spec, shard_machine_group, shard_node_count)
            cluster = Cluster.objects.get(id=info["cluster_id"])
            tolerance = get_mongodb_cluster_tolerance(cluster.disaster_tolerance_level, "mongodb")
            for role in info["resource_spec"]:
                self.patch_common_affinity(
                    info,
                    role=role,
                    cluster=cluster,
                    exclusive_hosts=[],
                    tolerance=tolerance,
                )

        super().format()

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            for info in next_flow.details["ticket_data"]["infos"]:
                info["mongodb"] = []
                for group in range(info["shard_machine_group"]):
                    info["mongodb"].append(info.pop(f"mongodb_nodes_{group}"))


@builders.BuilderFactory.register(
    TicketType.MONGODB_SCALE_UPDOWN, is_apply=True, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBScaleUpDownFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBScaleUpDownDetailSerializer
    inner_flow_builder = MongoDBScaleUpDownFlowParamBuilder
    inner_flow_name = _("MongoDB 集群容量变更执行")
    resource_batch_apply_builder = MongoDBScaleUpDownResourceParamBuilder
    need_patch_recycle_host_details = True
