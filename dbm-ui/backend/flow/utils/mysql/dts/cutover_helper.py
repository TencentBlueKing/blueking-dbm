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
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT
from backend.flow.utils.mysql.dts.migrate_helper import resolve_source_endpoint
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskSpec, SyncScope


def resolve_master_addr_from_plan(plan: DtsMigratePlan) -> str:
    """编排期解析 DTS master_addr（已有集群或部署入参均可）。"""
    if plan.dts_cluster_id:
        from backend.db_meta.models import MysqlDtsCluster

        dts_cluster = MysqlDtsCluster.objects.filter(id=plan.dts_cluster_id).first()
        if dts_cluster and dts_cluster.master_addr:
            return dts_cluster.master_addr
    if plan.deploy_subflow_inp and plan.deploy_subflow_inp.master_hosts:
        ip = plan.deploy_subflow_inp.master_hosts[0].ip
        if ip:
            return f"{ip}:{MYSQL_DTS_MASTER_PORT}"
    return ""


def sync_scope_to_dict(scope: SyncScope) -> dict[str, Any]:
    """将 SyncScope 转为 actuator 可消费的紧凑 dict（不含展开后的海量表名）。"""
    return {
        "do_dbs": list(scope.do_dbs or []),
        "ignore_dbs": list(scope.ignore_dbs or []),
        "do_tables": list(scope.do_tables or []),
        "ignore_tables": list(scope.ignore_tables or []),
        "table_routes": [asdict(route) for route in (scope.table_routes or [])],
        "binlog_filters": list(scope.binlog_filters or []),
    }


def merge_task_sync_scopes(task_spec: DtsTaskSpec) -> dict[str, Any]:
    """合并单任务下各 source 的 sync_scope（cutover 按任务停、源端各自加锁时仍可传合并视图）。

    主路径：多 source 时由 actuator 按 source_endpoints 分别展开；此处默认取第一个
    source 的 scope，若存在 sync_scope_merged 则优先使用单据合并结果。
    """
    if task_spec.sync_scope_merged:
        # sync_scope_merged 可能是 list[dict]（路由列表）或单 dict
        first = task_spec.sync_scope_merged[0]
        if isinstance(first, dict) and ("do_dbs" in first or "do_tables" in first or "table_routes" in first):
            return dict(first)
    if not task_spec.sources:
        raise ValueError(_("cutover 组装失败：task_spec 无 sources"))
    return sync_scope_to_dict(task_spec.sources[0].sync_scope)


def build_source_endpoints_for_cutover(
    *,
    task_spec: DtsTaskSpec,
    dts_user: str,
    dts_password: str,
) -> list[dict[str, Any]]:
    """为 cutover payload 组装源端连接信息（临时账号；连接发起方=dts-master）。"""
    if not dts_user or not dts_password:
        raise ValueError(_("cutover 组装失败：临时账号 dts_user/dts_password 为空"))
    endpoints: list[dict[str, Any]] = []
    for source_spec in task_spec.sources:
        cluster = Cluster.objects.get(id=source_spec.cluster_id)
        host, port = resolve_source_endpoint(source_spec, cluster)
        endpoints.append(
            {
                "host": host,
                "port": port,
                "user": dts_user,
                "password": dts_password,
                "source_name": source_spec.source_name,
                "sync_scope": sync_scope_to_dict(source_spec.sync_scope),
            }
        )
    if not endpoints:
        raise ValueError(_("cutover 组装失败：source_endpoints 为空"))
    return endpoints


def build_dts_cutover_payload(
    *,
    master_addr: str,
    task_name: str,
    task_spec: DtsTaskSpec,
    dts_user: str,
    dts_password: str,
    deploy_path: str = "",
    catchup_recheck: int = 3,
    api_timeout_sec: int = 600,
    checksum_passed: bool = False,
    skip_checksum: bool = False,
) -> dict[str, Any]:
    """组装下发给 dbactuator mysql dts-cutover 的 payload。

    约束：传紧凑 sync_scope，**默认不传**展开后的海量 lock_tables[]；
    本期不对目标端加锁，故无 target_endpoints。
    停任务走 Master HTTP API（与 status 查询同通道），不依赖本机 dmctl。
    持锁追平在 actuator 内按「加锁 master 快照」判定，因此必须带上 checksum_passed（或 skip_checksum）。
    """
    if not master_addr:
        raise ValueError(_("cutover 组装失败：master_addr 为空"))
    if not task_name:
        raise ValueError(_("cutover 组装失败：task_name 为空"))
    if not skip_checksum and not checksum_passed:
        raise ValueError(_("cutover 组装失败：checksum 未通过且未声明 skip_checksum"))

    source_endpoints = build_source_endpoints_for_cutover(
        task_spec=task_spec,
        dts_user=dts_user,
        dts_password=dts_password,
    )
    # 顶层 sync_scope：兼容单源；多源时 actuator 优先读各 endpoint 内嵌 scope
    sync_scope = merge_task_sync_scopes(task_spec)
    payload = {
        "dts_master_addr": master_addr,
        "task_name": task_name,
        "source_endpoints": source_endpoints,
        "sync_scope": sync_scope,
        "catchup_recheck": catchup_recheck,
        "api_timeout_sec": api_timeout_sec,
        "checksum_passed": checksum_passed,
        "skip_checksum": skip_checksum,
    }
    if deploy_path:
        # 可选：仅作运维上下文，actuator 停任务不再依赖
        payload["deploy_path"] = deploy_path
    return payload


def resolve_dts_master_exec_target(plan: DtsMigratePlan, master_addr: str) -> dict[str, Any]:
    """解析 Job 执行目标：只打 DTS Master 主机（dict，含 ip + bk_cloud_id）。"""
    master_ip = master_addr.split(":")[0] if master_addr else ""
    if not master_ip:
        raise ValueError(_("cutover 执行目标解析失败：master_addr 无效"))

    if plan.dts_cluster_id:
        from backend.db_meta.models import MysqlDtsCluster

        dts_cluster = MysqlDtsCluster.objects.filter(id=plan.dts_cluster_id).first()
        if dts_cluster:
            for node in dts_cluster.master_nodes or []:
                if node.get("ip") == master_ip:
                    return {"ip": master_ip, "bk_cloud_id": int(node.get("bk_cloud_id", plan.bk_cloud_id or 0))}

    if plan.deploy_subflow_inp:
        for host in plan.deploy_subflow_inp.master_hosts or []:
            if host.ip == master_ip:
                return {"ip": master_ip, "bk_cloud_id": int(host.bk_cloud_id)}

    # 兜底：使用 plan 云区域
    return {"ip": master_ip, "bk_cloud_id": int(plan.bk_cloud_id or 0)}
