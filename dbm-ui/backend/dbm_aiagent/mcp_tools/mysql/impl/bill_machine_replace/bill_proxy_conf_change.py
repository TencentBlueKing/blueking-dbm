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
from typing import List

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Cluster, ProxyInstance, Spec
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.builders.mysql.mysql_proxy_conf_change import MysqlProxyConfChangeDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def bill_proxy_conf_change(username: str, infos: List[dict]):
    """
    创建 TenDBHA proxy 升降配单据，支持多行。

    每行（info）字段：
    - cluster_domain: 集群域名（代表集群）
    - target_spec_id: 目标规格 ID
    - labels: 资源标签 ID 列表（可选）

    升降配是整机维度操作：
    - 同一台 proxy 机器上的多个端口实例按「机器」去重（port 统一置 0）；
    - 只提交一个代表集群时，自动补齐同机共享集群（proxy 机器集合完全一致），
      合并为同一行提单，cluster_ids 传全；
    - target_proxies.count 为去重后的机器数。

    is_safe 固定为 True（安全模式），不对外暴露开关。
    """
    if not infos:
        raise DBMMcpBaseException(msg=_("infos 不能为空"))

    cluster_domains = [info["cluster_domain"] for info in infos]
    if len(cluster_domains) != len(set(cluster_domains)):
        raise DBMMcpBaseException(msg=_("存在重复集群: {}").format(cluster_domains))

    # 统一校验集群（确保同属一个业务）
    cluster_objs, bk_biz_id, _bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)
    cluster_map = {cluster.immute_domain: cluster for cluster in cluster_objs}
    cluster_ids = [cluster.id for cluster in cluster_objs]

    _validate_target_specs(infos)

    proxies_by_cluster = _collect_proxies_by_cluster(cluster_ids)
    machines_by_cluster, machine_key_by_cluster = _build_machine_infos(cluster_objs, proxies_by_cluster, bk_biz_id)
    all_cluster_map, extra_valid_ids = _auto_complete_related_clusters(
        cluster_objs, cluster_ids, machines_by_cluster, machine_key_by_cluster, proxies_by_cluster, bk_biz_id
    )
    built_infos = _build_grouped_infos(
        infos,
        cluster_map,
        machine_key_by_cluster,
        all_cluster_map,
        extra_valid_ids,
        machines_by_cluster,
        proxies_by_cluster,
    )

    ticket_param = {
        "ticket_type": TicketType.MYSQL_PROXY_CONF_CHANGE,
        "remark": TicketType.MYSQL_PROXY_CONF_CHANGE,
        "creator": username,
        "helpers": [],
        "details": {
            "is_safe": True,
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": built_infos,
            "disable_manual_confirm": False,
        },
        "bk_biz_id": bk_biz_id,
    }

    slz = MysqlProxyConfChangeDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_PROXY_CONF_CHANGE
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted(
                (
                    tuple(sorted(info["cluster_ids"])),
                    info["resource_spec"]["target_proxies"]["spec_id"],
                    tuple(sorted(info["resource_spec"]["target_proxies"].get("labels") or [])),
                )
                for info in infos
            )
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.MYSQL_PROXY_CONF_CHANGE,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(built_infos),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return [
            {
                "bill_id": existing.pk,
                "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{existing.pk}",
            }
        ]

    tk = Ticket.create_ticket(**ticket_param)
    return [{"bill_id": tk.pk, "bill_url": f"{env.BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{tk.pk}"}]


def _validate_target_specs(infos: List[dict]):
    """校验所有行的目标规格存在且启用，且为 MySQL proxy 类型"""
    spec_ids = {info["target_spec_id"] for info in infos}
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.MySQL,
        spec_machine_type=SpecMachineType.PROXY,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))


def _collect_proxies_by_cluster(cluster_ids: List[int]) -> dict:
    """一次性取出所有集群的 proxy 实例（含 machine），并按 cluster 分组"""
    proxy_objs_all = (
        ProxyInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(cluster__pk__in=cluster_ids)
        .select_related("machine")
        .prefetch_related("cluster")
    )
    proxies_by_cluster = {}
    for pi in proxy_objs_all:
        for cluster in pi.cluster.all():
            if cluster.id in cluster_ids:
                proxies_by_cluster.setdefault(cluster.id, []).append(pi)
    return proxies_by_cluster


def _build_machine_infos(cluster_objs, proxies_by_cluster: dict, bk_biz_id: int):
    """
    按集群整理「机器维度」信息（同机多端口去重），并计算每个集群的 proxy 机器 bk_host_id 集合，
    用于识别同组共享。升降配是整集群操作，origin_proxies 必须是集群的全部 proxy 机器。
    """
    machines_by_cluster = {}
    machine_key_by_cluster = {}
    for cluster in cluster_objs:
        proxy_objs = proxies_by_cluster.get(cluster.id, [])
        if not proxy_objs:
            raise DBMMcpBaseException(msg=_("集群无 proxy 实例: {}").format(cluster.immute_domain))

        machines, machine_key = _dedup_machines(proxy_objs, bk_biz_id)
        machines_by_cluster[cluster.id] = machines
        machine_key_by_cluster[cluster.id] = machine_key
    return machines_by_cluster, machine_key_by_cluster


