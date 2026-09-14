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


def _cluster(domain="test.tendbha.db"):
    cluster = MagicMock()
    cluster.immute_domain = domain
    cluster.id = 1
    return cluster


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
        qs = mock_proxy.objects.using.return_value.filter.return_value
        qs.exists.return_value = True
        qs.values_list.return_value = [5]

        infos = [{"cluster_domain": cluster.immute_domain, "target_spec_id": 5}]
        with pytest.raises(Exception, match="目标规格与当前规格相同"):
            bill_proxy_conf_change("admin", infos)


class TestProxyConfChangeSuccessPath:
    """proxy 升降配：成功提单路径（验证 ticket_param 结构组装正确）"""

    @patch(f"{MODULE}.MysqlProxyConfChangeDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.ProxyInstance")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_spec, mock_proxy, mock_ticket, mock_serializer):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1

        pi = MagicMock()
        pi.machine.bk_cloud_id = 0
        pi.machine.ip = "1.1.1.1"
        pi.machine.bk_host_id = 10001
        pi.machine.bk_biz_id = 1
        pi.port = 0

        qs = mock_proxy.objects.using.return_value.filter.return_value
        qs.exists.return_value = True
        qs.values_list.return_value = [3]
        qs.__iter__.return_value = iter([pi])

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
        assert info["old_nodes"]["proxy"] == info["origin_proxies"]
