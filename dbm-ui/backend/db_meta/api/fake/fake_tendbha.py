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
import logging
from typing import List, Optional

from django.db import transaction
from django.db.models import Q

from backend.constants import DEFAULT_BK_CLOUD_ID, IP_PORT_DIVIDER
from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import (
    App,
    BKCity,
    Cluster,
    ClusterEntry,
    DBModule,
    LogicalCity,
    Machine,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)

logger = logging.getLogger("root")


@transaction.atomic
def fake_create_tendbha_cluster(
    proxies: List[str],
    master_instance: str,
    slave_instance: str,
    immute_domain: str,
    name: Optional[str] = None,
    bk_biz_id: Optional[int] = None,
    db_module_id: Optional[int] = None,
    slave_domain: Optional[str] = None,
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
):

    if bk_biz_id:
        if not App.objects.filter(bk_biz_id=bk_biz_id).exists():
            app = App.objects.create(bk_biz_id=bk_biz_id)
        else:
            app = App.objects.get(bk_biz_id=bk_biz_id)
    else:
        if not App.objects.exists():
            app = App.objects.create(bk_biz_id=1)
        else:
            app = App.objects.first()

    if db_module_id:
        if not DBModule.objects.filter(db_module_id=db_module_id).exists():
            db_module = DBModule.objects.create(
                bk_biz_id=app.bk_biz_id,
                db_module_name="fake_dbmodule_app_{}".format(app.bk_biz_id),
                db_module_id=db_module_id,
                cluster_type=ClusterType.TenDBHA,
            )
        else:
            db_module = DBModule.objects.get(db_module_id=db_module_id)
    else:
        if not DBModule.objects.exists():
            db_module = DBModule.objects.create(
                bk_biz_id=app.bk_biz_id,
                db_module_name="fake_dbmodule_app_{}".format(app.bk_biz_id),
                cluster_type=ClusterType.TenDBHA,
            )
        else:
            db_module = DBModule.objects.first()

    if not LogicalCity.objects.exists():
        LogicalCity.objects.create(name="阿希佳德")

    lc = LogicalCity.objects.first()

    if not BKCity.objects.exists():
        BKCity.objects.create(bk_idc_city_id=1, bk_idc_city_name=lc.name, logical_city=lc)

    bk_city = BKCity.objects.first()

    [master_ip, master_port] = master_instance.split(IP_PORT_DIVIDER)
    master_machine = Machine.objects.create(
        ip=master_ip,
        bk_biz_id=app.bk_biz_id,
        db_module_id=db_module.db_module_id,
        access_layer=AccessLayer.STORAGE,
        machine_type=MachineType.BACKEND,
        cluster_type=ClusterType.TenDBHA,
        bk_city=bk_city,
        bk_host_id=int(ipaddress.IPv4Address(master_ip)),
    )

    master_instance_obj = StorageInstance.objects.create(
        machine=master_machine,
        port=int(master_port),
        db_module_id=db_module.db_module_id,
        bk_biz_id=app.bk_biz_id,
        access_layer=AccessLayer.STORAGE,
        machine_type=MachineType.BACKEND,
        instance_role=InstanceRole.BACKEND_MASTER,
        instance_inner_role=InstanceInnerRole.MASTER,
        cluster_type=ClusterType.TenDBHA,
        status=InstanceStatus.RUNNING,
    )

    [slave_ip, slave_port] = slave_instance.split(IP_PORT_DIVIDER)
    slave_machine = Machine.objects.create(
        ip=slave_ip,
        bk_biz_id=app.bk_biz_id,
        db_module_id=db_module.db_module_id,
        access_layer=AccessLayer.STORAGE,
        machine_type=MachineType.BACKEND,
        cluster_type=ClusterType.TenDBHA,
        bk_city=bk_city,
        bk_host_id=int(ipaddress.IPv4Address(slave_ip)),
    )
    slave_instance_obj = StorageInstance.objects.create(
        machine=slave_machine,
        port=int(slave_port),
        db_module_id=db_module.db_module_id,
        bk_biz_id=app.bk_biz_id,
        access_layer=AccessLayer.STORAGE,
        machine_type=MachineType.BACKEND,
        instance_role=InstanceRole.BACKEND_SLAVE,
        instance_inner_role=InstanceInnerRole.SLAVE,
        cluster_type=ClusterType.TenDBHA,
        status=InstanceStatus.RUNNING,
    )

    StorageInstanceTuple.objects.create(ejector=master_instance_obj, receiver=slave_instance_obj)

    if name:
        cluster_name = name
    else:
        cluster_name = immute_domain
    cluster = Cluster.objects.create(
        bk_biz_id=app.bk_biz_id,
        name=cluster_name,
        cluster_type=ClusterType.TenDBHA,
        db_module_id=db_module.db_module_id,
        immute_domain=immute_domain,
        bk_cloud_id=bk_cloud_id,
    )
    cluster.storageinstance_set.add(master_instance_obj, slave_instance_obj)

    master_entry = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain
    )

    if slave_domain:
        slave_entry = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=slave_domain
        )
        slave_entry.storageinstance_set.add(slave_instance_obj)
    proxy_instance_objs = []
    for proxy in proxies:
        [ip, port] = proxy.split(IP_PORT_DIVIDER)
        m = Machine.objects.create(
            ip=ip,
            bk_biz_id=app.bk_biz_id,
            db_module_id=db_module.db_module_id,
            access_layer=AccessLayer.PROXY,
            machine_type=MachineType.PROXY,
            cluster_type=ClusterType.TenDBHA,
            bk_city=bk_city,
            bk_host_id=int(ipaddress.IPv4Address(ip)),
        )
        p = ProxyInstance.objects.create(
            machine=m,
            port=int(port),
            admin_port=int(port) + 1000,
            db_module_id=db_module.db_module_id,
            bk_biz_id=app.bk_biz_id,
            access_layer=AccessLayer.PROXY,
            machine_type=MachineType.PROXY,
            cluster_type=ClusterType.TenDBHA,
            status=InstanceStatus.RUNNING,
        )
        p.storageinstance.add(master_instance_obj)
        cluster.proxyinstance_set.add(p)
        p.bind_entry.add(master_entry)
        proxy_instance_objs.append(p)


