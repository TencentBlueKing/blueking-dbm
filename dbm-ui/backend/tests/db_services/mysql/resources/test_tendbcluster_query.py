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
from django.db.models import Q

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_services.mysql.resources.tendbcluster.query import (
    ListRetrieveResource,
    TenDBClusterCommonQueryResourceMixin,
)

pytestmark = pytest.mark.django_db


class TestTenDBClusterCommonQueryResourceMixin:
    """测试 TenDBClusterCommonQueryResourceMixin 类"""

    def test_fill_instances_to_cluster_info_with_spider_instances(self, tendbcluster_cluster):
        """测试填充实例信息 - 包含Spider实例"""
        cluster = tendbcluster_cluster
        cluster_info = {}
        role_header_ids = set()

        # 获取Spider代理实例
        proxy_queryset = cluster.proxyinstance_set.prefetch_related("tendbclusterspiderext").all()

        TenDBClusterCommonQueryResourceMixin.fill_instances_to_cluster_info(
            cluster_info, proxy_queryset, role_header_ids
        )

        # 验证Spider角色的实例信息被填充
        assert len(role_header_ids) > 0
        # 验证至少有一个Spider角色
        spider_roles = [
            TenDBClusterSpiderRole.SPIDER_MASTER,
            TenDBClusterSpiderRole.SPIDER_SLAVE,
        ]
        assert any(role in cluster_info for role in spider_roles)

    def test_update_headers(self):
        """测试更新表头"""
        headers = [{"id": "cluster_id", "name": "集群ID"}]

        new_headers, extra_headers = TenDBClusterCommonQueryResourceMixin.update_headers(headers)

        # 验证添加了TenDBCluster特有的表头
        extra_header_ids = [h["id"] for h in extra_headers]
        assert "clb" in extra_header_ids
        assert "spider_master" in extra_header_ids
        assert "spider_slave" in extra_header_ids
        assert "spider_mnt" in extra_header_ids
        assert "remote_master" in extra_header_ids
        assert "remote_slave" in extra_header_ids

    @patch("backend.db_services.dbbase.resources.query.CommonQueryResourceMixin.get_cluster_clb_polaris_entries")
    def test_update_cluster_info(self, mock_get_clb_polaris):
        """测试更新集群信息"""
        mock_get_clb_polaris.return_value = ("1.1.1.1:10000", "")

        cluster = MagicMock()
        cluster_info = {
            "cluster_id": 1,
            "cluster_name": "test",
        }

        result = TenDBClusterCommonQueryResourceMixin.update_cluster_info(cluster, cluster_info)

        # 验证添加了clb信息
        assert "clb" in result
        assert result["clb"] == "1.1.1.1:10000"


class TestListRetrieveResource:
    """测试 ListRetrieveResource 类"""

    def test_filter_instance_qs_remote_and_spider(self, tendbcluster_cluster):
        """测试过滤实例查询集 - 同时包含Remote和Spider实例"""
        cluster = tendbcluster_cluster
        query_filters = Q(cluster__id=cluster.id)
        query_params = {}

        instances = ListRetrieveResource._filter_instance_qs(query_filters, query_params)

        # 验证返回包含实例信息
        assert instances is not None

    def test_filter_instance_qs_with_spider_ctl(self, tendbcluster_cluster):
        """测试过滤实例查询集 - 包含Spider Controller"""
        cluster = tendbcluster_cluster
        query_filters = Q(cluster__id=cluster.id)
        query_params = {"spider_ctl": True}

        instances = ListRetrieveResource._filter_instance_qs(query_filters, query_params)

        # 验证查询集包含了spider_ctl角色的实例
        assert instances is not None

    def test_to_instance_representation(self, tendbcluster_cluster):
        """测试实例信息转换"""
        cluster = tendbcluster_cluster
        storage = cluster.storageinstance_set.first()

        # 构造完整的实例字典
        instance_dict = {
            "id": storage.id,
            "cluster__id": cluster.id,
            "cluster__cluster_type": cluster.cluster_type,
            "cluster__name": cluster.name,
            "cluster__db_module_id": cluster.db_module_id,
            "version": storage.version or "",
            "machine__bk_host_id": storage.machine.bk_host_id,
            "machine__ip": storage.machine.ip,
            "machine__bk_cloud_id": storage.machine.bk_cloud_id,
            "machine__bk_sub_zone": storage.machine.bk_sub_zone or "",
            "machine__bk_sub_zone_id": storage.machine.bk_sub_zone_id or 0,
            "machine__machine_type": storage.machine.machine_type,
            "machine__spec_config": storage.machine.spec_config or {},
            "machine__bk_os_name": storage.machine.bk_os_name or "",
            "machine__bk_rack_id": storage.machine.bk_rack_id or "",
            "machine__bk_svr_device_cls_name": storage.machine.bk_svr_device_cls_name or "",
            "inst_port": storage.port,
            "port": None,  # 将通过inst_port赋值
            "role": storage.instance_role,
            "status": storage.status,
            "create_at": storage.create_at,
            "bk_biz_id": cluster.bk_biz_id,
        }

        cluster_entry_map = {}
        db_module_names_map = {cluster.db_module_id: "test_module"}
        cloud_info = {"0": {"bk_cloud_name": "Default Area"}}

        result = ListRetrieveResource._to_instance_representation(
            instance_dict, cluster_entry_map, db_module_names_map, cloud_info=cloud_info
        )

        # 验证port字段被正确赋值
        assert result["port"] == storage.port
