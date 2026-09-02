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

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.endpoint import Side, resolve_endpoint


def _manager_returning(instance):
    manager = MagicMock()
    manager.select_related.return_value.filter.return_value.order_by.return_value.first.return_value = instance
    manager.select_related.return_value.order_by.return_value.first.return_value = instance
    return manager


def _cluster(cluster_type, *, storage=None, proxy=None):
    return SimpleNamespace(
        id=101,
        cluster_type=cluster_type,
        bk_cloud_id=7,
        storageinstance_set=_manager_returning(storage),
        proxyinstance_set=_manager_returning(proxy),
    )


class ResolveEndpointTest(TestCase):
    def setUp(self):
        self.instance = SimpleNamespace(
            machine=SimpleNamespace(ip="127.0.0.1"),
            port=3306,
        )

    def test_storage_endpoint_matrix(self):
        cases = (
            (ClusterType.TenDBHA.value, Side.SOURCE, InstanceRole.BACKEND_MASTER),
            (ClusterType.TenDBHA.value, Side.TARGET, InstanceRole.BACKEND_MASTER),
            (ClusterType.TenDBSingle.value, Side.SOURCE, InstanceRole.ORPHAN),
            (ClusterType.TenDBSingle.value, Side.TARGET, InstanceRole.ORPHAN),
            (ClusterType.TenDBCluster.value, Side.SOURCE, InstanceRole.REMOTE_MASTER),
        )
        for cluster_type, side, role in cases:
            with self.subTest(cluster_type=cluster_type, side=side):
                cluster = _cluster(cluster_type, storage=self.instance)
                endpoint = resolve_endpoint(cluster, side)
                self.assertEqual(endpoint.address, "127.0.0.1:3306")
                cluster.storageinstance_set.select_related.return_value.filter.assert_called_with(
                    instance_role=role.value
                )

    def test_tendbcluster_target_uses_spider_master(self):
        cluster = _cluster(ClusterType.TenDBCluster.value, proxy=self.instance)
        endpoint = resolve_endpoint(cluster, Side.TARGET)
        self.assertEqual(endpoint.address, "127.0.0.1:3306")
        cluster.proxyinstance_set.select_related.return_value.filter.assert_called_once()

    def test_explicit_address_overrides_default_mapping(self):
        cluster = _cluster("unsupported")
        endpoint = resolve_endpoint(cluster, Side.SOURCE, address="127.0.0.8:3307")
        self.assertEqual(endpoint.address, "127.0.0.8:3307")

    def test_invalid_address_fails(self):
        with self.assertRaises(PrecheckCollectError):
            resolve_endpoint(_cluster(ClusterType.TenDBHA.value), Side.SOURCE, address="bad")
