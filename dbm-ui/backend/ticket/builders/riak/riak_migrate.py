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
from backend.db_meta.models import DBModule
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.engine.controller.riak import RiakController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.common.bigdata import BigDataApplyDetailsSerializer
from backend.ticket.builders.riak.base import BaseRiakTicketFlowBuilder
from backend.ticket.constants import TicketType


class RiakMigrateDetailSerializer(BigDataApplyDetailsSerializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))

    # display fields
    bk_cloud_name = serializers.SerializerMethodField(help_text=_("云区域"))
    db_module_name = serializers.SerializerMethodField(help_text=_("DB模块名"))
    city_name = serializers.SerializerMethodField(help_text=_("城市名"))

    def get_bk_cloud_name(self, obj):
        clouds = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return clouds[str(obj["bk_cloud_id"])]["bk_cloud_name"]

    def get_db_module_name(self, obj):
        db_module_id = obj["db_module_id"]
        return self.context["ticket_ctx"].db_module_map.get(db_module_id) or f"db-module-{db_module_id}"

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def validate(self, attrs):
        # 校验集群名是否重复
        CommonValidate.validate_duplicate_cluster_name(
            self.context["bk_biz_id"], self.context["ticket_type"], attrs["cluster_name"]
        )
        return attrs


class RiakMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = RiakController.riak_cluster_migrate_scene

    def format_ticket_data(self):
        # 如果是手动部署，剔除riak层级
        if self.ticket_data["ip_source"] == IpSource.MANUAL_INPUT:
            riak_nodes = self.ticket_data.pop("nodes")["riak"]
            self.ticket_data["nodes"] = riak_nodes


@builders.BuilderFactory.register(TicketType.RIAK_CLUSTER_MIGRATE, is_apply=True, cluster_type=ClusterType.Riak)
class RiakMigrateFlowBuilder(BaseRiakTicketFlowBuilder):
    serializer = RiakMigrateDetailSerializer
    inner_flow_builder = RiakMigrateFlowParamBuilder
    inner_flow_name = _("Riak 集群迁移执行")

    def patch_ticket_detail(self):
        details = self.ticket.details
        db_module_name = DBModule.objects.get(db_module_id=details["db_module_id"]).db_module_name
        riak_cluster_name = riak_domain = f"{details['cluster_name']}.{db_module_name}"
        details.update(
            db_module_name=db_module_name,
            cluster_name=riak_cluster_name,
            domain=riak_domain,
        )
        self.ticket.save(update_fields=["details"])
