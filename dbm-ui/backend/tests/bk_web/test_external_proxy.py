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
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.bk_web.viewsets import ExternalProxyViewSet

pytestmark = pytest.mark.django_db


def _rewrite(data):
    request = SimpleNamespace(path="/external/apis/monitor/grafana/get_dashboard/")
    response = SimpleNamespace(json=lambda: {"data": data})
    with patch("backend.bk_web.viewsets.env.BK_SAAS_HOST", "https://dbm.example.com"):
        result = ExternalProxyViewSet().after_response(request, response)
    return result.data


class TestGrafanaDashboardExternalProxy:
    def test_empty_dashboard_passthrough(self):
        assert _rewrite({"url": "#", "urls": []}) == {"url": "#", "urls": []}

    def test_rewrite_host(self):
        data = _rewrite(
            {
                "url": "http://inner.example.com/grafana/d/uid/slug?orgId=1",
                "urls": [{"url": "http://inner.example.com/grafana/d/uid/slug?orgId=1"}],
            }
        )
        assert data["url"] == "https://dbm.example.com/grafana/d/uid/slug?orgId=1"
        assert data["urls"][0]["url"] == "https://dbm.example.com/grafana/d/uid/slug?orgId=1"
