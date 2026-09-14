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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_proxy_rebuild import bill_proxy_rebuild

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_proxy_rebuild"


def _cluster(cluster_id=1):
    cluster = MagicMock()
    cluster.id = cluster_id
    return cluster


def _proxy(ip, bk_host_id, clusters, port=30000):
    """构造一个 proxy 实例 mock，clusters 为该实例关联的集群列表"""
    pi = MagicMock()
    pi.machine.ip = ip
    pi.machine.bk_host_id = bk_host_id
    pi.port = port
    pi.cluster.all.return_value = list(clusters)
    return pi


def _set_proxy_query(mock_proxy, pi_list):
    """让 ProxyInstance 查询链的最终可迭代对象返回 pi_list"""
    qs = (
        mock_proxy.objects.using.return_value.filter.return_value.select_related.return_value.prefetch_related.return_value
    )
    qs.__iter__.return_value = iter(pi_list)


def _cluster_qs(ids):
    """构造 validate_clusters 返回的 cluster QuerySet mock，支持 values_list("id", flat=True)"""
    qs = MagicMock()
    qs.values_list.return_value = list(ids)
    return qs


class TestProxyRebuildEarlyValidation:
    """proxy 原地重建：靠前的纯逻辑校验分支（空 ips、部分 IP 未找到、跨集群不一致）"""

    @patch(f"{MODULE}.validate_clusters")
    def test_empty_ips_raises(self, mock_validate):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        with pytest.raises(Exception, match="ips 不能为空"):
            bill_proxy_rebuild("admin", ["test.tendbha.db"], [])

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_missing_ip_raises(self, mock_validate, mock_proxy):
        """输入 IP 未找到对应 proxy 实例时报错"""
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        _set_proxy_query(mock_proxy, [])

        with pytest.raises(Exception, match="部分 IP 未找到对应 proxy 实例"):
            bill_proxy_rebuild("admin", ["test.tendbha.db"], ["1.1.1.1"])

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_cluster_mismatch_raises(self, mock_validate, mock_proxy):
        """proxy 承载集群与输入集群不一致时，报错拦截（防止跨集群 IP 被静默丢弃）"""
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        other_cluster = _cluster(2)
        pi = _proxy("1.1.1.1", 10001, [other_cluster])
        _set_proxy_query(mock_proxy, [pi])

        with pytest.raises(Exception, match="输入集群与 proxy 机器承载集群不一致"):
            bill_proxy_rebuild("admin", ["test.tendbha.db"], ["1.1.1.1"])


class TestProxyRebuildSuccessPath:
    """proxy 原地重建：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlProxyRebuildDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_proxy, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        pi = _proxy("1.1.1.1", 10001, [cluster], port=30000)
        _set_proxy_query(mock_proxy, [pi])

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_proxy_rebuild("admin", ["test.tendbha.db"], ["1.1.1.1"])

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_id"] == 1
        assert len(info["rebuild_proxy_hosts"]) == 1
        host = info["rebuild_proxy_hosts"][0]
        assert host["ip"] == "1.1.1.1"
        assert host["port"] == 30000
        assert host["bk_host_id"] == 10001
        assert details["is_safe"] is True


class TestProxyRebuildDuplicate:
    """proxy 原地重建：防重路径（命中已有单据时直接复用，不再创建）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlProxyRebuildDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_duplicate_returns_existing(self, mock_validate, mock_proxy, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        pi = _proxy("1.1.1.1", 10001, [cluster])
        _set_proxy_query(mock_proxy, [pi])

        mock_dedup.return_value = Ticket(id=999)

        result = bill_proxy_rebuild("admin", ["test.tendbha.db"], ["1.1.1.1"])

        assert result[0]["bill_id"] == 999
        assert result[0]["bill_url"].endswith("/ticket-business-manage/999")
        mock_ticket.create_ticket.assert_not_called()
