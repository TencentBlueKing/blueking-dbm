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
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.builders.mongodb.mongo_backup import MongoDBBackupFlowParamBuilder
from backend.ticket.constants import TicketType


class MongoDBAddMongosDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AddMongosDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        role = serializers.CharField(help_text=_("接入层角色"), required=False, default=MachineType.MONGOS)
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("扩容接入层申请信息"), child=AddMongosDetailSerializer())

    def validate(self, attrs):
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]
        CommonValidate.validate_cluster_type(cluster_ids, ClusterType.MongoShardedCluster)
        return attrs


class MongoDBAddMongosFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        MongoDBBackupFlowParamBuilder.add_cluster_type_info(self.ticket_data["infos"])


class MongoDBAddMongosResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 扩容接入层亲和性需要和集群亲和性保持一致
        self.patch_info_affinity_location(roles=["mongos"])
        super().format()

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            for info in next_flow.details["ticket_data"]["infos"]:
                # 格式化mongodb节点信息和machine_specs规格信息
                self.format_mongo_node_infos(info)
                info["machine_specs"] = self.format_machine_specs(info["resource_spec"])


@builders.BuilderFactory.register(TicketType.MONGODB_ADD_MONGOS, is_apply=True)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBAddMongosDetailSerializer
    inner_flow_builder = MongoDBAddMongosFlowParamBuilder
    inner_flow_name = _("MongoDB 扩容接入层执行")
    resource_batch_apply_builder = MongoDBAddMongosResourceParamBuilder
