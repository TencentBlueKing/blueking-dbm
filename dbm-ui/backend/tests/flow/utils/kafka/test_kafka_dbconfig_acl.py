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
# 校验9个kafka dbconfig版本模板的authorizer.class.name取值：ZK模式(2.4.0之前)用老包名
# kafka.security.auth.SimpleAclAuthorizer，2.4.0~3.8.0用kafka.security.authorizer.AclAuthorizer，
# KRaft模式(4.1.0)用org.apache.kafka.metadata.authorizer.StandardAuthorizer——三者不能混，
# 用错版本会导致对应broker/controller在启动时找不到authorizer类，直接起不来。
import json
from pathlib import Path

import pytest

_DBCONF_ROOT = Path(__file__).resolve().parents[4] / "components" / "dbconfig" / "migrations" / "kafka" / "dbconf"

_SIMPLE_ACL_AUTHORIZER = "kafka.security.auth.SimpleAclAuthorizer"
_ACL_AUTHORIZER = "kafka.security.authorizer.AclAuthorizer"
_STANDARD_AUTHORIZER = "org.apache.kafka.metadata.authorizer.StandardAuthorizer"

_EXPECTED_AUTHORIZER_BY_VERSION = {
    "1.1.1": _SIMPLE_ACL_AUTHORIZER,
    "2.1.1": _SIMPLE_ACL_AUTHORIZER,
    "2.3.1": _SIMPLE_ACL_AUTHORIZER,
    "2.4.0": _ACL_AUTHORIZER,
    "2.4.bkbase": _ACL_AUTHORIZER,
    "2.8.2": _ACL_AUTHORIZER,
    "3.8.0": _ACL_AUTHORIZER,
    "4.1.0": _STANDARD_AUTHORIZER,
}


def _conf_items_by_name(version: str) -> dict:
    file_def = json.loads((_DBCONF_ROOT / f"{version}.json").read_text(encoding="utf-8"))
    return {item["conf_name"]: item for item in file_def}


class TestKafkaAclDbConfigTemplates:
    @pytest.mark.parametrize("version, expected_authorizer", list(_EXPECTED_AUTHORIZER_BY_VERSION.items()))
    def test_authorizer_class_name_matches_version(self, version, expected_authorizer):
        items = _conf_items_by_name(version)
        assert items["authorizer.class.name"]["value_default"] == expected_authorizer

    @pytest.mark.parametrize("version", list(_EXPECTED_AUTHORIZER_BY_VERSION.keys()))
    def test_super_users_renders_username_placeholder(self, version):
        items = _conf_items_by_name(version)
        assert items["super.users"]["value_default"] == "User:{{.Username}};User:kafka"

    @pytest.mark.parametrize("version", list(_EXPECTED_AUTHORIZER_BY_VERSION.keys()))
    def test_allow_everyone_if_no_acl_found_defaults_to_deny(self, version):
        items = _conf_items_by_name(version)
        assert items["allow.everyone.if.no.acl.found"]["value_default"] == "false"
