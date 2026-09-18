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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_spider_rebuild import bill_spider_rebuild

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_spider_rebuild"


def _cluster(cluster_id=1):
    cluster = MagicMock()
    cluster.id = cluster_id
    return cluster


def _spider(ip, bk_host_id, clusters, spider_role, port=25000):
    """构造一个 spider 实例 mock，携带 spider 角色与所属集群"""
    si = MagicMock()
    si.machine.ip = ip
    si.machine.bk_host_id = bk_host_id
    si.port = port
    spider_ext = MagicMock()
    spider_ext.spider_role = spider_role
    si.tendbclusterspiderext = spider_ext
    si.cluster.all.return_value = list(clusters)
    return si


def _set_spider_query(mock_proxy, spider_list):
    """让 ProxyInstance 查询链的最终可迭代对象返回 spider_list"""
    qs = (
        mock_proxy.objects.using.return_value.filter.return_value.select_related.return_value.prefetch_related.return_value
    )
    qs.__iter__.return_value = iter(spider_list)


def _cluster_qs(ids):
    qs = MagicMock()
    qs.values_list.return_value = list(ids)
    return qs


class TestSpiderRebuildEarlyValidation:
    """spider 原地重建：靠前的纯逻辑校验分支（空 ips、部分 IP 未找到、角色不支持、跨集群不一致）"""

    @patch(f"{MODULE}.validate_clusters")
    def test_empty_ips_raises(self, mock_validate):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        with pytest.raises(Exception, match="ips 不能为空"):
            bill_spider_rebuild("admin", ["test.tendbcluster.db"], [])

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_missing_ip_raises(self, mock_validate, mock_proxy):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        _set_spider_query(mock_proxy, [])

        with pytest.raises(Exception, match="部分 IP 未找到对应 spider 实例"):
            bill_spider_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_unsupported_role_raises(self, mock_validate, mock_proxy):
        """spider 角色不在 master/slave 白名单内时报错"""
        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        si = _spider("1.1.1.1", 10001, [cluster], spider_role="spider_mnt")
        _set_spider_query(mock_proxy, [si])

        with pytest.raises(Exception, match="角色 spider_mnt 不支持原地重建"):
            bill_spider_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_cluster_mismatch_raises(self, mock_validate, mock_proxy):
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        other_cluster = _cluster(2)
        si = _spider("1.1.1.1", 10001, [other_cluster], spider_role="spider_master")
        _set_spider_query(mock_proxy, [si])

        with pytest.raises(Exception, match="输入集群与 spider 实例承载集群不一致"):
            bill_spider_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])


class TestSpiderRebuildSuccessPath:
    """spider 原地重建：成功提单路径（按 (cluster_id, spider_role) 分组）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TendbClusterSpiderRebuildDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_proxy, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        master_spider = _spider("1.1.1.1", 10001, [cluster], spider_role="spider_master", port=25000)
        slave_spider = _spider("1.1.1.2", 10002, [cluster], spider_role="spider_slave", port=25000)
        _set_spider_query(mock_proxy, [master_spider, slave_spider])

        mock_dedup.return_value = None
        mock_ticket.create_ticket.return_value = Ticket(id=123)

        result = bill_spider_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1", "1.1.1.2"])

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        infos = details["infos"]
        # master / slave 两个角色各一行
        assert len(infos) == 2

        by_role = {info["rebuild_spider_role"]: info for info in infos}
        assert set(by_role) == {"spider_master", "spider_slave"}
        assert by_role["spider_master"]["cluster_id"] == 1
        assert by_role["spider_master"]["spider_ip_list"][0]["ip"] == "1.1.1.1"
        assert by_role["spider_master"]["spider_ip_list"][0]["port"] == 25000
        assert by_role["spider_slave"]["spider_ip_list"][0]["bk_host_id"] == 10002


class TestSpiderRebuildDuplicate:
    """spider 原地重建：防重路径（命中已有单据时直接复用，不再创建）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.TendbClusterSpiderRebuildDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.validate_clusters")
    def test_duplicate_returns_existing(self, mock_validate, mock_proxy, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster(1)
        mock_validate.return_value = (_cluster_qs([1]), 1, 0)
        si = _spider("1.1.1.1", 10001, [cluster], spider_role="spider_master")
        _set_spider_query(mock_proxy, [si])

        mock_dedup.return_value = Ticket(id=999)

        result = bill_spider_rebuild("admin", ["test.tendbcluster.db"], ["1.1.1.1"])

        assert result[0]["bill_id"] == 999
        assert result[0]["bill_url"].endswith("/ticket/999")
        mock_ticket.create_ticket.assert_not_called()
