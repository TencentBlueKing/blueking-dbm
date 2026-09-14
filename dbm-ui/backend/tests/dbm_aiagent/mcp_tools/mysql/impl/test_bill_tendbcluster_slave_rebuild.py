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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_slave_rebuild import (
    bill_tendbcluster_slave_rebuild,
)

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_slave_rebuild"


def _cluster(cluster_id=1):
    cluster = MagicMock()
    cluster.id = cluster_id
    return cluster


def _slave(ip, bk_host_id, clusters, port=20000):
    """构造一个 slave 存储实例 mock，clusters 为该实例关联的集群列表"""
    si = MagicMock()
    si.machine.ip = ip
    si.machine.bk_host_id = bk_host_id
    si.port = port
    si.cluster.all.return_value = list(clusters)
    return si


def _set_slave_query(mock_storage, slave_list):
    """让 StorageInstance 查询链的最终可迭代对象返回 slave_list"""
    qs = (
        mock_storage.objects.using.return_value.filter.return_value.select_related.return_value.prefetch_related.return_value
    )
    qs.__iter__.return_value = iter(slave_list)


def _cluster_qs(ids):
    qs = MagicMock()
    qs.values_list.return_value = list(ids)
    return qs


class TestTendbClusterSlaveRebuildEarlyValidation:
    """TenDBCluster slave 原地重建：靠前的纯逻辑校验分支（空 ips、部分 IP 未找到、跨集群不一致）"""

    @patch(f"{MODULE}.validate_clusters")
    def test_empty_ips_raises(self, mock_validate):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        with pytest.raises(Exception, match="ips 不能为空"):
            bill_tendbcluster_slave_rebuild("admin", ["test.tendbcluster.db"], [])

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_missing_ip_raises(self, mock_validate, mock_storage):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        _set_slave_query(mock_storage, [])

        with pytest.raises(Exception, match="部分 IP 未找到对应 slave 实例"):
            bill_tendbcluster_slave_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_cluster_mismatch_raises(self, mock_validate, mock_storage):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        other_cluster = _cluster(2)
        si = _slave("1.1.1.1", 10001, [other_cluster])
        _set_slave_query(mock_storage, [si])

        with pytest.raises(Exception, match="输入集群与 slave 实例承载集群不一致"):
            bill_tendbcluster_slave_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])


class TestTendbClusterSlaveRebuildSuccessPath:
    """TenDBCluster slave 原地重建：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TendbClusterRestoreLocalSlaveDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_storage, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        si = _slave("1.1.1.1", 10001, [cluster], port=20000)
        _set_slave_query(mock_storage, [si])

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_tendbcluster_slave_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_id"] == 1
        assert info["slave"]["ip"] == "1.1.1.1"
        assert info["slave"]["port"] == 20000
        assert info["slave"]["bk_host_id"] == 10001
        assert details["force"] is False


class TestTendbClusterSlaveRebuildDuplicate:
    """TenDBCluster slave 原地重建：防重路径（命中已有单据时直接复用，不再创建）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TendbClusterRestoreLocalSlaveDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_duplicate_returns_existing(self, mock_validate, mock_storage, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        si = _slave("1.1.1.1", 10001, [cluster])
        _set_slave_query(mock_storage, [si])

        mock_dedup.return_value = Ticket(id=999)

        result = bill_tendbcluster_slave_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])

        assert result[0]["bill_id"] == 999
        assert result[0]["bill_url"].endswith("/ticket-business-manage/999")
        mock_ticket.create_ticket.assert_not_called()
