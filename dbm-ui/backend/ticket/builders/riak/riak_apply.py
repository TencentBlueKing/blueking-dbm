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
from backend.ticket.builders.riak.base import RIAK_VERSION, BaseRiakTicketFlowBuilder
from backend.ticket.constants import TicketType


class RiakApplyDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    cluster_name = serializers.CharField(help_text=_("集群名"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )
    db_version = serializers.CharField(help_text=_("riak数据库版本"), required=False, default=RIAK_VERSION)
    resource_spec = serializers.JSONField(help_text=_("部署规格"))

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


class RiakApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = RiakController.riak_cluster_apply_scene

    def format_ticket_data(self):
        pass


class RiakApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        riak_nodes = next_flow.details["ticket_data"].pop("nodes")["riak"]
        next_flow.details["ticket_data"].update(nodes=riak_nodes)
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.RIAK_CLUSTER_APPLY, is_apply=True, cluster_type=ClusterType.Riak)
class RiakApplyFlowBuilder(BaseRiakTicketFlowBuilder):
    serializer = RiakApplyDetailSerializer
    inner_flow_builder = RiakApplyFlowParamBuilder
    inner_flow_name = _("Riak 集群部署执行")
    resource_apply_builder = RiakApplyResourceParamBuilder

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

    @property
    def need_itsm(self):
        return True
