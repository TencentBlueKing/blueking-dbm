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

# 在加载 settings 之前，从蓝鲸 KMS 信封中解密部署凭证。
#
# ENABLE_KMS 关闭时保持原有的环境变量读取行为；开启后所需凭证缺一不可，失败即停，不回退到旧密码。
# 解密结果写入当前进程的 os.environ，覆盖同名的旧值，不落地文件。
import json
import os
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, Tuple

import environ
from django.core.exceptions import ImproperlyConfigured

KMS_ENVELOPE_PATH = Path("/etc/secrets/bk-dbm-kms")
KMS_PRIVATE_KEY_ENV = "BK_DBM_KMS_PRIVATE_KEY"


def _credential_bindings() -> Dict[str, Tuple[str, ...]]:
    """环境变量名 -> 信封中的 JSON 路径"""
    bindings = {
        "APP_ID": ("bkapp_id_secret", "default", "app_code"),
        "APP_TOKEN": ("bkapp_id_secret", "default", "app_secret"),
        "DB_USER": ("mysql", "dbm", "username"),
        "DB_PASSWORD": ("mysql", "dbm", "password"),
        "REPORT_DB_USER": ("mysql", "dbmReport", "username"),
        "REPORT_DB_PASSWORD": ("mysql", "dbmReport", "password"),
        "STATS_DB_USER": ("mysql", "dbmStats", "username"),
        "STATS_DB_PASSWORD": ("mysql", "dbmStats", "password"),
        "DBM_STATSDB_USER": ("mysql", "dbmStats", "username"),
        "DBM_STATSDB_PASSWORD": ("mysql", "dbmStats", "password"),
        "REDIS_PASSWORD": ("redis", "default", "password"),
        "BKREPO_USERNAME": ("bkrepo", "default", "username"),
        "BKREPO_PASSWORD": ("bkrepo", "default", "password"),
        "BKM_DBM_TOKEN": ("bkmonitor", "default", "bkm_dbm_token"),
    }
    # 与 helm 渲染条件一致：externalKafka 开启 SASL 认证时才渲染 SECURITY_PROTOCOL，此时信封中必须有账号密码
    if os.environ.get("REVERSE_REPORT_KAFKA_BOOTSTRAP_SERVERS") and os.environ.get(
        "REVERSE_REPORT_KAFKA_SECURITY_PROTOCOL"
    ):
        bindings.update(
            {
                "REVERSE_REPORT_KAFKA_USERNAME": ("kafka", "default", "username"),
                "REVERSE_REPORT_KAFKA_PASSWORD": ("kafka", "default", "password"),
            }
        )
    return bindings


class KMSEnv(environ.Env):
    """KMS 写入的变量和默认值按原文读取，避免 django-environ 把 "$" 开头的值当作其他变量的引用"""

    def __init__(self, raw_vars: Iterable[str] = ()):
        super().__init__()
        self.raw_vars = frozenset(raw_vars)

    def get_value(self, var, cast=None, default=environ.Env.NOTSET, parse_default=False):
        if var in self.raw_vars and var in self.ENVIRON:
            return self.parse_value(self.ENVIRON[var], cast)
        if var not in self.ENVIRON and default is not self.NOTSET:
            # 默认值可能由凭证派生（如 SECRET_KEY[:16]），同样按原文返回，否则 "$" 开头时会无限递归
            return self.parse_value(default, cast) if parse_default and default else default
        return super().get_value(var, cast=cast, default=default, parse_default=parse_default)


def is_kms_enabled() -> bool:
    return os.environ.get("ENABLE_KMS") in ("true", "True")


def load_credentials() -> Dict[str, str]:
    if not is_kms_enabled():
        return {}

    private_key = os.environ.get(KMS_PRIVATE_KEY_ENV, "").strip()
    if not private_key:
        raise ImproperlyConfigured(f"KMS requires {KMS_PRIVATE_KEY_ENV}")

    try:
        from bk_kms import CryptoBackendUnavailableError, CryptoError, decrypt
    except ImportError:
        raise ImproperlyConfigured("KMS requires the bk-kms-sdk package") from None

    try:
        envelope = KMS_ENVELOPE_PATH.read_text(encoding="utf-8").strip()
        payload = json.loads(decrypt(envelope=envelope, private_key=private_key))
    except CryptoBackendUnavailableError:
        raise ImproperlyConfigured(
            "KMS SM2/SM4 crypto backend is unavailable; check the installed bk-kms-sdk[gm] dependencies"
        ) from None
    except (OSError, UnicodeError, ValueError, CryptoError):
        # 不透传 SDK / JSON 异常，避免错误信息中带出信封或明文
        raise ImproperlyConfigured("Unable to read or decrypt the KMS credential envelope") from None

    credentials = {}
    for name, path in _credential_bindings().items():
        value = payload
        for part in path:
            value = value.get(part) if isinstance(value, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise ImproperlyConfigured(f"KMS requires a non-empty string at {'.'.join(path)}")
        credentials[name] = value
    return credentials


def inject_credentials() -> FrozenSet[str]:
    """解密凭证并写入 os.environ，返回写入的变量名"""
    credentials = load_credentials()
    os.environ.update(credentials)
    return frozenset(credentials)
