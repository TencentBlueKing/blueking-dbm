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

from backend.db_meta.enums import ClusterType
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.common.bigdata import BigDataApplyDetailsSerializer
from backend.ticket.builders.mongodb.base import BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBApplyDetailSerializer(BigDataApplyDetailsSerializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    # display fields
    bk_cloud_name = serializers.SerializerMethodField(help_text=_("云区域"))
    city_name = serializers.SerializerMethodField(help_text=_("城市名"))

    def get_bk_cloud_name(self, obj):
        clouds = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return clouds[str(obj["bk_cloud_id"])]["bk_cloud_name"]


    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def validate(self, attrs):
        # 校验集群名是否重复
        CommonValidate.validate_duplicate_cluster_name(
            self.context["bk_biz_id"], self.context["ticket_type"], attrs["cluster_name"]
        )
        return attrs


class MongoDBApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongodb_cluster_apply_scene

    def format_ticket_data(self):
        pass


class MongoDBApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        mongodb_nodes = next_flow.details["ticket_data"].pop("nodes")["mongodb"]
        next_flow.details["ticket_data"].update(nodes=mongodb_nodes)
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MONGODB_REPLICASET_APPLY, is_apply=True,
                                  cluster_type=ClusterType.MongoReplicaSet)
class MongoDBApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBApplyDetailSerializer
    inner_flow_builder = MongoDBApplyFlowParamBuilder
    inner_flow_name = _("MongoDB 集群部署执行")
    resource_apply_builder = MongoDBApplyResourceParamBuilder

    def patch_ticket_detail(self):
        details = self.ticket.details
        mongodb_domain = f"mongodb.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
        details.update(
            domain=mongodb_domain,
        )
        self.ticket.save(update_fields=["details"])
