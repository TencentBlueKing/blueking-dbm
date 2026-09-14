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

from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_node_rebalance import (
    bill_tendbcluster_node_rebalance,
)

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_node_rebalance"


def _cluster(domain="test.tendbcluster.db"):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.id = 1
    cluster.bk_cloud_id = 0
    return cluster


class TestTendbClusterNodeRebalanceShardDivision:
    """容量变更：单机分片数 = 总分片数 / 机器组数，必须能整除"""

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_count_zero_raises(self, mock_validate, mock_spec, mock_storage_set, mock_storage_instance):
        """机器组数为 0 时，命中 count <= 0 分支直接报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 6

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 1, "count": 0}]
        with pytest.raises(Exception, match="机器组数必须为正整数: 0"):
            bill_tendbcluster_node_rebalance("admin", infos)

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_count_negative_raises(self, mock_validate, mock_spec, mock_storage_set, mock_storage_instance):
        """机器组数为负整数时，提前命中 count <= 0 分支报错，避免参与取模运算"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 6

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 1, "count": -3}]
        with pytest.raises(Exception, match="机器组数必须为正整数: -3"):
            bill_tendbcluster_node_rebalance("admin", infos)

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_count_not_divisible_raises(self, mock_validate, mock_spec, mock_storage_set, mock_storage_instance):
        """总分片数 6 无法被机器组数 4 整除时，报错拦截"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 6

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 1, "count": 4}]
        with pytest.raises(Exception, match="无法被机器组数 4 整除"):
            bill_tendbcluster_node_rebalance("admin", infos)

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_count_divisible_proceeds_to_remote_check(
        self, mock_validate, mock_spec, mock_storage_set, mock_storage_instance
    ):
        """总分片数 6 能被机器组数 2 整除时，不应误报整除错误，而应继续走到 remote 实例检查"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 6
        mock_storage_instance.objects.using.return_value.filter.return_value.exists.return_value = False

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 1, "count": 2}]
        with pytest.raises(Exception, match="无 remote 存储实例"):
            bill_tendbcluster_node_rebalance("admin", infos)


class TestTendbClusterNodeRebalanceEarlyValidation:
    """容量变更：靠前的纯逻辑校验分支（重复集群、目标规格校验）"""

    def test_duplicate_cluster_raises(self):
        """同一集群重复出现时，在进入任何 db 查询前直接报错"""
        infos = [
            {"cluster_domain": "dup.tendbcluster.db", "spec_id": 1, "count": 1},
            {"cluster_domain": "dup.tendbcluster.db", "spec_id": 2, "count": 1},
        ]
        with pytest.raises(Exception, match="存在重复集群"):
            bill_tendbcluster_node_rebalance("admin", infos)

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
            bill_tendbcluster_node_rebalance("admin", infos)

    def test_empty_infos_raises(self):
        """infos 为空时，在进入任何 db 查询前直接报错"""
        with pytest.raises(Exception, match="infos 不能为空"):
            bill_tendbcluster_node_rebalance("admin", [])


class TestTendbClusterNodeRebalanceShardInfo:
    """容量变更：分片信息相关校验（无分片信息）"""

    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_no_shard_info_raises(self, mock_validate, mock_spec, mock_storage_set):
        """集群无分片信息（分片数为 0）时直接报错"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 0

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 1, "count": 1}]
        with pytest.raises(Exception, match="无分片信息"):
            bill_tendbcluster_node_rebalance("admin", infos)


class TestTendbClusterNodeRebalanceSuccessPath:
    """容量变更：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_remote_spec_inconsistent_raises(self, mock_validate, mock_spec, mock_storage_set, mock_storage_instance):
        """同一集群 remote 实例规格不一致时，报错拦截（问题5）"""
        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 2

        remote_qs = mock_storage_instance.objects.using.return_value.filter.return_value
        remote_qs.exists.return_value = True

        def _fake_values_list(field, **kwargs):
            if field == "machine__bk_host_id":
                m = MagicMock()
                m.distinct.return_value.count.return_value = 2
                return m
            if field == "machine__spec_id":
                return [3, 5]  # 两个不同规格
            return MagicMock()

        remote_qs.values_list.side_effect = _fake_values_list

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 5, "count": 2}]
        with pytest.raises(Exception, match="规格不一致"):
            bill_tendbcluster_node_rebalance("admin", infos)

    @patch(f"{MODULE}.TendbNodeRebalanceDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.StorageInstance")
    @patch(f"{MODULE}.TenDBClusterStorageSet")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(
        self,
        mock_validate,
        mock_spec,
        mock_storage_set,
        mock_storage_instance,
        mock_ticket,
        mock_serializer,
    ):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1
        mock_storage_set.objects.using.return_value.filter.return_value.count.return_value = 6

        # 目标规格对象：详情展示需要 specName / futureCapacity
        target_spec_obj = MagicMock()
        target_spec_obj.spec_id = 5
        target_spec_obj.spec_name = "target_spec"
        target_spec_obj.capacity = 50.0
        mock_spec.objects.filter.return_value.__iter__.return_value = iter([target_spec_obj])

        current_spec = MagicMock()
        current_spec.spec_name = "test_spec"
        mock_spec.objects.filter.return_value.first.return_value = current_spec

        remote_qs = mock_storage_instance.objects.using.return_value.filter.return_value
        remote_qs.exists.return_value = True

        def _fake_values_list(field, **kwargs):
            # 机器组数统计：distinct().count()
            if field == "machine__bk_host_id":
                m = MagicMock()
                m.distinct.return_value.count.return_value = 2
                return m
            # 规格一致性校验：返回单一规格 3
            if field == "machine__spec_id":
                return [3]
            return MagicMock()

        remote_qs.values_list.side_effect = _fake_values_list

        mock_ticket.create_ticket.return_value = Ticket(id=123)

        infos = [{"cluster_domain": cluster.immute_domain, "spec_id": 5, "count": 2, "labels": ["1"]}]
        result = bill_tendbcluster_node_rebalance("admin", infos)

        assert len(result) == 1
        assert result[0]["bill_id"] == 123
        assert result[0]["bill_url"].endswith("/ticket-business-manage/123")

        details = mock_ticket.create_ticket.call_args.kwargs["details"]
        info = details["infos"][0]
        assert info["cluster_id"] == cluster.id
        assert info["cluster_shard_num"] == 6
        assert info["remote_shard_num"] == 3
        assert info["resource_spec"]["backend_group"]["count"] == 2
        assert info["resource_spec"]["backend_group"]["spec_id"] == 5
        assert info["resource_spec"]["backend_group"]["labels"] == ["1"]
