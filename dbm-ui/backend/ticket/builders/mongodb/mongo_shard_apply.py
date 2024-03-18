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
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateResourceParamBuilder, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoShardedClusterApplyDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )

    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_name = serializers.CharField(help_text=_("集群ID"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"))
    db_version = serializers.CharField(help_text=_("版本号"))
    start_port = serializers.IntegerField(help_text=_("起始端口"))
    oplog_percent = serializers.IntegerField(help_text=_("oplog容量占比"))

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    resource_spec = serializers.JSONField(help_text=_("资源申请规格"))

    shard_machine_group = serializers.IntegerField(help_text=_("机器组数"))
    shard_num = serializers.IntegerField(help_text=_("集群分片数"))

    # display fields
    bk_cloud_name = serializers.SerializerMethodField(help_text=_("云区域"), read_only=True)
    city_name = serializers.SerializerMethodField(help_text=_("城市名"), read_only=True)

    def get_bk_cloud_name(self, obj):
        clouds = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return clouds[str(obj["bk_cloud_id"])]["bk_cloud_name"]

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def validate(self, attrs):
        """TODO: validate"""
        return attrs


class MongoShardedClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.cluster_create

    def format_ticket_data(self):
        self.ticket_data["bk_app_abbr"] = self.ticket_data["db_app_abbr"]
        self.ticket_data["proxy_port"] = self.ticket_data["start_port"]


class MongoShardedClusterResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        """格式化mongodb申请的组数"""
        resource_spec = self.ticket_data["resource_spec"]
        self.format_mongo_resource_spec(resource_spec, self.ticket_data["shard_machine_group"])

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            # 重新组合mongodb的资源信息
            node_infos = next_flow.details["ticket_data"]["nodes"]
            self.format_mongo_node_infos(node_infos)
            # 格式化资源池申请信息
            resource_spec = next_flow.details["ticket_data"]["resource_spec"]
            machine_specs = self.format_machine_specs(resource_spec)
            # 更新ticket_data
            next_flow.details["ticket_data"].update(machine_specs=machine_specs)
            next_flow.details["ticket_data"].update(nodes=node_infos)


@builders.BuilderFactory.register(
    TicketType.MONGODB_SHARD_APPLY, is_apply=True, cluster_type=ClusterType.MongoShardedCluster
)
class MongoShardedClusterApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoShardedClusterApplyDetailSerializer
    inner_flow_builder = MongoShardedClusterApplyFlowParamBuilder
    inner_flow_name = _("MongoDB 分片集群部署执行")
    resource_apply_builder = MongoShardedClusterResourceParamBuilder

    def patch_ticket_detail(self):
        # TODO: 待后台flow就绪调试
        print(self.ticket.details)
