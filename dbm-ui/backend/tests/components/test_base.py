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
from unittest.mock import MagicMock, patch

import pytest
import requests

from backend.components.base import BaseApi, DataAPI, DataResponse
from backend.components.constants import SSLEnum
from backend.exceptions import ApiResultError


class TestDataResponse:
    """测试 DataResponse 类"""

    def test_is_success_with_result_true(self):
        """测试成功响应 - 有result字段"""
        response = {"result": True, "data": "success"}
        dr = DataResponse(response, "test_request_id")
        assert dr.is_success() is True

    def test_is_success_with_result_false(self):
        """测试失败响应 - 有result字段"""
        response = {"result": False, "message": "error"}
        dr = DataResponse(response, "test_request_id")
        assert dr.is_success() is False

    def test_is_success_with_code_zero(self):
        """测试成功响应 - 通过code判断"""
        response = {"code": 0, "data": "success"}
        dr = DataResponse(response, "test_request_id")
        assert dr.is_success() is True

    def test_is_success_with_code_nonzero(self):
        """测试失败响应 - 通过code判断"""
        response = {"code": 1, "message": "error"}
        dr = DataResponse(response, "test_request_id")
        assert dr.is_success() is False

    def test_properties(self):
        """测试属性访问"""
        response = {
            "result": True,
            "message": "ok",
            "code": 0,
            "data": {"key": "value"},
            "permission": {"view": True},
            "errors": [],
            "error_msg": "",
        }
        dr = DataResponse(response, "req_123")
        assert dr.message == "ok"
        assert dr.code == 0
        assert dr.data == {"key": "value"}
        assert dr.permission == {"view": True}
        assert dr.errors == []
        assert dr.error_msg == ""


