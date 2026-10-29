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
import posixpath
import re
import shlex
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import Error, transaction
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.db_meta.api.cluster.mysqldts.decommission import decommission
from backend.db_meta.models import Machine, MysqlDtsCluster
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus, MysqlDtsInfo
from backend.flow.consts import DBA_ROOT_USER, PENDING_STATES, SUCCESS
from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_revoke_downloads import (
    BackupDownloadPending,
    ensure_backup_downloads_finished,
)
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_DEPLOY_BASE_PATH,
    MYSQL_DTS_MASTER_PORT,
    MYSQL_DTS_MYLOADER_BACKUP_DIR_TMPL,
    MYSQL_DTS_WORKER_PORT,
    DtsLifecycleMode,
    FullLoadEngine,
    get_default_deploy_path,
    get_full_migrate_data_dir,
    validate_dts_deploy_path,
)
from backend.flow.utils.mysql.dts.migrate_plan import infer_dts_resource_intent
from backend.flow.utils.mysql.dts.monitor_config import (
    DTS_MACHINE_TYPES,
    MYSQL_CROND_INSTALL_PATH,
    MYSQL_MONITOR_INSTALL_PATH,
)
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.ticket.constants import FlowType
from backend.ticket.models import Flow, Ticket
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")

# 作业平台脚本超时；轮询要比它多等一会儿，避免作业还在跑就被判成失败
_JOB_TIMEOUT_SECONDS = 120
_JOB_POLL_DEADLINE_SECONDS = _JOB_TIMEOUT_SECONDS + 30
_JOB_POLL_SECONDS = 1
# mysql-crond 部署时会往 mysql 用户 crontab 写一条每分钟执行的保活任务
_KEEP_ALIVE_SCRIPT = f"{MYSQL_CROND_INSTALL_PATH}/mysql_crond_keep_alive.sh"
# 只允许 /data/dbbak/xxx、/data1/dbbak/xxx 这类数据盘备份目录下的子目录；/dataN 和 /dataN/dbbak 本身不允许
_BACKUP_SUBDIR_RE = re.compile(r"/data\d*/dbbak/[^/]+(/[^/]+)*")
_DTS_BASE = MYSQL_DTS_DEPLOY_BASE_PATH.rstrip("/")
# 本单申请的 DTS 机器上不该有 MySQL 实例；出现 mysqld 进程或 MySQL 数据目录就整台不碰
_MYSQL_DATA_GLOB = "/data*/mysqldata"


class MetaQueryError(Exception):
    """查询 Ticket / Machine / MysqlDtsCluster 失败。组件返回失败，不输出任何主机。"""


class RemoteJobUnknown(Exception):
    """主机脚本没下发成功，或在限时内没结束。结果未知，组件返回失败，等人工重试本步骤。"""


class CleanupIncomplete(Exception):
    """清理失败或仍有异步写入，保留失败状态供人工重试，不发布退池名单。"""


class HostVerdict(Enum):
    """单台主机的处理结论。"""

    # 已清理干净，可以退回资源池
    RETURN = "return"
    # 不能确认干净或不属于本单，留在原地不退回
    HOLD = "hold"


@dataclass(frozen=True)
class NodeHost:
    """单据 nodes 里本单申请到的一台主机。同一台机器同时是 master 和 worker 时 roles 有两个值。"""

    ip: str
    bk_cloud_id: int
    bk_host_id: int | None
    roles: tuple[str, ...]


@dataclass(frozen=True)
class DeployRow:
    """单据里一行 deploy 模式的迁移，以及清理这行机器需要的全部信息。

    paths 为 None 表示有路径越界或无法确定，这一行的机器一律不碰。
    myloader_markers 是这一行 myloader 可能用到的全部目录，用来匹配 myloader 进程。
    """

    cluster_name: str
    bk_biz_id: int
    deploy_path: str
    hosts: tuple[NodeHost, ...]
    paths: tuple[str, ...] | None
    use_myloader: bool
    myloader_markers: tuple[str, ...]


def _norm(path: str) -> str:
    """规范化成绝对路径。空串、相对路径、含 .. 的路径一律返回空串。"""
    raw = (path or "").strip()
    if not raw or any(part == ".." for part in raw.split("/")):
        return ""
    normalized = posixpath.normpath(raw)
    if not normalized.startswith("/"):
        return ""
    return normalized


def _is_deploy_subdir(path: str) -> bool:
    """是否位于 DTS 根目录之下（不含根目录本身）。"""
    return _norm(path).startswith(_DTS_BASE + "/")


def _is_backup_subdir(path: str) -> bool:
    """是否位于 /dataN/dbbak/ 之下（不含 /dataN 和 /dataN/dbbak 本身）。"""
    return bool(_BACKUP_SUBDIR_RE.fullmatch(_norm(path)))


