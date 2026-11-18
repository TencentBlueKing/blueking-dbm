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
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from backend.db_proxy.reverse_api.base_reverse_api_view import IPHasRegisteredPermission

MODULE = "backend.db_proxy.reverse_api.base_reverse_api_view"


def _make_request(query: str) -> Request:
    return Request(APIRequestFactory().get(f"/apis/proxypass/reverse_api/mysql/list_instance_info/?{query}"))


class TestIPHasRegisteredPermission:
    def test_denied_when_backend_api_disabled(self):
        request = _make_request("bk_cloud_id=0&ip=127.0.0.1")
        with patch(f"{MODULE}.env.ENABLE_BACKEND_API", False), patch(f"{MODULE}.validate_machine_ip") as validate:
            with pytest.raises(PermissionDenied):
                IPHasRegisteredPermission().has_permission(request, None)
        validate.assert_not_called()

    def test_validate_machine_ip_when_backend_api_enabled(self):
        request = _make_request("bk_cloud_id=0&ip=127.0.0.1")
        with patch(f"{MODULE}.env.ENABLE_BACKEND_API", True), patch(f"{MODULE}.validate_machine_ip") as validate:
            assert IPHasRegisteredPermission().has_permission(request, None) is True
        validate.assert_called_once_with(0, request)
