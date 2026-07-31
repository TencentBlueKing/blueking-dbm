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
from typing import Optional

from aidev_agent.packages.resource_manager import ResourceManagerProtocol
from aidev_bkplugin.views.agent import AgentInfoViewSet
from aidev_bkplugin.views.chat import ChatCompletionViewSet
from aidev_bkplugin.views.chat_group import ChatGroupViewSet
from aidev_bkplugin.views.llm import LLMViewSet
from aidev_bkplugin.views.session import (
    ChatSessionContentFeedbackViewSet,
    ChatSessionContentViewSet,
    ChatSessionShareView,
    ChatSessionViewSet,
)
from django.urls import reverse
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.dbm_aiagent.agent.commands import CommandProcessor
from backend.dbm_aiagent.agent.configs.manager import build_resource_manager


class AgentCodeResourceManagerMixin:
    """以前端传入的 agent_code 优先构造 resource_manager 的基类。
    前端会在每个 request 外层带上 agent_code，这里覆盖 ``PluginViewSet.get_resource_manager``，
    优先以 agent_code 构造子智能体的 resource_manager；未携带 agent_code 时回退到父类默认逻辑
    （主智能体 / 快捷指令路由）。
    """

    def get_resource_manager(self) -> Optional[ResourceManagerProtocol]:
        params = self.request.query_params or self.request.data
        agent_code = params.get("agent_code", env.BK_AIDEV_AGENT_APP_CODE)
        if not agent_code:
            return super().get_resource_manager()
        return build_resource_manager(agent_code, username=self.get_username())


class AIChatSessionViewSet(AgentCodeResourceManagerMixin, ChatSessionViewSet):
    pass


class AIChatSessionContentViewSet(AgentCodeResourceManagerMixin, ChatSessionContentViewSet):
    """AI 聊天框"""

    @staticmethod
    def __render_command(command_data):
        # 如果有命令且平台有注册，则渲染指令内容
        if not command_data.get("command"):
            return None
        if command_data["command"] not in CommandProcessor._handlers:
            return None
        rendered_content = CommandProcessor.process_command(command_data)
        command_data.update(rendered_content=rendered_content)
        return rendered_content

    def create(self, request):
        """创建聊天内容"""
        # 渲染快捷指令内容
        if request.data.get("property", {}).get("extra", {}).get("command"):
            request.data["content"] = self.__render_command(request.data["property"]["extra"])

        # 如果前端指定了agent_code，则利用快捷指令模式强制切换
        if request.data.get("agent_code") and request.data["role"] == "user":
            agent_code = request.data["agent_code"]
            session_property = {"extra": {"command": agent_code, "rendered_content": request.data["content"]}}
            request.data.update(property=session_property, content=request.data["content"])

        return super().create(request)


class AIChatCompletionViewSet(AgentCodeResourceManagerMixin, ChatCompletionViewSet):
    def create(self, request):
        return super().create(request)


class AIChatSessionContentFeedbackViewSet(AgentCodeResourceManagerMixin, ChatSessionContentFeedbackViewSet):
    pass


class AIAgentInfoViewSet(AgentCodeResourceManagerMixin, AgentInfoViewSet):
    @action(detail=False, methods=["GET"], url_path="agent_scene", url_name="agent_scene")
    def get_agent_scene(self, request):
        return Response(SystemSettings.get_setting_value(key=SystemSettingsEnum.AI_CODE_SCENE_MAP, default={}))

    @action(detail=False, methods=["GET"], url_path="info", url_name="info")
    def info(self, request):
        response = super().info(request)
        # 根据 agent code 获取 agent 信息；saas_url 指向本服务的 ping 配置接口
        agent_ping_path = reverse(f"{self.basename}-ping")
        response.data["saas_url"] = f"{env.BK_SAAS_HOST}{agent_ping_path}"
        return response


class AIChatGroupViewSet(AgentCodeResourceManagerMixin, ChatGroupViewSet):
    pass


class AIChatSessionShareView(AgentCodeResourceManagerMixin, ChatSessionShareView):
    pass


class AILLMViewSet(AgentCodeResourceManagerMixin, LLMViewSet):
    pass
