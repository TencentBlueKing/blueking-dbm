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
import traceback
from unittest.mock import Mock, patch

import pytest
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse
from rest_framework.test import APIClient

from backend import env
from backend.bk_web.viewsets import ExternalProxyViewSet
from backend.core.storages.exceptions import TemporaryDownloadError
from backend.core.storages.handlers import StorageHandler
from backend.core.storages.storage import MyBKGenericRepoClient

PROJECT = "system.bkdbm"
REPO = "bkdbm"
FILE_PATH = "mysql/actuator/1.0.6/dbactuator"
TOKEN = "0123456789abcdef0123456789abcdef"
DOWNLOAD_URL = f"/apis/core/storage/generic/temporary/download/{PROJECT}/{REPO}/{FILE_PATH}/"


def build_bkrepo_response(ok=True, status_code=200, chunks=(b"\x7fELF", b"payload")):
    resp = Mock()
    resp.ok = ok
    resp.status_code = status_code
    resp.headers = {"Content-Disposition": 'attachment; filename="dbactuator"'}
    resp.iter_content.return_value = iter(chunks)
    return resp


def build_handler(bkrepo_response=None):
    storage = Mock()
    storage.client.project = PROJECT
    storage.client.bucket = REPO
    storage.client.temporary_download.return_value = bkrepo_response or build_bkrepo_response()
    return StorageHandler(storage=storage), storage


class TestClientTemporaryDownload:
    @patch("backend.core.storages.storage.requests.get")
    def test_download_with_token_only(self, mock_get):
        client = MyBKGenericRepoClient(
            bucket=REPO, project=PROJECT, username="admin", password="password", endpoint_url="http://bkrepo.com/"
        )
        mock_get.return_value = build_bkrepo_response()

        with patch.object(client, "get_client") as mock_get_client:
            client.temporary_download(path=f"/{FILE_PATH}", token=TOKEN)
            mock_get_client.assert_not_called()

        args, kwargs = mock_get.call_args
        assert args[0] == f"http://bkrepo.com/generic/temporary/download/{PROJECT}/{REPO}/{FILE_PATH}"
        assert kwargs["params"] == {"token": TOKEN, "download": "true"}
        assert kwargs["stream"] is True
        assert "auth" not in kwargs


class TestHandlerTemporaryDownload:
    def test_stream_file_from_bkrepo(self):
        handler, storage = build_handler()

        resp = handler.temporary_download(project=PROJECT, repo=REPO, path=FILE_PATH, token=TOKEN)

        assert isinstance(resp, StreamingHttpResponse)
        assert b"".join(resp.streaming_content) == b"\x7fELFpayload"
        assert resp["Content-Type"] == "application/octet-stream"
        storage.client.temporary_download.assert_called_once_with(path=FILE_PATH, token=TOKEN, force_download=True)
        storage.client.batch_download.assert_not_called()

    @pytest.mark.parametrize("status_code", [401, 403, 404])
    def test_bkrepo_reject_raises(self, status_code):
        handler, _ = build_handler(build_bkrepo_response(ok=False, status_code=status_code))

        with pytest.raises(TemporaryDownloadError):
            handler.temporary_download(project=PROJECT, repo=REPO, path=FILE_PATH, token="invalid-token")

    @pytest.mark.parametrize(
        "project,repo,path",
        [
            ("other.project", REPO, FILE_PATH),
            (PROJECT, "other-repo", FILE_PATH),
            (PROJECT, REPO, "mysql/actuator/../../secret"),
            (PROJECT, REPO, "../secret"),
        ],
    )
    def test_invalid_target_rejected_before_request(self, project, repo, path):
        handler, storage = build_handler()

        with pytest.raises(TemporaryDownloadError):
            handler.temporary_download(project=project, repo=repo, path=path, token=TOKEN)
        storage.client.temporary_download.assert_not_called()

    @pytest.mark.parametrize("error_cls", [requests.ConnectionError, requests.Timeout])
    def test_request_exception_hides_token(self, error_cls):
        handler, storage = build_handler()
        storage.client.temporary_download.side_effect = error_cls(f"http://bkrepo.com/generic?token={TOKEN}")

        with pytest.raises(TemporaryDownloadError) as exc_info:
            handler.temporary_download(project=PROJECT, repo=REPO, path=FILE_PATH, token=TOKEN)

        assert TOKEN not in "".join(traceback.format_exception(exc_info.value))

    def test_upstream_closed_with_response(self):
        bkrepo_resp = build_bkrepo_response()
        handler, _ = build_handler(bkrepo_resp)

        resp = handler.temporary_download(project=PROJECT, repo=REPO, path=FILE_PATH, token=TOKEN)
        resp.close()

        bkrepo_resp.close.assert_called_once()

    def test_fallback_filename_from_path(self):
        bkrepo_resp = build_bkrepo_response()
        bkrepo_resp.headers = {}
        handler, _ = build_handler(bkrepo_resp)

        resp = handler.temporary_download(project=PROJECT, repo=REPO, path=FILE_PATH, token=TOKEN)

        assert resp["Content-Disposition"] == 'attachment; filename="dbactuator"'


