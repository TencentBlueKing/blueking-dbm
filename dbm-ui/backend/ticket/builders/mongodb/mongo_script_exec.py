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
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.constants import MongoDBScriptImportMode
from backend.ticket.builders.mongodb.base import (
    MONGODB_JS_FILE_PREFIX,
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBScriptExecDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ScriptDetailSerializer(serializers.Serializer):
        name = serializers.CharField(help_text=_("文件名"), allow_blank=True, allow_null=True)
        content = serializers.CharField(help_text=_("脚本内容"))

    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    scripts = serializers.ListField(help_text=_("脚本内容列表"), child=ScriptDetailSerializer())
    mode = serializers.ChoiceField(help_text=_("脚本导入类型"), choices=MongoDBScriptImportMode.get_choices())


class MongoDBScriptExecFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.exec_script

    def format_ticket_data(self):
        # 传递JS脚本文件执行结果地址
        self.ticket_data["rules"] = [
            {"cluster_id": cluster_id, "path": f"{MONGODB_JS_FILE_PREFIX}/{self.ticket.id}.{cluster_id}"}
            for cluster_id in self.ticket_data["cluster_ids"]
        ]
        # 格式化JS执行脚本字段
        for script in self.ticket_data["scripts"]:
            script["script_name"] = script.pop("name") or f"mongo_js_{get_random_string(8)}"
            script["script_content"] = script.pop("content")
        self.ticket_data["script_contents"] = self.ticket_data.pop("scripts")


@builders.BuilderFactory.register(TicketType.MONGODB_EXEC_SCRIPT_APPLY)
class MongoScriptExecApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBScriptExecDetailSerializer
    inner_flow_builder = MongoDBScriptExecFlowParamBuilder
    inner_flow_name = _("MongoDB 变更脚本执行执行")
