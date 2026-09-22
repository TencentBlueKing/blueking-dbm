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

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.http import StreamingHttpResponse

from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.agent.handlers import AgentHandler

AI_RESPONSE = {"choices": [{"delta": {"content": "回复正文"}}]}
TRACE_ID = "07d731498ddf6c7ce81684efcd328d8f"


@contextmanager
def mock_agent_runtime(execute_result=AI_RESPONSE, trace_id=TRACE_ID):
    """屏蔽 agent 装配与平台调用，暴露 executor / client 供断言"""
    executor = MagicMock()
    executor.execute_with_save.return_value = execute_result
    client = MagicMock()
    client.api.create_chat_session_content.return_value = {"data": {"id": 1}}
    with patch("backend.dbm_aiagent.agent.handlers.build_resource_manager"), patch(
        "backend.dbm_aiagent.agent.handlers.build_session_manager"
    ), patch("backend.dbm_aiagent.agent.handlers.AgentBuilder"), patch(
        "backend.dbm_aiagent.agent.handlers.AgentExecutor", return_value=executor
    ), patch(
        "backend.dbm_aiagent.agent.handlers.AgentHelper.get_client", return_value=client
    ), patch(
        "backend.dbm_aiagent.agent.handlers.get_current_trace_id", return_value=trace_id
    ):
        yield executor, client


class TestCreateChatCompletion:
    def test_non_stream_returns_raw_execute_result(self):
        """后台调用方直接取 choices[0].delta.content，返回结构不能被 execute_with_save 改写"""
        with mock_agent_runtime():
            result = AgentHandler.create_chat_completion(
                agent_code=DBMAgentCode.DBM, session_code="s-1", session_content_id=1
            )
        assert result == AI_RESPONSE

    def test_execute_kwargs_carries_caller_context(self):
        with mock_agent_runtime() as (executor, _):
            AgentHandler.create_chat_completion(
                agent_code=DBMAgentCode.DBM, session_code="s-1", session_content_id=1, username="tester"
            )
        execute_kwargs = executor.execute_with_save.call_args.args[1]
        assert execute_kwargs.session_code == "s-1"
        assert execute_kwargs.executor == "tester"
        assert execute_kwargs.caller_executor == "tester"
        assert execute_kwargs.caller_bk_app_code == settings.APP_CODE


class TestAskAgentWithContent:
    @staticmethod
    def __user_content_params(client):
        return client.api.create_chat_session_content.call_args.kwargs["json"]

    def test_user_content_carries_trace_id(self):
        with mock_agent_runtime() as (_, client):
            AgentHandler.ask_agent_with_content(agent_code=DBMAgentCode.DBM, content="hi", session_code="s-1")
        assert self.__user_content_params(client)["property"]["trace_id"] == TRACE_ID

    def test_user_content_skips_property_without_active_span(self):
        with mock_agent_runtime(trace_id=None) as (_, client):
            AgentHandler.ask_agent_with_content(agent_code=DBMAgentCode.DBM, content="hi", session_code="s-1")
        assert "property" not in self.__user_content_params(client)

    def test_command_agent_keeps_extra_property(self):
        """子智能体的工时统计字段不能被 trace_id 挤掉"""
        with mock_agent_runtime() as (_, client):
            AgentHandler.ask_agent_with_content(
                agent_code=DBMAgentCode.MYSQL_SLOW_LOGS_QUERY, content="hi", session_code="s-1"
            )
        content_property = self.__user_content_params(client)["property"]
        assert content_property["extra"]["command"] == DBMAgentCode.MYSQL_SLOW_LOGS_QUERY
        assert content_property["trace_id"] == TRACE_ID

    def test_non_stream_returns_content_text(self):
        with mock_agent_runtime():
            response = AgentHandler.ask_agent_with_content(
                agent_code=DBMAgentCode.DBM, content="hi", session_code="s-1"
            )
        assert response == "回复正文"

    def test_stream_returns_sse_response(self):
        with mock_agent_runtime(execute_result=iter(["data: {}\n\n"])):
            response = AgentHandler.ask_agent_with_content(
                agent_code=DBMAgentCode.DBM, content="hi", session_code="s-1", stream=True
            )
        assert isinstance(response, StreamingHttpResponse)
        assert response.headers["content-type"] == "text/event-stream"


if __name__ == "__main__":
    pytest.main([__file__])
