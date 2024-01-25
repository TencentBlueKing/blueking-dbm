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

from backend.flow.consts import MongoDBDropType
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    BaseMongoOperateFlowParamBuilder,
    DBTableSerializer,
)
from backend.ticket.constants import TicketType


class MongoDBClearDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ClearDetailSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        drop_type = serializers.ChoiceField(help_text=_("删除类型"), choices=MongoDBDropType.get_choices())
        drop_index = serializers.BooleanField(help_text=_("是否删除索引"))
        ns_filter = DBTableSerializer(help_text=_("库表选择器"))

    infos = serializers.ListSerializer(help_text=_("清档信息"), child=ClearDetailSerializer())

    def validate(self, attrs):
        return attrs


class MongoDBClearFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        self.ticket_data["infos"] = self.scatter_cluster_id_info(self.ticket_data["infos"])
        self.ticket_data["infos"] = self.add_cluster_type_info(self.ticket_data["infos"])


@builders.BuilderFactory.register(TicketType.MONGODB_REMOVE_NS)
class MongoDBClearApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBClearDetailSerializer
    inner_flow_builder = MongoDBClearFlowParamBuilder
    inner_flow_name = _("MongoDB 清档执行")
