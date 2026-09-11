# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MongoDB 自愈人工处理：PRE 鉴权失败 / GSE 不确定时的显式跟单，不挂工具箱。
审批+人工确认后空跑成功，便于单据中心跟踪与结案。
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBAutofixManualDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        autofix_core_id = serializers.IntegerField(help_text=_("MongoAutofixCore ID"), required=False)
        ip = serializers.IPAddressField(help_text=_("故障 IP"))
        port = serializers.IntegerField(help_text=_("端口"), required=False)
        ports = serializers.ListField(help_text=_("端口列表"), child=serializers.IntegerField(), required=False)
        bk_host_id = serializers.IntegerField(help_text=_("主机 ID"), required=False)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), required=False)
        cluster_id = serializers.IntegerField(help_text=_("集群 ID"), required=False)
        cluster_ids = serializers.ListField(help_text=_("关联集群"), child=serializers.IntegerField(), required=False)
        immute_domain = serializers.CharField(help_text=_("主域名"), required=False)
        confirm_result = serializers.CharField(help_text=_("PRE 确认结果"), required=False)
        reason = serializers.CharField(help_text=_("人工处理原因"), required=False, allow_blank=True)

    infos = serializers.ListSerializer(help_text=_("人工处理信息"), child=InfoSerializer(), allow_empty=False)


class MongoDBAutofixManualFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongo_autofix_manual


@builders.BuilderFactory.register(TicketType.MONGODB_AUTOFIX_MANUAL, is_apply=False, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBAutofixManualFlowBuilder(BaseMongoDBTicketFlowBuilder):
    """
    自愈人工处理单据。

    前置：MONGODB_AUTOFIX_PRE triage → auth_error / gse_inconclusive。
    不挂工具箱；默认走审批与人工确认，便于跟踪结案。
    """

    serializer = MongoDBAutofixManualDetailSerializer
    inner_flow_builder = MongoDBAutofixManualFlowParamBuilder
    inner_flow_name = _("MongoDB 自愈人工处理")

    default_need_itsm = True
    default_need_manual_confirm = True

    @property
    def need_itsm(self):
        if "need_itsm" in self.ticket.details:
            return bool(self.ticket.details["need_itsm"])
        return super().need_itsm

    @property
    def need_manual_confirm(self):
        if "need_manual_confirm" in self.ticket.details:
            return bool(self.ticket.details["need_manual_confirm"])
        return super().need_manual_confirm
