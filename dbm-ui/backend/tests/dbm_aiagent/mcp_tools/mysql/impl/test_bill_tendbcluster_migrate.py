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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_migrate import (
    bill_tendbcluster_migrate,
)

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_migrate"


def _cluster(domain="test.tendbcluster.db", cluster_id=1):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.id = cluster_id
    return cluster


def _instance(bk_host_id):
    inst = MagicMock()
    inst.machine.bk_host_id = bk_host_id
    return inst


def _mock_storage_first(mock_storage, master_inst, slave_inst):
    """让 StorageInstance 的两次 filter 查询（master/slave）分别返回对应实例的 first()"""

    def filter_side_effect(**kwargs):
        qs = MagicMock()
        if kwargs.get("instance_inner_role") == "master":
            qs.select_related.return_value.first.return_value = master_inst
        elif kwargs.get("instance_inner_role") == "slave":
            qs.select_related.return_value.first.return_value = slave_inst
        return qs

    mock_storage.objects.using.return_value.filter.side_effect = filter_side_effect


class TestTendbClusterMigrateEarlyValidation:
    """TenDBCluster 主从迁移：靠前的纯逻辑校验分支（空 infos、重复集群、目标规格）"""

    def test_empty_infos_raises(self):
        with pytest.raises(Exception, match="infos 不能为空"):
            bill_tendbcluster_migrate("admin", [])

    def test_duplicate_cluster_raises(self):
        infos = [
            {
                "cluster_domain": "dup.tendbcluster.db",
                "old_master_ip": "1.1.1.1",
                "old_slave_ip": "2.2.2.2",
                "spec_id": 1,
            },
            {
                "cluster_domain": "dup.tendbcluster.db",
                "old_master_ip": "3.3.3.3",
                "old_slave_ip": "4.4.4.4",
                "spec_id": 2,
            },
        ]
        with pytest.raises(Exception, match="存在重复集群"):
            bill_tendbcluster_migrate("admin", infos)

    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_spec_not_found_raises(self, mock_validate, mock_spec):
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 0
        mock_spec.objects.filter.return_value.values_list.return_value = []

        infos = [
            {
                "cluster_domain": cluster.immute_domain,
                "old_master_ip": "1.1.1.1",
                "old_slave_ip": "2.2.2.2",
                "spec_id": 999,
            }
        ]
        with pytest.raises(Exception, match="目标规格不存在或未启用"):
            bill_tendbcluster_migrate("admin", infos)


class TestTendbClusterMigrateInstanceValidation:
    """TenDBCluster 主从迁移：依赖实例反查的校验分支（master/slave IP 归属）"""

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_master_not_found_raises(self, mock_validate, mock_spec, mock_storage):
        """old_master_ip 不是集群 remote master 时报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        _mock_storage_first(mock_storage, master_inst=None, slave_inst=_instance(20002))

        infos = [
            {
                "cluster_domain": cluster.immute_domain,
                "old_master_ip": "1.1.1.1",
                "old_slave_ip": "2.2.2.2",
                "spec_id": 5,
            }
        ]
        with pytest.raises(Exception, match="不是集群 .* 的 remote master"):
            bill_tendbcluster_migrate("admin", infos)

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_slave_not_found_raises(self, mock_validate, mock_spec, mock_storage):
        """old_slave_ip 不是集群 remote slave 时报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        _mock_storage_first(mock_storage, master_inst=_instance(10001), slave_inst=None)

        infos = [
            {
                "cluster_domain": cluster.immute_domain,
                "old_master_ip": "1.1.1.1",
                "old_slave_ip": "2.2.2.2",
                "spec_id": 5,
            }
        ]
        with pytest.raises(Exception, match="不是集群 .* 的 remote slave"):
            bill_tendbcluster_migrate("admin", infos)


class TestTendbClusterMigrateSuccessPath:
    """TenDBCluster 主从迁移：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TendbClusterMigrateClusterDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_spec, mock_storage, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        _mock_storage_first(mock_storage, master_inst=_instance(10001), slave_inst=_instance(20002))

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        infos = [
            {
                "cluster_domain": cluster.immute_domain,
                "old_master_ip": "1.1.1.1",
                "old_slave_ip": "2.2.2.2",
                "spec_id": 5,
                "count": 2,
                "labels": ["1"],
            }
        ]
        result = bill_tendbcluster_migrate("admin", infos)

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_id"] == cluster.id
        assert info["old_nodes"]["old_master"][0]["ip"] == "1.1.1.1"
        assert info["old_nodes"]["old_master"][0]["bk_host_id"] == 10001
        assert info["old_nodes"]["old_slave"][0]["ip"] == "2.2.2.2"
        assert info["old_nodes"]["old_slave"][0]["bk_host_id"] == 20002
        assert info["resource_spec"]["backend_group"]["count"] == 2
        assert info["resource_spec"]["backend_group"]["spec_id"] == 5
        assert info["resource_spec"]["backend_group"]["labels"] == ["1"]


class TestTendbClusterMigrateDuplicate:
    """TenDBCluster 主从迁移：防重路径（命中已有单据时直接复用，不再创建）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TendbClusterMigrateClusterDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_duplicate_returns_existing(
        self, mock_validate, mock_spec, mock_storage, mock_ticket, mock_serializer, mock_dedup
    ):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        _mock_storage_first(mock_storage, master_inst=_instance(10001), slave_inst=_instance(20002))

        mock_dedup.return_value = Ticket(id=999)

        infos = [
            {
                "cluster_domain": cluster.immute_domain,
                "old_master_ip": "1.1.1.1",
                "old_slave_ip": "2.2.2.2",
                "spec_id": 5,
            }
        ]
        result = bill_tendbcluster_migrate("admin", infos)

        assert result[0]["bill_id"] == 999
        assert result[0]["bill_url"].endswith("/ticket-business-manage/999")
        mock_ticket.create_ticket.assert_not_called()
