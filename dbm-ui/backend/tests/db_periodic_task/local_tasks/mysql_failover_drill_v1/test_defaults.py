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

"""新表的初始行只从旧配置抄，代码里不放业务号和城市名单。"""


class _Old(object):
    def __init__(self):
        self.bk_biz_id = 3
        self.bk_cloud_id = 0
        self.db_module_id = 9
        self.labels = ["drill"]
        self.city_map = {"city-a": "aa", "city-b": "bb"}
        self.switch_flag = True


def _rows(drill_defaults, old, extra=None):
    return drill_defaults.rows_from_old(old, extra)


def test_missing_old_config_inserts_nothing(drill_defaults):
    assert _rows(drill_defaults, None) == []


def test_empty_city_map_inserts_nothing(drill_defaults):
    old = _Old()
    old.city_map = {}
    assert _rows(drill_defaults, old) == []


def test_v1_v2_old_config_makes_one_row_per_version(drill_defaults):
    old = _Old()
    old.version = "v1,v2"
    rows = _rows(drill_defaults, old)
    assert [(row["city"], row["version"]) for row in rows] == [
        ("city-a", "v1"),
        ("city-a", "v2"),
        ("city-b", "v1"),
        ("city-b", "v2"),
    ]


def test_rows_copy_biz_module_labels_and_abbr(drill_defaults):
    rows = _rows(drill_defaults, _Old())
    assert [row["city"] for row in rows] == ["city-a", "city-b"]
    assert rows[0]["city_abbr"] == "aa"
    assert rows[0]["bk_biz_id"] == 3
    assert rows[0]["bk_cloud_id"] == 0
    assert rows[0]["db_module_id"] == 9
    assert rows[0]["labels"] == ["drill"]
    assert rows[0]["enabled"] is False


def test_blank_city_and_default_are_skipped(drill_defaults):
    old = _Old()
    old.city_map = {"": "x", "  ": "y", "default": "d", "city-a": "aa"}
    assert [row["city"] for row in _rows(drill_defaults, old)] == ["city-a"]


def test_non_list_labels_become_empty(drill_defaults):
    old = _Old()
    old.labels = {"k": "v"}
    assert _rows(drill_defaults, old)[0]["labels"] == []


def test_extra_fields_are_copied_onto_each_row(drill_defaults):
    rows = _rows(drill_defaults, _Old(), {"start_proxy_port": 25000})
    assert rows[0]["start_proxy_port"] == 25000
    assert rows[1]["start_proxy_port"] == 25000
    assert rows[0]["enabled"] is False


def test_each_row_gets_its_own_labels_list(drill_defaults):
    rows = _rows(drill_defaults, _Old())
    rows[0]["labels"].append("extra")
    assert rows[1]["labels"] == ["drill"]