def _dedupe(paths: list[str]) -> tuple[str, ...]:
    """保序去重。"""
    seen = set()
    ordered = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return tuple(ordered)


def _task_names(row: dict) -> tuple[str, ...]:
    """取出这一行所有迁移任务名，用来拼内置导出目录 exported_data.{task_name}。"""
    migrate = row.get("migrate") or {}
    names = []
    for key in ("one_to_one", "many_to_one"):
        name = str((migrate.get(key) or {}).get("task_name") or "").strip()
        if name:
            names.append(name)
    for target in (migrate.get("one_to_many") or {}).get("targets") or []:
        if not isinstance(target, dict):
            continue
        name = str(target.get("task_name") or "").strip()
        if name:
            names.append(name)
    return tuple(dict.fromkeys(names))


def _source_blocks(row: dict) -> list[dict]:
    """取出这一行三种拓扑下的全部 source 配置块。"""
    migrate = row.get("migrate") or {}
    blocks = []
    one = (migrate.get("one_to_one") or {}).get("source")
    if isinstance(one, dict):
        blocks.append(one)
    for source in (migrate.get("many_to_one") or {}).get("sources") or []:
        if isinstance(source, dict):
            blocks.append(source)
    fanout = (migrate.get("one_to_many") or {}).get("source")
    if isinstance(fanout, dict):
        blocks.append(fanout)
    return blocks


def _explicit_myloader_dirs(row: dict) -> tuple[str, ...]:
    """单据里显式填写的 myloader_dir，包括 task 级和各 source 级。"""
    found = []
    task_myloader = ((row.get("task") or {}).get("full_load") or {}).get("myloader") or {}
    if isinstance(task_myloader, dict) and str(task_myloader.get("myloader_dir") or "").strip():
        found.append(str(task_myloader["myloader_dir"]).strip())
    for source in _source_blocks(row):
        myloader = source.get("myloader") or {}
        if isinstance(myloader, dict) and str(myloader.get("myloader_dir") or "").strip():
            found.append(str(myloader["myloader_dir"]).strip())
    return tuple(dict.fromkeys(found))


def _uses_myloader(row: dict) -> bool:
    """这一行的全量导入是否走 myloader。"""
    engine = str((((row.get("task") or {}).get("full_load") or {}).get("engine") or "")).strip()
    return engine == FullLoadEngine.MYLOADER.value


def resolve_deploy_path(deploy: dict) -> tuple[str, str, bool]:
    """解析部署路径。

    返回 (部署路径, 集群名, 是否自定义路径)。没填 deploy_path 时用默认路径；
    填了但不合法时返回空路径，后续整行不清理。
    """
    cluster_name = str(deploy.get("cluster_name") or "").strip()
    raw = str(deploy.get("deploy_path") or "").strip()
    try:
        default_path = get_default_deploy_path(cluster_name) if cluster_name else ""
    except ValueError:
        default_path = ""
    if not raw:
        return default_path, cluster_name, False
    try:
        path = validate_dts_deploy_path(raw)
    except ValueError:
        return "", cluster_name, True
    return path, cluster_name, _norm(path) != _norm(default_path)


def _exported_data_paths(cluster_name: str, task_names: tuple[str, ...]) -> tuple[str, ...] | None:
    """内置导出目录。它总在默认部署路径下，自定义部署路径时要单独删。"""
    paths = []
    for task_name in task_names:
        try:
            path = get_full_migrate_data_dir(cluster_name, task_name)
        except ValueError:
            return None
        if not _is_deploy_subdir(path):
            return None
        paths.append(_norm(path))
    return tuple(paths)


def myloader_dirs(explicit: tuple[str, ...], root_id: str) -> tuple[str, ...] | None:
    """这一行 myloader 可能用到的全部目录：每个显式目录，加上 root_id 推出的默认目录。

    迁移时每个 source 用的是 ``显式 myloader_dir or 默认目录``，所以两类都要算上。
    返回 None 表示有目录不在 /dataN/dbbak/ 之下，或一个目录都确定不了。
    同一份结果既用来删目录，也用来匹配 myloader 进程，保证两边口径一致。
    """
    paths = []
    for path in explicit:
        if not _is_backup_subdir(path):
            return None
        paths.append(_norm(path))
    root = (root_id or "").strip()
    if root:
        dump_root = posixpath.dirname(MYSQL_DTS_MYLOADER_BACKUP_DIR_TMPL).format(root_id=root)
        if not _is_backup_subdir(dump_root):
            return None
        paths.append(_norm(dump_root))
    if not paths:
        return None
    return _dedupe(paths)


