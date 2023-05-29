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
import logging

import pytest
from django.test import Client

from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import (
    App,
    BKCity,
    BKModule,
    Cluster,
    ClusterEntry,
    DBModule,
    Machine,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)

logger = logging.getLogger("root")
pytestmark = pytest.mark.django_db
client = Client()

mocked_search_business_fake_app = {"count": 1, "info": [{"db_app_abbr": "fake_app"}]}


@pytest.fixture(scope="module")
def cluster_base_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        ap = App.objects.create(bk_biz_id=32, bk_set_id=132)

        DBModule.objects.create(
            bk_biz_id=ap.bk_biz_id, cluster_type=ClusterType.TenDBHA, db_module_id=100, db_module_name="rise"
        )

        BKModule.objects.create(bk_module_id=1, db_module_id=100, machine_type=MachineType.PROXY)
        BKModule.objects.create(bk_module_id=2, db_module_id=100, machine_type=MachineType.BACKEND)

        yield

        ClusterEntry.objects.all().delete()
        StorageInstanceTuple.objects.all().delete()
        Cluster.objects.all().delete()
        ProxyInstance.objects.all().delete()
        StorageInstance.objects.all().delete()
        Machine.objects.all().delete()
        DBModule.objects.all().delete()
        App.objects.all().delete()
        BKModule.objects.all().delete()


@pytest.fixture(scope="function")
def cluster_create_base_fixture(django_db_blocker, cluster_base_fixture):
    with django_db_blocker.unblock():
        ap = App.objects.get(bk_biz_id=32)

        bk_city = BKCity.objects.first()

        pm1 = Machine.objects.create(
            ip="1.1.1.1",
            bk_biz_id=ap.bk_biz_id,
            machine_type=MachineType.PROXY,
            access_layer=AccessLayer.PROXY,
            bk_city=bk_city,
        )
        pm2 = Machine.objects.create(
            ip="2.2.2.2",
            bk_biz_id=ap.bk_biz_id,
            machine_type=MachineType.PROXY,
            access_layer=AccessLayer.PROXY,
            bk_city=bk_city,
        )
        sm1 = Machine.objects.create(
            ip="3.3.3.3",
            bk_biz_id=ap.bk_biz_id,
            machine_type=MachineType.BACKEND,
            access_layer=AccessLayer.STORAGE,
            bk_city=bk_city,
        )
        sm2 = Machine.objects.create(
            ip="4.4.4.4",
            bk_biz_id=ap.bk_biz_id,
            machine_type=MachineType.BACKEND,
            access_layer=AccessLayer.STORAGE,
            bk_city=bk_city,
        )

        ProxyInstance.objects.create(port=10000, machine=pm1)
        ProxyInstance.objects.create(port=10000, machine=pm2)
        s1 = StorageInstance.objects.create(
            port=20000,
            machine=sm1,
            instance_role=InstanceRole.BACKEND_MASTER,
            instance_inner_role=InstanceInnerRole.MASTER,
        )
        s2 = StorageInstance.objects.create(
            port=20000,
            machine=sm2,
            instance_role=InstanceRole.BACKEND_SLAVE,
            instance_inner_role=InstanceInnerRole.SLAVE,
        )

        StorageInstanceTuple.objects.create(ejector=s1, receiver=s2)
        # p1.storageinstance.add(s1)
        # p2.storageinstance.add(s1)


@pytest.fixture(scope="function")
def cluster_create_dirty_base(django_db_blocker, cluster_create_base_fixture):
    ap = App.objects.get(bk_biz_id=32)
    # cluster_type = MetaClusterType.objects.get(name=MetaClusterType.ClusterTypeChoice.TenDBHA)
    db_module = DBModule.objects.get(db_module_id=100)
    # p = ProxyInstance.objects.get(port=10000, machine__ip='1.1.1.1')

    Cluster.objects.create(
        name="dirty",
        bk_biz_id=ap.bk_biz_id,
        cluster_type=ClusterType.TenDBHA,
        db_module_id=db_module.db_module_id,
        immute_domain="dirty.test.db",
    )


