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

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import AppCache
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBDestroyDetailSerializer(BaseMongoDBOperateDetailSerializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    def validate(self, attrs):
        return attrs


class MongoDBDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.deinstall_cluster

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


@builders.BuilderFactory.register(TicketType.MONGODB_DESTROY, phase=ClusterPhase.DESTROY)
class MongoDBDestroyApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBDestroyDetailSerializer
    inner_flow_builder = MongoDBDestroyFlowParamBuilder
    inner_flow_name = _("MongoDB 集群下架")