def plan_delete_paths(
    *,
    deploy_path: str,
    cluster_name: str,
    deploy_path_is_custom: bool,
    task_names: tuple[str, ...],
    dump_dirs: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """算出这一行要删的全部目录：部署目录、自定义路径时的内置导出目录、myloader 目录。

    不走 myloader 时 dump_dirs 传空元组。返回 None 表示有路径越界，这一行不碰磁盘。
    """
    if not _is_deploy_subdir(deploy_path):
        return None
    paths = [_norm(deploy_path)]
    if deploy_path_is_custom:
        exported = _exported_data_paths(cluster_name, task_names)
        if exported is None:
            return None
        paths.extend(exported)
    if dump_dirs is None:
        return None
    paths.extend(dump_dirs)
    return _dedupe(paths)


def _iter_detail_rows(details: dict) -> list[tuple[int, dict]]:
    """遍历单据 details 的每一行，兼容多行 infos 和单行平铺两种格式。"""
    infos = details.get("infos")
    if isinstance(infos, list) and infos:
        return [(idx, row) for idx, row in enumerate(infos) if isinstance(row, dict)]
    if isinstance(details.get("dts_resource"), dict):
        return [(0, details)]
    return []


def _node_hosts(nodes: dict, row_index: int) -> tuple[NodeHost, ...]:
    """从单据 nodes 的 {idx}_master / {idx}_worker 取出这一行申请到的主机，同一台机器合并角色。"""
    by_key: dict[tuple[str, int], NodeHost] = {}
    order: list[tuple[str, int]] = []
    for role in ("master", "worker"):
        entries = nodes.get(f"{row_index}_{role}") or []
        if not isinstance(entries, list):
            continue
        for node in entries:
            host = _node_host(node, role)
            if host is None:
                continue
            key = (host.ip, host.bk_cloud_id)
            current = by_key.get(key)
            if current is None:
                by_key[key] = host
                order.append(key)
                continue
            roles = current.roles if role in current.roles else current.roles + (role,)
            host_id = current.bk_host_id if current.bk_host_id is not None else host.bk_host_id
            by_key[key] = NodeHost(ip=current.ip, bk_cloud_id=current.bk_cloud_id, bk_host_id=host_id, roles=roles)
    return tuple(by_key[key] for key in order)


def _node_host(node: Any, role: str) -> NodeHost | None:
    """把 nodes 里的一个主机字典转成 NodeHost，没有 IP 时返回 None。"""
    if not isinstance(node, dict):
        return None
    ip = str(node.get("ip") or "").strip()
    if not ip:
        return None
    raw_id = node.get("bk_host_id")
    host_id = None if raw_id in (None, "") else int(raw_id)
    return NodeHost(ip=ip, bk_cloud_id=int(node.get("bk_cloud_id") or 0), bk_host_id=host_id, roles=(role,))


def _deploy_spec(row: dict) -> dict | None:
    """deploy 模式的行返回部署配置；use_existing 或无法识别的行返回 None，不清理。"""
    try:
        intent = infer_dts_resource_intent(row.get("dts_resource"))
    except ValueError:
        logger.error(_("无法识别 dts_resource，跳过该行"))
        return None
    if intent.kind != DtsLifecycleMode.DEPLOY.value:
        return None
    return intent.deploy or {}


def collect_deploy_rows(details: dict, bk_biz_id: int, root_id: str) -> list[DeployRow]:
    """把单据 details 解析成待清理的 DeployRow 列表，只包含 deploy 模式的行。"""
    nodes = details.get("nodes") or {}
    if not isinstance(nodes, dict):
        nodes = {}
    rows = []
    for row_index, row in _iter_detail_rows(details):
        deploy = _deploy_spec(row)
        if deploy is None:
            continue
        deploy_path, cluster_name, is_custom = resolve_deploy_path(deploy)
        use_myloader = _uses_myloader(row)
        dump_dirs = myloader_dirs(_explicit_myloader_dirs(row), root_id) if use_myloader else ()
        paths = plan_delete_paths(
            deploy_path=deploy_path,
            cluster_name=cluster_name,
            deploy_path_is_custom=is_custom,
            task_names=_task_names(row),
            dump_dirs=dump_dirs,
        )
        rows.append(
            DeployRow(
                cluster_name=cluster_name,
                bk_biz_id=bk_biz_id,
                deploy_path=_norm(deploy_path),
                hosts=_node_hosts(nodes, row_index),
                paths=paths,
                use_myloader=use_myloader,
                myloader_markers=dump_dirs or (),
            )
        )
    return rows


def _parent_ticket_id(global_data: dict) -> int:
    """被终止的迁移单 ID。"""
    for key in ("parent_ticket", "ticket_id"):
        raw = global_data.get(key)
        if raw not in (None, ""):
            return int(raw)
    raise MetaQueryError("missing parent ticket")


def load_parent_ticket(global_data: dict):
    """读取被终止的迁移单。"""
    ticket_id = _parent_ticket_id(global_data)
    try:
        return Ticket.objects.get(id=ticket_id)
    except ObjectDoesNotExist as exc:
        raise MetaQueryError("ticket not found") from exc
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc


def load_migrate_root_id(ticket_id: int) -> str:
    """迁移单内置流程的 root_id，用来推 myloader 默认目录。没有内置流程时返回空串。"""
    try:
        flow = (
            Flow.objects.filter(ticket_id=ticket_id, flow_type=FlowType.INNER_FLOW.value)
            .exclude(flow_obj_id="")
            .first()
        )
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc
    if flow is None:
        return ""
    return str(flow.flow_obj_id or "")


def migrate_pipeline_started(root_id: str) -> bool:
    """迁移单内置流水线是否有节点开始执行过。

    节点在建流水线时就全部写入 FlowNode，状态为 CREATED；开始执行时写 started_at 并改状态。
    没有流水线，或所有节点都还没开始，说明 DBM 没往机器上下发过任何东西。
    """
    if not root_id:
        return False
    try:
        nodes = FlowNode.objects.filter(root_id=root_id)
        if nodes.exclude(status__in=PENDING_STATES, started_at=None).exists():
            return True
        tree = FlowTree.objects.filter(root_id=root_id).first()
        if tree is not None and (
            tree.is_expired or (not nodes.exists() and (tree.tree or tree.status not in PENDING_STATES))
        ):
            raise MetaQueryError("cannot prove migration pipeline never started")
        return False
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc


def load_machine(ip: str, bk_cloud_id: int):
    """按 IP 和云区域查 DBM 里的 Machine，没有时返回 None。"""
    try:
        return Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc


def _cluster_node_keys(cluster) -> set[tuple[str, int]]:
    """集群登记的全部节点 (ip, bk_cloud_id)。节点没写云区域时用集群的云区域。"""
    keys = set()
    for node in list(cluster.master_nodes or []) + list(cluster.worker_nodes or []):
        if isinstance(node, dict) and node.get("ip"):
            keys.add((str(node["ip"]), int(node.get("bk_cloud_id", cluster.bk_cloud_id) or 0)))
    return keys


def find_own_cluster(row: DeployRow):
    """找出这一行自己注册的 DTS 集群。

    按业务和集群名找未销毁的集群，且它登记的节点必须全部是这一行的主机，才算本单的。
    同名但节点对不上的集群属于别的单据（或被别的单据追加过节点），返回 None，不能下线它。
    """
    # 排除 DESTROYED：对已销毁集群再调 decommission 会按 IP 删除 Machine，可能删到后来占用同一 IP 的机器。
    if not row.cluster_name:
        return None
    try:
        cluster = (
            MysqlDtsCluster.objects.filter(bk_biz_id=row.bk_biz_id, name=row.cluster_name)
            .exclude(status=MysqlDtsClusterStatus.DESTROYED.value)
            .first()
        )
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc
    if cluster is None:
        return None
    nodes = _cluster_node_keys(cluster)
    if not nodes or not nodes <= {(host.ip, host.bk_cloud_id) for host in row.hosts}:
        return None
    return cluster


def cluster_used_by_other_ticket(cluster_id: int, ticket_id: int) -> bool:
    """锁内检查其他迁移占用，同时兼容旧版未绑定 DTS ID 的活跃预占。"""
    try:
        active = (
            MysqlDtsInfo.objects.select_for_update()
            .filter(status__in=MysqlDtsInfo.ACTIVE_EXCLUSIVE_STATUSES)
            .exclude(ticket_id=ticket_id)
        )
        if active.filter(dts_cluster_id=cluster_id).exists():
            return True
        legacy_ticket_ids = set(active.filter(dts_cluster_id=0).values_list("ticket_id", flat=True))
        for legacy_ticket in Ticket.objects.filter(id__in=legacy_ticket_ids):
            legacy_ticket_ids.discard(legacy_ticket.id)
            for row_index, detail in _iter_detail_rows(legacy_ticket.details or {}):
                try:
                    intent = infer_dts_resource_intent(detail.get("dts_resource"))
                except ValueError as exc:
                    raise MetaQueryError("invalid legacy DTS resource") from exc
                if intent.dts_cluster_id == cluster_id:
                    return True
        if legacy_ticket_ids:
            raise MetaQueryError("active DTS reservation has no ticket")
        return False
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc


def claim_cluster_for_cleanup(row: DeployRow, ticket_id: int) -> bool:
    """与预占使用同一集群行锁；先提交清理中状态，再做耗时的远程清理。"""
    try:
        with transaction.atomic():
            own = find_own_cluster(row)
            if own is None:
                return True
            cluster = MysqlDtsCluster.objects.select_for_update().get(id=own.id)
            if cluster.status == MysqlDtsClusterStatus.DESTROYED.value:
                raise MetaQueryError("DTS cluster changed during cleanup check")
            if _cluster_node_keys(cluster) != _cluster_node_keys(own):
                raise MetaQueryError("DTS cluster nodes changed during cleanup check")
            if cluster_used_by_other_ticket(cluster.id, ticket_id):
                logger.warning(_("DTS 集群 {} 仍被其他单据使用，这一行主机不清理、不退回").format(cluster.id))
                return False
            cluster.status = MysqlDtsClusterStatus.DESTROYING.value
            cluster.save(update_fields=["status", "update_at"])
        return True
    except (Error, ObjectDoesNotExist) as exc:
        raise MetaQueryError(str(exc)) from exc


def other_live_node_keys(own_cluster_id: int | None) -> set[tuple[str, int]]:
    """除本单集群外，所有未销毁 DTS 集群登记的节点。落在这里的主机被别人占用，不能清理。"""
    try:
        query = MysqlDtsCluster.objects.exclude(status=MysqlDtsClusterStatus.DESTROYED.value)
        if own_cluster_id is not None:
            query = query.exclude(id=own_cluster_id)
        clusters = list(query)
    except Error as exc:
        raise MetaQueryError(str(exc)) from exc
    keys = set()
    for cluster in clusters:
        keys |= _cluster_node_keys(cluster)
    return keys


# (进程名, 命令行里必须出现的路径之一)
ProcessTarget = tuple[str, tuple[str, ...]]

# 先按进程名精确找，再看命令行里有没有本行的路径，只停本行启动的进程。
# 路径后面必须紧跟 / 或空格，避免 /data/dbbak/a 误匹配 /data/dbbak/ab。
# 停不掉时置 DBM_DTS_REMAIN=1，脚本以非 0 退出。
_STOP_FUNCTIONS = """
matched_pids() {
  name="$1"
  shift
  for pid in $(pgrep -x "$name" || true); do
    cmd="$(tr '\\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true) "
    for marker in "$@"; do
      case "$cmd" in
        *"$marker "*|*"$marker/"*) echo "$pid"; break ;;
      esac
    done
  done
}
stop_matched() {
  pids=$(matched_pids "$@")
  if [ -z "$pids" ]; then
    return 0
  fi
  kill $pids 2>/dev/null || true
  sleep 1
  pids=$(matched_pids "$@")
  if [ -n "$pids" ]; then
    kill -9 $pids 2>/dev/null || true
    sleep 1
  fi
  if [ -n "$(matched_pids "$@")" ]; then
    DBM_DTS_REMAIN=1
  fi
}
"""


def _stop_script(targets: tuple[ProcessTarget, ...]) -> str:
    """生成停进程并复查的脚本。任一目标进程停不掉时脚本退出码为 1。"""
    lines = ["DBM_DTS_REMAIN=0", _STOP_FUNCTIONS]
    for name, markers in targets:
        lines.append(" ".join(["stop_matched", shlex.quote(name), *(shlex.quote(marker) for marker in markers)]))
    lines.append("exit $DBM_DTS_REMAIN")
    return "\n".join(lines) + "\n"


def _delete_script(paths: tuple[str, ...]) -> str:
    """生成删除目录的脚本。不存在的路径跳过；删完仍存在时退出码为 1。"""
    lines = ["fail=0"]
    for path in paths:
        quoted = shlex.quote(path)
        lines.append(
            f"if [ -e {quoted} ] || [ -L {quoted} ]; then\n"
            f"  rm -rf -- {quoted}\n"
            f"  if [ -e {quoted} ] || [ -L {quoted} ]; then\n"
            "    fail=1\n"
            "  fi\n"
            "fi"
        )
    lines.append("exit $fail")
    return "\n".join(lines) + "\n"


# 顺序：先摘保活 crontab，防止 mysql-crond 被重新拉起；再摘监控任务、停进程、删目录。
# crontab 只在读取成功且确有保活条目时才改写，且只去掉保活那一行，避免读失败时写入空 crontab 清掉其他任务。
# 结果只看最终状态。中间某步失败但最后都清干净了，这台机器仍可退回。
_MONITOR_BODY = """
monitor_bin="$monitor_root/mysql-monitor"
cur=$(mktemp)
new=$(mktemp)
if crontab -u mysql -l > "$cur" 2>/dev/null && grep -q mysql_crond_keep_alive "$cur"; then
  grep -v mysql_crond_keep_alive "$cur" > "$new" || true
  crontab -u mysql "$new" || true
fi
rm -f -- "$cur" "$new"
pkill -f -- "$keep_alive" 2>/dev/null || true
for port in $ports; do
  cfg="$monitor_root/monitor-config_${port}.yaml"
  if [ -f "$cfg" ] && [ -x "$monitor_bin" ]; then
    "$monitor_bin" clean -c "$cfg" || true
  fi
done
stop_name() {
  pids=$(pgrep -x "$1" || true)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(pgrep -x "$1" || true)
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
      sleep 1
    fi
  fi
}
stop_name mysql-crond
stop_name mysql-monitor
rm -rf -- "$crond_root" "$monitor_root" || true
fail=0
if [ -e "$crond_root" ] || [ -e "$monitor_root" ]; then
  fail=1
fi
if pgrep -x mysql-crond >/dev/null || pgrep -x mysql-monitor >/dev/null; then
  fail=1
fi
if crontab -u mysql -l 2>/dev/null | grep -q mysql_crond_keep_alive; then
  fail=1
fi
exit $fail
"""


def _monitor_script() -> str:
    """生成清理 mysql-crond、mysql-monitor 及保活 crontab 的脚本。"""
    header = [
        f"monitor_root={shlex.quote(MYSQL_MONITOR_INSTALL_PATH)}",
        f"crond_root={shlex.quote(MYSQL_CROND_INSTALL_PATH)}",
        f"keep_alive={shlex.quote(_KEEP_ALIVE_SCRIPT)}",
        f"ports='{MYSQL_DTS_MASTER_PORT} {MYSQL_DTS_WORKER_PORT}'",
    ]
    return "\n".join(header) + _MONITOR_BODY


def _mysql_guard_script(data_glob: str = _MYSQL_DATA_GLOB) -> str:
    """生成只读检查脚本：有 mysqld 进程或 MySQL 数据目录时退出码为 1，否则为 0。

    data_glob 不加引号，交给 shell 展开；没有匹配时保持字面量，[ -e ] 为假。
    """
    return (
        "if pgrep -x mysqld >/dev/null 2>&1; then\n"
        "  exit 1\n"
        "fi\n"
        f"for d in {data_glob}; do\n"
        '  if [ -e "$d" ]; then\n'
        "    exit 1\n"
        "  fi\n"
        "done\n"
        "exit 0\n"
    )


def _job_succeeded(job_instance_id: int) -> bool:
    """轮询作业直到结束。

    作业结束且成功返回 True，结束但失败返回 False。查询接口偶发报错时继续轮询；
    过了截止时间仍没结束则抛 RemoteJobUnknown，让本步骤失败可重试，而不是把机器误判成不退回。
    """
    deadline = time.monotonic() + _JOB_POLL_DEADLINE_SECONDS
    while time.monotonic() < deadline:
        try:
            resp = JobApi.get_job_instance_status(
                {
                    "bk_scope_type": "biz_set",
                    "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                    "job_instance_id": job_instance_id,
                    "return_ip_result": True,
                },
                raw=True,
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception(_("查询作业状态失败"))
            time.sleep(_JOB_POLL_SECONDS)
            continue
        data = (resp or {}).get("data") or {}
        if not data.get("finished"):
            time.sleep(_JOB_POLL_SECONDS)
            continue
        status = (data.get("job_instance") or {}).get("status")
        return status == SUCCESS
    raise RemoteJobUnknown(f"job {job_instance_id} did not finish in {_JOB_POLL_DEADLINE_SECONDS}s")


def run_remote_script(ip: str, bk_cloud_id: int, script: str) -> bool:
    """以 root 在目标主机执行脚本并等结果。下发失败抛 RemoteJobUnknown。"""
    body = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": f"DBM_dts_migrate_revoke_{ip}",
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": [{"bk_cloud_id": bk_cloud_id, "ip": ip}]},
        "account_alias": DBA_ROOT_USER,
        "timeout": _JOB_TIMEOUT_SECONDS,
    }
    try:
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)
    except Exception as exc:  # pylint: disable=broad-except
        raise RemoteJobUnknown(f"dispatch to {ip} failed") from exc
    job_instance_id = ((resp or {}).get("data") or {}).get("job_instance_id") if isinstance(resp, dict) else None
    if not job_instance_id:
        raise RemoteJobUnknown(f"dispatch to {ip} returned no job instance")
    return _job_succeeded(int(job_instance_id))


