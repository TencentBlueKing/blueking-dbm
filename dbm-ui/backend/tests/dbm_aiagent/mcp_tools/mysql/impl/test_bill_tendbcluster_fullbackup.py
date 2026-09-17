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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_tendbcluster_fullbackup import bill_tendbcluster_fullbackup
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_tendbcluster_fullbackup"


def _cluster(domain="test.tendbcluster.db", cluster_id=1):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.pk = cluster_id
    return cluster


def _set_cluster_query(mock_cluster, cluster_objs):
    """让 Cluster.objects.using(...).filter(...) 返回的 queryset 可迭代为 cluster_objs"""
    qs = mock_cluster.objects.using.return_value.filter.return_value
    qs.__iter__.side_effect = lambda: iter(cluster_objs)


class TestFullBackupEarlyValidation:
    """TenDBCluster 全库备份：靠前的纯逻辑校验分支"""

    def test_empty_cluster_domains_raises(self):
        """cluster_domains 为空时，在进入任何 db 查询前直接报错"""
        with pytest.raises(Exception, match="cluster_domains 不能为空"):
            bill_tendbcluster_fullbackup(1, "admin", [])

    @patch(f"{MODULE}.Cluster")
    def test_missing_cluster_raises(self, mock_cluster):
        """集群查询为空时，提示未找到或非 TenDBCluster 类型"""
        _set_cluster_query(mock_cluster, [])
        with pytest.raises(Exception, match="部分集群未找到"):
            bill_tendbcluster_fullbackup(1, "admin", ["not-exist.tendbcluster.db"])


class TestFullBackupFingerprint:
    """核心：幂等指纹必须包含 backup_type 与 backup_local，避免不同类型/位置的备份互相复用"""

    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TenDBClusterFullBackUpDetailSerializer")
    @patch(f"{MODULE}.Cluster")
    def test_fingerprint_includes_backup_type_and_local(
        self, mock_cluster, mock_serializer, mock_find_dup, mock_ticket
    ):
        """指纹应为 (cluster_ids, backup_type, backup_locals) 三元组"""
        _set_cluster_query(mock_cluster, [_cluster(cluster_id=1)])
        mock_find_dup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        bill_tendbcluster_fullbackup(
            bk_biz_id=1,
            username="admin",
            cluster_domains=["test.tendbcluster.db"],
            backup_type="physical",
            backup_local="slave",
        )

        target_fp = mock_find_dup.call_args.kwargs["target_fingerprint"]
        assert target_fp == ((1,), "physical", ("slave",))

    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TenDBClusterFullBackUpDetailSerializer")
    @patch(f"{MODULE}.Cluster")
    def test_different_backup_type_produces_different_fingerprint(
        self, mock_cluster, mock_serializer, mock_find_dup, mock_ticket
    ):
        """同一集群先物理备份、再逻辑备份时，指纹应不同，不能互相复用"""
        _set_cluster_query(mock_cluster, [_cluster(cluster_id=1)])
        mock_find_dup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=1)

        bill_tendbcluster_fullbackup(
            1, "admin", ["test.tendbcluster.db"], backup_type="physical", backup_local="slave"
        )
        bill_tendbcluster_fullbackup(1, "admin", ["test.tendbcluster.db"], backup_type="logical", backup_local="slave")

        fp_physical = mock_find_dup.call_args_list[0].kwargs["target_fingerprint"]
        fp_logical = mock_find_dup.call_args_list[1].kwargs["target_fingerprint"]
        assert fp_physical != fp_logical
        assert fp_physical[1] == "physical"
        assert fp_logical[1] == "logical"

    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TenDBClusterFullBackUpDetailSerializer")
    @patch(f"{MODULE}.Cluster")
    def test_different_backup_local_produces_different_fingerprint(
        self, mock_cluster, mock_serializer, mock_find_dup, mock_ticket
    ):
        """同一集群、同一类型，但备份位置不同（slave vs master）时，指纹应不同"""
        _set_cluster_query(mock_cluster, [_cluster(cluster_id=1)])
        mock_find_dup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=1)

        bill_tendbcluster_fullbackup(
            1, "admin", ["test.tendbcluster.db"], backup_type="physical", backup_local="slave"
        )
        bill_tendbcluster_fullbackup(
            1, "admin", ["test.tendbcluster.db"], backup_type="physical", backup_local="master"
        )

        fp_slave = mock_find_dup.call_args_list[0].kwargs["target_fingerprint"]
        fp_master = mock_find_dup.call_args_list[1].kwargs["target_fingerprint"]
        assert fp_slave != fp_master
        assert fp_slave[2] == ("slave",)
        assert fp_master[2] == ("master",)

    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TenDBClusterFullBackUpDetailSerializer")
    @patch(f"{MODULE}.Cluster")
    def test_fingerprint_of_extracts_from_historical_ticket(
        self, mock_cluster, mock_serializer, mock_find_dup, mock_ticket
    ):
        """fingerprint_of 回调应从历史单据 details 中提取与 target 同构的指纹"""
        _set_cluster_query(mock_cluster, [_cluster(cluster_id=1)])
        mock_find_dup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=1)

        bill_tendbcluster_fullbackup(
            1, "admin", ["test.tendbcluster.db"], backup_type="physical", backup_local="slave"
        )

        target_fp = mock_find_dup.call_args.kwargs["target_fingerprint"]
        fingerprint_of = mock_find_dup.call_args.kwargs["fingerprint_of"]

        hist_ticket = MagicMock()
        hist_ticket.details = {
            "backup_type": "physical",
            "infos": [{"cluster_id": 1, "backup_local": "slave"}],
        }
        assert fingerprint_of(hist_ticket) == target_fp


class TestFullBackupSuccessPath:
    """TenDBCluster 全库备份：成功提单路径与幂等复用"""

    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TenDBClusterFullBackUpDetailSerializer")
    @patch(f"{MODULE}.Cluster")
    def test_success_path(self, mock_cluster, mock_serializer, mock_find_dup, mock_ticket):
        """未命中重复单据时，正常创建单据并组装 ticket_param"""
        _set_cluster_query(mock_cluster, [_cluster(cluster_id=1)])
        mock_find_dup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_tendbcluster_fullbackup(
            bk_biz_id=1,
            username="admin",
            cluster_domains=["test.tendbcluster.db"],
            backup_type="physical",
            backup_local="slave",
        )

        assert result[0]["bill_id"] == 123

        ticket_param = mock_ticket.create_ticket.call_args.kwargs
        assert ticket_param["ticket_type"] == TicketType.TENDBCLUSTER_FULL_BACKUP
        assert ticket_param["bk_biz_id"] == 1
        assert ticket_param["details"]["backup_type"] == "physical"
        assert ticket_param["details"]["infos"] == [{"cluster_id": 1, "backup_local": "slave"}]

    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TenDBClusterFullBackUpDetailSerializer")
    @patch(f"{MODULE}.Cluster")
    def test_duplicate_ticket_reused(self, mock_cluster, mock_serializer, mock_find_dup, mock_ticket):
        """命中已有单据时，直接复用已有单据，不再创建新单据"""
        _set_cluster_query(mock_cluster, [_cluster(cluster_id=1)])
        existing = Ticket(id=999)
        mock_find_dup.return_value = existing

        result = bill_tendbcluster_fullbackup(1, "admin", ["test.tendbcluster.db"])

        assert result[0]["bill_id"] == 999
        mock_ticket.create_ticket.assert_not_called()
