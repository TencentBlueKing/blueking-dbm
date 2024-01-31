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

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBReduceShardNodesDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReduceMongosDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        reduce_shard_nodes = serializers.IntegerField(help_text=_("缩容数量"))

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListSerializer(help_text=_("缩容shard节点数信息"), child=ReduceMongosDetailSerializer())

    def validate(self, attrs):
        return attrs


class MongoDBReduceShardNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MONGODB_REDUCE_SHARD_NODES)
class MongoDBAddMongosApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBReduceShardNodesDetailSerializer
    inner_flow_builder = MongoDBReduceShardNodesFlowParamBuilder
    inner_flow_name = _("MongoDB 缩容Shard节点数执行")
