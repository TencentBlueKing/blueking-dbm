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
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_MIGRATE_USER_MAX_LENGTH,
    MYSQL_DTS_MIGRATE_USER_PREFIX,
    MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH,
)
from backend.flow.utils.mysql.mysql_act_dataclass import AddTempUserKwargs, DropUserKwargs

logger = logging.getLogger("flow")

# 与 AddUserComponent / DropUserComponent.code 对齐，避免 utils 反向依赖 components
_MYSQL_ADD_USER_COMPONENT_CODE = "mysql_add_user"
_MYSQL_DROP_USER_COMPONENT_CODE = "mysql_drop_user"

if TYPE_CHECKING:
    from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan

# Wiki: 源端读 + binlog；目标端写。一期共用临时账号，权限取并集。
# RELOAD 属于 GLOBAL 权限（见 dbpermission.constants.MySQLPrivType.GLOBAL）
# 版本附加：<5.6 → SUPER；≥8.0 → BACKUP_ADMIN（按每个授权目标自身 major_version）
DTS_MIGRATE_DML_DDL_PRIV = (
    "SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, "
    "LOCK TABLES, CREATE VIEW, SHOW VIEW, TRIGGER, EVENT"
)
DTS_MIGRATE_GLOBAL_PRIV = "REPLICATION SLAVE, REPLICATION CLIENT, PROCESS, RELOAD"

_MYSQL_VERSION_56 = None
_MYSQL_VERSION_80 = None


def _mysql_version_thresholds() -> tuple[int, int]:
    """延迟加载阈值，避免循环依赖。"""
    global _MYSQL_VERSION_56, _MYSQL_VERSION_80
    if _MYSQL_VERSION_56 is None or _MYSQL_VERSION_80 is None:
        from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

        _MYSQL_VERSION_56 = mysql_version_parse("5.6")
        _MYSQL_VERSION_80 = mysql_version_parse("8.0")
    return _MYSQL_VERSION_56, _MYSQL_VERSION_80


def parse_dts_migrate_major_version(major_version: str) -> int:
    """解析集群 major_version；空或无数字返回 0（视为不可解析）。"""
    from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

    if not (major_version or "").strip():
        return 0
    return mysql_version_parse(major_version)


def resolve_dts_migrate_global_priv(major_version: str) -> str:
    """按实例主版本拼 DTS 临时账号 GLOBAL 权限串。

    - 基础：DTS_MIGRATE_GLOBAL_PRIV
    - ver < 5.6：追加 SUPER
    - ver >= 8.0：追加 BACKUP_ADMIN
    - ver == 0：抛 ValueError（主闸在单据 Serializer；此处为防御）
    """
    ver = parse_dts_migrate_major_version(major_version)
    if ver <= 0:
        raise ValueError(_("集群 major_version 无效或为空: {!r}").format(major_version))
    ver_56, ver_80 = _mysql_version_thresholds()
    privs = [DTS_MIGRATE_GLOBAL_PRIV]
    if ver < ver_56:
        privs.append("SUPER")
    if ver >= ver_80:
        privs.append("BACKUP_ADMIN")
    return ", ".join(privs)


@dataclass(frozen=True)
class DtsGrantTarget:
    bk_cloud_id: int
    address: str
    cluster_id: int
    major_version: str = ""


def generate_dts_migrate_username() -> str:
    """生成 DTS 迁移临时用户名：``{prefix}{随机后缀}``，总长 ≤16（兼容旧版 MySQL）。

    创建与删除共用同一用户名：由本函数生成后写入 migrate_context / temp_account_snapshot，
    drop_user 路径只读取快照中的 user，不再二次生成。
    """
    if len(MYSQL_DTS_MIGRATE_USER_PREFIX) + MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH > MYSQL_DTS_MIGRATE_USER_MAX_LENGTH:
        raise ValueError(_("DTS 临时用户名前缀+后缀长度超过 MySQL 兼容上限 {}").format(MYSQL_DTS_MIGRATE_USER_MAX_LENGTH))
    suffix = get_random_string(length=MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH).lower()
    return f"{MYSQL_DTS_MIGRATE_USER_PREFIX}{suffix}"


def generate_dts_migrate_credentials() -> tuple[str, str]:
    """生成迁移用临时账号，由 Flow 内部使用，不暴露给提单页。"""
    user = generate_dts_migrate_username()
    password = get_random_string(length=16)
    return user, password


def resolve_migrate_temp_account_for_pipeline(
    plan: "DtsMigratePlan",
) -> tuple[str, str, list[str], list[DtsGrantTarget]]:
    """建流期解析授权并生成临时账号，供 migrate 与成功路径 dts-task-clean 同源使用。"""
    from backend.flow.utils.mysql.dts.migrate_helper import collect_migrate_grant_targets

    grant_hosts = resolve_dts_grant_hosts(plan)
    grant_targets = collect_migrate_grant_targets(plan)
    if not grant_hosts:
        raise ValueError(_("未解析到 DTS Worker IP，拒绝使用 %% 授权，请先确保 DTS 集群已部署或填写 deploy"))
    if not grant_targets:
        raise ValueError(_("未找到需要授权的迁移实例"))
    dts_user, dts_password = generate_dts_migrate_credentials()
    return dts_user, dts_password, grant_hosts, grant_targets


