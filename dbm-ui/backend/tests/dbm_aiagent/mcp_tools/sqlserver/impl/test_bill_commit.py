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

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.helper import check_master_clusters_consistency

MODULE_CLUSTER_MIGRATE = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_cluster_migrate"
MODULE_HOST_MIGRATE = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_host_migrate"
MODULE_MASTER_SLAVE_SWITCH = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_master_slave_switch"
MODULE_RESTORE_LOCAL_SLAVE = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_restore_local_slave"
MODULE_RESTORE_SLAVE = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_restore_slave"
MODULE_BACKUP_DBS = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_backup_dbs"


def _qs(ids):
    qs = MagicMock()
    qs.values_list.return_value = list(ids)
    return qs


def _master(cluster_ids):
    master = MagicMock()
    master.cluster.values_list.return_value = list(cluster_ids)
    return master


def _cluster(domain="sqlserver-ha-1.test.db", cluster_id=1, bk_cloud_id=0):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.id = cluster_id
    cluster.pk = cluster_id
    cluster.bk_cloud_id = bk_cloud_id
    return cluster


class TestCheckMasterClustersConsistency:
    """主从互切等价一致性校验：master 归属集群集合必须与输入集群集合完全一致（不能只比数量或只做包含校验）"""

    def test_equal_clusters_pass(self):
        check_master_clusters_consistency(_qs([1, 2]), "1.1.1.1", [_master([1]), _master([2])])

    def test_missing_cluster_raises(self):
        # master 只归属集群 1，输入为 [1,2]，数量不同但此处重点是集合不等
        with pytest.raises(Exception, match="不一致"):
            check_master_clusters_consistency(_qs([1, 2]), "1.1.1.1", [_master([1])])

    def test_extra_cluster_raises(self):
        # 输入集合是 master 归属集合的子集（包含校验也会放行），必须因不等而拒绝
        with pytest.raises(Exception, match="不一致"):
            check_master_clusters_consistency(_qs([1, 2]), "1.1.1.1", [_master([1]), _master([2]), _master([3])])


class TestSqlserverClusterMigrate:
    """SQLServer 集群迁移：成功提单路径"""

    @patch(f"{MODULE_CLUSTER_MIGRATE}.find_duplicate_ticket")
    @patch(f"{MODULE_CLUSTER_MIGRATE}.SQLServerClusterMigrateDetailSerializer")
    @patch(f"{MODULE_CLUSTER_MIGRATE}.Ticket")
    @patch(f"{MODULE_CLUSTER_MIGRATE}.validate_sqlserver_specs")
    @patch(f"{MODULE_CLUSTER_MIGRATE}.validate_sqlserver_ha_clusters")
    def test_success_path(self, mock_validate_clusters, mock_validate_specs, mock_ticket, mock_serializer, mock_dedup):
        from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_cluster_migrate import (
            bill_sqlserver_cluster_migrate,
        )
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate_clusters.return_value = ([cluster], 1, 0)
        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 5, "count": 2, "labels": ["1"]}]
        result = bill_sqlserver_cluster_migrate("admin", infos)

        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_ids"] == [1]
        assert info["resource_spec"]["backend_group"]["spec_id"] == 5
        assert info["resource_spec"]["backend_group"]["count"] == 2
        assert info["resource_spec"]["backend_group"]["labels"] == ["1"]


class TestSqlserverHostMigrate:
    """SQLServer 整机迁移：源主机承载集群与输入集群的等价一致性校验"""

    @patch(f"{MODULE_HOST_MIGRATE}.StorageInstance")
    @patch(f"{MODULE_HOST_MIGRATE}.Machine")
    @patch(f"{MODULE_HOST_MIGRATE}.validate_sqlserver_specs")
    @patch(f"{MODULE_HOST_MIGRATE}.validate_sqlserver_ha_clusters")
    def test_machine_cluster_mismatch_raises(
        self, mock_validate_clusters, mock_validate_specs, mock_machine, mock_storage
    ):
        from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_host_migrate import (
            bill_sqlserver_host_migrate,
        )

        c1 = _cluster("sqlserver-ha-1.test.db", 1)
        c2 = _cluster("sqlserver-ha-2.test.db", 2)
        mock_validate_clusters.return_value = ([c1, c2], 1, 0)

        machine = MagicMock()
        machine.ip = "1.1.1.1"
        machine.bk_cloud_id = 0
        machine.bk_host_id = 10001
        mock_machine.objects.filter.return_value.first.return_value = machine

        # 机器实际只承载集群 1，与输入 [1,2] 不一致（等价校验必须拒绝，而非只做包含校验）
        mock_storage.objects.filter.return_value.values_list.return_value.distinct.return_value = [1]

        infos = [
            {
                "cluster_domains": ["sqlserver-ha-1.test.db", "sqlserver-ha-2.test.db"],
                "ip": "1.1.1.1",
                "spec_id": 5,
            }
        ]
        with pytest.raises(Exception, match="不一致"):
            bill_sqlserver_host_migrate("admin", infos)


