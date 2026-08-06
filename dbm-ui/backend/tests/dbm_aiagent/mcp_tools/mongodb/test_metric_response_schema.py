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
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_metrics import _wrap_metric_result
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mcp import MongoQueryMetricOutputSerializer

_SERIES = [
    {
        "dimensions": {"instance": "127.0.0.1:27001"},
        "min": 1,
        "max": 10,
        "avg": 5,
        "max_time": "2026-08-05 10:00:00",
    }
]


def test_metric_output_keys_match_serializer():
    """query_metric 实际响应字段必须都在输出 serializer 中声明，避免文档与实现不一致"""
    out = _wrap_metric_result(cluster_domain="m1.rs0.dba.db", metric_type="qps", result={"series": _SERIES})
    declared = set(MongoQueryMetricOutputSerializer().fields)
    assert set(out) <= declared, "未声明的响应字段: {}".format(set(out) - declared)
    assert out["metric"] == "qps"
    assert "global" in out["summary"]


def test_metric_error_keys_match_serializer():
    out = _wrap_metric_result(cluster_domain="m1.rs0.dba.db", metric_type="qps", result={"error": "boom"})
    declared = set(MongoQueryMetricOutputSerializer().fields)
    assert set(out) <= declared
    assert out["error"] == "boom"
