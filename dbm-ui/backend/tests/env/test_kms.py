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
import os
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

from backend.tests.env.conftest import FakeCryptoBackendUnavailableError, FakeCryptoError
from blueking import kms


@pytest.fixture
def envelope_path(kms_inputs, monkeypatch):
    monkeypatch.setattr(kms, "KMS_ENVELOPE_PATH", kms_inputs)
    return kms_inputs


class TestLoadCredentials:
    def test_disabled_returns_empty(self, monkeypatch):
        """未开启 KMS 时不读取信封，也不要求 SDK"""
        monkeypatch.delenv("ENABLE_KMS", raising=False)
        monkeypatch.setitem(sys.modules, "bk_kms", None)
        assert kms.load_credentials() == {}

    @pytest.mark.parametrize("value", ["TRUE", "1", " true", "yes"])
    def test_only_literal_true_enables(self, monkeypatch, value):
        monkeypatch.setenv("ENABLE_KMS", value)
        assert kms.load_credentials() == {}

    def test_enabled_maps_all_bindings(self, fake_kms_sdk, envelope_path):
        credentials = kms.load_credentials()

        assert credentials["APP_ID"] == "bk_dbm"
        assert credentials["APP_TOKEN"] == "app-secret"
        assert credentials["DB_USER"] == "dbm_user"
        assert credentials["DB_PASSWORD"] == "dbm_pass"
        assert credentials["STATS_DB_PASSWORD"] == credentials["DBM_STATSDB_PASSWORD"] == "stats_pass"
        assert credentials["REDIS_PASSWORD"] == "redis-pass"
        assert credentials["BKREPO_PASSWORD"] == "repo_pass"
        assert credentials["BKM_DBM_TOKEN"] == "bkm-token"
        assert "REVERSE_REPORT_KAFKA_PASSWORD" not in credentials

    def test_kafka_required_when_sasl_enabled(self, fake_kms_sdk, envelope_path, monkeypatch):
        monkeypatch.setenv("REVERSE_REPORT_KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        monkeypatch.setenv("REVERSE_REPORT_KAFKA_SECURITY_PROTOCOL", "SASL_PLAINTEXT")
        assert kms.load_credentials()["REVERSE_REPORT_KAFKA_PASSWORD"] == "kafka_pass"

        del fake_kms_sdk["payload"]["kafka"]
        with pytest.raises(ImproperlyConfigured, match="kafka.default.username"):
            kms.load_credentials()

    def test_missing_private_key(self, envelope_path, monkeypatch):
        monkeypatch.setenv("BK_DBM_KMS_PRIVATE_KEY", "  ")
        with pytest.raises(ImproperlyConfigured, match="BK_DBM_KMS_PRIVATE_KEY"):
            kms.load_credentials()

    def test_missing_sdk(self, envelope_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "bk_kms", None)
        with pytest.raises(ImproperlyConfigured, match="bk-kms-sdk"):
            kms.load_credentials()

    def test_missing_envelope_file(self, fake_kms_sdk, envelope_path):
        envelope_path.unlink()
        with pytest.raises(ImproperlyConfigured, match="Unable to read or decrypt"):
            kms.load_credentials()

    def test_decrypt_error_hides_detail(self, fake_kms_sdk, envelope_path):
        fake_kms_sdk["error"] = FakeCryptoError("secret-detail")
        with pytest.raises(ImproperlyConfigured) as exc_info:
            kms.load_credentials()
        assert "secret-detail" not in str(exc_info.value)
        assert exc_info.value.__cause__ is None

    def test_gm_backend_unavailable(self, fake_kms_sdk, envelope_path):
        fake_kms_sdk["error"] = FakeCryptoBackendUnavailableError()
        with pytest.raises(ImproperlyConfigured, match="SM2/SM4"):
            kms.load_credentials()

    @pytest.mark.parametrize("value", [None, "", "   ", 123])
    def test_invalid_field_reports_path_only(self, fake_kms_sdk, envelope_path, value):
        fake_kms_sdk["payload"]["mysql"]["dbm"]["password"] = value
        with pytest.raises(ImproperlyConfigured, match=r"^KMS requires a non-empty string at mysql\.dbm\.password$"):
            kms.load_credentials()


class TestInjectCredentials:
    def test_disabled_keeps_environ(self, monkeypatch):
        monkeypatch.delenv("ENABLE_KMS", raising=False)
        monkeypatch.setenv("DB_PASSWORD", "plain")
        assert kms.inject_credentials() == frozenset()
        assert os.environ["DB_PASSWORD"] == "plain"

    def test_enabled_overrides_environ(self, fake_kms_sdk, envelope_path, monkeypatch):
        monkeypatch.setenv("DB_PASSWORD", "old")
        monkeypatch.setenv("DB_HOST", "127.0.0.1")

        injected = kms.inject_credentials()

        assert injected == frozenset(kms._credential_bindings())
        assert os.environ["DB_PASSWORD"] == "dbm_pass"
        assert os.environ["APP_TOKEN"] == "app-secret"
        assert os.environ["DB_HOST"] == "127.0.0.1"

    def test_failure_leaves_environ_untouched(self, fake_kms_sdk, envelope_path, monkeypatch):
        monkeypatch.setenv("DB_PASSWORD", "old")
        fake_kms_sdk["payload"]["bkrepo"] = {}
        with pytest.raises(ImproperlyConfigured):
            kms.inject_credentials()
        assert os.environ["DB_PASSWORD"] == "old"


class TestKMSEnv:
    def test_raw_var_keeps_dollar_literal(self, monkeypatch):
        """KMS 写入的变量以 $ 开头时，不能被 django-environ 当作变量引用"""
        monkeypatch.setenv("HOME", "/home/someone")
        monkeypatch.setenv("REDIS_PASSWORD", "$HOME")
        env = kms.KMSEnv({"REDIS_PASSWORD"})
        assert env.str("REDIS_PASSWORD") == "$HOME"
        assert env.get_value("REDIS_PASSWORD", cast=str, default="") == "$HOME"

    def test_other_vars_keep_django_environ_semantics(self, monkeypatch):
        """未由 KMS 写入的变量（包括关闭 KMS 时的全部变量）行为不变"""
        monkeypatch.setenv("HOME", "/home/someone")
        monkeypatch.setenv("REDIS_PASSWORD", "$HOME")
        monkeypatch.delenv("DB_USER", raising=False)
        env = kms.KMSEnv()
        assert env.str("REDIS_PASSWORD") == "/home/someone"
        assert env.str("DB_USER", default="root") == "root"

    def test_raw_var_missing_falls_back(self, monkeypatch):
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        env = kms.KMSEnv({"REDIS_PASSWORD"})
        assert env.str("REDIS_PASSWORD", default="") == ""

    def test_dollar_default_returned_verbatim(self, monkeypatch):
        """默认值由凭证派生且以 $ 开头时（如 SECRET_KEY[:16]），不能解析为引用，否则会无限递归"""
        monkeypatch.delenv("BKMONITOR_BEARER_TOKEN", raising=False)
        env = kms.KMSEnv()
        assert env.get_value("BKMONITOR_BEARER_TOKEN", cast=str, default="$secret") == "$secret"
        assert env.get_value("BKMONITOR_BEARER_TOKEN", cast=int, default="7", parse_default=True) == 7

    def test_missing_without_default_raises(self, monkeypatch):
        monkeypatch.delenv("DB_USER", raising=False)
        with pytest.raises(ImproperlyConfigured, match="DB_USER"):
            kms.KMSEnv().str("DB_USER")
