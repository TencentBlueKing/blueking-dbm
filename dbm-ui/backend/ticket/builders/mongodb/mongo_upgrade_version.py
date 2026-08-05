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

from backend.flow.consts import MongoDBStrategyEnum
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongodbUpgradeDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        cluster_id_list = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(), min_length=1)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        current_version = serializers.CharField(help_text=_("当前版本"))
        dest_version = serializers.CharField(help_text=_("目标版本"))
        strategy = serializers.ChoiceField(help_text=_("升级策略"), choices=MongoDBStrategyEnum.get_choices())

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))


class MongoDBUpgradeParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongo_upgrade_version

    def format_ticket_data(self):
        self.ticket_data["ticket_id"] = self.ticket.id


@builders.BuilderFactory.register(TicketType.MONGODB_UPGRADE_VERSION, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBUpgradeFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongodbUpgradeDetailSerializer
    inner_flow_builder = MongoDBUpgradeParamBuilder
    validator = None
