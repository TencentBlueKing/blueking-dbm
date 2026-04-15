# -*- coding: utf-8 -*-
"""
TenDBCluster 接入层全毁灾难恢复：端口解析与路由预览 / 初始化 payload 组装。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, TenDBClusterStorageSet
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum

logger = logging.getLogger("flow")


def get_spider_pkg_id_for_layer_disaster_recover(cluster: Cluster, bk_biz_id: int) -> int:
    """
    优先用元数据 spider_master 版本号解析介质包；若无版本则取 Spider 最新可用包。
    """
    masters = cluster.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
    )
    versions = {p.version for p in masters if p.version}
    if len(versions) == 1:
        return Package.get_package_for_version_no(
            db_type=DBType.MySQL, pkg_type=PackageType.Spider, version_no=str(versions.pop())
        ).id
    return Package.get_latest_package(
        version=MediumEnum.Latest.value,
        pkg_type=PackageType.Spider,
        bk_biz_id=bk_biz_id,
    ).id


def resolve_spider_ctl_ports(
    cluster: Cluster,
    spider_port: Optional[int],
    ctl_port: Optional[int],
) -> Tuple[int, int]:
    """
    解析 Spider 业务端口与 tdbctl 端口：单据可覆盖；否则从元数据 spider_master 端口集合推导。

    TenDBCluster 设计约定：同集群所有 spider_master 共享同一 spider/ctl 端口。
    本函数允许 master 数量为任意 ≥1，但要求端口集合唯一；端口不一致视为元数据异常。

    @raises ValueError: 无 spider_master 元数据 / 端口集合不唯一 / 用户参数非法
    """
    if spider_port is not None and ctl_port is not None:
        return int(spider_port), int(ctl_port)
    if spider_port is not None and ctl_port is None:
        return int(spider_port), int(spider_port) + 1000

    masters = list(
        cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
        )
    )
    if not masters:
        raise ValueError(
            _("集群 {} 元数据中无 spider_master 节点，无法推导 spider 端口，请在单据中填写 spider_port/ctl_port").format(cluster.id)
        )
    spider_ports = {m.port for m in masters}
    if len(spider_ports) != 1:
        raise ValueError(
            _("集群 {} 元数据中 spider_master 端口不一致: {}，请在单据中填写 spider_port/ctl_port").format(
                cluster.id, sorted(spider_ports)
            )
        )
    meta_spider_port = spider_ports.pop()
    admin_ports = {m.admin_port for m in masters if m.admin_port}
    if len(admin_ports) > 1:
        raise ValueError(
            _("集群 {} 元数据中 spider_master 中控端口不一致: {}，请在单据中填写 ctl_port").format(cluster.id, sorted(admin_ports))
        )
    meta_ctl_port = admin_ports.pop() if admin_ports else (meta_spider_port + 1000)
    return int(meta_spider_port), int(meta_ctl_port)


def build_append_deploy_style_routing_extend(
    cluster: Cluster,
    new_spider_hosts: List[Dict[str, Any]],
    spider_port: int,
    ctl_port: int,
    tdbctl_user: str,
    tdbctl_pass: str,
) -> Dict[str, Any]:
    """
    生成与 AppendDeployCTLFlow.__get_init_tdbctl_router_payload 同结构的 extend 字段，
    host 使用新机器 IP，端口使用解析结果。
    """
    info = {
        "spider_instances": [{"host": h["ip"], "port": spider_port} for h in new_spider_hosts],
        "spider_slave_instances": [],
        "mnt_spider_instances": [],
        "mnt_spider_slave_instances": [],
        "mysql_instance_tuples": [],
        "ctl_instances": [{"host": h["ip"], "port": ctl_port} for h in new_spider_hosts],
        "tdbctl_user": tdbctl_user,
        "tdbctl_pass": tdbctl_pass,
        "only_init_ctl": False,
    }
    shards = cluster.tendbclusterstorageset_set.all()
    for shard in shards:
        remote_master = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
        remote_slave = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)
        info["mysql_instance_tuples"].append(
            {
                "host": remote_master.machine.ip,
                "port": remote_master.port,
                "slave_host": remote_slave.machine.ip,
                "shard_id": shard.shard_id,
            }
        )
    return info


def build_route_preview_for_ticket(
    cluster: Cluster,
    new_spider_hosts: List[Dict[str, Any]],
    spider_port: int,
    ctl_port: int,
) -> Dict[str, Any]:
    """
    供 RoutePreview 节点与单据日志展示：不含敏感密码，仅摘要。
    """
    routing_extend = build_append_deploy_style_routing_extend(
        cluster=cluster,
        new_spider_hosts=new_spider_hosts,
        spider_port=spider_port,
        ctl_port=ctl_port,
        tdbctl_user="",
        tdbctl_pass="",
    )
    preview = {
        "cluster_id": cluster.id,
        "immute_domain": cluster.immute_domain,
        "resolved_spider_port": spider_port,
        "resolved_ctl_port": ctl_port,
        "spider_endpoints": ["{}{}{}".format(h["ip"], IP_PORT_DIVIDER, spider_port) for h in new_spider_hosts],
        "tdbctl_endpoints": ["{}{}{}".format(h["ip"], IP_PORT_DIVIDER, ctl_port) for h in new_spider_hosts],
        "mysql_instance_tuples": routing_extend["mysql_instance_tuples"],
    }
    return preview


def build_combined_route_preview(
    cluster: Cluster,
    new_master_hosts: List[Dict[str, Any]],
    new_slave_hosts: List[Dict[str, Any]],
    spider_port: int,
    ctl_port: int,
    old_master_hosts: Optional[List[Dict[str, Any]]] = None,
    old_slave_hosts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    合并 master/slave 两组的路由预览：用于同时恢复或单角色恢复场景。

    输出结构化字段：
      - master_changes / slave_changes：[{action, ip, spider_port, ctl_port, bk_host_id}, ...]
        其中 action 取 "新增" / "下架"
      - shards：Remote 分片对照（仅供查看，本流程不变更）

    同时保留旧字段（spider_endpoints / tdbctl_endpoints / spider_slave_endpoints / mysql_instance_tuples）
    供前端 / 其他消费者向后兼容。
    """
    base = build_route_preview_for_ticket(
        cluster=cluster,
        new_spider_hosts=new_master_hosts,
        spider_port=spider_port,
        ctl_port=ctl_port,
    )
    base["spider_slave_endpoints"] = [
        "{}{}{}".format(h["ip"], IP_PORT_DIVIDER, spider_port) for h in (new_slave_hosts or [])
    ]
    base["recover_master"] = bool(new_master_hosts)
    base["recover_slave"] = bool(new_slave_hosts)

    # 结构化变更对比（master 段含 ctl_port；slave 段无中控故 ctl_port=None）
    base["master_changes"] = _build_role_changes(
        new_hosts=new_master_hosts,
        old_hosts=old_master_hosts or [],
        spider_port=spider_port,
        ctl_port=ctl_port,
    )
    base["slave_changes"] = _build_role_changes(
        new_hosts=new_slave_hosts,
        old_hosts=old_slave_hosts or [],
        spider_port=spider_port,
        ctl_port=None,
    )

    # Remote 分片对照（直接转换 mysql_instance_tuples 为更直观的 ip:port 字符串）
    base["shards"] = [
        {
            "shard_id": tup["shard_id"],
            "remote_master": "{}{}{}".format(tup["host"], IP_PORT_DIVIDER, tup["port"]),
            "remote_slave": "{}{}{}".format(tup["slave_host"], IP_PORT_DIVIDER, tup["port"]),
        }
        for tup in base.get("mysql_instance_tuples", [])
    ]
    return base


