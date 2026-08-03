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
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.dbm_aiagent.mcp_tools.common.impl import host_performance_query as mod
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportClusterTypeException


def _fake_cluster(cluster_type, cid=1, domain="example.db"):
    cluster = MagicMock()
    cluster.id = cid
    cluster.immute_domain = domain
    cluster.cluster_type = cluster_type
    return cluster


class TestQueryClusterRefHostPerf:
    @patch.object(mod, "_storage_host_row")
    @patch.object(mod, "_pick_tendbha_storage")
    def test_tendbha_storage_only(self, pick_storage, storage_row):
        cluster = _fake_cluster(ClusterType.TenDBHA, cid=10001, domain="tendbha.example.db")
        inst = MagicMock()
        pick_storage.return_value = inst
        storage_row.return_value = {
            "ref_role": InstanceRole.BACKEND_MASTER.value,
            "instance_count": 1,
            "ip": "127.0.0.2",
            "datadir": "/data1/mysqldata",
            "data_dir_mount": "/data1",
            "mount_point": "/data1",
            "performance_iops": 50000,
        }

        result = mod.query_cluster_ref_host_perf(cluster)

        assert result["cluster_id"] == 10001
        assert result["immute_domain"] == "tendbha.example.db"
        assert result["cluster_type"] == ClusterType.TenDBHA
        assert result["ref_shard_id"] is None
        assert result["spider_host"] is None
        assert result["storage_host"]["ref_role"] == "backend_master"
        assert result["storage_host"]["instance_count"] == 1
        assert result["storage_host"]["data_dir_mount"] == "/data1"
        storage_row.assert_called_once_with(inst, InstanceRole.BACKEND_MASTER.value)

    @patch.object(mod, "_storage_host_row")
    @patch.object(mod, "_spider_host_row")
    @patch.object(mod, "_pick_tc_storage")
    @patch.object(mod, "_pick_tc_spider")
    def test_tendbcluster_one_each(self, pick_spider, pick_storage, spider_row, storage_row):
        cluster = _fake_cluster(ClusterType.TenDBCluster, cid=21004525, domain="spider.example.db")
        spider_machine = MagicMock()
        storage_inst = MagicMock()
        pick_spider.return_value = spider_machine
        pick_storage.return_value = (storage_inst, 0)
        spider_row.return_value = {
            "ref_role": TenDBClusterSpiderRole.SPIDER_MASTER.value,
            "ip": "127.0.0.10",
            "bk_cloud_id": 0,
            "vcpu": 16,
            "memory_gb": 64,
        }
        storage_row.return_value = {
            "ref_role": InstanceRole.REMOTE_MASTER.value,
            "instance_count": 16,
            "ip": "127.0.0.20",
            "data_dir_mount": "/data1",
            "mount_point": "/data1",
            "performance_iops": 50000,
        }

        result = mod.query_cluster_ref_host_perf(cluster)

        assert result["ref_shard_id"] == 0
        assert result["spider_host"]["ref_role"] == "spider_master"
        assert result["spider_host"]["ip"] == "127.0.0.10"
        assert "machine" not in result["spider_host"]
        assert result["storage_host"]["ref_role"] == "remote_master"
        assert result["storage_host"]["instance_count"] == 16
        spider_row.assert_called_once_with(spider_machine, TenDBClusterSpiderRole.SPIDER_MASTER.value)
        storage_row.assert_called_once_with(storage_inst, InstanceRole.REMOTE_MASTER.value)

    def test_unsupported_cluster_type(self):
        cluster = _fake_cluster("redis")
        with pytest.raises(DBMMcpNotSupportClusterTypeException):
            mod.query_cluster_ref_host_perf(cluster)