def process_targets(host: NodeHost, row: DeployRow) -> tuple[ProcessTarget, ...]:
    """这台主机上要停的进程。

    dm-worker / dm-master 按本行部署路径下的 bin 匹配；worker 机器走 myloader 时，
    再按本行全部 myloader 目录匹配 myloader 进程。
    """
    targets = [
        ("dm-worker", (f"{row.deploy_path}/bin/dm-worker",)),
        ("dm-master", (f"{row.deploy_path}/bin/dm-master",)),
    ]
    if row.use_myloader and "worker" in host.roles:
        targets.append(("myloader", row.myloader_markers))
    return tuple(targets)


def host_free_of_mysql(host: NodeHost) -> bool:
    """主机上没有 mysqld 进程，也没有 /dataN/mysqldata 目录时返回 True。

    检查脚本只读；脚本因任何原因失败都按「有 MySQL」处理，宁可不退回也不误清理。
    """
    return run_remote_script(host.ip, host.bk_cloud_id, _mysql_guard_script())


def stop_processes_and_recheck(host: NodeHost, targets: tuple[ProcessTarget, ...]) -> bool:
    """停掉目标进程并复查，全部停掉返回 True。"""
    return run_remote_script(host.ip, host.bk_cloud_id, _stop_script(targets))


def delete_remote_paths(host: NodeHost, paths: tuple[str, ...]) -> bool:
    """删除主机上的目录。下发前再校验一次，任一路径越界就不下发，直接返回 False。"""
    if not all(_is_deploy_subdir(path) or _is_backup_subdir(path) for path in paths):
        return False
    return run_remote_script(host.ip, host.bk_cloud_id, _delete_script(tuple(_norm(path) for path in paths)))


