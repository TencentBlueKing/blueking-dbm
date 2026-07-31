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

from aidev_agent.pydantic_models import ExecuteKwargs
from aidev_bkplugin.services.agent_builder import AgentBuilder
from aidev_bkplugin.services.agent_helpers import AgentHelper
from aidev_bkplugin.services.agent_session import SessionManager
from django.http import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _

from backend.dbm_aiagent.agent.commands import CommandProcessor
from backend.dbm_aiagent.agent.configs.manager import (
    DBMAgentResourceManager,
    build_resource_manager,
    build_session_manager,
)
from backend.dbm_aiagent.agent.constants import DEFAULT_AGENT_CHAT_TIMEOUT, RISK_COMPARE_PROMPT, DBMAgentCode
from backend.env import DEFAULT_USERNAME

logger = logging.getLogger("root")


class AgentHandler:
    """Agent 处理器。用于开发一些agent处理函数"""

    @staticmethod
    def __generate_session_code():
        """生成session_code

        :return: uuid4 字符串，作为 aidev 平台会话的唯一标识
        """
        return str(uuid.uuid4())

    @staticmethod
    def __build_resource_manager(agent_code, username, model: str = "") -> DBMAgentResourceManager:
        """创建子智能体 resource manager
        resource manager 决定了本次调用使用哪套 app 凭证、以谁的身份换取 access_token，
        以及最终装配 agent 时使用的模型配置。
        """
        return build_resource_manager(agent_code, username, model)

    @staticmethod
    def __build_session_manager(agent_code, username) -> SessionManager:
        """创建session manager
        session manager 只负责会话及会话内容的增删查，不参与 agent 装配，因此无需模型信息。
        """
        return build_session_manager(agent_code, username)

    @classmethod
    def __build_client(cls, agent_code, username):
        """按 agent_code 构建携带对应 resource_manager 的 client"""
        return AgentHelper.get_client(resource_manager=cls.__build_resource_manager(agent_code, username))

    @classmethod
    def create_temporary_session(cls, username, agent_code):
        """创建临时会话

        临时会话（is_temporary=True）不会出现在用户的会话列表中，适用于后台任务、
        单次问答等不需要留存上下文的场景。

        :param username: 会话归属的用户名
        :param agent_code: 会话使用的智能体 code
        :return: 新建会话的 session_code
        """
        session_code = cls.__generate_session_code()

        # 创建临时会话
        create_session_params = {
            "session_code": session_code,
            "session_name": "temporary_session",
            "is_temporary": True,
            "session_property": {},
        }
        client = cls.__build_client(agent_code, username)
        client.api.create_chat_session(json=create_session_params, headers={"X-BKAIDEV-USER": username})

        return session_code

    @classmethod
    def create_chat_completion(
        cls,
        agent_code,
        session_code,
        session_content_id,
        stream: bool = False,
        timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
        username=DEFAULT_USERNAME,
        *,
        model: str = "",
    ):
        """获得本次对话内容，支持流式/非流式

        以 session_code 为上下文装配 agent 并执行，会话历史由 SDK 从平台侧拉取，
        因此调用前需保证用户提问已写入该会话。

        :param agent_code: 应答使用的智能体 code
        :param session_code: 会话 code，agent 由此还原完整对话上下文
        :param session_content_id: 本轮用户提问的内容 ID。当前实现未使用（SDK 直接按
            session_code 拉取会话上下文），保留该参数用于调用链路追溯
        :param stream: 是否流式返回
        :param timeout: 单次对话的超时时间（秒）
        :param username: 调用者用户名，决定 access_token 与工时归属
        :param model: 指定本次对话使用的 LLM，为空时使用智能体发布时配置的模型
        :return: 非流式返回 dict（含 choices/model/id/reference_doc）；流式返回事件生成器
        """
        execute_kwargs = ExecuteKwargs(stream=stream, invoke_timeout=timeout)
        # 模型覆盖挂在 resource manager 上，agent 装配时经 get_agent_config 生效
        rm = cls.__build_resource_manager(agent_code, username, model)
        sm = cls.__build_session_manager(agent_code, username)
        agent_instance = AgentBuilder(
            resource_manager=rm,
            session_manager=sm,
            username=username,
            agent_code=rm.get_agent_code(),
        ).by_session_code(session_code, version=execute_kwargs.version)
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
        *,
        model: str = "",
    ):
        """根据agent直接内容询问agent

        完整链路：准备会话 -> 写入用户提问 -> 触发 AI 应答。
        未传 session_code 时会新建临时会话，即一次性问答；传入则在既有会话内追加提问。

        :param agent_code: 目标智能体 code。非主智能体时按快捷指令语义记录，用于工时统计
        :param content: 用户提问内容
        :param username: 调用者用户名
        :param session_code: 复用的会话 code，为空时新建临时会话
        :param stream: 是否流式返回
        :param timeout: 单次对话的超时时间（秒）
        :param model: 指定本次对话使用的 LLM，为空时使用智能体发布时配置的模型
        :return: 非流式返回 AI 回复正文字符串；流式返回 StreamingHttpResponse
        """
        # 创建临时会话
        session_code = session_code or cls.create_temporary_session(username, agent_code)

        # 创建会话内容
        # 主智能体直接询问，子智能体走快捷指令切换询问
        content_params = {"session_code": session_code, "role": "user", "content": content}
        if agent_code != DBMAgentCode.DBM:
            # 特殊：为了统计工时，这里加上command名称
            rendered_content = f"comment：{agent_code}\n" + content
            content_property = {"extra": {"command": agent_code, "rendered_content": rendered_content}}
            content_params.update(property=content_property, content=str(DBMAgentCode.get_choice_label(agent_code)))
        client = cls.__build_client(agent_code, username)
        resp = client.api.create_chat_session_content(json=content_params, headers={"X-BKAIDEV-USER": username})

        # 获取AI回复
        session_content_id = resp["data"]["id"]
        ai_response = cls.create_chat_completion(
            agent_code=agent_code,
            session_content_id=session_content_id,
            session_code=session_code,
            stream=stream,
            timeout=timeout,
            username=username,
            model=model,
        )

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
        *,
        model: str = "",
    ):
        """根据agent直接内容询问agent, 连续对话

        与 ask_agent_with_content 的差别在于额外返回 session_code，调用方把它带入下一轮
        即可延续上下文，实现多轮对话。仅支持非流式。

        :param agent_code: 目标智能体 code
        :param content: 用户提问内容
        :param username: 调用者用户名
        :param session_code: 复用的会话 code，为空时新建临时会话
        :param timeout: 单次对话的超时时间（秒）
        :param model: 指定本次对话使用的 LLM，为空时使用智能体发布时配置的模型
        :return: (AI 回复正文, 本轮使用的 session_code)
        """
        session_code = session_code or cls.create_temporary_session(username, agent_code)
        ai_response = cls.ask_agent_with_content(
            agent_code, content, username, session_code, timeout=timeout, model=model
        )
        return ai_response, session_code

    @classmethod
    def ask_agent_with_command(
        cls,
        command: str,
        command_params: dict,
        username=DEFAULT_USERNAME,
        stream: bool = False,
        timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
        *,
        model: str = "",
    ):
        """根据快捷指令询问agent

        与 ask_agent_with_content 的差别在于提问内容不由调用方直接给出，而是把 command_params
        填入指令注册时声明的模板渲染得到；目标智能体也由指令自身声明，无需调用方指定。
        每次调用都会新建临时会话，不支持多轮。

        :param command: 快捷指令 code，须已注册到 CommandProcessor
        :param command_params: 指令模板的填充参数，key 为模板变量名
        :param username: 调用者用户名
        :param stream: 是否流式返回
        :param timeout: 单次对话的超时时间（秒）
        :param model: 指定本次对话使用的 LLM，为空时使用智能体发布时配置的模型
        :return: 非流式返回 AI 回复正文字符串；流式返回 StreamingHttpResponse
        :raises ValueError: 指令未注册到 CommandProcessor
        """
        if command not in CommandProcessor._handlers:
            raise ValueError(f"Command {command} not found")
        command_handler = CommandProcessor._handlers[command]
        agent_code = command_handler.agent_code

        # 创建临时会话
        session_code = cls.create_temporary_session(username, agent_code)

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
        client = cls.__build_client(agent_code, username)
        resp = client.api.create_chat_session_content(json=content_params, headers={"X-BKAIDEV-USER": username})

        # 获取AI回复
        session_content_id = resp["data"]["id"]
        ai_response = cls.create_chat_completion(
            agent_code=agent_code,
            session_code=session_code,
            session_content_id=session_content_id,
            stream=stream,
            timeout=timeout,
            username=username,
            model=model,
        )

        if stream and not isinstance(ai_response, dict):
            return cls.streaming_response(ai_response)

        return ai_response["choices"][0]["delta"]["content"]

    @staticmethod
    def streaming_response(generator):
        """将 agent 的流式输出包装为 SSE 响应

        关闭客户端缓存与 nginx 缓冲，避免 AI 回复被攒到最后一次性吐出。

        :param generator: agent 执行产生的事件生成器
        :return: content-type 为 text/event-stream 的流式响应
        """
        sr = StreamingHttpResponse(generator)
        sr.headers["Cache-Control"] = "no-cache"
        sr.headers["X-Accel-Buffering"] = "no"
        sr.headers["content-type"] = "text/event-stream"
        return sr

    @classmethod
    def compare_risk_reports(
        cls,
        last_report: str,
        current_report: str,
        username=DEFAULT_USERNAME,
        agent_code: DBMAgentCode = DBMAgentCode.TASK_GUARDIAN,
        *,
        model: str = "",
    ) -> dict:
        """
        调用智能体比对两份风险报告是否描述同一风险问题
        单据值守使用的方法

        利用 AI 的语义理解能力判断两次风险报告是否为同一风险，
        避免 MD5 指纹方案中 "CPU高" 和 "CPU很高" 被误判为不同风险的问题。

        Args:
            last_report: 上一次推送的风险报告内容
            current_report: 本次的风险报告内容
            username: 调用智能体的用户名
            agent_code: 智能体代码，默认使用通用单据值守智能体，可传入对应DB组件的单据值守智能体
            model: 指定本次对话使用的 LLM，为空时使用智能体发布时配置的模型

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
                agent_code=agent_code,
                content=compare_prompt,
                username=username,
                model=model,
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
