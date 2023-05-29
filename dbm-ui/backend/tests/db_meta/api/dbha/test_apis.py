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
import ipaddress

import pytest
from rest_framework.exceptions import ValidationError

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api, models
from backend.db_meta.enums import (
    AccessLayer,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db

TEST_PROXY_PORT1 = 10000
TEST_PROXY_PORT2 = 10001
TEST_PROXY_PORT3 = 10002

TEST_STORAGE_PORT1 = 20000
TEST_STORAGE_PORT2 = 20001
TEST_STORAGE_PORT3 = 20002


@pytest.fixture
def dbha_fixture(create_city):
    ap = models.App.objects.create(bk_biz_id=constant.BK_BIZ_ID, bk_set_id=constant.BK_SET_ID)
    # TODO 提取常量，把 conftest 里的 yaml 用常量维护起来
    city1 = models.BKCity.objects.get(bk_idc_city_name="南京")
    city2 = models.BKCity.objects.get(bk_idc_city_name="上海")
    m1 = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=ap.bk_biz_id,
        machine_type=MachineType.PROXY,
        access_layer=AccessLayer.PROXY,
        bk_city=city1,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP)),
    )
    m2 = models.Machine.objects.create(
        ip=cc.NORMAL_IP2,
        bk_biz_id=ap.bk_biz_id,
        machine_type=MachineType.BACKEND,
        access_layer=AccessLayer.STORAGE,
        bk_city=city2,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP2)),
    )
    m3 = models.Machine.objects.create(
        ip=cc.NORMAL_IP3,
        bk_biz_id=ap.bk_biz_id,
        machine_type=MachineType.BACKEND,
        access_layer=AccessLayer.STORAGE,
        bk_city=city2,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP3)),
    )

    p1 = models.ProxyInstance.objects.create(port=TEST_PROXY_PORT1, machine=m1, status=InstanceStatus.RUNNING)
    p2 = models.ProxyInstance.objects.create(port=TEST_PROXY_PORT2, machine=m1, status=InstanceStatus.RUNNING)
    p3 = models.ProxyInstance.objects.create(port=TEST_PROXY_PORT3, machine=m1, status=InstanceStatus.UNAVAILABLE)

    s1 = models.StorageInstance.objects.create(
        port=TEST_STORAGE_PORT1,
        machine=m2,
        status=InstanceStatus.RUNNING,
        instance_role=InstanceRole.BACKEND_MASTER,
        instance_inner_role=InstanceInnerRole.MASTER,
    )
    models.StorageInstance.objects.create(
        port=TEST_STORAGE_PORT2,
        machine=m2,
        status=InstanceStatus.RUNNING,
        instance_role=InstanceRole.BACKEND_MASTER,
        instance_inner_role=InstanceInnerRole.MASTER,
    )
    models.StorageInstance.objects.create(
        port=TEST_STORAGE_PORT3,
        machine=m2,
        status=InstanceStatus.UNAVAILABLE,
        instance_role=InstanceRole.BACKEND_SLAVE,
        instance_inner_role=InstanceInnerRole.SLAVE,
    )

    s2 = models.StorageInstance.objects.create(
        port=TEST_STORAGE_PORT1,
        machine=m3,
        status=InstanceStatus.UNAVAILABLE,
        instance_role=InstanceRole.BACKEND_SLAVE,
        instance_inner_role=InstanceInnerRole.SLAVE,
    )
    models.StorageInstance.objects.create(
        port=TEST_STORAGE_PORT2,
        machine=m3,
        status=InstanceStatus.RUNNING,
        instance_role=InstanceRole.BACKEND_MASTER,
        instance_inner_role=InstanceInnerRole.MASTER,
    )
    models.StorageInstance.objects.create(
        port=TEST_STORAGE_PORT3,
        machine=m3,
        status=InstanceStatus.UNAVAILABLE,
        instance_role=InstanceRole.BACKEND_SLAVE,
        instance_inner_role=InstanceInnerRole.SLAVE,
    )

    models.StorageInstanceTuple.objects.create(ejector=s1, receiver=s2)
    s1.proxyinstance_set.add(p1, p2)

    cluster = models.Cluster.objects.create(
        bk_biz_id=ap.bk_biz_id,
        name=constant.CLUSTER_NAME,
        db_module_id=constant.DB_MODULE_ID,
        immute_domain=constant.CLUSTER_IMMUTE_DOMAIN,
        cluster_type=ClusterType.TenDBHA.value,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
    )
    cluster.storageinstance_set.add(s1, s2)
    cluster.proxyinstance_set.add(p1, p2, p3)


