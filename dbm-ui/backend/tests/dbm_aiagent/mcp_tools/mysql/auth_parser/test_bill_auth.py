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

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.mysql.auth_parser import bill as auth_bill

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.auth_parser.bill"


def _request(**data):
    request = MagicMock()
    request.method = "POST"
    request.data = data
    return request


class TestAuthParseInfosClusters:
    """鉴权解析核心辅助函数：从多行 infos 提取 cluster_domain 并解析集群 ID"""

    @patch(f"{MODULE}.Cluster")
    def test_no_cluster_domain_raises(self, mock_cluster):
        """infos 为空时，抛 no cluster_domain 错误"""
        with pytest.raises(ValueError, match="no cluster_domain found in infos"):
            auth_bill._auth_parse_infos_clusters(_request(infos=[]), ClusterType.TenDBHA)

    @patch(f"{MODULE}.Cluster")
    def test_skips_empty_domain(self, mock_cluster):
        """跳过空 cluster_domain，只把有效域名传给 filter"""
        qs = mock_cluster.objects.using.return_value.filter.return_value
        qs.exists.return_value = True
        qs.values_list.return_value = [1]

        auth_bill._auth_parse_infos_clusters(
            _request(infos=[{"cluster_domain": ""}, {"cluster_domain": "a.db"}]),
            ClusterType.TenDBHA,
        )

        mock_cluster.objects.using.return_value.filter.assert_called_once_with(
            immute_domain__in=["a.db"], cluster_type=ClusterType.TenDBHA
        )

    @patch(f"{MODULE}.Cluster")
    def test_no_clusters_found_raises(self, mock_cluster):
        """查询不到集群时抛错"""
        qs = mock_cluster.objects.using.return_value.filter.return_value
        qs.exists.return_value = False

        with pytest.raises(ValueError, match="No clusters found"):
            auth_bill._auth_parse_infos_clusters(_request(infos=[{"cluster_domain": "a.db"}]), ClusterType.TenDBHA)

    @patch(f"{MODULE}.Cluster")
    def test_returns_cluster_ids(self, mock_cluster):
        """正常返回集群 ID 列表"""
        qs = mock_cluster.objects.using.return_value.filter.return_value
        qs.exists.return_value = True
        qs.values_list.return_value = [10, 20]

        result = auth_bill._auth_parse_infos_clusters(
            _request(infos=[{"cluster_domain": "a.db"}, {"cluster_domain": "b.db"}]),
            ClusterType.TenDBHA,
        )
        assert result == [10, 20]

    @patch(f"{MODULE}.Cluster")
    def test_get_method_uses_query_params(self, mock_cluster):
        """GET 请求从 query_params 提取参数"""
        qs = mock_cluster.objects.using.return_value.filter.return_value
        qs.exists.return_value = True
        qs.values_list.return_value = [1]

        request = MagicMock()
        request.method = "GET"
        request.query_params = {"infos": [{"cluster_domain": "a.db"}]}

        auth_bill._auth_parse_infos_clusters(request, ClusterType.TenDBHA)
        mock_cluster.objects.using.return_value.filter.assert_called_once_with(
            immute_domain__in=["a.db"], cluster_type=ClusterType.TenDBHA
        )


class TestAuthParseDispatchers:
    """4 个鉴权解析器按集群类型正确分发"""

    @pytest.mark.parametrize(
        "func_name, expected_type",
        [
            ("auth_parse_mysql_proxy_conf_change", ClusterType.TenDBHA),
            ("auth_parse_mysql_migrate", ClusterType.TenDBHA),
            ("auth_parse_spider_conf_change", ClusterType.TenDBCluster),
            ("auth_parse_tendbcluster_node_rebalance", ClusterType.TenDBCluster),
        ],
    )
    @patch(f"{MODULE}.Cluster")
    def test_dispatcher_uses_correct_cluster_type(self, mock_cluster, func_name, expected_type):
        """各解析器必须按对应集群类型过滤"""
        qs = mock_cluster.objects.using.return_value.filter.return_value
        qs.exists.return_value = True
        qs.values_list.return_value = [1]

        func = getattr(auth_bill, func_name)
        func(_request(infos=[{"cluster_domain": "a.db"}]))

        mock_cluster.objects.using.return_value.filter.assert_called_once_with(
            immute_domain__in=["a.db"], cluster_type=expected_type
        )
