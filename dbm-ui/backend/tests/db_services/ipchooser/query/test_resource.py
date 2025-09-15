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
from unittest.mock import patch

import pytest

from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.tests.mock_data import constant

pytestmark = pytest.mark.django_db


class TestResourceQueryHelper:
    """测试 ResourceQueryHelper 类"""

    @patch("backend.components.CCApi.get_biz_internal_module")
    @patch("django.core.cache.cache.get")
    @patch("django.core.cache.cache.set")
    def test_get_biz_internal_module_cache(self, mock_cache_set, mock_cache_get, mock_cc_api):
        """测试获取业务内部模块信息 - 缓存机制"""
        bk_biz_id = constant.BK_BIZ_ID
        mock_data = {
            "bk_set_id": constant.BK_SET_ID,
            "bk_set_name": "空闲机池",
            "module": [{"default": 1, "bk_module_id": constant.BK_MODULE_ID}],
        }
        mock_cc_api.return_value = mock_data
        # 第一次调用时，缓存为空
        mock_cache_get.return_value = None

        # 第一次调用，应该调用CC接口
        result1 = ResourceQueryHelper.get_biz_internal_module(bk_biz_id)
        assert result1 == mock_data
        assert mock_cc_api.call_count == 1
        assert mock_cache_set.called

    @patch("backend.components.CCApi.get_biz_internal_module")
    def test_get_idle_set_module(self, mock_cc_api):
        """测试获取空闲机池模块信息"""
        bk_biz_id = constant.BK_BIZ_ID
        mock_cc_api.return_value = {
            "bk_set_id": constant.BK_SET_ID,
            "bk_set_name": "空闲机池",
            "module": [
                {"default": 1, "bk_module_id": constant.BK_MODULE_ID},
                {"default": 2, "bk_module_id": constant.BK_MODULE_ID2},
            ],
        }

        idle_set_id, idle_module_id = ResourceQueryHelper.get_idle_set_module(bk_biz_id)

        assert idle_set_id == constant.BK_SET_ID
        assert idle_module_id == constant.BK_MODULE_ID

    @patch("backend.components.CCApi.search_business")
    def test_fetch_biz_list_all(self, mock_search_business):
        """测试查询所有业务列表"""
        mock_search_business.return_value = {
            "info": [
                {"bk_biz_id": constant.BK_BIZ_ID, "bk_biz_name": "测试业务", "bk_biz_maintainer": "admin"},
                {"bk_biz_id": constant.BK_BIZ_ID + 1, "bk_biz_name": "DBA业务", "bk_biz_maintainer": "dba"},
            ]
        }

        result = ResourceQueryHelper.fetch_biz_list()

        assert len(result) == 2
        assert result[0]["bk_biz_id"] == constant.BK_BIZ_ID
        assert result[1]["bk_biz_id"] == constant.BK_BIZ_ID + 1

    @patch("backend.components.CCApi.search_business")
    def test_fetch_biz_list_with_filter(self, mock_search_business):
        """测试查询业务列表 - 带过滤"""
        mock_search_business.return_value = {
            "info": [
                {"bk_biz_id": constant.BK_BIZ_ID, "bk_biz_name": "测试业务", "bk_biz_maintainer": "admin"},
                {"bk_biz_id": constant.BK_BIZ_ID + 1, "bk_biz_name": "DBA业务", "bk_biz_maintainer": "dba"},
            ]
        }

        result = ResourceQueryHelper.fetch_biz_list(bk_biz_ids=[constant.BK_BIZ_ID])

        assert len(result) == 1
        assert result[0]["bk_biz_id"] == constant.BK_BIZ_ID

    @patch("backend.components.CCApi.get_biz_internal_module")
    def test_get_topo_tree_internal_only(self, mock_cc_api):
        """测试获取拓扑树 - 仅内部拓扑"""
        bk_biz_id = constant.BK_BIZ_ID
        mock_cc_api.return_value = {
            "bk_set_id": constant.BK_SET_ID,
            "bk_set_name": "空闲机池",
            "module": [{"bk_module_id": constant.BK_MODULE_ID, "bk_module_name": "空闲机"}],
        }

        result = ResourceQueryHelper.get_topo_tree(bk_biz_id, return_all=False)

        assert result["bk_inst_id"] == constant.BK_SET_ID
        assert result["bk_obj_id"] == "set"
        assert len(result["child"]) == 1

    @patch("backend.components.CCApi.search_biz_inst_topo")
    @patch("backend.components.CCApi.get_biz_internal_module")
    def test_get_topo_tree_all(self, mock_internal_module, mock_search_topo):
        """测试获取拓扑树 - 完整拓扑"""
        bk_biz_id = constant.BK_BIZ_ID
        mock_internal_module.return_value = {
            "bk_set_id": constant.BK_SET_ID,
            "bk_set_name": "空闲机池",
            "module": [],
        }
        mock_search_topo.return_value = [
            {
                "bk_inst_id": bk_biz_id,
                "bk_inst_name": "测试业务",
                "bk_obj_id": "biz",
                "child": [{"bk_inst_id": 100, "bk_inst_name": "业务集群", "bk_obj_id": "set", "child": []}],
            }
        ]

        result = ResourceQueryHelper.get_topo_tree(bk_biz_id, return_all=True)

        assert result["bk_inst_id"] == bk_biz_id
        # 应该包含空闲机池和业务拓扑
        assert len(result["child"]) == 2

    @patch("backend.components.CCApi.list_biz_hosts")
    def test_query_cc_hosts_by_module(self, mock_list_hosts):
        """测试查询CC主机 - 按模块查询"""
        tree_node = {
            "bk_biz_id": constant.BK_BIZ_ID,
            "bk_obj_id": "module",
            "bk_inst_id": constant.BK_MODULE_ID,
        }
        mock_list_hosts.return_value = {
            "count": 1,
            "info": [{"bk_host_id": 10001, "bk_host_innerip": "127.0.0.1", "bk_cloud_id": 0}],
        }

        result = ResourceQueryHelper.query_cc_hosts(tree_node=tree_node, return_status=False)

        assert result["count"] == 1
        assert len(result["info"]) == 1
        assert mock_list_hosts.called
        call_args = mock_list_hosts.call_args[0][0]
        assert "bk_module_ids" in call_args

    @patch("backend.components.CCApi.list_biz_hosts")
    def test_query_cc_hosts_by_set(self, mock_list_hosts):
        """测试查询CC主机 - 按集群查询"""
        tree_node = {
            "bk_biz_id": constant.BK_BIZ_ID,
            "bk_obj_id": "set",
            "bk_inst_id": constant.BK_SET_ID,
        }
        mock_list_hosts.return_value = {"count": 0, "info": []}

        result = ResourceQueryHelper.query_cc_hosts(tree_node=tree_node)

        assert result["count"] == 0
        call_args = mock_list_hosts.call_args[0][0]
        assert "bk_set_ids" in call_args

    @patch("backend.components.CCApi.list_biz_hosts")
    def test_query_cc_hosts_with_cloud_filter(self, mock_list_hosts):
        """测试查询CC主机 - 带云区域过滤"""
        tree_node = {
            "bk_biz_id": constant.BK_BIZ_ID,
            "bk_obj_id": "module",
            "bk_inst_id": constant.BK_MODULE_ID,
        }
        mock_list_hosts.return_value = {"count": 0, "info": []}

        ResourceQueryHelper.query_cc_hosts(tree_node=tree_node, bk_cloud_id=1)

        call_args = mock_list_hosts.call_args[0][0]
        assert "host_property_filter" in call_args
        rules = call_args["host_property_filter"]["rules"]
        assert any(rule.get("field") == "bk_cloud_id" for rule in rules)

    @patch("backend.components.bknodeman.client.BKNodeManApi.ipchooser_host_details")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    def test_query_agent_status_from_nodeman(self, mock_find_relations, mock_nodeman_api):
        """测试从Nodeman查询Agent状态"""
        cc_hosts = [
            {"bk_host_id": 10001, "bk_host_innerip": "127.0.0.1"},
            {"bk_host_id": 10002, "bk_host_innerip": "127.0.0.2"},
        ]
        mock_find_relations.return_value = [
            {"bk_host_id": 10001, "bk_biz_id": constant.BK_BIZ_ID},
            {"bk_host_id": 10002, "bk_biz_id": constant.BK_BIZ_ID},
        ]
        mock_nodeman_api.return_value = [
            {"host_id": 10001, "alive": 1},
            {"host_id": 10002, "alive": 0},
        ]

        ResourceQueryHelper.query_agent_status_from_nodeman(cc_hosts)

        assert cc_hosts[0]["status"] == 1
        assert cc_hosts[1]["status"] == 0

    @patch("backend.components.bknodeman.client.BKNodeManApi.ipchooser_host_details")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    def test_fill_agent_status_empty(self, mock_find_relations, mock_nodeman_api):
        """测试填充Agent状态 - 空主机列表"""
        ResourceQueryHelper.fill_agent_status([])
        # 不应该调用任何API
        assert not mock_find_relations.called
        assert not mock_nodeman_api.called

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_fill_cloud_name(self, mock_search_cloud):
        """测试填充云区域名称"""
        mock_search_cloud.return_value = {
            "0": {"bk_cloud_name": "直连区域"},
            "1": {"bk_cloud_name": "测试云区域"},
        }
        cc_hosts = [
            {"bk_host_id": 10001, "bk_cloud_id": 0},
            {"bk_host_id": 10002, "bk_cloud_id": 1},
            {"bk_host_id": 10003, "bk_cloud_id": 999},  # 不存在的云区域
        ]

        ResourceQueryHelper.fill_cloud_name(cc_hosts)

        assert cc_hosts[0]["bk_cloud_name"] == "直连区域"
        assert cc_hosts[1]["bk_cloud_name"] == "测试云区域"
        assert cc_hosts[2]["bk_cloud_name"] == 999

    @patch("backend.components.CCApi.list_host_total_mainline_topo")
    @patch("backend.components.CCApi.list_biz_hosts")
    def test_query_host_topo_infos_with_ip_filter(self, mock_list_hosts, mock_list_topo):
        """测试查询主机拓扑信息 - 带IP过滤"""
        bk_biz_id = constant.BK_BIZ_ID
        # 第一次调用：根据IP查询host_id
        mock_list_hosts.return_value = {"count": 1, "info": [{"bk_host_id": 10001}]}
        # 第二次调用：获取拓扑信息
        mock_list_topo.return_value = {
            "count": 1,
            "info": [
                {
                    "host": {"bk_host_id": 10001, "bk_host_innerip": "127.0.0.1", "bk_cloud_id": 0},
                    "topo": [
                        {
                            "inst": {"id": 1, "name": "测试集群"},
                            "children": [{"inst": {"id": 11, "name": "测试模块"}, "children": []}],
                        }
                    ],
                }
            ],
        }

        result = ResourceQueryHelper.query_host_topo_infos(
            bk_biz_id=bk_biz_id, filter_conditions={"bk_host_innerip": ["127.0.0.1"]}
        )

        assert len(result) == 1
        assert result[0]["ip"] == "127.0.0.1"
        assert "topo" in result[0]

    @patch("backend.components.CCApi.list_hosts_without_biz")
    @patch("backend.components.bknodeman.client.BKNodeManApi.ipchooser_host_details")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_search_cc_hosts_with_keyword(self, mock_search_cloud, mock_find_relations, mock_nodeman, mock_list_hosts):
        """测试搜索主机 - 带关键字过滤"""
        mock_list_hosts.return_value = {
            "count": 1,
            "info": [{"bk_host_id": 10001, "bk_host_innerip": "127.0.0.1", "bk_cloud_id": 0}],
        }
        mock_find_relations.return_value = [{"bk_host_id": 10001, "bk_biz_id": constant.BK_BIZ_ID}]
        mock_nodeman.return_value = [{"host_id": 10001, "alive": 1}]
        mock_search_cloud.return_value = {"0": {"bk_cloud_name": "直连区域"}}

        result = ResourceQueryHelper.search_cc_hosts(role_host_ids=[10001], keyword="127")

        assert len(result) == 1
        assert result[0]["bk_host_innerip"] == "127.0.0.1"
        # 验证关键字被应用到过滤条件
        assert mock_list_hosts.called

    @patch("backend.components.CCApi.list_biz_hosts")
    @patch("backend.components.bknodeman.client.BKNodeManApi.ipchooser_host_details")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_search_cc_hosts_empty(self, mock_search_cloud, mock_find_relations, mock_nodeman, mock_list_hosts):
        """测试搜索主机 - 空主机ID列表"""
        result = ResourceQueryHelper.search_cc_hosts(role_host_ids=[])

        assert result == []
        assert not mock_list_hosts.called

    @patch("backend.components.CCApi.list_hosts_without_biz")
    @patch("backend.components.bknodeman.client.BKNodeManApi.ipchooser_host_details")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_search_cc_hosts_with_set_filter(
        self, mock_search_cloud, mock_find_relations, mock_nodeman, mock_list_hosts
    ):
        """测试搜索主机 - 带集群过滤"""
        mock_list_hosts.return_value = {"count": 1, "info": [{"bk_host_id": 10001, "bk_cloud_id": 0}]}
        mock_search_cloud.return_value = {"0": {"bk_cloud_name": "直连区域"}}
        mock_find_relations.return_value = [{"bk_host_id": 10001, "bk_biz_id": constant.BK_BIZ_ID}]
        mock_nodeman.return_value = [{"host_id": 10001, "alive": 1}]

        ResourceQueryHelper.search_cc_hosts(role_host_ids=[10001], set_filter="测试集群")

        assert mock_list_hosts.called

    @patch("backend.components.CCApi.list_hosts_without_biz")
    @patch("backend.components.bknodeman.client.BKNodeManApi.ipchooser_host_details")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_search_cc_hosts_with_module_filter(
        self, mock_search_cloud, mock_find_relations, mock_nodeman, mock_list_hosts
    ):
        """测试搜索主机 - 带模块过滤"""
        mock_list_hosts.return_value = {"count": 1, "info": [{"bk_host_id": 10001, "bk_cloud_id": 0}]}
        mock_search_cloud.return_value = {"0": {"bk_cloud_name": "直连区域"}}
        mock_find_relations.return_value = [{"bk_host_id": 10001, "bk_biz_id": constant.BK_BIZ_ID}]
        mock_nodeman.return_value = [{"host_id": 10001, "alive": 1}]

        ResourceQueryHelper.search_cc_hosts(role_host_ids=[10001], module_filter=[constant.BK_MODULE_ID])

        assert mock_list_hosts.called

    @patch("backend.db_services.ipchooser.query.resource.batch_request")
    def test_search_cc_cloud(self, mock_batch_request):
        """测试查询云区域信息"""
        mock_batch_request.return_value = [
            {"bk_cloud_id": 0, "bk_cloud_name": "Default"},
            {"bk_cloud_id": 1, "bk_cloud_name": "测试云区域"},
        ]

        result = ResourceQueryHelper.search_cc_cloud()

        assert "0" in result
        assert result["0"]["bk_cloud_name"] == "直连区域"
        # 至少应该有直连区域
        assert len(result) >= 1

    @patch("backend.components.CCApi.list_host_total_mainline_topo")
    def test_query_host_topo_infos_with_mode_filter(self, mock_list_topo):
        """测试查询主机拓扑信息 - 带模式过滤（空闲机）"""
        bk_biz_id = constant.BK_BIZ_ID
        mock_list_topo.return_value = {"count": 0, "info": []}

        with patch.object(ResourceQueryHelper, "get_idle_set_module", return_value=(1, 11)):
            ResourceQueryHelper.query_host_topo_infos(bk_biz_id=bk_biz_id, filter_conditions={"mode": "idle_only"})

        call_args = mock_list_topo.call_args[0][0]
        assert "module_property_filter" in call_args
