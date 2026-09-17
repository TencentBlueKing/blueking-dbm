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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbha_migrate import bill_tendbha_migrate

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbha_migrate"


def _cluster(domain="test.tendbha.db"):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.id = 1
    return cluster


class TestTendbhaMigrateEarlyValidation:
    """主从迁移：靠前的纯逻辑校验分支（重复集群、目标规格校验）"""

    def test_duplicate_cluster_raises(self):
        """同一集群重复出现时，在进入任何 db 查询前直接报错"""
        infos = [
            {"cluster_domain": "dup.tendbha.db", "spec_id": 1, "count": 1},
            {"cluster_domain": "dup.tendbha.db", "spec_id": 2, "count": 1},
        ]
        with pytest.raises(Exception, match="存在重复集群"):
            bill_tendbha_migrate("admin", infos, opera_object="cluster")

    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_spec_not_found_raises(self, mock_validate, mock_spec):
        """目标规格不存在或未启用时，命中 spec 校验分支直接报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 0
        mock_spec.objects.filter.return_value.values_list.return_value = []

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 999, "count": 1}]
        with pytest.raises(Exception, match="目标规格不存在或未启用"):
            bill_tendbha_migrate("admin", infos, opera_object="cluster")

    def test_empty_infos_raises(self):
        """infos 为空时，在进入任何 db 查询前直接报错"""
        with pytest.raises(Exception, match="infos 不能为空"):
            bill_tendbha_migrate("admin", [], opera_object="cluster")


class TestTendbhaMigrateSuccessPath:
    """主从迁移：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlMigrateClusterDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_spec, mock_ticket, mock_serializer, mock_dedup):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        mock_ticket.create_ticket.return_value = Ticket(id=123)

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 1, "count": 2, "labels": ["1"]}]
        result = bill_tendbha_migrate("admin", infos, opera_object="cluster")

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_ids"] == [cluster.id]
        assert info["resource_spec"]["backend_group"]["count"] == 2
        assert info["resource_spec"]["backend_group"]["spec_id"] == 1
        assert info["resource_spec"]["backend_group"]["labels"] == ["1"]
        assert details["opera_object"] == "cluster"


def _storage_instance(bk_host_id, role, is_stand_by, clusters):
    """构造一个存储实例 mock，clusters 为该实例关联的集群列表"""
    si = MagicMock()
    si.machine.bk_host_id = bk_host_id
    si.instance_inner_role = role
    si.is_stand_by = is_stand_by
    si.cluster.all.return_value = list(clusters)
    return si


def _mock_storage_query(mock_storage, cluster_items, master_items, slave_items):
    """让 StorageInstance 的多次 filter 查询分别返回不同的实例集合"""

    def filter_side_effect(**kwargs):
        qs = MagicMock()
        if "cluster__pk__in" in kwargs:
            qs.select_related.return_value.prefetch_related.return_value.__iter__.return_value = iter(cluster_items)
        elif kwargs.get("instance_inner_role") == "master":
            qs.prefetch_related.return_value.__iter__.return_value = iter(master_items)
        elif kwargs.get("instance_inner_role") == "slave":
            qs.prefetch_related.return_value.__iter__.return_value = iter(slave_items)
        return qs

    mock_storage.objects.using.return_value.filter.side_effect = filter_side_effect


class TestTendbhaMigrateMachinePath:
    """主从迁移：整机迁移路径（按 master+slave 机器组聚合同机关联集群）"""

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlMigrateClusterDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_machine_migrate_group_merge(
        self, mock_validate, mock_spec, mock_storage, mock_ticket, mock_serializer, mock_dedup
    ):
        """同机共享的两个集群，整机迁移合并为一行，cluster_ids 传全"""
        from backend.ticket.models import Ticket

        cluster_a = _cluster("a.tendbha.db")
        cluster_a.id = 1
        cluster_b = _cluster("b.tendbha.db")
        cluster_b.id = 2

        mock_validate.return_value = ([cluster_a, cluster_b], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        # 机器组：master=10001, slave=20001，承载 A、B 两个集群
        master_a = _storage_instance(10001, "master", False, [cluster_a])
        slave_a = _storage_instance(20001, "slave", True, [cluster_a])
        master_b = _storage_instance(10001, "master", False, [cluster_b])
        slave_b = _storage_instance(20001, "slave", True, [cluster_b])

        _mock_storage_query(
            mock_storage, [master_a, slave_a, master_b, slave_b], [master_a, master_b], [slave_a, slave_b]
        )

        mock_ticket.create_ticket.return_value = Ticket(id=300)

        infos = [
            {"cluster_domain": cluster_a.immute_domain, "spec_id": 5, "count": 1},
            {"cluster_domain": cluster_b.immute_domain, "spec_id": 5, "count": 1},
        ]
        bill_tendbha_migrate("admin", infos, opera_object="machine")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        assert details["opera_object"] == "machine"
        assert len(details["infos"]) == 1
        info = details["infos"][0]
        assert info["cluster_ids"] == [1, 2]
        assert info["resource_spec"]["backend_group"]["count"] == 1
        assert info["resource_spec"]["backend_group"]["spec_id"] == 5

    @patch(f"{MODULE}.find_duplicate_ticket")
    @patch(f"{MODULE}.MysqlMigrateClusterDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_machine_migrate_auto_complete(
        self, mock_validate, mock_spec, mock_storage, mock_ticket, mock_serializer, mock_dedup
    ):
        """只提交一个代表集群，整机迁移自动补齐同机共享集群"""
        from backend.ticket.models import Ticket

        cluster_a = _cluster("a.tendbha.db")
        cluster_a.id = 1
        cluster_b = _cluster("b.tendbha.db")
        cluster_b.id = 2

        # 只提交 A，validate_clusters 只返回 A
        mock_validate.return_value = ([cluster_a], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_dedup.return_value = None

        master_a = _storage_instance(10001, "master", False, [cluster_a])
        slave_a = _storage_instance(20001, "slave", True, [cluster_a])
        master_b = _storage_instance(10001, "master", False, [cluster_b])
        slave_b = _storage_instance(20001, "slave", True, [cluster_b])

        # 第一次查询只返回 A 的实例；反查 master/slave 机器时返回 A、B 的实例
        _mock_storage_query(mock_storage, [master_a, slave_a], [master_a, master_b], [slave_a, slave_b])

        mock_ticket.create_ticket.return_value = Ticket(id=400)

        infos = [{"cluster_domain": cluster_a.immute_domain, "spec_id": 5, "count": 1}]
        bill_tendbha_migrate("admin", infos, opera_object="machine")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        assert len(details["infos"]) == 1
        info = details["infos"][0]
        assert info["cluster_ids"] == [1, 2]
        assert info["resource_spec"]["backend_group"]["spec_id"] == 5
