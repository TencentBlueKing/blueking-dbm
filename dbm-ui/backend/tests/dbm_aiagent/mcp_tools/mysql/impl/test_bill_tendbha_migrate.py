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

    @patch(f"{MODULE}.MysqlMigrateClusterDetailSerializer")
    @patch(f"{MODULE}.Ticket")
    @patch(f"{MODULE}.Spec")
    @patch(f"{MODULE}.validate_clusters")
    def test_success_path(self, mock_validate, mock_spec, mock_ticket, mock_serializer):
        from backend.ticket.models import Ticket

        cluster = _cluster()
        mock_validate.return_value = ([cluster], 1, 0)
        mock_spec.objects.filter.return_value.count.return_value = 1

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
