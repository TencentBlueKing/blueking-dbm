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

from datetime import datetime, timezone

import pytest

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_slowlog import get_query_params


@pytest.fixture()
def _time_range():
    # datetime2str 要求带时区的时间（与 SlowlogInputSerializer 的 DateTimeField 行为一致）
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)


def test_user_values_are_escaped_in_query_string(_time_range):
    """用户输入的 ns/queryHash 等字段必须被转义，不能逃逸出 Lucene 短语上下文。"""
    start_time, end_time = _time_range
    params = get_query_params(
        start_time=start_time,
        end_time=end_time,
        cluster_domain="my-cluster.db",
        ns='x" OR meta.cluster_domain:"victim-other-biz-cluster',
        query_hash='abc" OR attr.ns:"secret',
        size=10,
    )
    qs = params["query_string"]

    # 注入的双引号必须被反斜杠转义，短语上下文不会被关闭
    assert '\\"' in qs
    # 不能出现未转义的、可改变查询语义的裸 OR / 字段表达式
    assert ' OR meta.cluster_domain:"victim-other-biz-cluster' not in qs
    assert ' OR attr.ns:"secret' not in qs
    # 转义后仍以合法的短语形式出现
    assert 'attr.ns:"x\\" OR meta.cluster_domain:\\"victim-other-biz-cluster"' in qs
    assert 'attr.queryHash:"abc\\" OR attr.ns:\\"secret"' in qs


def test_backslash_in_ns_is_escaped(_time_range):
    """ns 中的反斜杠也需转义，避免吞掉后续转义字符。"""
    start_time, end_time = _time_range
    params = get_query_params(
        start_time=start_time,
        end_time=end_time,
        cluster_domain="my-cluster.db",
        ns='a\\"b',
        size=10,
    )
    qs = params["query_string"]
    # 原始 `a\"b` -> 转义后 `a\\\"b`，短语不会被提前关闭
    assert 'attr.ns:"a\\\\"b' not in qs
    assert 'attr.ns:"a\\\\\\"b"' in qs


@pytest.mark.parametrize(
    "field,value",
    [
        ("cluster_domain", "a\\b"),
        ("cluster_domain", 'a"b'),
        ("instance_host", "127.0.0.1\\"),
        ("instance_host", '127.0.0.1"'),
        ("instance_role", "mongo\\s"),
        ("instance_role", 'mongo"s'),
        ("instance", "127.0.0.1:27000\\"),
        ("instance", '127.0.0.1:27000"'),
    ],
)
def test_identifier_fields_reject_backslash_and_quote(_time_range, field, value):
    """域名、主机、角色、实例是标识符，值里不允许 \\ 或 "。"""
    start_time, end_time = _time_range
    with pytest.raises(DBMMcpBaseException, match="backslash and double quote are not allowed"):
        get_query_params(start_time=start_time, end_time=end_time, size=10, **{field: value})


def test_normal_values_unchanged(_time_range):
    """正常无特殊字符的输入不应被改动。"""
    start_time, end_time = _time_range
    params = get_query_params(
        start_time=start_time,
        end_time=end_time,
        cluster_domain="my-cluster.db",
        instance_host="127.0.0.1",
        instance_role="mongod",
        instance="127.0.0.1:27000",
        ns="bkrepo_prod.node_188",
        query_hash="F9BA5F6E",
        size=10,
    )
    qs = params["query_string"]
    assert 'meta.cluster_domain:"my-cluster.db"' in qs
    assert 'meta.instance_host:"127.0.0.1"' in qs
    assert 'meta.instance_role:"mongod"' in qs
    assert 'meta.instance:"127.0.0.1:27000"' in qs
    assert 'attr.ns:"bkrepo_prod.node_188"' in qs
    assert 'attr.queryHash:"F9BA5F6E"' in qs