def grant_targets_to_dicts(targets: list[DtsGrantTarget]) -> list[dict]:
    return [asdict(t) for t in targets]


def resolve_dts_grant_hosts(plan: "DtsMigratePlan") -> list[str]:
    """从 migrate plan 解析授权来源 IP，供编排期组装 AddUser acts。

    grant_hosts = DTS Worker IP ∪ DTS Master IP。
    cutover 在 dts-master 上连源端加锁，MySQL 校验的是 user@'<master-ip>'，
    因此必须显式并入 Master（同机部署时去重即可）。
    """
    ips: set[str] = set()
    if plan.dts_cluster_id:
        from backend.db_meta.models import MysqlDtsCluster

        dts_cluster = MysqlDtsCluster.objects.filter(id=plan.dts_cluster_id).first()
        if dts_cluster:
            ips.update(node["ip"] for node in (dts_cluster.worker_nodes or []) if node.get("ip"))
            ips.update(node["ip"] for node in (dts_cluster.master_nodes or []) if node.get("ip"))
    if plan.deploy_subflow_inp:
        for host in plan.deploy_subflow_inp.worker_hosts or []:
            if host.ip:
                ips.add(host.ip)
        for host in plan.deploy_subflow_inp.master_hosts or []:
            if host.ip:
                ips.add(host.ip)
    return sorted(ips)


def build_dts_add_user_parallel_acts(
    *,
    dts_user: str,
    dts_password: str,
    grant_hosts: list[str],
    grant_targets: list[DtsGrantTarget],
) -> list[dict[str, Any]]:
    """组装并行 AddUserComponent acts（每个授权目标实例一个）。"""
    acts = []
    for target in grant_targets:
        acts.append(
            {
                "act_name": _("创建 DTS 临时用户 {}@{}").format(dts_user, target.address),
                "act_component_code": _MYSQL_ADD_USER_COMPONENT_CODE,
                "kwargs": asdict(
                    AddTempUserKwargs(
                        bk_cloud_id=target.bk_cloud_id,
                        hosts=list(grant_hosts),
                        user=dts_user,
                        psw=dts_password,
                        address=target.address,
                        dbname="%",
                        dml_ddl_priv=DTS_MIGRATE_DML_DDL_PRIV,
                        global_priv=resolve_dts_migrate_global_priv(target.major_version),
                    )
                ),
            }
        )
    return acts


def build_dts_drop_user_parallel_acts(
    *,
    dts_user: str,
    grant_hosts: list[str],
    grant_targets: list[dict],
    ignore_errors: bool = True,
) -> list[dict[str, Any]]:
    """组装并行 DropUserComponent acts（user@host × 目标实例笛卡尔积）。"""
    acts = []
    for target in grant_targets:
        address = target.get("address")
        bk_cloud_id = target.get("bk_cloud_id")
        if not address or bk_cloud_id is None:
            continue
        for host in grant_hosts:
            kwargs = asdict(
                DropUserKwargs(
                    bk_cloud_id=int(bk_cloud_id),
                    host=host,
                    user=dts_user,
                    address=address,
                )
            )
            kwargs["ignore_errors"] = ignore_errors
            acts.append(
                {
                    "act_name": _("删除 DTS 临时用户 {}@{}@{}").format(dts_user, host, address),
                    "act_component_code": _MYSQL_DROP_USER_COMPONENT_CODE,
                    "kwargs": kwargs,
                }
            )
    return acts


def build_temp_account_snapshot(
    *,
    dts_user: str,
    grant_hosts: list[str],
    grant_targets: list[DtsGrantTarget] | list[dict],
) -> dict:
    """构建可落库/可回放的临时账号快照（不含密码）。"""
    targets: list[dict] = []
    for item in grant_targets:
        if isinstance(item, DtsGrantTarget):
            targets.append(asdict(item))
        else:
            targets.append(dict(item))
    return {
        "user": dts_user,
        "grant_hosts": list(grant_hosts),
        "grant_targets": targets,
    }


def _normalize_temp_account_snapshot(snapshot: dict | None) -> dict | None:
    """校验并规范化临时账号快照；信息不完整时返回 None。"""
    if not snapshot or not isinstance(snapshot, dict):
        return None
    user = snapshot.get("user") or ""
    grant_hosts = list(snapshot.get("grant_hosts") or [])
    grant_targets = list(snapshot.get("grant_targets") or [])
    if not user or not grant_hosts or not grant_targets:
        return None
    return {
        "user": user,
        "grant_hosts": grant_hosts,
        "grant_targets": grant_targets,
    }