def _dedup_machines(proxy_objs, bk_biz_id: int):
    """同一台机器可能运行多个 proxy 进程（不同端口），按 bk_host_id 去重，port 统一置 0"""
    machines = {}
    for pi in proxy_objs:
        machines[pi.machine.bk_host_id] = {
            "bk_cloud_id": pi.machine.bk_cloud_id,
            "ip": pi.machine.ip,
            "bk_host_id": pi.machine.bk_host_id,
            "bk_biz_id": bk_biz_id,
            "port": 0,
        }
    machine_infos = list(machines.values())
    machine_key = frozenset(m["bk_host_id"] for m in machine_infos)
    return machine_infos, machine_key


def _auto_complete_related_clusters(
    cluster_objs, cluster_ids, machines_by_cluster, machine_key_by_cluster, proxies_by_cluster, bk_biz_id
):
    """
    自动补齐同机关联集群：只提交代表集群时，反查该机器上部署的全部 TenDBHA 集群，
    仅保留「proxy 机器集合与已提交集群完全一致」的集群，避免误补部分共享机器的集群。
    """
    represent_host_ids = {m["bk_host_id"] for c in cluster_objs for m in machines_by_cluster[c.id]}
    related_cluster_ids = set(
        ProxyInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(machine__bk_host_id__in=represent_host_ids, cluster__cluster_type=ClusterType.TenDBHA.value)
        .values_list("cluster", flat=True)
        .distinct()
    )

    extra_cluster_ids = related_cluster_ids - set(cluster_ids)
    extra_valid_ids = set()
    extra_cluster_objs = []
    if extra_cluster_ids:
        extra_cluster_objs = list(Cluster.objects.using(MYSQL_MCP_DB_READ).filter(id__in=extra_cluster_ids))
        extra_proxy_objs = (
            ProxyInstance.objects.using(MYSQL_MCP_DB_READ)
            .filter(cluster__pk__in=extra_cluster_ids)
            .select_related("machine")
            .prefetch_related("cluster")
        )
        for pi in extra_proxy_objs:
            for cluster in pi.cluster.all():
                if cluster.id in extra_cluster_ids:
                    proxies_by_cluster.setdefault(cluster.id, []).append(pi)

        submitted_machine_keys = {machine_key_by_cluster[c.id] for c in cluster_objs}
        for cluster in extra_cluster_objs:
            machines, machine_key = _dedup_machines(proxies_by_cluster.get(cluster.id, []), bk_biz_id)
            machines_by_cluster[cluster.id] = machines
            machine_key_by_cluster[cluster.id] = machine_key
            if machine_key in submitted_machine_keys:
                extra_valid_ids.add(cluster.id)

    all_cluster_map = {c.id: c for c in cluster_objs}
    all_cluster_map.update({ec.id: ec for ec in extra_cluster_objs if ec.id in extra_valid_ids})
    return all_cluster_map, extra_valid_ids


def _build_grouped_infos(
    infos,
    cluster_map,
    machine_key_by_cluster,
    all_cluster_map,
    extra_valid_ids,
    machines_by_cluster,
    proxies_by_cluster,
):
    """按同组共享集群（proxy 机器 bk_host_id 集合完全一致）合并成一行提单"""
    grouped = {}
    for info in infos:
        cluster = cluster_map[info["cluster_domain"]]
        target_spec_id = info["target_spec_id"]
        labels = info.get("labels") or []

        group = grouped.setdefault(
            machine_key_by_cluster[cluster.id],
            {"cluster_ids": set(), "target_spec_ids": set(), "labels": None},
        )
        group["cluster_ids"].add(cluster.id)
        group["target_spec_ids"].add(target_spec_id)
        if group["labels"] is None:
            group["labels"] = labels
        elif sorted(group["labels"]) != sorted(labels):
            raise DBMMcpBaseException(
                msg=_("同组共享集群资源标签不一致: {}").format(
                    [all_cluster_map[cid].immute_domain for cid in sorted(group["cluster_ids"])]
                )
            )

    # 自动补齐的集群归入对应组（继承该组已提交集群的目标规格与标签）
    for extra_id in extra_valid_ids:
        grouped[machine_key_by_cluster[extra_id]]["cluster_ids"].add(extra_id)

    built_infos = []
    for group in grouped.values():
        cluster_ids_in_group = sorted(group["cluster_ids"])
        clusters = [all_cluster_map[cid] for cid in cluster_ids_in_group]
        first_cluster = clusters[0]
        machines = machines_by_cluster[first_cluster.id]

        if len(group["target_spec_ids"]) != 1:
            raise DBMMcpBaseException(msg=_("同组共享集群目标规格不一致: {}").format([c.immute_domain for c in clusters]))
        target_spec_id = next(iter(group["target_spec_ids"]))

        # 校验目标规格与当前规格不同：同组机器相同，取组内任一集群判断即可
        proxy_objs = proxies_by_cluster.get(first_cluster.id, [])
        current_spec_ids = {pi.machine.spec_id for pi in proxy_objs}
        if current_spec_ids == {target_spec_id}:
            raise DBMMcpBaseException(msg=_("目标规格与当前规格相同，无需升降配: {}").format(first_cluster.immute_domain))

        resource_spec = {"spec_id": target_spec_id, "count": len(machines), "labels": group["labels"]}

        built_infos.append(
            {
                "cluster_ids": cluster_ids_in_group,
                "origin_proxies": machines,
                "old_nodes": {
                    "proxy": machines,
                },
                "resource_spec": {"target_proxies": resource_spec},
            }
        )
    return built_infos
