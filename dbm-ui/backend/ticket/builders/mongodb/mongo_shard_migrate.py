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
from backend.db_meta.enums import MachineType
from backend.db_meta.models import AppCache
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBShardMigrateDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ShardMigrateDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        shard_name = serializers.ListField(help_text=_("分片名称集合"), child=serializers.CharField())
        db_version = serializers.CharField(help_text=_("DB版本"))
        current_shard_nodes_num = serializers.IntegerField(help_text=_("当前每分片节点数"))
        disaster_tolerance_level = serializers.ChoiceField(
            help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
        )
        city_code = serializers.CharField(help_text=_("城市"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)
        related_instances = serializers.ListSerializer(
            help_text=_("实例信息查询"), child=serializers.JSONField(), required=False
        )

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("实例信息"), child=ShardMigrateDetailSerializer())


class MongoDBShardMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.migrate_meta
    validator = None

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBShardMigrateResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        self.patch_info_common_affinity(
            role="mongodb", remain_machine_type=MachineType.MONGODB, replace_key="shard", tolerance=0.5
        )

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            new_infos = {"MongoShardedCluster": []}
            info_map = {}
            shard_name_resource_map = {}
            for info in next_flow.details["ticket_data"]["infos"]:
                if info["cluster_id"] not in info_map:
                    info_map[info["cluster_id"]] = info
                if info["cluster_id"] not in shard_name_resource_map:
                    shard_name_resource_map[info["cluster_id"]] = {
                        "shard_name": [info["shard_name"]],
                        "resource": [info.pop("mongodb")],
                    }
                else:
                    shard_name_resource_map[info["cluster_id"]]["shard_name"].append(info["shard_name"])
                    shard_name_resource_map[info["cluster_id"]]["resource"].append(info.pop("mongodb"))
            for cluster_id in info_map:
                info = info_map[cluster_id]
                info["shard_name"] = shard_name_resource_map[cluster_id]["shard_name"]
                info["mongodb"] = shard_name_resource_map[cluster_id]["resource"]
                new_infos["MongoShardedCluster"].append(info)
            next_flow.details["ticket_data"]["infos"] = new_infos


@builders.BuilderFactory.register(TicketType.MONGODB_SHARD_MIGRATE, is_recycle=True)
class MongoDBShardMigrateFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBShardMigrateDetailSerializer
    resource_batch_apply_builder = MongoDBShardMigrateResourceParamBuilder
    inner_flow_builder = MongoDBShardMigrateFlowParamBuilder
    inner_flow_name = _("MongoDB 分片集群迁移")
    need_patch_recycle_host_details = True
