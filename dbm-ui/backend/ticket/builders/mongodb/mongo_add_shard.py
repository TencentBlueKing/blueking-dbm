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

from backend.configuration.constants import AffinityEnum
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


class MongoDBAddShardDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AddShardDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        db_version = serializers.CharField(help_text=_("DB版本"))
        add_shards_num = serializers.IntegerField(help_text=_("新增分片数"))
        current_shard_nodes_num = serializers.IntegerField(help_text=_("当前每分片节点数"))
        node_replicaset_count = serializers.IntegerField(help_text=_("单机部署实例数"))
        disaster_tolerance_level = serializers.ChoiceField(
            help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
        )
        city_code = serializers.CharField(help_text=_("DB版本"), required=False, default=None)
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        current_shards_num = serializers.IntegerField(help_text=_("当前的分片数"), required=False)
        single_host_shard_num = serializers.IntegerField(help_text=_("单节点主机分片数"), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("扩容shard节点数申请信息"), child=AddShardDetailSerializer())


class MongoDBAddShardFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.increase_node

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBAddShardResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        self.patch_info_affinity_location()

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            for info in next_flow.details["ticket_data"]["infos"]:
                info["mongo_add_shards"] = info.pop("mongodb")


@builders.BuilderFactory.register(TicketType.MONGODB_ADD_SHARD, is_apply=True)
class MongoDBAddShardFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBAddShardDetailSerializer
    inner_flow_builder = MongoDBAddShardFlowParamBuilder
    inner_flow_name = _("MongoDB 增加分片数")
    resource_batch_apply_builder = MongoDBAddShardResourceParamBuilder
