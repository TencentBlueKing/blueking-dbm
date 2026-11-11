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

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import BKCity, Cluster, Machine, StorageInstance
from backend.tests.mock_data import constant
from backend.ticket.builders.common.base import cluster_location_spec

pytestmark = pytest.mark.django_db


def create_cluster(name: str, cloud_zones=None, bk_cloud_region: str = "") -> Cluster:
    return Cluster.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        name=name,
        immute_domain=f"{name}.db",
        cluster_type=ClusterType.TenDBSingle.value,
        db_module_id=1,
        # region 即将下线，这里故意留空/写 default，确认逻辑不再读它
        region="default",
        cloud_zone_list=cloud_zones or [],
        bk_cloud_region=bk_cloud_region,
        creator="admin",
        updater="admin",
    )


def add_storage(cluster: Cluster, ip: str, host_id: int, port: int) -> Machine:
    machine = Machine.objects.create(
        ip=ip,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=BKCity.objects.first(),
        bk_cloud_id=0,
        bk_host_id=host_id,
        creator="admin",
        updater="admin",
    )
    storage = StorageInstance.objects.create(machine=machine, port=port, creator="admin", updater="admin")
    cluster.storageinstance_set.add(storage)
    return machine


def test_city_comes_from_machine_not_cluster_region():
    """城市从实例机器反查逻辑城，Cluster.region 是 default 也不影响"""
    cluster = create_cluster("test-loc-city", cloud_zones=["ap-guangzhou-3"], bk_cloud_region="ap-guangzhou")
    machine = add_storage(cluster, "127.0.0.201", 9201, 20101)

    location_spec = cluster_location_spec(cluster)

    assert location_spec["city"] == machine.bk_city.logical_city.name
    assert location_spec["bk_cloud_zone_list"] == ["ap-guangzhou-3"]
    assert location_spec["bk_cloud_region"] == "ap-guangzhou"


def test_no_instance_means_no_city():
    """集群还没有实例时反查不到城市，就不带 city 字段（而不是塞 default）"""
    cluster = create_cluster("test-loc-no-instance", cloud_zones=["ap-guangzhou-3"], bk_cloud_region="ap-guangzhou")

    location_spec = cluster_location_spec(cluster)

    assert "city" not in location_spec
    assert location_spec["bk_cloud_region"] == "ap-guangzhou"
    assert location_spec["bk_cloud_zone_list"] == ["ap-guangzhou-3"]


def test_returns_none_when_nothing_known():
    """没有任何位置信息时返回 None，表示不限位置（不再用 city=default 当哨兵）"""
    cluster = create_cluster("test-loc-empty")

    assert cluster_location_spec(cluster) is None


def test_cloud_zone_list_override():
    """显式传空可用区时（跨机架/无亲和性），只保留地域"""
    cluster = create_cluster("test-loc-override", cloud_zones=["ap-guangzhou-3"], bk_cloud_region="ap-guangzhou")
    add_storage(cluster, "127.0.0.202", 9202, 20102)

    location_spec = cluster_location_spec(cluster, cloud_zone_list=[])

    assert "bk_cloud_zone_list" not in location_spec
    assert location_spec["bk_cloud_region"] == "ap-guangzhou"