class TestSqlserverMasterSlaveSwitch:
    """SQLServer 主从互切：成功提单路径"""

    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.find_duplicate_ticket")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.SQLServerMasterSlaveSwitchDetailSerializer")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.Ticket")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.Machine")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.StorageInstanceTuple")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.StorageInstance")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.check_master_clusters_consistency")
    @patch(f"{MODULE_MASTER_SLAVE_SWITCH}.validate_sqlserver_ha_clusters")
    def test_success_path(
        self,
        mock_validate_clusters,
        mock_check,
        mock_storage,
        mock_tuple,
        mock_machine,
        mock_ticket,
        mock_serializer,
        mock_dedup,
    ):
        from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_master_slave_switch import (
            bill_sqlserver_master_slave_switch,
        )
        from backend.ticket.models import Ticket

        cluster_objs = _qs([1, 2])
        mock_validate_clusters.return_value = (cluster_objs, 1, 0)

        tuple_obj = MagicMock()
        tuple_obj.receiver.machine.ip = "2.2.2.2"
        mock_tuple.objects.filter.return_value = [tuple_obj]

        master_machine = MagicMock()
        master_machine.ip = "1.1.1.1"
        master_machine.bk_host_id = 10001
        slave_machine = MagicMock()
        slave_machine.ip = "2.2.2.2"
        slave_machine.bk_host_id = 20002
        mock_machine.objects.get.side_effect = [master_machine, slave_machine]

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_sqlserver_master_slave_switch("admin", ["sqlserver-ha-1.test.db"], ["1.1.1.1"])

        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["master"]["ip"] == "1.1.1.1"
        assert info["slave"]["ip"] == "2.2.2.2"
        assert info["cluster_ids"] == [1, 2]


class TestSqlserverRestoreLocalSlave:
    """SQLServer 原地重建：成功提单路径"""

    @patch(f"{MODULE_RESTORE_LOCAL_SLAVE}.find_duplicate_ticket")
    @patch(f"{MODULE_RESTORE_LOCAL_SLAVE}.SQLServerRestoreLocalSlaveDetailSerializer")
    @patch(f"{MODULE_RESTORE_LOCAL_SLAVE}.Ticket")
    @patch(f"{MODULE_RESTORE_LOCAL_SLAVE}.StorageInstance")
    @patch(f"{MODULE_RESTORE_LOCAL_SLAVE}.validate_sqlserver_ha_clusters")
    def test_success_path(self, mock_validate_clusters, mock_storage, mock_ticket, mock_serializer, mock_dedup):
        from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_restore_local_slave import (
            bill_sqlserver_restore_local_slave,
        )
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate_clusters.return_value = ([cluster], 1, 0)

        slave = MagicMock()
        slave.port = 1433
        slave.machine.bk_host_id = 10001
        mock_storage.objects.filter.return_value.select_related.return_value.first.return_value = slave

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_sqlserver_restore_local_slave("admin", "sqlserver-ha-1.test.db", ["1.1.1.1"])

        assert result[0]["bill_id"] == 123
        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_id"] == 1
        assert info["slave"]["ip"] == "1.1.1.1"
        assert info["slave"]["port"] == 1433
        assert info["slave"]["bk_host_id"] == 10001


class TestSqlserverRestoreSlave:
    """SQLServer 新机重建：成功提单路径"""

    @patch(f"{MODULE_RESTORE_SLAVE}.find_duplicate_ticket")
    @patch(f"{MODULE_RESTORE_SLAVE}.SQLServerRestoreSlaveDetailSerializer")
    @patch(f"{MODULE_RESTORE_SLAVE}.Ticket")
    @patch(f"{MODULE_RESTORE_SLAVE}.StorageInstance")
    @patch(f"{MODULE_RESTORE_SLAVE}.validate_sqlserver_specs")
    @patch(f"{MODULE_RESTORE_SLAVE}.validate_sqlserver_ha_clusters")
    def test_success_path(
        self, mock_validate_clusters, mock_validate_specs, mock_storage, mock_ticket, mock_serializer, mock_dedup
    ):
        from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_restore_slave import (
            bill_sqlserver_restore_slave,
        )
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate_clusters.return_value = ([cluster], 1, 0)

        slave = MagicMock()
        slave.machine.bk_host_id = 10001
        mock_storage.objects.filter.return_value.select_related.return_value.first.return_value = slave

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_sqlserver_restore_slave("admin", "sqlserver-ha-1.test.db", ["1.1.1.1"], spec_id=5, labels=["1"])

        assert result[0]["bill_id"] == 123
        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_ids"] == [1]
        assert info["old_nodes"]["old_slave_host"][0]["ip"] == "1.1.1.1"
        assert info["old_nodes"]["old_slave_host"][0]["bk_host_id"] == 10001
        assert info["resource_spec"]["sqlserver_ha"]["spec_id"] == 5


class TestSqlserverBackupDbs:
    """SQLServer 库表备份：成功提单路径"""

    @patch(f"{MODULE_BACKUP_DBS}.find_duplicate_ticket")
    @patch(f"{MODULE_BACKUP_DBS}.SQLServerBackupDetailSerializer")
    @patch(f"{MODULE_BACKUP_DBS}.Ticket")
    @patch(f"{MODULE_BACKUP_DBS}.Cluster")
    def test_success_path(self, mock_cluster, mock_ticket, mock_serializer, mock_dedup):
        from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_backup_dbs import bill_sqlserver_backup_dbs
        from backend.ticket.models import Ticket

        cluster = _cluster()
        cluster.cluster_type = ClusterType.SqlserverHA.value
        mock_cluster.objects.filter.return_value.first.return_value = cluster

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_sqlserver_backup_dbs("admin", 1, "sqlserver-ha-1.test.db", backup_dbs=["db1", "db2"])

        assert result[0]["bill_id"] == 123
        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        assert details["infos"][0]["cluster_id"] == 1
        assert details["infos"][0]["backup_dbs"] == ["db1", "db2"]
