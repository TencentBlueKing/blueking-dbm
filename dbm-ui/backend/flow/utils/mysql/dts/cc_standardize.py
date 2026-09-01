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
from typing import Iterable, List, Optional, Sequence, Tuple

from backend.configuration.constants import DBType
from backend.configuration.models import BizSettings
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, MysqlDtsCluster
from backend.db_meta.models.cluster_monitor import get_monitor_set_name
from backend.db_services.cmdb.biz import get_or_create_cmdb_module_with_name, get_or_create_set_with_name
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.mysql.dts.constants import DTS_CC_MONITOR_PLUGIN_NAME


def dts_cc_set_name() -> str:
    """托管业务下 DTS 固定 Set 名，形如 db.mysql.dts。"""
    return get_monitor_set_name(DBType.MySQL.value, DTS_CC_MONITOR_PLUGIN_NAME)


def collect_unique_ips(*node_lists: Optional[Sequence[dict]]) -> List[str]:
    """从 master/worker 节点 JSON 去重收集 IP。"""
    ips: List[str] = []
    for nodes in node_lists:
        if not nodes:
            continue
        for node in nodes:
            ip = node.get("ip") if isinstance(node, dict) else None
            if ip:
                ips.append(ip)
    return sorted(set(ips))


def resolve_dts_cc_context(
    *,
    bk_biz_id: Optional[int] = None,
    cluster_name: Optional[str] = None,
    master_nodes: Optional[Sequence[dict]] = None,
    worker_nodes: Optional[Sequence[dict]] = None,
    dts_cluster_id: Optional[int] = None,
) -> Tuple[int, str, List[str]]:
    """
    解析 (bk_biz_id, cluster_name, ips)。

    - CREATE 部署：传 bk_biz_id + cluster_name + nodes
    - APPEND / 仅有 id：传 dts_cluster_id，必要时从 MysqlDtsCluster 补齐
    """
    ips = collect_unique_ips(master_nodes, worker_nodes)
    if dts_cluster_id:
        dts_cluster = MysqlDtsCluster.objects.get(id=dts_cluster_id)
        if not ips:
            ips = collect_unique_ips(dts_cluster.master_nodes, dts_cluster.worker_nodes)
        return dts_cluster.bk_biz_id, dts_cluster.name, ips

    if bk_biz_id is None or not cluster_name:
        raise ValueError("bk_biz_id and cluster_name are required when dts_cluster_id is absent")
    if not ips:
        raise ValueError("no host ips provided for DTS CC standardize")
    return int(bk_biz_id), cluster_name, ips


def transfer_dts_hosts_to_cluster_module(
    bk_biz_id: int,
    bk_cloud_id: int,
    cluster_name: str,
    ips: Iterable[str],
) -> int:
    """
    在托管业务下 get_or_create Set(db.mysql.dts) + Module(cluster_name)，并 transfer 主机。

    @return: 目标 bk_module_id
    """
    ip_list = sorted({ip for ip in ips if ip})
    if not ip_list:
        raise ValueError("no host ips to transfer for DTS CC standardize")

    hosting_biz_id = BizSettings.get_exact_hosting_biz(bk_biz_id, ClusterType.MySQLDTS.value)
    set_name = dts_cc_set_name()
    bk_set_id = get_or_create_set_with_name(hosting_biz_id, set_name)
    bk_module_id = get_or_create_cmdb_module_with_name(hosting_biz_id, bk_set_id, cluster_name)

    machines = list(Machine.objects.filter(ip__in=ip_list, bk_cloud_id=bk_cloud_id))
    found_ips = {m.ip for m in machines}
    missing = set(ip_list) - found_ips
    if missing:
        raise ValueError(f"Machine meta missing for DTS hosts: {sorted(missing)}")
    bk_host_ids = [m.bk_host_id for m in machines if m.bk_host_id]
    if not bk_host_ids:
        raise ValueError("no bk_host_id found for DTS hosts")

    CcManage(bk_biz_id, ClusterType.MySQLDTS.value).transfer_host_module(
        bk_host_ids=bk_host_ids,
        target_module_ids=[bk_module_id],
    )
    return bk_module_id
