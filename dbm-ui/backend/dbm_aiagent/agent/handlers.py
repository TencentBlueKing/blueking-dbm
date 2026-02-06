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
import logging
import uuid

from aidev_agent.services.pydantic_models import ExecuteKwargs
from aidev_bkplugin.services.agent import build_chat_completion_agent_by_session_code
from aidev_bkplugin.views.builtin import client

from backend.dbm_aiagent.agent.commands import CommandProcessor
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.env import DEFAULT_USERNAME

logger = logging.getLogger("root")


class AgentHandler:
    """Agent 处理器。用于开发一些agent处理函数"""

    @staticmethod
    def __generate_session_code():
        """生成session_code"""
        return str(uuid.uuid4())

    @classmethod
    def create_temporary_session(cls, username=DEFAULT_USERNAME):
        """创建临时会话"""
        session_code = cls.__generate_session_code()

        # 创建临时会话
        create_session_params = {
            "session_code": session_code,
            "session_name": "temporary_session",
            "is_temporary": False,
            "session_property": {},
        }
        client.api.create_chat_session(json=create_session_params, headers={"X-BKAIDEV-USER": username})

        return session_code

    @classmethod
    def create_chat_completion(cls, session_code, session_content_id):
        """获得本次对话内容，内部调用默认非流式"""
        execute_kwargs = ExecuteKwargs(stream=False)
        agent_instance = build_chat_completion_agent_by_session_code(session_code)
        result = agent_instance.execute(execute_kwargs)
        return result

    @classmethod
    def ask_agent_with_content(cls, agent_code: DBMAgentCode, content: str, username=DEFAULT_USERNAME):
        """根据agent直接内容询问agent"""
        # 创建临时会话
        session_code = cls.create_temporary_session(username)

        # 创建会话内容
        # 主智能体直接询问，子智能体走快捷指令切换询问
        content_params = {"session_code": session_code, "role": "user", "content": content}
        if agent_code != DBMAgentCode.DBM:
            content_property = {"extra": {"command": agent_code, "rendered_content": content}}
            content_params.update(property=content_property, content=str(DBMAgentCode.get_choice_label(agent_code)))
        resp = client.api.create_chat_session_content(json=content_params, headers={"X-BKAIDEV-USER": username})

        # 获取AI回复
        session_content_id = resp["data"]["id"]
        ai_response = cls.create_chat_completion(session_code, session_content_id)
        return ai_response["choices"][0]["delta"]["content"]

    @classmethod
    def ask_agent_with_command(cls, command: str, command_params: dict, username=DEFAULT_USERNAME):
        """根据快捷指令询问agent"""
        if command not in CommandProcessor._handlers:
            raise ValueError(f"Command {command} not found")
        command_handler = CommandProcessor._handlers[command]

        # 创建临时会话
        session_code = cls.create_temporary_session(username)

        # 渲染command内容
        context = [{"__key": key, "__value": value, "context_type": "text"} for key, value in command_params.items()]
        command_data = {"command": command, "context": context}
        rendered_content = CommandProcessor.process_command(command_data)
        # 创建会话内容。特殊：为了统计工时，这里加上command名称
        rendered_content = f"comment：{command}\n" + rendered_content
        content_property = {"extra": {"command": command, "rendered_content": rendered_content, "context": context}}
        content_params = {
            "session_code": session_code,
            "role": "user",
            "property": content_property,
            "content": command_handler.name,
        }
        resp = client.api.create_chat_session_content(json=content_params, headers={"X-BKAIDEV-USER": username})

        # 获取AI回复
        session_content_id = resp["data"]["id"]
        ai_response = cls.create_chat_completion(session_code, session_content_id)
        return ai_response["choices"][0]["delta"]["content"]
