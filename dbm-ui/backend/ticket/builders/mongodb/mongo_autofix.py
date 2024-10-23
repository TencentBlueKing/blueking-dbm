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

from backend.db_meta.models import AppCache
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBAutofixDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AutofixDetailSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField(help_text=_("IP地址"))
            spec_id = serializers.IntegerField(help_text=_("规格ID"))

        immute_domain = serializers.CharField(help_text=_("主域名"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云ID"))
        bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
        cluster_ids = serializers.ListField(help_text=_("集群ID"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        cluster_type = serializers.CharField(help_text=_("集群类型"))
        mongos_list = serializers.ListSerializer(help_text=_("故障mongos列表"), child=HostInfoSerializer())
        mongod_list = serializers.ListSerializer(help_text=_("故障mongod列表"), child=HostInfoSerializer())

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("mongo自愈申请信息"), child=AutofixDetailSerializer())


class MongoDBAutofixFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongo_autofix

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBAutofixResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        pass

    def post_callback(self):
        pass


@builders.BuilderFactory.register(TicketType.MONGODB_AUTOFIX, is_apply=True)
class MongoDBAutofixFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBAutofixDetailSerializer
    inner_flow_builder = MongoDBAutofixFlowParamBuilder
    inner_flow_name = _("MongoDB 故障自愈")
    resource_batch_apply_builder = MongoDBAutofixResourceParamBuilder
    default_need_itsm = False
    default_need_manual_confirm = False
