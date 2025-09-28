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


class MongoDBReplicasetMigrateDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReplicasetMigrateDetailSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        db_version = serializers.CharField(help_text=_("DB版本"))
        current_replicaset_nodes_num = serializers.IntegerField(help_text=_("当前一个副本集的节点数量"))
        disaster_tolerance_level = serializers.ChoiceField(
            help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
        )
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)
        related_instances = serializers.ListSerializer(
            help_text=_("实例信息查询"), child=serializers.JSONField(), required=False
        )

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("实例信息"), child=ReplicasetMigrateDetailSerializer())


class MongoDBReplicasetMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.migrate_meta
    validator = None

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBReplicasetMigrateResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        self.patch_info_common_affinity(
            role="mongodb", remain_machine_type=MachineType.MONGODB, replace_key="replicaset", tolerance=0.5
        )

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            new_infos = {"MongoReplicaSet": next_flow.details["ticket_data"]["infos"]}
            next_flow.details["ticket_data"]["infos"] = new_infos


@builders.BuilderFactory.register(TicketType.MONGODB_REPLICASET_MIGRATE, is_recycle=True)
class MongoDBReplicasetMigrateFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBReplicasetMigrateDetailSerializer
    resource_batch_apply_builder = MongoDBReplicasetMigrateResourceParamBuilder
    inner_flow_builder = MongoDBReplicasetMigrateFlowParamBuilder
    inner_flow_name = _("MongoDB 副本集集群迁移")
    need_patch_recycle_host_details = True
