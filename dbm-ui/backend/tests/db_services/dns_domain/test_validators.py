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

import pytest

from backend.db_services.dns_domain.format import (
    as_instances,
    clamp_page_size,
    display_record,
    format_managers,
    normalize_domain,
    page_from_limit_offset,
)
from backend.db_services.dns_domain.validators import validate_domain, validate_ips, validate_owners, validate_remark
from backend.exceptions import ValidationError


class TestDnsDomainValidators:
    def test_normalize_and_validate_domain(self):
        assert validate_domain("API.Game.DB.") == "api.game.db"

    def test_reject_domain_without_suffix(self):
        with pytest.raises(ValidationError):
            validate_domain("api.game.com")

    def test_reject_invalid_label(self):
        with pytest.raises(ValidationError):
            validate_domain("-api.db")

    def test_reject_domain_outside_label_count(self):
        with pytest.raises(ValidationError):
            validate_domain("api.db")
        with pytest.raises(ValidationError):
            validate_domain("a.b.c.d.e.f.g.h.i.db")

    def test_dedupe_ips(self):
        assert validate_ips(["127.0.0.1", "127.0.0.1", "127.0.0.2"]) == ["127.0.0.1", "127.0.0.2"]

    def test_reject_bad_ip(self):
        with pytest.raises(ValidationError):
            validate_ips(["127.0.0.1:3306"])

    def test_owners_keep_at_least_one(self):
        with pytest.raises(ValidationError):
            validate_owners(["", " "])
        assert validate_owners(["alice", "alice", "bob"]) == ["alice", "bob"]

    def test_remark_length(self):
        assert validate_remark("  note ") == "note"
        with pytest.raises(ValidationError):
            validate_remark("a" * 501)

    def test_display_record(self):
        assert display_record({"ip": "127.0.0.8", "port": 0}) == "127.0.0.8"
        assert display_record({"ip": "127.0.0.1", "port": 3306}) == "127.0.0.1:3306"
        assert normalize_domain("Foo.DB.") == "foo.db"

    def test_format_managers_and_instances(self):
        assert format_managers(["zhangsan", " zhangsan ", "lisi"]) == "zhangsan,lisi"
        assert format_managers(["zhangsan, lisi"]) == "zhangsan,lisi"
        assert as_instances(["1.1.1.1", "1.1.1.2#3306"]) == ["1.1.1.1#0", "1.1.1.2#3306"]

    def test_page_size_stays_inside_dns_api_range(self):
        assert clamp_page_size(0) == 20
        assert clamp_page_size(-1) == 1000
        assert clamp_page_size(1001) == 1000
        assert page_from_limit_offset(20, 40) == (3, 20)
