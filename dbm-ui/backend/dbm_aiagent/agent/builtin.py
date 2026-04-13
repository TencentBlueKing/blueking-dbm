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
import base64
import json

from aidev_agent.api import BKAidevApi
from aidev_agent.enums import PromptRole
from aidev_bkplugin.views.builtin import (
    AgentInfoViewSet,
    ChatCompletionViewSet,
    ChatGroupViewSet,
    ChatSessionContentFeedbackViewSet,
    ChatSessionContentViewSet,
    ChatSessionShareView,
    ChatSessionViewSet,
)
from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.dbm_aiagent.agent.commands import CommandProcessor


class AICorsResponseMixin:
    """为 AI 接口的所有响应注入 CORS 头，并处理 OPTIONS 预检请求"""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.headers.get("Origin"):
            response["Access-Control-Allow-Origin"] = request.headers.get("Origin")
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "*"
        return response

    def options(self, request, *args, **kwargs):
        """OPTIONS 预检请求直接返回 200"""
        response = Response(status=200)
        return response


def get_agent_config_info(username: str | None = None, agent_code: str = None):
    agent_code = agent_code or settings.AGENT_APP_CODE
    agent_info_key = f"get_agent_config_info:{username or 'default'}-{agent_code}"

    agent_info = cache.get(agent_info_key)
    if not agent_info:
        client = BKAidevApi.get_client()
        result = client.api.retrieve_agent_config(
            path_params={"agent_code": agent_code}, headers={"X-BKAIDEV-USER": username}
        )
        agent_info = result["data"]
        otel_env_info = agent_info.pop("otel_info", None)
        if otel_env_info:
            agent_info["otel_info"] = json.loads(base64.b64decode(otel_env_info).decode())
        cache.set(agent_info_key, agent_info, 60)
    return agent_info


class AIChatSessionViewSet(ChatSessionViewSet):
    pass


class AIChatSessionContentViewSet(ChatSessionContentViewSet):
    """AI 聊天框"""

    @staticmethod
    def __render_command(command_data):
        # 如果有命令且平台有注册，则渲染指令内容
        if not command_data.get("command"):
            return
        if command_data["command"] not in CommandProcessor._handlers:
            return
        rendered_content = CommandProcessor.process_command(command_data)
        command_data.update(rendered_content=rendered_content)
        return rendered_content

    def create(self, request):
        """创建聊天内容"""
        # 渲染快捷指令内容
        if request.data["property"]["extra"].get("command"):
            request.data["content"] = self.__render_command(request.data["property"]["extra"])

        # 如果前端指定了agent_code，则利用快捷指令模式强制切换
        if request.data.get("agent_code") and request.data["role"] == "user":
            agent_code = request.data["agent_code"]
            session_property = {"extra": {"command": agent_code, "rendered_content": request.data["content"]}}
            request.data.update(property=session_property, content=request.data["content"])

        return super().create(request)


class AIChatCompletionViewSet(ChatCompletionViewSet):
    def create(self, request):
        return super().create(request)


class AIChatSessionContentFeedbackViewSet(ChatSessionContentFeedbackViewSet):
    pass


class AIAgentInfoViewSet(AgentInfoViewSet):
    @action(detail=False, methods=["GET"], url_path="agent_scene", url_name="agent_scene")
    def get_agent_scene(self, request):
        return Response(SystemSettings.get_setting_value(key=SystemSettingsEnum.AI_CODE_SCENE_MAP, default={}))

    @action(detail=False, methods=["GET"], url_path="info", url_name="info")
    def info(self, request):
        # 根据agent code获取agent信息
        agent_info = get_agent_config_info(request.user.username, request.query_params.get("agent_code"))

        # 新增群聊信息
        agent_info["chat_group"] = {
            "enabled": settings.CHAT_GROUP_ENABLED,
            "staff": settings.CHAT_GROUP_STAFF,
            "username": request.user.username,
        }
        prompt_setting = agent_info.get("prompt_setting", {})
        prompt_setting["collection_content"] = []
        prompt_setting["collection_variables"] = []
        prompt_setting["content"] = [
            content for content in prompt_setting["content"] if content.get("role") == PromptRole.PAUSE.value
        ]
        agent_info["prompt_setting"] = prompt_setting
        agent_info.pop("otel_info", None)
        return Response(data=agent_info)


class AIChatGroupViewSet(ChatGroupViewSet):
    pass


class AIChatSessionShareView(ChatSessionShareView):
    pass
