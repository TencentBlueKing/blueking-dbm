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
from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from backend import env
from backend.iam_app.views.v4.dispatcher import LIST_INSTANCE, IAMV4ResourceApiDispatcher


class TestIAMV4ResourceApiDispatcher:
    @patch.object(IAMV4ResourceApiDispatcher, "_is_auth_allowed", return_value=True)
    def test_provider_error_not_exposed(self, mock_auth):
        """provider 抛异常时返回500，但不把异常详情回传给调用方"""
        provider = MagicMock()
        provider.list_instance.side_effect = RuntimeError("secret table detail")
        dispatcher = IAMV4ResourceApiDispatcher(env.BK_IAM_SYSTEM_ID)
        dispatcher._provider["mysql"] = provider

        request = RequestFactory().post(
            "/iam/v4/resource/api/",
            data=json.dumps({"type": "mysql", "method": LIST_INSTANCE, "filter": {}}),
            content_type="application/json",
            HTTP_X_REQUEST_ID="req-1",
        )
        response = dispatcher._dispatch(request)

        assert response.status_code == 500
        assert response["X-Request-Id"] == "req-1"
        body = json.loads(response.content)
        assert body["error"]["code"] == "INTERNAL"
        assert "secret table detail" not in response.content.decode()
