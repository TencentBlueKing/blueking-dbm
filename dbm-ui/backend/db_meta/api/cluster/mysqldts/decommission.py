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
from typing import List, Optional, Union

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import (
    Cluster,
    ClusterDBHAExt,
    ClusterEntry,
    Machine,
    MysqlDtsCluster,
    ProxyInstance,
    StorageInstance,
)
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


@transaction.atomic
def decommission(
    dts_cluster_id: int,
    recycle_hosts: bool = True,
    target_hosts: Optional[List[dict]] = None,
    updater: str = "",
):
    """下线 MySQL DTS 集群元数据。

    主路径（精简模型）：MysqlDtsCluster 软删（DESTROYED, cluster_id=0），按节点 IP 回收 Machine。
    兼容路径：历史数据若仍挂 cluster_id>0，先硬删 Cluster/Entry/实例树，再回收剩余 Machine。
    """
    dts_cluster = MysqlDtsCluster.objects.get(id=dts_cluster_id)

    if dts_cluster.cluster_id:
        cluster = Cluster.objects.filter(id=dts_cluster.cluster_id).first()
        if cluster:
            _delete_cluster_meta(cluster, recycle_hosts=recycle_hosts)

    ips = _collect_host_ips(dts_cluster, target_hosts)
    _recycle_machines_by_ips(
        bk_biz_id=dts_cluster.bk_biz_id,
        bk_cloud_id=dts_cluster.bk_cloud_id,
        ips=ips,
        recycle_hosts=recycle_hosts,
    )

    dts_cluster.status = MysqlDtsClusterStatus.DESTROYED.value
    dts_cluster.cluster_id = 0
    dts_cluster.updater = updater
    dts_cluster.save(update_fields=["status", "cluster_id", "updater", "update_at"])

    if recycle_hosts:
        logger.info(_("回收 DTS 主机到资源池: {}").format(ips))
    logger.info(_("MySQL DTS 集群下线完成: id={}").format(dts_cluster_id))


def _delete_cluster_meta(cluster: Cluster, recycle_hosts: bool = True):
    """兼容：彻底删除历史 DTS 关联的 Cluster / 实例 / 入口。"""
    cc_manage = CcManage(cluster.bk_biz_id, cluster.cluster_type)

    for proxy in list(cluster.proxyinstance_set.all()):
        machine_obj = proxy.machine
        proxy.bind_entry.clear()
        proxy.storageinstance.clear()
        _delete_instance_and_maybe_machine(proxy, machine_obj, cc_manage, recycle_hosts)

    for storage in list(cluster.storageinstance_set.all()):
        machine_obj = storage.machine
        storage.bind_entry.clear()
        _delete_instance_and_maybe_machine(storage, machine_obj, cc_manage, recycle_hosts)

    for ce in ClusterEntry.objects.filter(cluster=cluster).all():
        ce.proxyinstance_set.clear()
        ce.delete(keep_parents=True)

    ClusterDBHAExt.objects.filter(cluster=cluster).delete()
    cluster.tags.clear()

    logger.info(_("删除 DTS Cluster 元数据: id={} domain={}").format(cluster.id, cluster.immute_domain))
    cluster.delete(keep_parents=True)


def _delete_instance_and_maybe_machine(
    instance: Union[ProxyInstance, StorageInstance],
    machine_obj: Machine,
    cc_manage: CcManage,
    recycle_hosts: bool,
):
    """删除实例；若机器上已无任何实例则删除 Machine（可选回收到资源池）。"""
    if instance.bk_instance_id:
        cc_manage.delete_service_instance(bk_instance_ids=[instance.bk_instance_id])
    instance.delete(keep_parents=True)
    _maybe_delete_machine(machine_obj, recycle_hosts=recycle_hosts, cc_manage=cc_manage)


def _maybe_delete_machine(machine_obj: Machine, recycle_hosts: bool, cc_manage: CcManage):
    """DTS 可能同机部署 Master+Worker，需同时检查 Proxy/Storage 实例。"""
    if machine_obj.proxyinstance_set.exists() or machine_obj.storageinstance_set.exists():
        return
    if recycle_hosts and machine_obj.bk_host_id:
        cc_manage.recycle_host([machine_obj.bk_host_id])
    machine_obj.delete(keep_parents=True)


def _recycle_machines_by_ips(bk_biz_id: int, bk_cloud_id: int, ips: List[str], recycle_hosts: bool):
    """精简模型：按 IP 回收/删除无实例占用的 Machine。"""
    if not ips:
        return
    cc_manage = CcManage(bk_biz_id, ClusterType.MySQLDTS.value)
    for ip in ips:
        machine_obj = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
        if not machine_obj:
            continue
        _maybe_delete_machine(machine_obj, recycle_hosts=recycle_hosts, cc_manage=cc_manage)


def _collect_host_ips(dts_cluster: MysqlDtsCluster, target_hosts: Optional[List[dict]]) -> list[str]:
    if target_hosts:
        return [h["ip"] for h in target_hosts]
    ips = set()
    for node in dts_cluster.master_nodes + dts_cluster.worker_nodes:
        ips.add(node["ip"])
    return list(ips)
