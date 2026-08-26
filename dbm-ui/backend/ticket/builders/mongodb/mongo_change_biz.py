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

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class MongoDBChangeBizInfoSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    source_bk_biz_id = serializers.IntegerField(help_text=_("源业务ID"))
    target_bk_biz_id = serializers.IntegerField(help_text=_("目标业务ID"))


class MongoDBChangeBizDetailSerializer(BaseMongoDBOperateDetailSerializer):
    infos = serializers.ListField(help_text=_("变更信息列表"), child=MongoDBChangeBizInfoSerializer())


class MongoDBChangeBizFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongo_change_biz


@builders.BuilderFactory.register(TicketType.MONGODB_CHANGE_BIZ, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBChangeBizFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBChangeBizDetailSerializer
    inner_flow_builder = MongoDBChangeBizFlowParamBuilder
    inner_flow_name = _("MongoDB 集群业务变更")
    retry_type = FlowRetryType.MANUAL_RETRY
