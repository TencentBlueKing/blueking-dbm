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
# 本文件仅覆盖命令构造和请求序列化，不访问 ORM，无需 django_db 标记。
import shlex
from unittest.mock import patch

import pytest

from backend.dbm_aiagent.mcp_tools.pulsar.impl import pulsar_toolbox as mod
from backend.dbm_aiagent.mcp_tools.pulsar.serializers.pulsar_toolbox import (
    ListNamespacesInputSerializer,
    PulsarListTopicsInputSerializer,
    TopicInputSerializer,
)


class TestPulsarToolboxShellEscaping:
    """用户可控的 Pulsar CLI 参数必须作为单一 shell 参数传递。"""

    @pytest.mark.parametrize(
        "func_name,kwargs,expected_prefix",
        [
            # 以下输入会被 API serializer 拒绝；这里故意绕过 serializer，
            # 验证执行层仍会把动态值安全地作为单个 shell 参数传递。
            ("list_namespaces", {"immute_domain": "test.db", "tenant": "tenant; id"}, "namespaces list"),
            ("list_topics", {"immute_domain": "test.db", "namespace": "public/default; id"}, "topics list"),
            (
                "describe_topic",
                {"immute_domain": "test.db", "topic": "persistent://public/default/topic; id"},
                "topics stats",
            ),
            (
                "topic_internal_stats",
                {"immute_domain": "test.db", "topic": "persistent://public/default/$(id)"},
                "topics stats-internal",
            ),
            (
                "list_subscriptions",
                {"immute_domain": "test.db", "topic": "persistent://public/default/topic name"},
                "topics subscriptions",
            ),
            (
                "get_namespace_policies",
                {"immute_domain": "test.db", "namespace": "public/default $(id)"},
                "namespaces policies",
            ),
        ],
    )
    def test_dynamic_cli_argument_is_shell_quoted(self, func_name, kwargs, expected_prefix):
        with patch.object(mod, "execute_pulsar_cli", return_value="{}") as execute_cli:
            getattr(mod, func_name)(**kwargs)

        admin_args = execute_cli.call_args.kwargs["admin_args"]
        user_value = next(value for key, value in kwargs.items() if key != "immute_domain")
        assert admin_args == f"{expected_prefix} {shlex.quote(user_value)}"

    def test_build_script_preserves_quoted_topic_as_single_argument(self):
        topic = "persistent://public/default/topic; $(id)"
        script = mod.build_pulsar_cli_script(
            {"admin_url": "http://127.0.0.1:8080"},
            f"topics stats {shlex.quote(topic)}",
        )
        command_line = next(line.strip() for line in script.splitlines() if line.startswith(mod.PULSAR_ADMIN))

        assert shlex.split(command_line.split(" 2>&1", maxsplit=1)[0]) == [
            mod.PULSAR_ADMIN,
            "--admin-url",
            "http://127.0.0.1:8080",
            "topics",
            "stats",
            topic,
        ]


class TestPulsarToolboxInputValidation:
    @pytest.mark.parametrize(
        "serializer_cls,data",
        [
            (ListNamespacesInputSerializer, {"cluster_domain": "test.db", "tenant": "tenant;id"}),
            (PulsarListTopicsInputSerializer, {"cluster_domain": "test.db", "namespace": "public/default;id"}),
            (
                TopicInputSerializer,
                {"cluster_domain": "test.db", "topic": "persistent://public/default/topic;id"},
            ),
        ],
    )
    def test_rejects_shell_metacharacters(self, serializer_cls, data):
        serializer = serializer_cls(data=data)

        assert serializer.is_valid() is False

    @pytest.mark.parametrize(
        "serializer_cls,data",
        [
            (ListNamespacesInputSerializer, {"cluster_domain": "test.db", "tenant": "public"}),
            (PulsarListTopicsInputSerializer, {"cluster_domain": "test.db", "namespace": "public/default"}),
            (
                TopicInputSerializer,
                {"cluster_domain": "test.db", "topic": "persistent://public/default/topic-1"},
            ),
        ],
    )
    def test_accepts_valid_pulsar_names(self, serializer_cls, data):
        serializer = serializer_cls(data=data)

        assert serializer.is_valid(), serializer.errors
