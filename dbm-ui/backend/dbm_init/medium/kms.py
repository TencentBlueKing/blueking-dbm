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

# dbmedium 镜像独立运行，读不到 dbm 的 blueking.kms，这里保留一份只覆盖本脚本所需凭证的精简实现，约定与 blueking.kms 一致。
import json
import os
from pathlib import Path
from typing import Dict

KMS_ENVELOPE_PATH = Path("/etc/secrets/bk-dbm-kms")
KMS_PRIVATE_KEY_ENV = "BK_DBM_KMS_PRIVATE_KEY"

# 环境变量名 -> 信封中的 JSON 路径
CREDENTIAL_BINDINGS = {
    "APP_CODE": ("bkapp_id_secret", "default", "app_code"),
    "APP_TOKEN": ("bkapp_id_secret", "default", "app_secret"),
    "BKREPO_USERNAME": ("bkrepo", "default", "username"),
    "BKREPO_PASSWORD": ("bkrepo", "default", "password"),
}


class KMSConfigError(RuntimeError):
    pass


def is_kms_enabled() -> bool:
    return os.environ.get("ENABLE_KMS") in ("true", "True")


def load_credentials() -> Dict[str, str]:
    if not is_kms_enabled():
        return {}

    private_key = os.environ.get(KMS_PRIVATE_KEY_ENV, "").strip()
    if not private_key:
        raise KMSConfigError(f"KMS requires {KMS_PRIVATE_KEY_ENV}")

    try:
        from bk_kms import CryptoBackendUnavailableError, CryptoError, decrypt
    except ImportError:
        raise KMSConfigError("KMS requires the bk-kms-sdk package") from None

    try:
        envelope = KMS_ENVELOPE_PATH.read_text(encoding="utf-8").strip()
        payload = json.loads(decrypt(envelope=envelope, private_key=private_key))
    except CryptoBackendUnavailableError:
        raise KMSConfigError(
            "KMS SM2/SM4 crypto backend is unavailable; check the installed bk-kms-sdk[gm] dependencies"
        ) from None
    except (OSError, UnicodeError, ValueError, CryptoError):
        # 不透传 SDK / JSON 异常，避免错误信息中带出信封或明文
        raise KMSConfigError("Unable to read or decrypt the KMS credential envelope") from None

    credentials = {}
    for name, path in CREDENTIAL_BINDINGS.items():
        value = payload
        for part in path:
            value = value.get(part) if isinstance(value, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise KMSConfigError(f"KMS requires a non-empty string at {'.'.join(path)}")
        credentials[name] = value
    return credentials


def inject_credentials() -> None:
    """解密凭证并写入 os.environ，KMS 关闭时不做任何事"""
    os.environ.update(load_credentials())
