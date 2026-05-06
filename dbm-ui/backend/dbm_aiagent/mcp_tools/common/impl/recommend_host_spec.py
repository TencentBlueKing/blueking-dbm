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
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, Spec

logger = logging.getLogger("root")


def recommend_specs_for_hosts(
    ip_list: List[str],
    bk_cloud_id: int = 0,
    spec_name_keywords: List[str] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """
    根据主机信息推荐合适的规格

    Args:
        ip_list: 主机 IP 列表
        bk_cloud_id: 云区域 ID，默认 0
        spec_name_keywords: 规格名称关键字列表，用于模糊匹配

    Returns:
        (recommendations, failed_hosts): 推荐结果列表和失败主机列表
        - recommendations: [{"spec_id": 1, "spec_name": "xxx", "matched_hosts": ["ip1", "ip2"]}]
        - failed_hosts: [{"ip": "x.x.x.x", "reason": "失败原因"}]
    """
    if spec_name_keywords is None:
        spec_name_keywords = ["标准", "推荐", "standard"]

    logger.info(_("开始为主机推荐规格，IP 列表: {}, 云区域: {}").format(ip_list, bk_cloud_id))

    # 查询主机信息
    machines = Machine.objects.filter(ip__in=ip_list, bk_cloud_id=bk_cloud_id).values(
        "ip", "cluster_type", "machine_type", "bk_svr_device_cls_name"
    )

    # 记录查询到的主机 IP
    found_ips: Set[str] = {machine["ip"] for machine in machines}
    failed_hosts = []

    # 记录未找到的主机
    for ip in ip_list:
        if ip not in found_ips:
            logger.warning(_("主机 {} 在云区域 {} 中不存在").format(ip, bk_cloud_id))
            failed_hosts.append({"ip": ip, "reason": _("主机不存在或云区域不匹配")})

    # 按 (cluster_type, machine_type) 分组主机
    host_groups = _group_hosts_by_type(machines, failed_hosts)

    # 用于聚合结果：spec_id -> [ip1, ip2, ...]
    spec_host_map: Dict[int, List[str]] = defaultdict(list)
    spec_cache: Dict[int, Spec] = {}

    # 遍历每个主机组，查询匹配的规格
    for (cluster_type, machine_type), hosts in host_groups.items():
        _match_specs_for_host_group(
            cluster_type=cluster_type,
            machine_type=machine_type,
            hosts=hosts,
            spec_name_keywords=spec_name_keywords,
            spec_host_map=spec_host_map,
            spec_cache=spec_cache,
        )

    # 构建推荐结果
    recommendations = _build_recommendations(spec_host_map, spec_cache)

    # 检查是否有主机没有匹配到任何规格
    _check_unmatched_hosts(found_ips, spec_host_map, failed_hosts)

    logger.info(_("推荐完成，推荐规格数: {}, 失败主机数: {}").format(len(recommendations), len(failed_hosts)))

    return recommendations, failed_hosts


def _group_hosts_by_type(machines, failed_hosts: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
    """
    按 (cluster_type, machine_type) 分组主机

    Args:
        machines: 主机查询结果
        failed_hosts: 失败主机列表（用于记录验证失败的主机）

    Returns:
        host_groups: {(cluster_type, machine_type): [host1, host2, ...]}
    """
    host_groups = defaultdict(list)

    for machine in machines:
        cluster_type = machine["cluster_type"]
        machine_type = machine["machine_type"]
        device_cls = machine["bk_svr_device_cls_name"]

        # 检查必要字段
        if not cluster_type or not machine_type:
            logger.warning(_("主机 {} 的 cluster_type 或 machine_type 为空").format(machine["ip"]))
            failed_hosts.append({"ip": machine["ip"], "reason": _("主机的集群类型或机器类型为空")})
            continue

        if not device_cls:
            logger.warning(_("主机 {} 的机型（bk_svr_device_cls_name）为空").format(machine["ip"]))
            failed_hosts.append({"ip": machine["ip"], "reason": _("主机的机型信息为空")})
            continue

        key = (cluster_type, machine_type)
        host_groups[key].append(machine)

    return host_groups


def _match_specs_for_host_group(
    cluster_type: str,
    machine_type: str,
    hosts: List[Dict],
    spec_name_keywords: List[str],
    spec_host_map: Dict[int, List[str]],
    spec_cache: Dict[int, Spec],
) -> None:
    """
    为一组主机查询并匹配规格

    Args:
        cluster_type: 集群类型
        machine_type: 机器类型
        hosts: 主机列表
        spec_name_keywords: 规格名称关键字列表
        spec_host_map: 规格到主机映射（用于累积结果）
        spec_cache: 规格缓存（用于避免重复查询）
    """
    logger.info(_("查询 cluster_type={}, machine_type={} 的规格，主机数量: {}").format(cluster_type, machine_type, len(hosts)))

    # 将 cluster_type 转换为 db_type，因为 Spec.spec_cluster_type 实际存储的是 db_type
    try:
        db_type = ClusterType.cluster_type_to_db_type(cluster_type)
    except ValueError as e:
        logger.error(_("无法将 cluster_type {} 转换为 db_type: {}").format(cluster_type, str(e)))
        return

    # 构建规格查询条件（使用 db_type 而不是 cluster_type）
    spec_query = Q(spec_cluster_type=db_type, spec_machine_type=machine_type, enable=True)

    # spec_name 模糊匹配关键字
    name_query = Q()
    for keyword in spec_name_keywords:
        name_query |= Q(spec_name__icontains=keyword)

    # 查询匹配的规格
    specs = Spec.objects.filter(spec_query & name_query)
    logger.info(_("找到 {} 个候选规格").format(specs.count()))

    # 遍历规格和主机，进行 device_class 匹配
    for spec in specs:
        # 跳过 device_class 为空的规格
        if not spec.device_class:
            logger.debug(_("规格 {} (ID: {}) 的 device_class 为空，跳过").format(spec.spec_name, spec.spec_id))
            continue

        # 缓存规格信息
        if spec.spec_id not in spec_cache:
            spec_cache[spec.spec_id] = spec

        # 检查每个主机的机型是否在规格的 device_class 列表中
        for host in hosts:
            host_device_cls = host["bk_svr_device_cls_name"]
            if host_device_cls in spec.device_class:
                logger.debug(
                    _("主机 {} 的机型 {} 匹配规格 {} (ID: {})").format(
                        host["ip"], host_device_cls, spec.spec_name, spec.spec_id
                    )
                )
                spec_host_map[spec.spec_id].append(host["ip"])


def _build_recommendations(spec_host_map: Dict[int, List[str]], spec_cache: Dict[int, Spec]) -> List[Dict]:
    """
    构建推荐结果列表

    Args:
        spec_host_map: 规格到主机映射 {spec_id: [ip1, ip2, ...]}
        spec_cache: 规格缓存 {spec_id: Spec对象}

    Returns:
        recommendations: 推荐结果列表
    """
    recommendations = []

    for spec_id, matched_ips in spec_host_map.items():
        spec = spec_cache[spec_id]
        recommendations.append(
            {
                "spec_id": spec.spec_id,
                "spec_name": spec.spec_name,
                "spec_cluster_type": spec.spec_cluster_type,
                "spec_machine_type": spec.spec_machine_type,
                "cpu": spec.cpu,
                "mem": spec.mem,
                "device_class": spec.device_class,
                "storage_spec": spec.storage_spec,
                "matched_hosts": matched_ips,
            }
        )

    return recommendations


def _check_unmatched_hosts(
    found_ips: Set[str],
    spec_host_map: Dict[int, List[str]],
    failed_hosts: List[Dict],
) -> None:
    """
    检查是否有主机没有匹配到任何规格

    Args:
        found_ips: 查询到的主机 IP 集合
        spec_host_map: 规格到主机映射
        failed_hosts: 失败主机列表（用于记录未匹配的主机）
    """
    # 收集所有已匹配的主机 IP
    all_matched_ips = set()
    for matched_ips in spec_host_map.values():
        all_matched_ips.update(matched_ips)

    # 找出未匹配的主机
    for ip in found_ips:
        if ip not in all_matched_ips:
            logger.warning(_("主机 {} 没有找到匹配的规格").format(ip))
            failed_hosts.append({"ip": ip, "reason": _("没有找到匹配的规格")})
