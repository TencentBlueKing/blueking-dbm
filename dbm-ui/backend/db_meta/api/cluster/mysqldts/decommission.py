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
from typing import List, Optional

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, MysqlDtsCluster
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

    精简模型只写 MysqlDtsCluster + Machine：软删业务表（DESTROYED, cluster_id=0），
    按节点 IP 回收并删除 Machine。不处理 Cluster / Proxy / Storage / ClusterEntry。
    """
    dts_cluster = MysqlDtsCluster.objects.get(id=dts_cluster_id)

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


def _recycle_machines_by_ips(bk_biz_id: int, bk_cloud_id: int, ips: List[str], recycle_hosts: bool):
    """按 IP 回收/删除 Machine。"""
    if not ips:
        return
    cc_manage = CcManage(bk_biz_id, ClusterType.MySQLDTS.value)
    for ip in ips:
        machine_obj = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
        if not machine_obj:
            continue
        if recycle_hosts and machine_obj.bk_host_id:
            cc_manage.recycle_host([machine_obj.bk_host_id])
        machine_obj.delete(keep_parents=True)


def _collect_host_ips(dts_cluster: MysqlDtsCluster, target_hosts: Optional[List[dict]]) -> list[str]:
    if target_hosts:
        return [h["ip"] for h in target_hosts]
    ips = set()
    for node in dts_cluster.master_nodes + dts_cluster.worker_nodes:
        ips.add(node["ip"])
    return list(ips)