class TestDataAPI:
    """测试 DataAPI 类"""

    def test_init(self):
        """测试初始化"""
        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test")
        assert api.method == "GET"
        assert api.base == "http://test.com"
        assert api.module == "test"
        assert api.url == "http://test.com/api/test"

    def test_build_actual_url_with_params(self):
        """测试构建URL - 带参数"""
        api = DataAPI(method="GET", base="http://test.com", url="/api/{user_id}/test", module="test")
        url = api.build_actual_url({"user_id": 123})
        assert url == "http://test.com/api/123/test"

    def test_build_actual_url_without_params(self):
        """测试构建URL - 不带参数"""
        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test")
        url = api.build_actual_url({})
        assert url == "http://test.com/api/test"

    def test_safe_response_full(self):
        """测试safe_response - 完整响应"""
        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test")
        response = {"result": True, "message": "ok", "data": {"key": "value"}, "request_id": "123"}
        safe_resp = api.safe_response(response)
        assert safe_resp["result"] is True
        assert safe_resp["message"] == "ok"
        assert safe_resp["data"] == {"key": "value"}

    def test_safe_response_minimal(self):
        """测试safe_response - 最小响应"""
        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test")
        response = {"code": 0}
        safe_resp = api.safe_response(response)
        assert "result" in safe_resp
        assert "message" in safe_resp
        assert "data" in safe_resp

    def test_split_file_data(self):
        """测试分离文件数据"""
        mock_file = MagicMock()
        mock_file.read = MagicMock()
        data = {"key1": "value1", "file": mock_file, "key2": "value2"}
        non_file, file_data = DataAPI._split_file_data(data)
        assert "key1" in non_file
        assert "key2" in non_file
        assert "file" in file_data

    @patch("backend.components.base.requests.session")
    def test_call_with_default_return_value(self, mock_session):
        """测试调用 - 使用默认返回值"""
        api = DataAPI(
            method="GET",
            base="http://test.com",
            url="/api/test",
            module="test",
            default_return_value={"result": True, "data": "default"},
        )
        result = api(params={})
        assert result == "default"

    @patch("backend.components.base.requests.session")
    def test_call_raise_exception_on_failure(self, mock_session):
        """测试调用 - 失败时抛出异常"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": False, "message": "error", "code": 1}

        # 设置完整的mock session
        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_resp
        mock_session_instance.headers = {}
        mock_session_instance.cookies = {}
        mock_session.return_value = mock_session_instance

        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test")
        with pytest.raises(ApiResultError):
            api(params={}, raise_exception=True)

    @patch("backend.components.base.requests.session")
    def test_call_timeout_retry(self, mock_session):
        """测试调用 - 超时重试"""
        mock_session.return_value.request.side_effect = requests.exceptions.Timeout()

        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test", max_retry_times=1)

        with pytest.raises(Exception):  # 最终会因为达到最大重试次数而失败
            api(params={})

    def test_is_backend_request(self):
        """测试是否是后台请求"""
        mock_request = MagicMock()
        mock_request.internal_call = True
        assert DataAPI.is_backend_request(mock_request) is True

    def test_build_cache_key(self):
        """测试构建缓存key"""
        api = DataAPI(method="GET", base="http://test.com", url="/api/test", module="test")
        key1 = api._build_cache_key({"param1": "value1"})
        key2 = api._build_cache_key({"param1": "value1"})
        key3 = api._build_cache_key({"param1": "value2"})
        assert key1 == key2
        assert key1 != key3


class TestFetchClientCrt:
    """测试客户端证书的获取"""

    @staticmethod
    def _make_api():
        return DataAPI(method="POST", base="http://test.com", url="/api/test", module="test", ssl=True)

    @patch("backend.components.base.os.path.isfile", return_value=True)
    @patch("backend.components.base.SystemSettings.get_setting_value")
    def test_reuse_local_crt_without_db_query(self, mock_get_setting, mock_isfile):
        """证书已落盘时直接复用，不读库，避免高并发调用占满 DB 连接池"""
        client_crt, client_key = self._make_api()._fetch_client_crt()
        assert client_crt.endswith(SSLEnum.CLIENT_CRT.value)
        assert client_key.endswith(SSLEnum.CLIENT_KEY.value)
        mock_get_setting.assert_not_called()

    @patch("backend.components.base.SystemSettings.insert_setting_value")
    @patch("backend.components.base.os.makedirs")
    @patch("backend.components.base.os.path.isfile", return_value=False)
    @patch("backend.components.base.SystemSettings.get_setting_value")
    def test_localize_crt_when_file_missing(self, mock_get_setting, mock_isfile, mock_makedirs, mock_insert_setting):
        """证书缺失时才读库取内容并落盘"""
        mock_get_setting.return_value = {
            SSLEnum.CLIENT_CRT.value: "crt-content",
            SSLEnum.CLIENT_KEY.value: "key-content",
        }
        with patch.object(DataAPI, "_write_file_atomically") as mock_write:
            self._make_api()._fetch_client_crt()

        mock_get_setting.assert_called_once()
        assert mock_write.call_count == 2
        mock_insert_setting.assert_called_once()


class TestBaseApi:
    """测试 BaseApi 类"""

    def test_is_esb(self):
        """测试是否是ESB接口"""

        class TestApi(BaseApi):
            MODULE = "test"
            BASE = "http://bkapi.example.com/api/c/compapi/v2/test/"

        api = TestApi()
        assert api.is_esb() is True

    def test_is_not_esb(self):
        """测试不是ESB接口"""

        class TestApi(BaseApi):
            MODULE = "test"
            BASE = "http://test.com/api/"

        api = TestApi()
        assert api.is_esb() is False

    def test_generate_data_api(self):
        """测试生成DataAPI"""

        class TestApi(BaseApi):
            MODULE = "test_module"
            BASE = "http://test.com"

        api = TestApi()
        data_api = api.generate_data_api(method="POST", url="/api/test", description="test api")
        assert isinstance(data_api, DataAPI)
        assert data_api.method == "POST"
        assert data_api.module == "test_module"