def clean_monitor_and_crontab(host: NodeHost) -> bool:
    """清理主机上的监控组件和保活 crontab，最终干净返回 True。"""
    return run_remote_script(host.ip, host.bk_cloud_id, _monitor_script())


def reconcile_host(
    host: NodeHost, row: DeployRow, occupied: set[tuple[str, int]], remote_cleanup: bool
) -> HostVerdict:
    """判断并清理一台主机，返回是否可以退回。

    以下情况直接 HOLD，不碰机器：
    - 没有 bk_host_id；
    - 被别的未销毁 DTS 集群占用；
    - DBM 里登记的 Machine 不是 DTS 机器，或 bk_host_id 和单据里的对不上（IP 已换给别的机器）。
    remote_cleanup 为 False 时（内置流水线一个节点都没跑过），过了上面的检查就直接退回，不下发任何远程脚本。
    否则还要过下面几项，任一项不满足或失败都抛 CleanupIncomplete，保留可重试状态：
    - 这一行路径没有越界；
    - 主机上没有 mysqld 进程和 /dataN/mysqldata 目录（只读检查）；
    - 依次停进程、删目录、清监控都成功。
    """
    if host.bk_host_id is None:
        return HostVerdict.HOLD
    if (host.ip, host.bk_cloud_id) in occupied:
        return HostVerdict.HOLD
    machine = load_machine(host.ip, host.bk_cloud_id)
    if machine is not None and (
        machine.machine_type not in DTS_MACHINE_TYPES or machine.bk_host_id != host.bk_host_id
    ):
        return HostVerdict.HOLD
    if not remote_cleanup:
        return HostVerdict.RETURN
    if row.paths is None:
        raise CleanupIncomplete(_("主机 {}（云区域 {}）的清理路径不安全或无法确定").format(host.ip, host.bk_cloud_id))
    if not host_free_of_mysql(host):
        raise CleanupIncomplete(_("主机 {}（云区域 {}）未通过 MySQL 安全检查，请核查实例、数据目录及作业结果").format(host.ip, host.bk_cloud_id))
    if not stop_processes_and_recheck(host, process_targets(host, row)):
        raise CleanupIncomplete(_("主机 {}（云区域 {}）停止 DTS 进程失败").format(host.ip, host.bk_cloud_id))
    if not delete_remote_paths(host, row.paths):
        raise CleanupIncomplete(_("主机 {}（云区域 {}）删除 DTS 目录失败").format(host.ip, host.bk_cloud_id))
    if not clean_monitor_and_crontab(host):
        raise CleanupIncomplete(_("主机 {}（云区域 {}）清理监控及保活任务失败").format(host.ip, host.bk_cloud_id))
    return HostVerdict.RETURN


