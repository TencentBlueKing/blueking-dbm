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
from backend.db_meta.models import AppCache
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.flow.utils.mongodb.mongodb_get_remove_hosts import instance_migrate_remove_hosts
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import get_mongodb_cluster_tolerance
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
        related_instances = serializers.ListSerializer(
            help_text=_("实例信息查询"), child=serializers.JSONField(), required=False
        )

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)
    cluster_type = serializers.CharField(help_text=_("集群版本"))
    infos = serializers.ListSerializer(help_text=_("实例信息"), child=ShardMigrateDetailSerializer())


class MongoDBShardMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.instance_migrate

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBShardMigrateResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        self.patch_info_common_affinity(
            role="mongodb", tolerance=get_mongodb_cluster_tolerance, tolerance_type="mongodb"
        )


@builders.BuilderFactory.register(TicketType.MONGODB_SHARD_MIGRATE, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBShardMigrateFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBShardMigrateDetailSerializer
    validator = MongoDBController.instance_migrate.validator
    resource_batch_apply_builder = MongoDBShardMigrateResourceParamBuilder
    inner_flow_builder = MongoDBShardMigrateFlowParamBuilder
    inner_flow_name = _("MongoDB 分片集群迁移")
    need_patch_recycle_host_details = True

    def patch_ticket_detail(self):
        details = self.ticket.details
        details["old_nodes"] = {}
        remove_hosts = instance_migrate_remove_hosts(details)
        details["old_nodes"]["shard"] = remove_hosts
        super().patch_ticket_detail()
