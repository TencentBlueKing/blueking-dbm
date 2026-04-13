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
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


def _capture_promql(module, condition):
    captured = {"promql": ""}

    def _mock_unify_query(params, use_admin=True):
        captured["promql"] = params["query_configs"][0]["promql"]
        return {"series": []}

    with patch.object(module.BKMonitorV3Api, "unify_query", side_effect=_mock_unify_query):
        module._instant_fetch_metric(condition, retry_times=1, sleep_time=0)
    return captured["promql"]


class TestInstantFetchMetricConditionBuild:
    def test_instance_list_escape_regex_meta(self, sync_instance_status_module):
        promql = _capture_promql(
            sync_instance_status_module,
            {"instance": ["127.0.0.1:27017", "127.0.0.2:27017"]},
        )
        assert 'instance=~"^(127\\\\.0\\\\.0\\\\.1\\\\-27017|127\\\\.0\\\\.0\\\\.2\\\\-27017)$"' in promql

    def test_instance_string_keeps_exact_match_selector(self, sync_instance_status_module):
        promql = _capture_promql(sync_instance_status_module, {"instance": "127.0.0.1:27017"})
        assert 'instance="127.0.0.1-27017"' in promql
        assert 'instance=~"' not in promql

    def test_other_keys_behavior_unchanged(self, sync_instance_status_module):
        promql = _capture_promql(
            sync_instance_status_module,
            {"cluster_domain": ["a.b", "c-d"], "shard": "rs0"},
        )
        assert 'cluster_domain=~"^(a.b|c-d)$"' in promql
        assert 'shard="rs0"' in promql
