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
from aidev_bkplugin.views.builtin import (
    AgentInfoViewSet,
    ChatCompletionViewSet,
    ChatGroupViewSet,
    ChatSessionContentFeedbackViewSet,
    ChatSessionContentViewSet,
    ChatSessionShareView,
    ChatSessionViewSet,
)

from backend.dbm_aiagent.agent.commands import CommandProcessor


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

    def create(self, request):
        """创建聊天内容"""
        self.__render_command(request.data["property"]["extra"])
        return super().create(request)


class AIChatCompletionViewSet(ChatCompletionViewSet):
    pass


class AIChatSessionContentFeedbackViewSet(ChatSessionContentFeedbackViewSet):
    pass


class AIAgentInfoViewSet(AgentInfoViewSet):
    pass


class AIChatGroupViewSet(ChatGroupViewSet):
    pass


class AIChatSessionShareView(ChatSessionShareView):
    pass
