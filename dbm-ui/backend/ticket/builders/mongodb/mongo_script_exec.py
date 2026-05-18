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
from backend.ticket import builders
from backend.ticket.builders.common.constants import MongoDBScriptImportMode
from backend.ticket.builders.mongodb.base import (
    MONGODB_JS_FILE_PREFIX,
    MONGODB_JS_FILE_STORE_PREFIX,
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBScriptExecDetailSerializer(BaseMongoDBOperateDetailSerializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    script_files = serializers.ListField(help_text=_("脚本文件列表(制品库文件路径)"), child=serializers.CharField(), required=False)
    mode = serializers.ChoiceField(help_text=_("脚本导入类型"), choices=MongoDBScriptImportMode.get_choices())

    def validate(self, attrs):
        # 兼容逻辑：优先使用scripts字段，如果scripts不存在则使用script_files
        if attrs.get("scripts"):
            # 验证scripts格式是否正确
            for script in attrs["scripts"]:
                if not isinstance(script, dict):
                    raise serializers.ValidationError(_("scripts列表中的每个元素必须是字典格式"))
                if "content" not in script:
                    raise serializers.ValidationError(_("scripts字典中必须包含content字段"))
                # name字段可选，如果没有则设置默认值
                if "name" not in script:
                    script["name"] = ""

        # 确保至少有一个脚本相关的字段
        if not (attrs.get("script_files") or attrs.get("scripts")):
            raise serializers.ValidationError(_("脚本内容不能为空！"))

        # 如果同时提供了script_files和scripts，优先使用scripts（兼容旧客户端）
        if attrs.get("scripts") and attrs.get("script_files"):
            # 记录日志或警告，但继续使用scripts
            pass

        return attrs


class MongoDBScriptExecFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.exec_script

    def format_ticket_data(self):
        # 传递JS脚本文件执行结果地址
        self.ticket_data["rules"] = [
            {
                "cluster_id": cluster_id,
                "path": f"{MONGODB_JS_FILE_PREFIX.format(uid=self.ticket.id,cluster_id=cluster_id)}",
            }
            for cluster_id in self.ticket_data["cluster_ids"]
        ]

        # 将制品库路径保存到ticket.details中，用于获取脚本文件内容（参考MYSQL_IMPORT_SQLFILE实现）
        self.ticket_data["path"] = MONGODB_JS_FILE_STORE_PREFIX.format(bk_biz_id=self.ticket.bk_biz_id)

        self.ticket_data["script_files"] = [file_path.split("/")[-1] for file_path in self.ticket_data["script_files"]]


@builders.BuilderFactory.register(TicketType.MONGODB_EXEC_SCRIPT_APPLY)
class MongoScriptExecApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBScriptExecDetailSerializer
    inner_flow_builder = MongoDBScriptExecFlowParamBuilder
    inner_flow_name = _("MongoDB 变更脚本执行执行")