@pytest.fixture(scope="function")
def cluster_create_proxy_in_another_cluster(django_db_blocker, cluster_create_dirty_base):
    p = ProxyInstance.objects.get(port=10000, machine__ip="1.1.1.1")
    dirty_cluster = Cluster.objects.get(name="dirty")

    dirty_cluster.proxyinstance_set.add(p)


@pytest.fixture(scope="function")
def cluster_create_dirty_storage(django_db_blocker, cluster_create_dirty_base):
    s = StorageInstance.objects.get(port=20000, machine__ip="3.3.3.3")
    dirty_cluster = Cluster.objects.get(name="dirty")

    dirty_cluster.storageinstance_set.add(s)


@pytest.fixture(scope="function")
def cluster_create_dirty_proxy(django_db_blocker, cluster_create_dirty_base):
    with django_db_blocker.unblock():
        pm = Machine.objects.get(ip="1.1.1.1")
        s1 = StorageInstance.objects.get(machine__ip="3.3.3.3", port=20000)
        p = ProxyInstance.objects.create(port=10001, machine=pm)
        dirty_cluster = Cluster.objects.get(name="dirty")
        dirty_cluster.proxyinstance_set.add(p)
        p.storageinstance.add(s1)


@pytest.fixture(scope="function")
def cluster_create_wrong_bkd(django_db_blocker, cluster_create_base_fixture):
    with django_db_blocker.unblock():
        pm = Machine.objects.get(ip="1.1.1.1")
        p = ProxyInstance.objects.create(port=10001, machine=pm)

        s = StorageInstance.objects.create(
            port=20001,
            machine=Machine.objects.get(ip="3.3.3.3"),
            instance_role=InstanceRole.BACKEND_MASTER,
            instance_inner_role=InstanceInnerRole.MASTER,
        )

        # p = ProxyInstance.objects.get(port=10001, machine__ip='1.1.1.1')
        p.storageinstance.add(s)


@pytest.fixture(scope="function")
def cluster_create_more_proxy_storage(django_db_blocker, cluster_create_base_fixture):
    pm = Machine.objects.get(ip="1.1.1.1")
    sm = Machine.objects.get(ip="3.3.3.3")

    ProxyInstance.objects.create(port=10001, machine=pm)
    StorageInstance.objects.create(
        port=20001, machine=sm, instance_role=InstanceRole.BACKEND_MASTER, instance_inner_role=InstanceInnerRole.MASTER
    )


@pytest.fixture(scope="function")
def cluster_create_missing_storage(django_db_blocker, cluster_create_base_fixture):
    s = StorageInstance.objects.get(machine__ip="3.3.3.3", port=20000)
    s.instance_role = InstanceRole.BACKEND_SLAVE
    s.instance_inner_role = InstanceInnerRole.SLAVE
    s.save(update_fields=["instance_role", "instance_inner_role"])


@pytest.fixture(scope="function")
def cluster_create_missing_slave(django_db_blocker, cluster_create_base_fixture):
    StorageInstance.objects.create(
        port=20001,
        machine=Machine.objects.get(ip="3.3.3.3"),
        instance_role=InstanceRole.BACKEND_REPEATER,
        instance_inner_role=InstanceInnerRole.REPEATER,
    )


@pytest.fixture(scope="function")
def cluster_create_dirty_tuple_record(django_db_blocker, cluster_create_base_fixture):
    s1 = StorageInstance.objects.get(machine__ip="3.3.3.3", port=20000)

    m = Machine.objects.get(ip="4.4.4.4")
    s2 = StorageInstance.objects.create(machine=m, port=30000)
    StorageInstanceTuple.objects.create(ejector=s1, receiver=s2)


@pytest.fixture(scope="function")
def cluster_create_missing_related_slave(django_db_blocker, cluster_create_base_fixture):
    s1 = StorageInstance.objects.create(
        port=20001,
        machine=Machine.objects.get(ip="4.4.4.4"),
        instance_role=InstanceRole.BACKEND_REPEATER,
        instance_inner_role=InstanceInnerRole.REPEATER,
    )
    s2 = StorageInstance.objects.get(machine__ip="3.3.3.3", port=20000)
    StorageInstanceTuple.objects.create(ejector=s2, receiver=s1)
