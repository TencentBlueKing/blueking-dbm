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
from backend.ticket.builders.mongodb.base import (
    MONGODB_JS_FILE_PREFIX,
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBScriptExecDetailSerializer(BaseMongoDBOperateDetailSerializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    script_contents = serializers.ListField(help_text=_("脚本内容列表"), child=serializers.CharField())


class MongoDBScriptExecFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        # 传递JS脚本文件执行结果地址
        self.ticket_data["rules"] = [
            f"{MONGODB_JS_FILE_PREFIX}/{self.ticket.id}.{cluster_id}" for cluster_id in self.ticket_data["cluster_ids"]
        ]


@builders.BuilderFactory.register(TicketType.MONGODB_EXEC_SCRIPT_APPLY)
class MongoReplicaSetApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBScriptExecDetailSerializer
    inner_flow_builder = MongoDBScriptExecFlowParamBuilder
    inner_flow_name = _("MongoDB 变更脚本执行执行")
