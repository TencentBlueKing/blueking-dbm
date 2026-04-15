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
import re

_MAJOR_MINOR_RE = re.compile(r"^\d+\.\d+$")
_FULL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
_MONGODB_PREFIX = "mongodb-"


def normalize_mongodb_full_version(version: str) -> str:
    """Normalize to mongodb-<full_version> and validate format."""
    if not version:
        raise ValueError("version is empty")
    version = version.strip()
    # Cluster metadata may store "MongoDB-5.0.4"; strip prefix case-insensitively.
    if version.lower().startswith(_MONGODB_PREFIX):
        raw = version[len(_MONGODB_PREFIX) :]
    else:
        # Reject prefixed-but-not-mongodb values (e.g. percona-5.0.14), while
        # still allowing legal suffix forms like 5.0.14-rc1.
        _, has_sep, _ = version.partition("-")
        if has_sep and not _FULL_VERSION_RE.match(version):
            raise ValueError("invalid version prefix: {}".format(version))
        raw = version
    if _MAJOR_MINOR_RE.match(raw):
        raw = "{}.0".format(raw)
    if not _FULL_VERSION_RE.match(raw):
        raise ValueError("invalid full version: {}".format(version))
    return "mongodb-{}".format(raw)
