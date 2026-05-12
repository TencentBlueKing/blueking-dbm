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
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.configuration.constants import AffinityEnum
from backend.db_report.enums import ReportStateType

pytestmark = pytest.mark.django_db


class TestCheckAffinityRules:
    def test_normal_for_cross_subzone_with_consistent_zone_list(self, check_affinity_module):
        ret = check_affinity_module.CheckMongodbAffinityTask().check_affinity_rules(
            disaster_tolerance_level=AffinityEnum.CROS_SUBZONE,
            zone_list={"1", "2"},
            actual_sub_zone_set={"1", "2"},
            actual_region_set={"南京"},
            actual_rack_set={"11", "12"},
            component_nodes=[
                {"actual_sub_zone": "1", "actual_rack": "11"},
                {"actual_sub_zone": "2", "actual_rack": "12"},
            ],
            cluster_region="南京",
        )
        assert ret["state"] == ReportStateType.NORMAL.value
        assert ret["msg"] == ""

    def test_zone_list_mismatch_returns_abnormal(self, check_affinity_module):
        ret = check_affinity_module.CheckMongodbAffinityTask().check_affinity_rules(
            disaster_tolerance_level=AffinityEnum.CROS_SUBZONE,
            zone_list={"1", "2"},
            actual_sub_zone_set={"1", "3"},
            actual_region_set={"南京"},
            actual_rack_set={"11", "12"},
            component_nodes=[
                {"actual_sub_zone": "1", "actual_rack": "11"},
                {"actual_sub_zone": "3", "actual_rack": "12"},
            ],
            cluster_region="南京",
        )
        assert ret["state"] == ReportStateType.ABNORMAL.value
        assert "zone_list mismatch" in ret["msg"]

    def test_same_subzone_cross_switch_requires_two_racks(self, check_affinity_module):
        ret = check_affinity_module.CheckMongodbAffinityTask().check_affinity_rules(
            disaster_tolerance_level=AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
            zone_list={"1"},
            actual_sub_zone_set={"1", "2"},
            actual_region_set={"南京"},
            actual_rack_set={"11", "99"},
            component_nodes=[
                {"actual_sub_zone": "1", "actual_rack": "11", "instance_role": "MONGO_DATA"},
                {"actual_sub_zone": "2", "actual_rack": "99", "instance_role": "MONGO_BACKUP"},
            ],
            cluster_region="南京",
        )
        assert ret["state"] == ReportStateType.ABNORMAL.value
        assert "at least 2 racks for non-backup nodes" in ret["msg"]

    def test_same_subzone_cross_switch_allows_backup_outside_zone(self, check_affinity_module):
        ret = check_affinity_module.CheckMongodbAffinityTask().check_affinity_rules(
            disaster_tolerance_level=AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
            zone_list={"1"},
            actual_sub_zone_set={"1", "2"},
            actual_region_set={"南京"},
            actual_rack_set={"11", "12", "99"},
            component_nodes=[
                {"actual_sub_zone": "1", "actual_rack": "11", "instance_role": "MONGO_DATA"},
                {"actual_sub_zone": "1", "actual_rack": "12", "instance_role": "MONGO_DATA"},
                {"actual_sub_zone": "2", "actual_rack": "99", "instance_role": "MONGO_BACKUP"},
            ],
            cluster_region="南京",
        )
        assert ret["state"] == ReportStateType.NORMAL.value

    def test_cross_subzone_weak_allows_empty_zone_list(self, check_affinity_module):
        ret = check_affinity_module.CheckMongodbAffinityTask().check_affinity_rules(
            disaster_tolerance_level=AffinityEnum.CROSS_SUBZONE_WEAK,
            zone_list=set(),
            actual_sub_zone_set={"1", "2"},
            actual_region_set={"南京"},
            actual_rack_set={"11", "12"},
            component_nodes=[
                {"actual_sub_zone": "1", "actual_rack": "11"},
                {"actual_sub_zone": "2", "actual_rack": "12"},
            ],
            cluster_region="南京",
        )
        assert ret["state"] == ReportStateType.NORMAL.value
        assert ret["msg"] == ""


class TestTopologyHelpers:
    def test_normalize_to_str_set(self, check_affinity_module):
        assert check_affinity_module.normalize_to_str_set([1, "2", None, ""]) == {"1", "2"}

    def test_collect_topology_with_missing_machine(self, check_affinity_module):
        nodes = [SimpleNamespace(ip="127.0.0.1", port=27017, bk_cloud_id=0, set_name="rs0")]
        with patch(
            "backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity.Machine.objects.filter"
        ) as machine_filter:
            machine_filter.return_value.values.return_value = []
            ret = check_affinity_module.collect_topology_by_set(nodes)
        assert ret["rs0"]["missing_messages"][0]["msg"] == "machine not found in db_meta"

    def test_collect_topology_merge_shardsvr_by_machine_group(self, check_affinity_module):
        nodes = [
            SimpleNamespace(ip="127.0.0.1", port=27017, bk_cloud_id=0, set_name="shard0", instance_role="m1"),
            SimpleNamespace(ip="127.0.0.2", port=27017, bk_cloud_id=0, set_name="shard0", instance_role="m2"),
            SimpleNamespace(ip="127.0.0.1", port=37017, bk_cloud_id=0, set_name="shard1", instance_role="m1"),
            SimpleNamespace(ip="127.0.0.2", port=37017, bk_cloud_id=0, set_name="shard1", instance_role="m2"),
            SimpleNamespace(ip="127.0.0.3", port=50000, bk_cloud_id=0, set_name="mongos", instance_role=""),
        ]
        machine_rows = [
            {"ip": "127.0.0.1", "bk_sub_zone_id": "1", "bk_rack_id": "11", "bk_cloud_id": 0},
            {"ip": "127.0.0.2", "bk_sub_zone_id": "1", "bk_rack_id": "12", "bk_cloud_id": 0},
            {"ip": "127.0.0.3", "bk_sub_zone_id": "2", "bk_rack_id": "21", "bk_cloud_id": 0},
        ]
        with patch(
            "backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity.Machine.objects.filter"
        ) as machine_filter:
            machine_filter.return_value.values.return_value = machine_rows
            ret = check_affinity_module.collect_topology_by_set(nodes, is_sharded_cluster=True)

        shard_keys = [key for key in ret if key.startswith("shardsvr_group:")]
        assert len(shard_keys) == 1
        # 同机多分片合并后按机器去重，2 台机器 => 2 条节点
        assert len(ret[shard_keys[0]]["nodes"]) == 2
        assert "mongos" in ret