class TestDBHA:
    def test_cities(self, dbha_fixture):
        assert len(api.dbha.cities()) > 0

    def test_instance_all(self, dbha_fixture):
        assert len(api.dbha.instances()) == 9

    def test_instance_with_city1_filter(self, dbha_fixture):
        assert len(api.dbha.instances(logical_city_ids=[1])) == 3

    def test_instance_with_city2_filter(self, dbha_fixture):
        assert len(api.dbha.instances(logical_city_ids=[2])) == 6

    def test_instance_filter1(self, dbha_fixture):
        assert (
            len(
                api.dbha.instances(
                    logical_city_ids=[1, 2],
                    addresses=[
                        f"{cc.IP_NOT_IN_BKCC}{IP_PORT_DIVIDER}30000",
                        cc.NORMAL_IP,
                        f"{cc.NORMAL_IP2}{IP_PORT_DIVIDER}{TEST_STORAGE_PORT1}",
                    ],
                )
            )
            == 4
        )

    def test_instance_filter2(self, dbha_fixture):
        assert len(api.dbha.instances(statuses=[InstanceStatus.UNAVAILABLE.value])) == 4

    def test_update_success(self, dbha_fixture):
        api.dbha.update_status(
            [
                {"ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT1, "status": InstanceStatus.RUNNING.value},
                {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT1, "status": InstanceStatus.UNAVAILABLE.value},
                {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT2, "status": InstanceStatus.RUNNING.value},  # 实例不属于任何集群
                {"ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT3, "status": InstanceStatus.UNAVAILABLE.value},  # 同步修改集群状态
            ],
            bk_cloud_id=0,
        )
        assert models.ProxyInstance.objects.filter(
            machine__ip=cc.NORMAL_IP, port=TEST_PROXY_PORT1, status=InstanceStatus.RUNNING.value
        ).exists()
        assert models.StorageInstance.objects.filter(
            machine__ip=cc.NORMAL_IP2, port=TEST_STORAGE_PORT1, status=InstanceStatus.UNAVAILABLE.value
        ).exists()
        assert models.StorageInstance.objects.filter(
            machine__ip=cc.NORMAL_IP2, port=TEST_STORAGE_PORT2, status=InstanceStatus.RUNNING.value
        ).exists()
        assert models.ProxyInstance.objects.filter(
            machine__ip=cc.NORMAL_IP, port=TEST_PROXY_PORT3, status=InstanceStatus.UNAVAILABLE.value
        ).exists()

        p = models.ProxyInstance.objects.get(
            machine__ip=cc.NORMAL_IP, port=TEST_PROXY_PORT3, status=InstanceStatus.UNAVAILABLE.value
        )
        assert p.cluster.first().status == ClusterStatus.ABNORMAL.value

    def test_update_invalid_status(self):
        with pytest.raises(Exception):
            api.dbha.update_status(
                [
                    {"ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT1, "status": "not_found"},
                ]
            )

    def test_update_instance_not_found(self):
        with pytest.raises(Exception):
            api.dbha.update_status(
                [
                    {"ip": cc.IP_NOT_IN_BKCC, "port": TEST_PROXY_PORT1, "status": InstanceStatus.RUNNING.value},
                ]
            )

    def test_update_missing_key(self):
        with pytest.raises(ValidationError):
            api.dbha.update_status(
                [
                    {"ip": cc.IP_NOT_IN_BKCC, "port": TEST_PROXY_PORT1},
                ],
                bk_cloud_id=0,
            )

    def test_update_empty(self):
        with pytest.raises(ValidationError):
            api.dbha.update_status([], bk_cloud_id=0)

    def test_update_invalid_ip(self):
        with pytest.raises(ValidationError):
            api.dbha.update_status(
                [{"ip": "a.b.c.d", "port": TEST_PROXY_PORT1, "status": InstanceStatus.RUNNING.value}], bk_cloud_id=0
            )

    def test_update_invalid_port(self):
        with pytest.raises(ValidationError):
            api.dbha.update_status([{"ip": cc.NORMAL_IP, "port": "aa", "status": InstanceStatus.RUNNING.value}], 0)

    def test_swap_success(self, dbha_fixture):
        api.dbha.swap_role(
            [
                {
                    "instance1": {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT1},
                    "instance2": {"ip": cc.NORMAL_IP3, "port": TEST_STORAGE_PORT1},
                },
            ],
            bk_cloud_id=0,
        )
        assert (
            models.StorageInstanceTuple.objects.filter(
                ejector__machine__ip=cc.NORMAL_IP3,
                ejector__port=TEST_STORAGE_PORT1,
                receiver__machine__ip=cc.NORMAL_IP2,
                receiver__port=TEST_STORAGE_PORT1,
            ).count()
            == 1
        )

        assert (
            models.StorageInstance.objects.get(machine__ip=cc.NORMAL_IP2, port=TEST_STORAGE_PORT1).instance_inner_role
            == InstanceInnerRole.SLAVE
        )
        assert (
            models.StorageInstance.objects.get(machine__ip=cc.NORMAL_IP3, port=TEST_STORAGE_PORT1).instance_inner_role
            == InstanceInnerRole.MASTER
        )

        assert (
            models.StorageInstance.objects.get(
                machine__ip=cc.NORMAL_IP3, port=TEST_STORAGE_PORT1
            ).proxyinstance_set.count()
            == 2
        )
        assert not models.StorageInstance.objects.get(
            machine__ip=cc.NORMAL_IP2, port=TEST_STORAGE_PORT1
        ).proxyinstance_set.exists()

    def test_swap_only_1(self):
        with pytest.raises(Exception):
            api.dbha.swap_role([{"instance1": {"ip": cc.NORMAL_IP3, "port": TEST_STORAGE_PORT1}}])

    def test_swap_invalid_input(self):
        with pytest.raises(ValidationError):
            api.dbha.swap_role([{"instance1": {"ip": "a.c.b.c", "port": "aa"}}], bk_cloud_id=0)

    def test_swap_no_relation(self):
        with pytest.raises(Exception):
            api.dbha.swap_role(
                [
                    {
                        "instance1": {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT1},
                        "instance2": {"ip": cc.NORMAL_IP3, "port": TEST_STORAGE_PORT3},
                    }
                ]
            )