def collect_unique_temp_account_snapshots(
    *,
    ticket_id: int = 0,
    dts_cluster_id: int = 0,
) -> list[dict]:
    """按 ticket / dts_cluster 收集 MysqlDtsInfo.temp_account_snapshot，按 user 去重。"""
    from backend.db_meta.models.mysql_dts import MysqlDtsInfo

    if not ticket_id and not dts_cluster_id:
        return []
    qs = MysqlDtsInfo.objects.all()
    if ticket_id:
        qs = qs.filter(ticket_id=ticket_id)
    if dts_cluster_id:
        qs = qs.filter(dts_cluster_id=dts_cluster_id)

    snapshots: list[dict] = []
    seen_users: set[str] = set()
    for dts_info in qs.iterator():
        normalized = _normalize_temp_account_snapshot(dts_info.temp_account_snapshot)
        if not normalized:
            continue
        user = normalized["user"]
        if user in seen_users:
            continue
        seen_users.add(user)
        snapshots.append(normalized)
    return snapshots


def extract_temp_account_snapshot_from_node_inputs(node_inputs: dict | None) -> dict | None:
    """从 pipeline 节点 inputs.trans_data.migrate_context 提取临时账号快照。

    覆盖 update_meta 尚未落库、仅 prepare_user 已写入上下文的失败/终止场景。
    """
    if not node_inputs or not isinstance(node_inputs, dict):
        return None
    trans_data = node_inputs.get("trans_data")
    if trans_data is None:
        return None

    if isinstance(trans_data, dict):
        ctx = trans_data.get("migrate_context") or {}
        if not isinstance(ctx, dict):
            return None
        dts_user = ctx.get("dts_user") or ""
        grant_hosts = list(ctx.get("grant_hosts") or [])
        grant_targets = list(ctx.get("grant_targets") or [])
    else:
        ctx = getattr(trans_data, "migrate_context", None)
        if ctx is None:
            return None
        dts_user = getattr(ctx, "dts_user", "") or ""
        grant_hosts = list(getattr(ctx, "grant_hosts", None) or [])
        grant_targets = list(getattr(ctx, "grant_targets", None) or [])

    if not dts_user or not grant_hosts or not grant_targets:
        return None
    return build_temp_account_snapshot(
        dts_user=dts_user,
        grant_hosts=grant_hosts,
        grant_targets=grant_targets,
    )


def _drop_one_temp_user(*, dts_user: str, host: str, address: str, bk_cloud_id: int) -> None:
    """对单个 user@host@address 尽力 DROP；失败只打日志。"""
    from backend.components import DRSApi
    from backend.flow.plugins.components.collections.mysql.drop_user import is_ignorable_drop_user_error

    sql = "drop user `{}`@`{}`;".format(dts_user, host)
    try:
        resp = DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": [sql],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        top_err = (resp[0].get("error_msg") or "") if resp else ""
        cmd_err = ""
        if resp and resp[0].get("cmd_results"):
            cmd_err = resp[0]["cmd_results"][0].get("error_msg") or ""
        err = top_err or cmd_err
        if not err:
            logger.info(_("回收 DTS 临时用户成功 {}@{}@{}").format(dts_user, host, address))
            return
        if is_ignorable_drop_user_error(err):
            logger.warning(_("忽略回收 DTS 临时用户失败 {}@{}@{}: {}").format(dts_user, host, address, err))
            return
        logger.warning(_("回收 DTS 临时用户失败 {}@{}@{}: {}").format(dts_user, host, address, err))
    except Exception as exc:  # pylint: disable=broad-except
        if is_ignorable_drop_user_error(str(exc)):
            logger.warning(_("忽略回收 DTS 临时用户失败 {}@{}@{}: {}").format(dts_user, host, address, exc))
            return
        logger.warning(_("回收 DTS 临时用户异常 {}@{}@{}: {}").format(dts_user, host, address, exc))


def best_effort_drop_dts_temp_accounts_from_snapshots(snapshots: list[dict]) -> None:
    """按快照同步尽力 DROP 临时账号；全程不抛异常，避免阻断终止回调。"""
    for snapshot in snapshots or []:
        normalized = _normalize_temp_account_snapshot(snapshot)
        if not normalized:
            continue
        dts_user = normalized["user"]
        grant_hosts = normalized["grant_hosts"]
        logger.info(
            _("开始回收 DTS 临时账号: user={}, hosts={}, targets={}").format(
                dts_user, len(grant_hosts), len(normalized["grant_targets"])
            )
        )
        for target in normalized["grant_targets"]:
            if not isinstance(target, dict):
                continue
            address = target.get("address")
            bk_cloud_id = target.get("bk_cloud_id")
            if not address or bk_cloud_id is None:
                continue
            for host in grant_hosts:
                _drop_one_temp_user(
                    dts_user=dts_user,
                    host=host,
                    address=address,
                    bk_cloud_id=int(bk_cloud_id),
                )
