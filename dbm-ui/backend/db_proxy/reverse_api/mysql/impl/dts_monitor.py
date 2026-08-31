# -*- coding: utf-8 -*-
"""DTS 机器 mysql-monitor reverse 旁路：无实例，items 查 plat dbconfig。"""
import logging
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import MysqlDtsCluster
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT
from backend.flow.utils.mysql.dts.monitor_config import DTS_MACHINE_TYPES, build_monitor_runtime_dict

logger = logging.getLogger("root")

_ACTIVE_STATUSES = (
    MysqlDtsClusterStatus.DEPLOYING.value,
    MysqlDtsClusterStatus.RUNNING.value,
)
_MACHINE_MASTER = MachineType.MYSQL_DTS_MASTER.value
_MACHINE_WORKER = MachineType.MYSQL_DTS_WORKER.value


def is_dts_machine_type(machine_type: str) -> bool:
    return machine_type in DTS_MACHINE_TYPES


def query_dts_plat_monitor_items() -> dict:
    """只查 mysqldts 平台级 items-config，不按集群覆盖。"""
    return DBConfigApi.query_conf_item(
        {
            "bk_biz_id": "0",
            "level_name": LevelName.PLAT.value,
            "level_value": "0",
            "conf_file": "items-config.yaml",
            "conf_type": "mysql_monitor",
            "namespace": ClusterType.MySQLDTS.value,
            "format": FormatType.MAP.value,
        }
    )["content"]


def _iter_roles_for_ip(cluster: MysqlDtsCluster, ip: str) -> list[dict]:
    roles: list[dict] = []
    for node in cluster.master_nodes or []:
        if (node or {}).get("ip") != ip:
            continue
        roles.append(
            {
                "port": int(node.get("port") or MYSQL_DTS_MASTER_PORT),
                "machine_type": _MACHINE_MASTER,
            }
        )
    for node in cluster.worker_nodes or []:
        if (node or {}).get("ip") != ip:
            continue
        roles.append(
            {
                "port": int(node.get("port") or MYSQL_DTS_WORKER_PORT),
                "machine_type": _MACHINE_WORKER,
            }
        )
    return roles


def find_dts_cluster_roles(*, ip: str, bk_cloud_id: int, port_list: Optional[List[int]] = None) -> tuple:
    """在活跃 MysqlDtsCluster 的 JSON 节点里按 IP 对角色。

    返回 (cluster, roles)；找不到则 (None, [])。
    """
    qs = MysqlDtsCluster.objects.filter(bk_cloud_id=bk_cloud_id, status__in=_ACTIVE_STATUSES).order_by("id")
    for cluster in qs:
        roles = _iter_roles_for_ip(cluster, ip)
        if port_list:
            ports = {int(p) for p in port_list}
            roles = [r for r in roles if r["port"] in ports]
        if roles:
            return cluster, roles
    logger.warning(_("DTS 监控旁路未匹配到活跃集群: ip={} bk_cloud_id={}").format(ip, bk_cloud_id))
    return None, []


def dts_monitor_runtime_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List[Dict]:
    cluster, roles = find_dts_cluster_roles(ip=ip, bk_cloud_id=bk_cloud_id, port_list=port_list)
    if not cluster:
        return []
    return [
        build_monitor_runtime_dict(
            bk_biz_id=cluster.bk_biz_id,
            ip=ip,
            port=role["port"],
            machine_type=role["machine_type"],
            cluster_name=cluster.name,
            bk_cloud_id=bk_cloud_id,
        )
        for role in roles
    ]


def dts_monitor_items_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> Dict[int, Dict]:
    cluster, roles = find_dts_cluster_roles(ip=ip, bk_cloud_id=bk_cloud_id, port_list=port_list)
    if not cluster:
        return {}
    items = query_dts_plat_monitor_items()
    return {role["port"]: items for role in roles}