class TestExternalProxyTemporaryDownload:
    PROXY_PATH = f"/external{DOWNLOAD_URL}"

    @pytest.fixture(autouse=True)
    def disable_open_external_proxy(self):
        with patch.object(env, "ENABLE_OPEN_EXTERNAL_PROXY", False):
            yield

    def test_file_streamed(self):
        upstream = build_bkrepo_response()

        resp = ExternalProxyViewSet().after_response(Mock(path=self.PROXY_PATH), upstream)

        assert isinstance(resp, StreamingHttpResponse)
        assert resp["Content-Type"] == "application/octet-stream"
        assert resp["Content-Disposition"] == 'attachment; filename="dbactuator"'
        assert b"".join(resp.streaming_content) == b"\x7fELFpayload"
        resp.close()
        upstream.close.assert_called_once()

    def test_error_json_not_streamed(self):
        error = {"result": False, "code": 1000006, "data": None, "message": "制品库拒绝下载请求", "errors": None}
        upstream = Mock(
            status_code=200, headers={"Content-Type": "application/json"}, content=json.dumps(error).encode()
        )

        resp = ExternalProxyViewSet().after_response(Mock(path=self.PROXY_PATH), upstream)

        assert not isinstance(resp, StreamingHttpResponse)
        assert resp.data["result"] is False
        upstream.iter_content.assert_not_called()


@pytest.mark.django_db
class TestTemporaryDownloadView:
    @pytest.fixture(autouse=True)
    def set_empty_middleware(self):
        with patch.object(settings, "MIDDLEWARE", []):
            yield

    @pytest.fixture
    def storage(self):
        handler, storage = build_handler()
        with patch("backend.core.storages.views.StorageHandler", return_value=handler):
            yield storage

    @pytest.fixture
    def api_client(self):
        user, _ = get_user_model().objects.get_or_create(username="admin")
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_download_with_token(self, api_client, storage):
        resp = api_client.get(DOWNLOAD_URL, {"token": TOKEN, "download": "true"})

        assert resp.status_code == 200
        assert b"".join(resp.streaming_content) == b"\x7fELFpayload"
        storage.client.temporary_download.assert_called_once_with(path=FILE_PATH, token=TOKEN, force_download=True)

    def test_download_without_token_rejected(self, api_client, storage):
        resp = api_client.get(DOWNLOAD_URL, {"download": "true"})

        assert not isinstance(resp, StreamingHttpResponse)
        assert resp.json()["result"] is False
        storage.client.temporary_download.assert_not_called()
        storage.client.batch_download.assert_not_called()
        storage.batch_download.assert_not_called()

    def test_download_with_invalid_token_rejected(self, api_client, storage):
        storage.client.temporary_download.return_value = build_bkrepo_response(ok=False, status_code=401)

        resp = api_client.get(DOWNLOAD_URL, {"token": "forged-token", "download": "true"})

        assert not isinstance(resp, StreamingHttpResponse)
        assert resp.json()["result"] is False
        storage.client.batch_download.assert_not_called()
        storage.batch_download.assert_not_called()
