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
import pytest

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.dataclass import DBInstance

pytestmark = pytest.mark.django_db


class TestClusterServiceHandler:
    def test_find_related_clusters_by_cluster_id(self, bk_biz_id, dbha_cluster):
        results = ClusterServiceHandler(bk_biz_id).find_related_clusters_by_cluster_ids([dbha_cluster.id])
        assert results
        for result in results:
            assert result["cluster_info"]["bk_biz_id"] == bk_biz_id
            for related_cluster in result["related_clusters"]:
                assert related_cluster["id"] != result["cluster_info"]["id"]

    def test_find_related_clusters_by_instances(self, bk_biz_id, dbha_cluster):
        masters = StorageInstance.objects.filter(
            cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER.value
        )
        master_results = ClusterServiceHandler(bk_biz_id=bk_biz_id).find_related_clusters_by_instances(
            [DBInstance.from_inst_obj(master) for master in masters]
        )
        assert master_results
        for result in master_results:
            assert result["cluster_info"]["bk_biz_id"] == bk_biz_id
            for related_cluster in result["related_clusters"]:
                assert related_cluster["id"] != result["cluster_info"]["id"]

        proxies = ProxyInstance.objects.filter(cluster=dbha_cluster)
        proxy_results = ClusterServiceHandler(bk_biz_id=bk_biz_id).find_related_clusters_by_instances(
            [DBInstance.from_inst_obj(proxy) for proxy in proxies]
        )
        # 此case中master和proxy属于相同集群，因此结果应该是一致的
        assert master_results[0]["cluster_info"] == proxy_results[0]["cluster_info"]
        assert master_results[0]["related_clusters"] == proxy_results[0]["related_clusters"]
