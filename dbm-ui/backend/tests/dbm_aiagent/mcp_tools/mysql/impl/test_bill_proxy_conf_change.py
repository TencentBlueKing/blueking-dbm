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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_proxy_conf_change import bill_proxy_conf_change

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_proxy_conf_change"


def _cluster(domain="test.tendbha.db", cluster_id=1):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.id = cluster_id
    return cluster


def _proxy(ip, bk_host_id, spec_id, clusters, port=0):
    """构造一个 proxy 实例 mock，clusters 为该实例关联的集群列表"""
    pi = MagicMock()
    pi.machine.bk_cloud_id = 0
    pi.machine.ip = ip
    pi.machine.bk_host_id = bk_host_id
    pi.machine.bk_biz_id = 1
    pi.machine.spec_id = spec_id
    pi.port = port
    pi.cluster.all.return_value = list(clusters)
    return pi


def _set_proxy_query(mock_proxy, pi_list):
    """让 ProxyInstance 查询链的最终可迭代对象返回 pi_list"""
    qs = (
        mock_proxy.objects.using.return_value.filter.return_value.select_related.return_value.prefetch_related.return_value
    )
    qs.__iter__.return_value = iter(pi_list)


class TestProxyConfChangeEarlyValidation:
    """proxy 升降配：靠前的纯逻辑校验分支（重复集群、目标规格校验）"""

    def test_duplicate_cluster_raises(self):
        """同一集群重复出现时，在进入任何 db 查询前直接报错"""
        infos = [
            {"cluster_domain": "dup.tendbha.db", "target_spec_id": 1},
            {"cluster_domain": "dup.tendbha.db", "target_spec_id": 2},
        ]
        with pytest.raises(Exception, match="存在重复集群"):
            bill_proxy_conf_change("admin", infos)

    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_spec_not_found_raises(self, mock_validate, mock_spec):
        """目标规格不存在或未启用时，命中 spec 校验分支直接报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 0
        mock_spec.objects.filter.return_value.values_list.return_value = []

        infos = [{"cluster_domain": cluster.immute_domain, "target_spec_id": 999}]
        with pytest.raises(Exception, match="目标规格不存在或未启用"):
            bill_proxy_conf_change("admin", infos)

    def test_empty_infos_raises(self):
        """infos 为空时，在进入任何 db 查询前直接报错"""
        with pytest.raises(Exception, match="infos 不能为空"):
            bill_proxy_conf_change("admin", [])


class TestProxyConfChangeInstanceValidation:
    """proxy 升降配：依赖 proxy 实例查询的校验分支（无实例、目标规格=当前规格）"""

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_no_proxy_instances_raises(self, mock_validate, mock_spec, mock_proxy):
        """集群无 proxy 实例时直接报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_proxy.objects.using.return_value.filter.return_value.exists.return_value = False

        infos = [{"cluster_domain": cluster.immute_domain, "target_spec_id": 1}]
        with pytest.raises(Exception, match="集群无 proxy 实例"):
            bill_proxy_conf_change("admin", infos)

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_spec_same_as_current_raises(self, mock_validate, mock_spec, mock_proxy):
        """目标规格与当前规格相同时，提示无需升降配"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        pi = _proxy("1.1.1.1", 10001, spec_id=5, clusters=[cluster])
        _set_proxy_query(mock_proxy, [pi])

        infos = [{"cluster_domain": cluster.immute_domain, "target_spec_id": 5}]
        with pytest.raises(Exception, match="目标规格与当前规格相同"):
            bill_proxy_conf_change("admin", infos)


class TestProxyConfChangeSuccessPath:
    """proxy 升降配：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlProxyConfChangeDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_spec, mock_proxy, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        pi = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster], port=30000)
        _set_proxy_query(mock_proxy, [pi])

        mock_ticket.create_ticket.return_value = Ticket(id=123)

        infos = [{"cluster_domain": cluster.immute_domain, "target_spec_id": 5, "labels": ["1"]}]
        result = bill_proxy_conf_change("admin", infos)

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_ids"] == [cluster.id]
        assert info["resource_spec"]["target_proxies"]["spec_id"] == 5
        assert info["resource_spec"]["target_proxies"]["count"] == 1
        assert info["resource_spec"]["target_proxies"]["labels"] == ["1"]
        assert "origin_proxies" in info
        assert info["origin_proxies"][0]["port"] == 0
        assert info["old_nodes"]["proxy"] == info["origin_proxies"]


