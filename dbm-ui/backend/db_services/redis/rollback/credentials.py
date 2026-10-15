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
import hashlib
import hmac

from django.conf import settings

TEMP_PASSWORD_PREFIX = "restored_"
# 128 bits of the digest. Task records keep the base64 repr of the password in a varchar(128).
TEMP_PASSWORD_DIGEST_CHARS = 32

# Proxy config keys holding a password, for both twemproxy and predixy.
PROXY_PASSWORD_KEYS = ("password", "redis_password", "redis_proxy_admin_password")


def rollback_temp_password(source: str, plan_id) -> str:
    """Password of a temp instance or proxy, standing in for the source cluster's ``source``.

    Not stored in the password service: every node of the flow derives it again from the source
    and the plan. Keyed by SECRET_KEY so it reveals nothing of the source, and salted by the plan
    so two temp clusters of one source do not share a password.
    """
    if not plan_id:
        raise ValueError("rollback temp password needs the plan id")
    message = "{}\n{}".format(plan_id, source or "").encode("utf-8")
    digest = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return TEMP_PASSWORD_PREFIX + digest[:TEMP_PASSWORD_DIGEST_CHARS]


def with_temp_passwords(config: dict, plan_id, keys=PROXY_PASSWORD_KEYS) -> dict:
    """A copy of config with every present password key derived."""
    config = dict(config)
    for key in keys:
        if config.get(key):
            config[key] = rollback_temp_password(config[key], plan_id)
    return config
