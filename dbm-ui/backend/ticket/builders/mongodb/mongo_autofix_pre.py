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

from backend.db_meta.models import AppCache
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBAutofixPreDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class AutofixPreDetailSerializer(serializers.Serializer):
        autofix_core_id = serializers.IntegerField(help_text=_("MongoAutofixCore ID"))
        ip = serializers.IPAddressField(help_text=_("故障 IP"))
        bk_host_id = serializers.IntegerField(help_text=_("主机 ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
        bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"), required=False)
        ports = serializers.ListField(help_text=_("端口列表"), child=serializers.IntegerField(), required=False)
        cluster_id = serializers.IntegerField(help_text=_("主集群 ID"), required=False)
        cluster_ids = serializers.ListField(help_text=_("关联集群 ID"), child=serializers.IntegerField(), required=False)
        cluster_type = serializers.CharField(help_text=_("集群类型"), required=False)
        immute_domain = serializers.CharField(help_text=_("主域名"), required=False)
        disk_rw_ok = serializers.IntegerField(help_text=_("磁盘读写探测结果"), required=False, allow_null=True)

    infos = serializers.ListSerializer(help_text=_("Mongo 自愈预确认信息"), child=AutofixPreDetailSerializer())


class MongoDBAutofixPreFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongo_autofix_pre

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


@builders.BuilderFactory.register(TicketType.MONGODB_AUTOFIX_PRE, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBAutofixPreFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBAutofixPreDetailSerializer
    inner_flow_builder = MongoDBAutofixPreFlowParamBuilder
    inner_flow_name = _("MongoDB 故障自愈预确认")
    default_need_itsm = False
    default_need_manual_confirm = False
