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
import importlib.util
import os
from pathlib import Path

import pytest

from backend.tests.env.conftest import FakeCryptoError

MEDIUM_KMS_PATH = Path(__file__).resolve().parents[2] / "dbm_init" / "medium" / "kms.py"


@pytest.fixture
def medium_kms(monkeypatch, kms_inputs):
    """dbmedium 以扁平模块运行，这里按文件路径独立加载，避免与 blueking.kms 冲突"""
    spec = importlib.util.spec_from_file_location("dbmedium_kms", MEDIUM_KMS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "KMS_ENVELOPE_PATH", kms_inputs)
    return module


class TestMediumKMS:
    def test_disabled_keeps_environ(self, medium_kms, monkeypatch):
        monkeypatch.setenv("ENABLE_KMS", "false")
        monkeypatch.setenv("BKREPO_PASSWORD", "plain")
        medium_kms.inject_credentials()
        assert os.environ["BKREPO_PASSWORD"] == "plain"

    def test_enabled_overrides_bound_credentials(self, medium_kms, fake_kms_sdk, monkeypatch):
        monkeypatch.setenv("APP_TOKEN", "old-token")
        monkeypatch.setenv("BKREPO_PROJECT", "blueking")
        medium_kms.inject_credentials()
        assert os.environ["APP_CODE"] == "bk_dbm"
        assert os.environ["APP_TOKEN"] == "app-secret"
        assert os.environ["BKREPO_USERNAME"] == "repo_user"
        assert os.environ["BKREPO_PASSWORD"] == "repo_pass"
        assert os.environ["BKREPO_PROJECT"] == "blueking"

    def test_missing_field_fails(self, medium_kms, fake_kms_sdk, monkeypatch):
        monkeypatch.setenv("APP_TOKEN", "old-token")
        del fake_kms_sdk["payload"]["bkrepo"]
        with pytest.raises(medium_kms.KMSConfigError, match="bkrepo.default.username"):
            medium_kms.inject_credentials()
        assert os.environ["APP_TOKEN"] == "old-token"

    def test_decrypt_error_hides_detail(self, medium_kms, fake_kms_sdk):
        fake_kms_sdk["error"] = FakeCryptoError("secret-detail")
        with pytest.raises(medium_kms.KMSConfigError) as exc_info:
            medium_kms.inject_credentials()
        assert "secret-detail" not in str(exc_info.value)
