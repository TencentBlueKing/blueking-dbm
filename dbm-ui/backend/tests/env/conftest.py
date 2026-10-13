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
import os
import sys
import types

import pytest

TEST_PRIVATE_KEY = "test-private-key"
TEST_ENVELOPE = "test-envelope"


class FakeCryptoError(Exception):
    pass


class FakeCryptoBackendUnavailableError(FakeCryptoError):
    pass


def full_payload() -> dict:
    """覆盖 dbm、dbmedium 所需字段的信封明文"""
    account = {"username": "user", "password": "pass"}
    return {
        "bkapp_id_secret": {"default": {"app_code": "bk_dbm", "app_secret": "app-secret"}},
        "mysql": {
            "dbm": {"username": "dbm_user", "password": "dbm_pass"},
            "dbmReport": dict(account),
            "dbmStats": {"username": "stats_user", "password": "stats_pass"},
        },
        "redis": {"default": {"password": "redis-pass"}},
        "kafka": {"default": {"username": "kafka_user", "password": "kafka_pass"}},
        "bkrepo": {"default": {"username": "repo_user", "password": "repo_pass"}},
        "bkmonitor": {"default": {"bkm_dbm_token": "bkm-token"}},
    }


@pytest.fixture(autouse=True)
def restore_environ():
    """inject_credentials 直接写 os.environ，monkeypatch 无法还原原本不存在的变量"""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture
def fake_kms_sdk(monkeypatch):
    """以假的 bk_kms 模块替代 SDK：校验入参并返回预设明文，或抛出预设异常"""

    state = {"payload": full_payload(), "error": None}
    module = types.ModuleType("bk_kms")
    module.CryptoError = FakeCryptoError
    module.CryptoBackendUnavailableError = FakeCryptoBackendUnavailableError

    def decrypt(envelope: str, private_key: str) -> str:
        if state["error"]:
            raise state["error"]
        assert envelope == TEST_ENVELOPE
        assert private_key == TEST_PRIVATE_KEY
        return json.dumps(state["payload"])

    module.decrypt = decrypt
    monkeypatch.setitem(sys.modules, "bk_kms", module)
    return state


@pytest.fixture
def kms_inputs(monkeypatch, tmp_path):
    """开启 KMS，并准备私钥环境变量与信封文件，返回信封文件路径"""
    envelope_path = tmp_path / "bk-dbm-kms"
    envelope_path.write_text(f"{TEST_ENVELOPE}\n", encoding="utf-8")
    monkeypatch.setenv("ENABLE_KMS", "true")
    monkeypatch.setenv("BK_DBM_KMS_PRIVATE_KEY", f" {TEST_PRIVATE_KEY} ")
    monkeypatch.delenv("REVERSE_REPORT_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    monkeypatch.delenv("REVERSE_REPORT_KAFKA_SECURITY_PROTOCOL", raising=False)
    return envelope_path