def _decommission_row(row: DeployRow, updater: str) -> None:
    """把这一行自己注册的 DTS 集群标记下线，只改元数据，不回收主机。

    下线前重新确认一次集群归属；找不到本单的集群或集群已不存在时跳过。
    decommission 会按 IP 删除 Machine，所以只传该集群自己登记的节点，不传这一行的其他主机。
    """
    cluster = find_own_cluster(row)
    if cluster is None:
        return
    targets = [{"ip": ip, "bk_cloud_id": cloud} for ip, cloud in sorted(_cluster_node_keys(cluster))]
    try:
        decommission(dts_cluster_id=int(cluster.id), recycle_hosts=False, target_hosts=targets, updater=updater)
    except MysqlDtsCluster.DoesNotExist:
        logger.info(_("DTS 集群记录已不存在，跳过下线"))


def _output_hosts(hosts: tuple[NodeHost, ...]) -> list[dict]:
    """转成退回资源池需要的主机格式，按 bk_host_id 去重。"""
    seen = set()
    output = []
    for host in hosts:
        if host.bk_host_id is None or host.bk_host_id in seen:
            continue
        seen.add(host.bk_host_id)
        output.append({"ip": host.ip, "bk_cloud_id": host.bk_cloud_id, "bk_host_id": host.bk_host_id})
    return output


