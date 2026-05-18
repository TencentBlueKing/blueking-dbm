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
import json
import logging
import re
import uuid

from aidev_agent.services.pydantic_models import ExecuteKwargs
from aidev_bkplugin.services.agent import build_chat_completion_agent_by_session_code
from aidev_bkplugin.views.builtin import client
from django.http import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _

from backend.dbm_aiagent.agent.commands import CommandProcessor
from backend.dbm_aiagent.agent.constants import DEFAULT_AGENT_CHAT_TIMEOUT, RISK_COMPARE_PROMPT, DBMAgentCode
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
            "is_temporary": True,
            "session_property": {},
        }
        client.api.create_chat_session(json=create_session_params, headers={"X-BKAIDEV-USER": username})

        return session_code

    @classmethod
    def create_chat_completion(
        cls,
        session_code,
        session_content_id,
        stream: bool = False,
        timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
    ):
        """获得本次对话内容，支持流式/非流式"""
        execute_kwargs = ExecuteKwargs(stream=stream, invoke_timeout=timeout)
        agent_instance = build_chat_completion_agent_by_session_code(session_code)
        result = agent_instance.execute(execute_kwargs)
        return result

    @classmethod
    def ask_agent_with_content(
        cls,
        agent_code: DBMAgentCode,
        content: str,
        username=DEFAULT_USERNAME,
        session_code=None,
        stream: bool = False,
        timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
    ):
        """根据agent直接内容询问agent"""
        # 创建临时会话
        session_code = session_code or cls.create_temporary_session(username)

        # 创建会话内容
        # 主智能体直接询问，子智能体走快捷指令切换询问
        content_params = {"session_code": session_code, "role": "user", "content": content}
        if agent_code != DBMAgentCode.DBM:
            # 特殊：为了统计工时，这里加上command名称
            rendered_content = f"comment：{agent_code}\n" + content
            content_property = {"extra": {"command": agent_code, "rendered_content": rendered_content}}
            content_params.update(property=content_property, content=str(DBMAgentCode.get_choice_label(agent_code)))
        resp = client.api.create_chat_session_content(json=content_params, headers={"X-BKAIDEV-USER": username})

        # 获取AI回复
        session_content_id = resp["data"]["id"]
        ai_response = cls.create_chat_completion(session_code, session_content_id, stream=stream, timeout=timeout)

        if stream and not isinstance(ai_response, dict):
            return cls.streaming_response(ai_response)

        return ai_response["choices"][0]["delta"]["content"]

    @classmethod
    def ask_agent_with_content_in_session(
        cls,
        agent_code: DBMAgentCode,
        content: str,
        username=DEFAULT_USERNAME,
        session_code=None,
        timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
    ):
        """根据agent直接内容询问agent, 连续对话"""
        session_code = session_code or cls.create_temporary_session(username)
        ai_response = cls.ask_agent_with_content(agent_code, content, username, session_code, timeout=timeout)
        return ai_response, session_code

    @classmethod
    def ask_agent_with_command(
        cls,
        command: str,
        command_params: dict,
        username=DEFAULT_USERNAME,
        stream: bool = False,
        timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
    ):
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
        ai_response = cls.create_chat_completion(session_code, session_content_id, stream=stream, timeout=timeout)

        if stream and not isinstance(ai_response, dict):
            return cls.streaming_response(ai_response)

        return ai_response["choices"][0]["delta"]["content"]

    @staticmethod
    def streaming_response(generator):
        sr = StreamingHttpResponse(generator)
        sr.headers["Cache-Control"] = "no-cache"
        sr.headers["X-Accel-Buffering"] = "no"
        sr.headers["content-type"] = "text/event-stream"
        return sr

    @classmethod
    def compare_risk_reports(cls, last_report: str, current_report: str, username=DEFAULT_USERNAME) -> dict:
        """
        调用智能体比对两份风险报告是否描述同一风险问题
        单据值守使用的方法

        利用 AI 的语义理解能力判断两次风险报告是否为同一风险，
        避免 MD5 指纹方案中 "CPU高" 和 "CPU很高" 被误判为不同风险的问题。

        Args:
            last_report: 上一次推送的风险报告内容
            current_report: 本次的风险报告内容
            username: 调用智能体的用户名

        Returns:
            dict: {"is_same_risk": bool, "reason": str}
                - is_same_risk=True: 两份报告描述的是同一个风险
                - is_same_risk=False: 两份报告描述的是不同的风险
                - 解析失败时默认返回 {"is_same_risk": False, "reason": "解析失败，保守推送"}
        """
        compare_prompt = RISK_COMPARE_PROMPT.format(
            last_report=last_report,
            current_report=current_report,
        )
        try:
            ai_response = cls.ask_agent_with_content(
                agent_code=DBMAgentCode.DBM,
                content=compare_prompt,
                username=username,
            )
            # 从返回中提取 JSON
            json_match = re.search(r'\{.*?"is_same_risk".*?}', ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                if isinstance(result, dict):
                    return result
                logger.warning(_("[风险比对] json.loads返回非dict类型: %s"), type(result))
        except Exception as err:
            logger.warning(_("[风险比对] 调用智能体比对失败: %s"), type(err))

        # 解析失败时，保守策略：认为是不同风险，允许推送
        return {"is_same_risk": False, "reason": _("智能体比对失败，保守策略允许推送")}
