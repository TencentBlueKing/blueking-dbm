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
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBInstanceDeInstallDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class InstanceDeInstallDetailSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("IP地址"))
        port = serializers.IntegerField(help_text=_("端口"))
        role = serializers.ListField(help_text=_("实例角色"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云ID"))

    infos = serializers.ListSerializer(help_text=_("实例下架申请信息"), child=InstanceDeInstallDetailSerializer())


class MongoDBInstanceDeInstallFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.instance_deinstall

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBInstanceDeInstallResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        pass

    def post_callback(self):
        pass


@builders.BuilderFactory.register(TicketType.MONGODB_INSTANCE_DEINSTALL, is_apply=True)
class MongoDBInstanceDeInstallFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBInstanceDeInstallDetailSerializer
    inner_flow_builder = MongoDBInstanceDeInstallFlowParamBuilder
    inner_flow_name = _("MongoDB 实例下架")
    resource_batch_apply_builder = MongoDBInstanceDeInstallResourceParamBuilder