def reconcile_ticket(global_data: dict) -> list[dict]:
    """处理整张被终止的迁移单，返回可以退回资源池的主机。

    内置流水线一个节点都没跑过时，机器只做本地元数据检查，不下发远程清理脚本。
    按行处理：本单集群正被别的单据使用时，这一行整行不碰；
    一行里只要有一台主机 HOLD，这一行一台都不退回，也不下线集群。
    整行都干净时，先下线本单集群，再把这一行的主机加入退回名单。
    """
    ticket_id = _parent_ticket_id(global_data)
    ticket = load_parent_ticket(global_data)
    details = ticket.details or {}
    bk_biz_id = int(getattr(ticket, "bk_biz_id", 0) or details.get("bk_biz_id") or 0)
    updater = str(getattr(ticket, "creator", "") or global_data.get("created_by") or "")
    root_id = load_migrate_root_id(ticket_id)
    remote_cleanup = migrate_pipeline_started(root_id)
    if not remote_cleanup:
        logger.info(_("迁移单 {} 的内置流水线未执行过任何节点，跳过主机远程清理").format(ticket_id))
    rows = collect_deploy_rows(details, bk_biz_id, root_id)
    if remote_cleanup and any(row.use_myloader and row.hosts for row in rows):
        ensure_backup_downloads_finished(root_id)
    cleaned_rows = []
    for row in rows:
        if not row.hosts:
            continue
        own = find_own_cluster(row)
        own_id = int(own.id) if own is not None else None
        occupied = other_live_node_keys(own_id)
        if any(reconcile_host(host, row, occupied, False) == HostVerdict.HOLD for host in row.hosts):
            logger.warning(_("DTS 集群 {} 的主机归属无法确认，整行保留且不清理").format(row.cluster_name))
            continue
        if not claim_cluster_for_cleanup(row, ticket_id):
            continue
        verdicts = [reconcile_host(host, row, occupied, remote_cleanup) for host in row.hosts]
        if any(verdict != HostVerdict.RETURN for verdict in verdicts):
            raise CleanupIncomplete(_("DTS 集群 {} 的主机归属在清理期间发生变化").format(row.cluster_name))
        cleaned_rows.append(row)
    returned = []
    for row in cleaned_rows:
        _decommission_row(row, updater)
        returned.extend(_output_hosts(row.hosts))
    return returned


class MysqlDtsMigrateRevokeService(BaseService):
    """DTS 迁移单终止后的「核对待退回主机」步骤。

    清理本单 deploy 模式申请到的机器，只把清理干净的主机写入流程输出，
    供退机器单后续的人工确认和分池处理使用。清理失败或下载未确认结束时步骤失败且可重试，
    不发布部分结果；明确不属于本单或被其他单据使用的主机则安全保留。
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        try:
            hosts = reconcile_ticket(global_data)
        except MetaQueryError:
            self.log_error(_("查询 DTS 机器或集群失败，不退回主机"))
            return False
        except RemoteJobUnknown as exc:
            self.log_error(_("主机脚本未下发或未在限时内结束，请重试本步骤: {}").format(exc))
            return False
        except (CleanupIncomplete, BackupDownloadPending) as exc:
            self.log_error(_("DTS 主机清理未完成，请处理后重试本步骤: {}").format(exc))
            return False
        if not hosts:
            self.log_info(_("没有可退回的 DTS 主机"))
        FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(global_data["job_root_id"], hosts)
        return True


class MysqlDtsMigrateRevokeComponent(Component):
    name = __name__
    code = "mysql_dts_migrate_revoke"
    bound_service = MysqlDtsMigrateRevokeService
