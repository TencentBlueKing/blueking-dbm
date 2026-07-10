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
from dataclasses import asdict, is_dataclass

from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.mysqldts import decommission
from backend.db_meta.models import MysqlDtsCluster
from backend.db_meta.models.mysql_dts import MysqlDtsInfo, MysqlDtsStatus
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.signal.callback_map import create_ticket_handler
from backend.flow.utils.mysql.dts.constants import DtsLifecycleMode
from backend.flow.utils.mysql.dts.migrate_credentials import (
    best_effort_drop_dts_temp_accounts_from_snapshots,
    collect_unique_temp_account_snapshots,
    extract_temp_account_snapshot_from_node_inputs,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")

# 人工终止(撤销，页面「终止任务」→ REVOKED)：仅尽力 DROP 临时账号（非完整 dts-task-clean）。
# FAILED（节点执行失败）不 drop，保留账号便于排查；FINISHED 不 drop——成功 DROP 由总流程末尾 dts-task-clean 编排。
_RECYCLE_TEMP_ACCOUNT_STATUSES = {StateType.REVOKED}

# cutover / 终止后的业务终态：节点 RUNNING/FAILED 不得回写覆盖（后续 dts-task-clean 仍会触发节点信号）。
# REVOKED 另单独保护 Disconnected（见 _sync_migrate_status）。
_TERMINAL_MIGRATE_STATUSES = {
    MysqlDtsStatus.Disconnected.value,
    MysqlDtsStatus.Terminated.value,
}


def _as_mapping(value) -> dict:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return {}


def _sync_migrate_status(ticket_id: int, status: StateType):
    # call_ticket_handler 透传的是节点级 to_state；每个节点 FINISHED 都会触发本回调。
    # 迁移 status 由 update_meta / cutover_meta 等组件写入；节点 FINISHED 不再改库。
    status_map = {
        StateType.RUNNING: MysqlDtsStatus.FullOnline.value,
        StateType.FAILED: MysqlDtsStatus.FullFailed.value,
        StateType.REVOKED: MysqlDtsStatus.Terminated.value,
    }
    mapped = status_map.get(status)
    if not mapped:
        return
    qs = MysqlDtsInfo.objects.filter(ticket_id=ticket_id)
    # 节点生命周期信号不能盖掉业务终态：
    # - RUNNING/FAILED：排除 Disconnected/Terminated
    # - REVOKED：可把进行中行标 Terminated，但不得盖掉已 cutover 成功的 Disconnected
    #   （同单多 task 时部分已切换、部分未切换仍可终止未完成行）
    if status in (StateType.RUNNING, StateType.FAILED):
        qs = qs.exclude(status__in=_TERMINAL_MIGRATE_STATUSES)
    elif status == StateType.REVOKED:
        qs = qs.exclude(status=MysqlDtsStatus.Disconnected.value)
    qs.update(status=mapped)


def _resolve_node_inputs(root_id: str, node_id: str) -> dict:
    """读取节点 inputs；失败返回空 dict，不阻断终止回调。"""
    try:
        engine = BambooEngine(root_id=root_id)
        result = engine.get_node_input_data(node_id=node_id)
        data = getattr(result, "data", None) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(_("读取 DTS 迁移节点 inputs 失败 root_id={} node_id={}: {}").format(root_id, node_id, exc))
        return {}


def _recycle_migrate_temp_accounts(ticket_id: int, node_inputs: dict):
    """REVOKED（终止任务）时尽力回收本单已创建的 DTS 临时账号（仅账号，非完整 clean）。

    账号来源优先 MysqlDtsInfo.temp_account_snapshot；若 update_meta 未落库，
    回退到节点 trans_data.migrate_context（prepare_user 已写入）。
    DROP 失败只打日志，不抛异常。

    禁止在本回调编排 mysql_dts_task_clean_subflow，也禁止终止时 stop_task / 注销 source；
    完整 clean（含后续 task/source 扩展）仅属成功路径总流程末尾 dts-task-clean。
    """
    try:
        snapshots = collect_unique_temp_account_snapshots(ticket_id=ticket_id) if ticket_id else []
        if not snapshots:
            ctx_snapshot = extract_temp_account_snapshot_from_node_inputs(node_inputs)
            if ctx_snapshot:
                snapshots = [ctx_snapshot]
        if not snapshots:
            logger.info(_("DTS 迁移终态无临时账号快照可回收 ticket_id={}").format(ticket_id))
            return
        best_effort_drop_dts_temp_accounts_from_snapshots(snapshots)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(_("DTS 迁移终态回收临时账号异常 ticket_id={}: {}").format(ticket_id, exc))


def _finalize_ephemeral_dts(global_data: dict):
    """临时 DTS 终态回收元数据（与临时账号回收相互独立）。"""
    ticket_id = global_data.get("ticket_id")
    migrate_plan = _as_mapping(global_data.get("migrate_plan"))
    lifecycle = migrate_plan.get("dts_lifecycle", "")
    cleanup_after = migrate_plan.get("cleanup_after_migrate", False)
    if lifecycle != DtsLifecycleMode.DEPLOY_EPHEMERAL.value and not cleanup_after:
        return
    dts_info = MysqlDtsInfo.objects.filter(ticket_id=ticket_id).first()
    if not dts_info or not dts_info.dts_cluster_id:
        return
    dts_cluster = MysqlDtsCluster.objects.filter(id=dts_info.dts_cluster_id).first()
    if not dts_cluster:
        return
    # 一期终态先回收元数据；完整 stop_task/kill 进程由独立 DESTROY 单据或后续 cleanup 编排补齐
    decommission(
        dts_cluster_id=dts_cluster.id,
        recycle_hosts=migrate_plan.get("recycle_dts_hosts", True),
        updater=global_data.get("created_by", ""),
    )


def _handle_migrate_callback(root_id: str, node_id: str, status: StateType, ticket_id_from_signal: int = 0):
    """迁移单据回调：同步状态；REVOKED（终止任务）时仅尽力 DROP 临时账号，并可选回收 ephemeral DTS。

    FAILED 仅同步元数据状态，不 DROP 临时账号；成功路径账号清理由总流程 dts-task-clean 负责，
    本 handler 在 FINISHED 时不 DROP。
    """
    node_inputs = _resolve_node_inputs(root_id, node_id)
    global_data = node_inputs.get("global_data") or {}
    if not isinstance(global_data, dict):
        global_data = {}
    # global_data.ticket_id 优先；信号侧 tree.uid 兜底（部分节点 inputs 可能不含 ticket_id）
    ticket_id = int(global_data.get("ticket_id") or ticket_id_from_signal or 0)
    if ticket_id and "ticket_id" not in global_data:
        global_data = {**global_data, "ticket_id": ticket_id}
    if ticket_id:
        _sync_migrate_status(ticket_id, status)
    if status not in _RECYCLE_TEMP_ACCOUNT_STATUSES:
        return
    # 临时账号在源/目标 MySQL 上，与 ephemeral DTS 生命周期无关；终止仅尽力 DROP 账号
    _recycle_migrate_temp_accounts(ticket_id, node_inputs)
    _finalize_ephemeral_dts(global_data)


@create_ticket_handler(TicketType.MYSQL_TO_MYSQL_MIGRATE)
def mysql_to_mysql_migrate_callback_handler(root_id: str, node_id: str, status: StateType, **kwargs):
    """MySQL 数据迁移状态回调与终态清理。"""
    logger.info(_("执行 mysql_to_mysql_migrate_callback_handler root_id={}").format(root_id))
    _handle_migrate_callback(root_id, node_id, status, ticket_id_from_signal=int(kwargs.get("ticket_id") or 0))


@create_ticket_handler(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE)
def mysql_ha_to_cluster_migrate_callback_handler(root_id: str, node_id: str, status: StateType, **kwargs):
    """HA→Cluster 迁移状态回调与终态清理。"""
    logger.info(_("执行 mysql_ha_to_cluster_migrate_callback_handler root_id={}").format(root_id))
    _handle_migrate_callback(root_id, node_id, status, ticket_id_from_signal=int(kwargs.get("ticket_id") or 0))