@transaction.atomic
def fake_reset_tendbha_cluster(
    proxies: List[str],
    master_instance: str,
    slave_instance: str,
    immute_domain: str,
    slave_domain: Optional[str] = None,
):
    cluster = Cluster.objects.get(immute_domain=immute_domain)
    master_entry = ClusterEntry.objects.get(entry=immute_domain, cluster=cluster)
    master_entry.proxyinstance_set.clear()

    [master_ip, master_port] = master_instance.split(IP_PORT_DIVIDER)
    master_obj = StorageInstance.objects.get(
        machine__ip=master_ip, port=master_port, cluster=cluster, cluster__bk_cloud_id=cluster.bk_cloud_id
    )
    master_obj.instance_role = InstanceRole.BACKEND_MASTER.value
    master_obj.instance_inner_role = InstanceInnerRole.MASTER.value
    master_obj.status = InstanceStatus.RUNNING.value
    master_obj.save(update_fields=["instance_role", "instance_inner_role", "status"])

    [slave_ip, slave_port] = slave_instance.split(IP_PORT_DIVIDER)
    slave_obj = StorageInstance.objects.get(
        machine__ip=slave_ip, port=slave_port, cluster=cluster, cluster__bk_cloud_id=cluster.bk_cloud_id
    )
    slave_obj.instance_role = InstanceRole.BACKEND_SLAVE.value
    slave_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
    slave_obj.status = InstanceStatus.RUNNING.value
    slave_obj.save(update_fields=["instance_role", "instance_inner_role", "status"])

    StorageInstanceTuple.objects.filter(
        (Q(ejector=master_obj) & Q(receiver=slave_obj)) | (Q(ejector=slave_obj) & Q(receiver=master_obj))
    ).delete()

    StorageInstanceTuple.objects.create(ejector=master_obj, receiver=slave_obj)

    for proxy_instance in proxies:
        [proxy_ip, proxy_port] = proxy_instance.split(IP_PORT_DIVIDER)
        proxy_obj = ProxyInstance.objects.get(
            machine__ip=proxy_ip, port=proxy_port, cluster=cluster, cluster__bk_cloud_id=cluster.bk_cloud_id
        )
        proxy_obj.storageinstance.clear()
        proxy_obj.storageinstance.add(master_obj)
        proxy_obj.status = InstanceStatus.RUNNING.value
        proxy_obj.save(update_fields=["status"])
        master_entry.proxyinstance_set.add(proxy_obj)

    if slave_domain:
        slave_entry = ClusterEntry.objects.get(
            entry=slave_domain, cluster=cluster, cluster__bk_cloud_id=cluster.bk_cloud_id
        )
        slave_entry.storageinstance_set.clear()
        slave_entry.storageinstance_set.add(slave_obj)