class TestDatadirMountAndFlatten:
    def test_datadir_mount_fields(self):
        assert mod._datadir_mount_fields("/data1/mysqldata/data") == {
            "datadir": "/data1/mysqldata/data",
            "data_dir_mount": "/data1",
        }
        assert mod._datadir_mount_fields("")["data_dir_mount"] == ""

    def test_match_disk_by_mount(self):
        disks = [
            {"mount_point": "/data", "disk_type": "SSD", "size": 500, "baseline": None},
            {
                "mount_point": "/data1",
                "disk_type": "NVME_SSD",
                "size": 2000,
                "baseline": {"disk_name": "NVME-2000", "performance_iops": 100000},
            },
        ]
        matched = mod._match_disk_by_mount(disks, "/data1")
        assert matched["disk_type"] == "NVME_SSD"
        assert mod._match_disk_by_mount(disks, "/data2") is None

    @patch.object(mod.StorageInstance.objects, "filter")
    def test_flatten_storage_row(self, filter_qs):
        filter_qs.return_value.count.return_value = 16
        machine = MagicMock()
        perf = {
            "machine": {"ip": "127.0.0.20", "bk_cloud_id": 0, "bk_svr_device_cls_name": "S5"},
            "host_baseline": {
                "device_class": "S5",
                "cpu_model": "Xeon",
                "cpu_frequency_ghz": 2.5,
                "network_card_speed": "25G",
                "vcpu": 32,
                "memory_gb": 128,
                "network_pps_w": 500,
                "intranet_bandwidth_gbps": 25.0,
                "queue_count": 32,
            },
            "disks": [],
        }
        disk = {
            "mount_point": "/data1",
            "disk_type": "SSD",
            "size": 2000,
            "baseline": {
                "disk_name": "SSD-2000",
                "disk_type": "SSD",
                "capacity_gb": 2000,
                "performance_iops": 50000,
                "performance_throughput_mbps": 800,
                "random_read_iops": 45000,
                "sequential_write_throughput_mbps": 700,
                "write_latency_ms": 0.5,
            },
        }
        row = mod._flatten_storage_row(
            machine,
            InstanceRole.REMOTE_MASTER.value,
            perf,
            {"datadir": "/data1/mysqldata", "data_dir_mount": "/data1"},
            disk,
        )
        assert row["ip"] == "127.0.0.20"
        assert row["vcpu"] == 32
        assert row["memory_gb"] == 128
        assert row["datadir"] == "/data1/mysqldata"
        assert row["mount_point"] == "/data1"
        assert row["performance_iops"] == 50000
        assert row["instance_count"] == 16
        assert "machine" not in row
        assert "host_baseline" not in row
        assert "disks" not in row

    @patch.object(mod, "query_host_performance_for_machine")
    def test_spider_host_row_flat(self, query_perf):
        machine = MagicMock()
        query_perf.return_value = {
            "machine": {"ip": "127.0.0.10", "bk_cloud_id": 0, "bk_svr_device_cls_name": "S5"},
            "host_baseline": {
                "device_class": "S5",
                "cpu_model": "Xeon",
                "cpu_frequency_ghz": 2.5,
                "network_card_speed": "25G",
                "vcpu": 16,
                "memory_gb": 64,
                "network_pps_w": 300,
                "intranet_bandwidth_gbps": 10.0,
                "queue_count": 16,
            },
            "disks": [],
        }
        row = mod._spider_host_row(machine, TenDBClusterSpiderRole.SPIDER_MASTER.value)
        assert row["ref_role"] == "spider_master"
        assert row["ip"] == "127.0.0.10"
        assert row["vcpu"] == 16
        assert row["memory_gb"] == 64
        assert "instance_count" not in row
        assert "datadir" not in row
        assert "machine" not in row

    @patch.object(mod, "_flatten_storage_row")
    @patch.object(mod, "query_host_performance_for_machine")
    @patch.object(mod, "_query_inst_datadir")
    def test_storage_host_row_uses_datadir(self, query_datadir, query_perf, flatten):
        inst = MagicMock()
        inst.ip_port = "127.0.0.20:20000"
        inst.machine = MagicMock()
        inst.machine.bk_cloud_id = 0
        query_datadir.return_value = {"datadir": "/data1/mysqldata", "data_dir_mount": "/data1"}
        query_perf.return_value = {
            "machine": {"ip": "127.0.0.20"},
            "host_baseline": None,
            "disks": [{"mount_point": "/data1", "disk_type": "SSD", "size": 2000, "baseline": None}],
        }
        flatten.return_value = {"ip": "127.0.0.20", "mount_point": "/data1"}

        row = mod._storage_host_row(inst, InstanceRole.REMOTE_MASTER.value)

        assert row["mount_point"] == "/data1"
        query_datadir.assert_called_once_with(0, "127.0.0.20:20000")
        flatten.assert_called_once()
        matched_disk = flatten.call_args[0][4]
        assert matched_disk["mount_point"] == "/data1"
