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
from typing import List

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta import request_validator
from backend.db_meta.api import machine
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Machine, MysqlDtsCluster
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus

logger = logging.getLogger("root")

# 同名不允许再建的活跃状态
_ACTIVE_STATUSES = (
    MysqlDtsClusterStatus.DEPLOYING.value,
    MysqlDtsClusterStatus.RUNNING.value,
)


@transaction.atomic
def create(
    bk_biz_id: int,
    bk_cloud_id: int,
    name: str,
    master_nodes: List[dict],
    worker_nodes: List[dict],
    master_addr: str,
    deploy_path: str,
    version: str = "",
    creator: str = "",
    db_module_id: int = 0,
) -> MysqlDtsCluster:
    """注册 MySQL DTS 集群元数据。

    仅写入 MysqlDtsCluster + Machine，不再创建 Cluster / Proxy / Storage / ClusterEntry。
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    # db_module_id 保留入参兼容，精简模型下不再落库
    if db_module_id:
        request_validator.validated_integer(db_module_id)

    _assert_name_available(bk_biz_id=bk_biz_id, name=name)
    _ensure_machines(bk_biz_id, bk_cloud_id, master_nodes, worker_nodes, creator=creator)

    dts_cluster = MysqlDtsCluster.objects.create(
        name=name,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        cluster_id=0,
        status=MysqlDtsClusterStatus.RUNNING.value,
        master_nodes=master_nodes,
        worker_nodes=worker_nodes,
        master_addr=master_addr,
        deploy_path=deploy_path,
        version=version,
        creator=creator,
        updater=creator,
    )
    logger.info(_("MySQL DTS 集群注册成功: {} dts_cluster_id={}").format(name, dts_cluster.id))
    return dts_cluster


def _assert_name_available(bk_biz_id: int, name: str):
    exists = MysqlDtsCluster.objects.filter(
        bk_biz_id=bk_biz_id,
        name=name,
        status__in=_ACTIVE_STATUSES,
    ).exists()
    if exists:
        raise DBMetaException(message=_("业务 {} 下 DTS 集群名称 {} 已存在（deploying/running）").format(bk_biz_id, name))


def _ensure_machines(
    bk_biz_id: int,
    bk_cloud_id: int,
    master_nodes: List[dict],
    worker_nodes: List[dict],
    creator: str = "",
):
    """按 IP 去重创建 Machine。

    同机部署时 Master/Worker 共用一个 bk_host_id；若分别 machine.create 会触发
    Duplicate entry for PRIMARY，外层 atomic 回滚后库内又查不到该行。
    同机场景 Machine.machine_type 记为 MYSQL_DTS_COLOCATED。
    """
    master_ips = {n["ip"] for n in master_nodes}
    worker_ips = {n["ip"] for n in worker_nodes}
    # 追加 Worker 到已有 Master 同机时，master_nodes 可能为空，需结合已有元数据判断
    existing_master_like_ips = set(
        Machine.objects.filter(
            ip__in=worker_ips,
            bk_cloud_id=bk_cloud_id,
            machine_type__in=[
                MachineType.MYSQL_DTS_MASTER.value,
                MachineType.MYSQL_DTS_COLOCATED.value,
            ],
        ).values_list("ip", flat=True)
    )
    colocated_ips = (master_ips & worker_ips) | (worker_ips & existing_master_like_ips)
    machines = []
    for ip in sorted(master_ips | worker_ips):
        if ip in colocated_ips:
            machine_type = MachineType.MYSQL_DTS_COLOCATED.value
        elif ip in master_ips:
            machine_type = MachineType.MYSQL_DTS_MASTER.value
        else:
            machine_type = MachineType.MYSQL_DTS_WORKER.value
        machines.append(
            {
                "ip": ip,
                "bk_biz_id": bk_biz_id,
                "bk_cloud_id": bk_cloud_id,
                "machine_type": machine_type,
            }
        )
    if machines:
        # ignore_conflicts：同 IP 已存在（含同机二次注册）时跳过
        machine.get_or_create(bk_cloud_id=bk_cloud_id, machines=machines, creator=creator)

    # 已有纯 Master/Worker 机器后来变成同机时，升级 machine_type
    for ip in colocated_ips:
        Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).exclude(
            machine_type=MachineType.MYSQL_DTS_COLOCATED.value
        ).update(
            machine_type=MachineType.MYSQL_DTS_COLOCATED.value,
            access_layer=AccessLayer.PROXY.value,
            cluster_type=ClusterType.MySQLDTS.value,
        )


@transaction.atomic
def append_worker_nodes(dts_cluster_id: int, new_worker_nodes: List[dict], updater: str = ""):
    """追加 Worker 节点：只更新 JSON + Machine，不再挂 Cluster/StorageInstance。"""
    dts_cluster = MysqlDtsCluster.objects.get(id=dts_cluster_id)
    merged = list(dts_cluster.worker_nodes)
    merged.extend(new_worker_nodes)
    dts_cluster.worker_nodes = merged
    dts_cluster.updater = updater
    dts_cluster.save(update_fields=["worker_nodes", "updater", "update_at"])

    _ensure_machines(
        dts_cluster.bk_biz_id,
        dts_cluster.bk_cloud_id,
        master_nodes=[],
        worker_nodes=new_worker_nodes,
        creator=updater,
    )