class TestProxyConfChangeMultiInstance:
    """proxy 升降配：多实例场景（同机多端口去重、同组共享集群合并）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlProxyConfChangeDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_same_machine_multi_port_dedup(
        self, mock_validate, mock_spec, mock_proxy, mock_ticket, mock_serializer, mock_dedup
    ):
        """同一集群内一台机器跑多个端口：按机器去重，count=机器数"""
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        # 机器 10001 跑 2 个端口，机器 10002 跑 1 个端口
        pi1 = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster], port=30000)
        pi2 = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster], port=30001)
        pi3 = _proxy("1.1.1.2", 10002, spec_id=3, clusters=[cluster], port=30000)
        _set_proxy_query(mock_proxy, [pi1, pi2, pi3])

        mock_ticket.create_ticket.return_value = Ticket(id=200)

        infos = [{"cluster_domain": cluster.immute_domain, "target_spec_id": 5}]
        bill_proxy_conf_change("admin", infos)

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_ids"] == [cluster.id]
        # 3 个 proxy 实例去重为 2 台机器
        assert len(info["origin_proxies"]) == 2
        assert info["resource_spec"]["target_proxies"]["count"] == 2
        # 所有 origin_proxies 的 port 均被置 0（机器维度）
        assert {p["port"] for p in info["origin_proxies"]} == {0}
        assert {p["bk_host_id"] for p in info["origin_proxies"]} == {10001, 10002}

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlProxyConfChangeDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_shared_clusters_merged(
        self, mock_validate, mock_spec, mock_proxy, mock_ticket, mock_serializer, mock_dedup
    ):
        """同组共享集群（proxy 机器集合一致）合并为一行提单"""
        from backend.ticket.models import Ticket

        cluster_a = _cluster("a.tendbha.db", cluster_id=1)
        cluster_b = _cluster("b.tendbha.db", cluster_id=2)
        mock_validate.return_value = ([cluster_a, cluster_b], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        # 机器 10001 分别以不同端口服务 A、B；机器 10002 一个实例同时服务 A、B
        pi1 = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_a], port=30000)
        pi2 = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_b], port=30001)
        pi3 = _proxy("1.1.1.2", 10002, spec_id=3, clusters=[cluster_a, cluster_b], port=30000)
        _set_proxy_query(mock_proxy, [pi1, pi2, pi3])

        mock_ticket.create_ticket.return_value = Ticket(id=300)

        infos = [
            {"cluster_domain": cluster_a.immute_domain, "target_spec_id": 5},
            {"cluster_domain": cluster_b.immute_domain, "target_spec_id": 5},
        ]
        bill_proxy_conf_change("admin", infos)

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        assert len(details["infos"]) == 1
        info = details["infos"][0]
        assert info["cluster_ids"] == [1, 2]
        assert len(info["origin_proxies"]) == 2
        assert info["resource_spec"]["target_proxies"]["count"] == 2

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_shared_clusters_conflicting_spec_raises(self, mock_validate, mock_spec, mock_proxy):
        """同组共享集群目标规格不一致时直接报错"""
        cluster_a = _cluster("a.tendbha.db", cluster_id=1)
        cluster_b = _cluster("b.tendbha.db", cluster_id=2)
        mock_validate.return_value = ([cluster_a, cluster_b], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 2

        pi1 = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_a, cluster_b])
        _set_proxy_query(mock_proxy, [pi1])

        infos = [
            {"cluster_domain": cluster_a.immute_domain, "target_spec_id": 5},
            {"cluster_domain": cluster_b.immute_domain, "target_spec_id": 6},
        ]
        with pytest.raises(Exception, match="同组共享集群目标规格不一致"):
            bill_proxy_conf_change("admin", infos)

    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_shared_clusters_conflicting_labels_raises(self, mock_validate, mock_spec, mock_proxy):
        """同组共享集群资源标签不一致时直接报错"""
        cluster_a = _cluster("a.tendbha.db", cluster_id=1)
        cluster_b = _cluster("b.tendbha.db", cluster_id=2)
        mock_validate.return_value = ([cluster_a, cluster_b], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1

        pi1 = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_a, cluster_b])
        _set_proxy_query(mock_proxy, [pi1])

        infos = [
            {"cluster_domain": cluster_a.immute_domain, "target_spec_id": 5, "labels": ["1"]},
            {"cluster_domain": cluster_b.immute_domain, "target_spec_id": 5, "labels": ["2"]},
        ]
        with pytest.raises(Exception, match="同组共享集群资源标签不一致"):
            bill_proxy_conf_change("admin", infos)


class TestProxyConfChangeAutoComplete:
    """proxy 升降配：同机关联集群自动补齐（只传一个代表集群，自动带出同机全部集群）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlProxyConfChangeDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.Cluster")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_single_represent_cluster_auto_complete(
        self, mock_validate, mock_spec, mock_proxy, mock_cluster, mock_ticket, mock_serializer, mock_dedup
    ):
        """只提交 1 个代表集群，机器上 4 个同机关联集群自动补齐合并为一行"""
        from backend.ticket.models import Ticket

        cluster_a = _cluster("a.tendbha.db", cluster_id=1)
        cluster_b = _cluster("b.tendbha.db", cluster_id=2)
        cluster_c = _cluster("c.tendbha.db", cluster_id=3)
        cluster_d = _cluster("d.tendbha.db", cluster_id=4)

        mock_validate.return_value = ([cluster_a], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        # 机器 10001 上部署 4 个集群，每个集群一个 proxy 进程（不同端口）
        pi_a = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_a], port=30000)
        pi_b = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_b], port=30001)
        pi_c = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_c], port=30002)
        pi_d = _proxy("1.1.1.1", 10001, spec_id=3, clusters=[cluster_d], port=30003)

        # 第一次查询（cluster__pk__in=[1]）→ 只返回代表集群的 proxy 实例
        qs_initial = MagicMock()
        qs_initial.select_related.return_value.prefetch_related.return_value.__iter__.return_value = iter([pi_a])

        # 自动补齐查询（machine__bk_host_id__in={10001}）→ 返回该机器的 4 个集群 id
        qs_related = MagicMock()
        qs_related.values_list.return_value.distinct.return_value = [1, 2, 3, 4]

        # 补齐集群的 proxy 实例查询（cluster__pk__in={2,3,4}）
        qs_extra = MagicMock()
        qs_extra.select_related.return_value.prefetch_related.return_value.__iter__.return_value = iter(
            [pi_b, pi_c, pi_d]
        )

        def filter_side_effect(**kwargs):
            if "machine__bk_host_id__in" in kwargs:
                return qs_related
            if "cluster__pk__in" in kwargs:
                if set(kwargs["cluster__pk__in"]) == {cluster_a.id}:
                    return qs_initial
                return qs_extra
            return MagicMock()

        mock_proxy.objects.using.return_value.filter.side_effect = filter_side_effect

        # 补齐集群对象查询（id__in={2,3,4}）
        qs_cluster = MagicMock()
        qs_cluster.__iter__.return_value = iter([cluster_b, cluster_c, cluster_d])
        mock_cluster.objects.using.return_value.filter.return_value = qs_cluster

        mock_ticket.create_ticket.return_value = Ticket(id=400)

        infos = [{"cluster_domain": cluster_a.immute_domain, "target_spec_id": 5}]
        bill_proxy_conf_change("admin", infos)

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        assert len(details["infos"]) == 1
        info = details["infos"][0]
        assert info["cluster_ids"] == [1, 2, 3, 4]
        assert len(info["origin_proxies"]) == 1
        assert info["origin_proxies"][0]["bk_host_id"] == 10001
        assert info["resource_spec"]["target_proxies"]["count"] == 1
        assert info["resource_spec"]["target_proxies"]["spec_id"] == 5
