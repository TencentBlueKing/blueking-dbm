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
from backend.dbm_aiagent.mcp_tools.common.views import dbmeta_query as mod


class TestStorageCapacityRangeContains:
    def test_single_data_within_range(self):
        assert mod._storage_capacity_range_contains([{"mount_point": "/data", "min": 100, "max": 1000}], 500) is True

    def test_single_data_below_range(self):
        assert mod._storage_capacity_range_contains([{"mount_point": "/data", "min": 100, "max": 1000}], 50) is False

    def test_single_data_above_range(self):
        assert mod._storage_capacity_range_contains([{"mount_point": "/data", "min": 100, "max": 1000}], 2000) is False

    def test_multi_disk_only_match_data(self):
        storage_spec = [
            {"mount_point": "/data", "min": 100, "max": 500},
            {"mount_point": "/data1", "min": 500, "max": 1000},
        ]
        # 800 超出 /data 的 max，虽在 /data1 范围内，仍不匹配
        assert mod._storage_capacity_range_contains(storage_spec, 800) is False
        assert mod._storage_capacity_range_contains(storage_spec, 300) is True

    def test_no_data_mount(self):
        assert mod._storage_capacity_range_contains([{"mount_point": "/data1", "min": 100, "max": 1000}], 500) is False

    def test_empty_list(self):
        assert mod._storage_capacity_range_contains([], 500) is False

    def test_none(self):
        assert mod._storage_capacity_range_contains(None, 500) is False

    def test_dict_instead_of_list(self):
        # 历史脏数据：storage_spec 为 dict 而非 list，应安全返回 False 而非抛异常
        assert mod._storage_capacity_range_contains({"mount_point": "/data", "min": 100, "max": 1000}, 500) is False