def _build_role_changes(
    new_hosts: List[Dict[str, Any]],
    old_hosts: List[Dict[str, Any]],
    spider_port: int,
    ctl_port: Optional[int],
) -> List[Dict[str, Any]]:
    """
    构造单一角色（master 或 slave）的变更行：先列新增、再列下架。
    每行：{action: "新增"/"下架", ip, spider_port, ctl_port, bk_host_id}
    """
    changes: List[Dict[str, Any]] = []
    for h in new_hosts or []:
        changes.append(
            {
                "action": _("新增"),
                "ip": h["ip"],
                "spider_port": spider_port,
                "ctl_port": ctl_port,
                "bk_host_id": h.get("bk_host_id"),
            }
        )
    for h in old_hosts or []:
        changes.append(
            {
                "action": _("下架"),
                "ip": h["ip"],
                "spider_port": spider_port,
                "ctl_port": ctl_port,
                "bk_host_id": h.get("bk_host_id"),
            }
        )
    return changes


def probe_running_ctl_via_drs(
    cluster: Cluster,
    running_ctls: Optional[Iterable[ProxyInstance]] = None,
) -> Optional[str]:
    """
    L3 校验：遍历集群中 RUNNING 的 spider_master（中控），通过 DRS 在 admin_port 上执行
    `select @@version` 探活，返回第 1 个能成功响应的中控 IP；全部失败返回 None。

    DRS 内部使用 drs_account 高权账号连接，无需用户传 tdbctl_pass。
    参考 backend/flow/plugins/components/collections/spider/add_spider_routing.py 中的现有用法。

    @param cluster: 待探活的集群对象
    @param running_ctls: 可选，已查出的 RUNNING 中控集合；不传则按 SPIDER_MASTER + RUNNING 自动查询
    """
    if running_ctls is None:
        running_ctls = ProxyInstance.objects.filter(
            cluster=cluster,
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            status=InstanceStatus.RUNNING,
        )
    for ctl in running_ctls:
        admin_port = ctl.admin_port or (ctl.port + 1000)
        ctl_address = "{}{}{}".format(ctl.machine.ip, IP_PORT_DIVIDER, admin_port)
        try:
            res = DRSApi.rpc(
                {
                    "addresses": [ctl_address],
                    "cmds": ["select @@version"],
                    "force": False,
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
            if res and not res[0].get("error_msg"):
                return ctl.machine.ip
            logger.warning(_("中控 {} DRS 探活失败: {}").format(ctl_address, (res[0].get("error_msg") if res else _("无返回"))))
        except Exception as exc:
            logger.warning(_("中控 {} DRS 探活异常: {}").format(ctl_address, str(exc)))
            continue
    return None


def resolve_running_ctl_ip_strict(cluster: Cluster) -> str:
    """
    取一个探活成功的中控 IP；全部失败抛 ValueError。
    用于"仅恢复 spider_slave"的 Validator 与 Flow 运行时（_cluster_sub_flow 求 primary_ctl_ip）。
    """
    alive_ip = probe_running_ctl_via_drs(cluster)
    if not alive_ip:
        raise ValueError(_("集群 {} 当前无可用中控（spider_master.admin_port DRS 探活均失败），无法独立恢复 spider_slave").format(cluster.id))
    return alive_ip


def get_shard_zero_remote_master(cluster: Cluster) -> Tuple[str, int]:
    """
    表结构同步到中控时，以 shard_id=0 的 Remote Master 为只读源。
    """
    shard0 = TenDBClusterStorageSet.objects.filter(cluster=cluster, shard_id=0).first()
    if not shard0:
        shard0 = TenDBClusterStorageSet.objects.filter(cluster=cluster).order_by("shard_id").first()
    if not shard0:
        raise ValueError(_("集群 {} 无分片元数据，无法推导 Remote 源").format(cluster.id))
    master = StorageInstance.objects.get(id=shard0.storage_instance_tuple.ejector_id)
    return master.machine.ip, int(master.port)


def build_mysql_ip_list_and_ports(cluster: Cluster) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    供 AddSystemUserInCluster：对集群所有 Remote 实例所在主机与端口集合去重。
    """
    seen_ip: Set[str] = set()
    mysql_ip_list: List[Dict[str, Any]] = []
    ports: set = set()
    for si in cluster.storageinstance_set.select_related("machine").all():
        ports.add(int(si.port))
        if si.machine.ip not in seen_ip:
            seen_ip.add(si.machine.ip)
            mysql_ip_list.append({"ip": si.machine.ip})
    return mysql_ip_list, sorted(ports)


def build_add_system_user_global_data(
    *,
    cluster: Cluster,
    ticket_uid: str,
    created_by: str,
    bk_biz_id: int,
    ticket_type: str,
    spider_ip_list: List[Dict[str, Any]],
    spider_port: int,
    ctl_port: int,
    tdbctl_pass: str,
    ctl_master_ip: str,
) -> Tuple[Dict[str, Any], str]:
    mysql_ip_list, mysql_ports = build_mysql_ip_list_and_ports(cluster)
    global_data = {
        "uid": ticket_uid,
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": cluster.bk_cloud_id,
        "cluster_id": cluster.id,
        "created_by": created_by,
        "ticket_type": ticket_type,
        "spider_ip_list": spider_ip_list,
        "spider_port": spider_port,
        "ctl_port": ctl_port,
        "mysql_ip_list": mysql_ip_list,
        "mysql_ports": mysql_ports,
        "tdbctl_pass": tdbctl_pass,
    }
    return global_data, ctl_master_ip
