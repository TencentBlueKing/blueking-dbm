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
from dataclasses import asdict, dataclass, field
from typing import Any

from django.utils.translation import gettext as _

from backend.db_meta.models import MysqlDtsCluster
from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.consts import MySQLBackupTypeEnum
from backend.flow.utils.mysql.dts.constants import DEFAULT_MYLOADER_PATH, get_myloader_backup_dir
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, MyloaderSpec, SourceSpec
from backend.ticket.builders.common.constants import MySQLBackupSource


@dataclass
class ResolvedLogicalBackup:
    """单个 source 解析出的逻辑全备信息，供下载子流程与 create_task 使用。"""

    cluster_id: int
    source_name: str
    backup_id: str
    backup_type: str
    backup_source: str
    task_ids: list[str]
    local_files: list[str]
    backup_host: str
    myloader_dir: str
    dest_worker_ip: str
    index: dict | None = None
    raw: dict = field(default_factory=dict)

    def to_context_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "source_name": self.source_name,
            "backup_id": self.backup_id,
            "backup_type": self.backup_type,
            "backup_source": self.backup_source,
            "task_ids": self.task_ids,
            "local_files": self.local_files,
            "backup_host": self.backup_host,
            "myloader_dir": self.myloader_dir,
            "dest_worker_ip": self.dest_worker_ip,
            "index": self.index,
        }


def _worker_ip_by_name(workers: list[dict], worker_name: str) -> str:
    for node in workers:
        name = node.get("name") or node.get("worker_name") or ""
        if name == worker_name and node.get("ip"):
            return node["ip"]
    return ""


def resolve_dest_worker_ip(
    migrate_plan: DtsMigratePlan,
    source: SourceSpec,
    source_index: int = 0,
) -> str:
    """解析全备下发目标 DTS Worker IP。

    优先级：myloader.dest_worker_ip → source.worker_name 对应节点 → 按下标轮询。
    """
    if source.myloader and source.myloader.dest_worker_ip:
        return source.myloader.dest_worker_ip

    workers: list[dict] = []
    if migrate_plan.dts_cluster_id:
        dts_cluster = MysqlDtsCluster.objects.filter(id=migrate_plan.dts_cluster_id).first()
        workers = list((dts_cluster.worker_nodes if dts_cluster else None) or [])

    if source.worker_name and workers:
        ip = _worker_ip_by_name(workers, source.worker_name)
        if ip:
            return ip

    if workers:
        return workers[source_index % len(workers)]["ip"]

    deploy = migrate_plan.deploy_subflow_inp
    if deploy and deploy.worker_hosts:
        if source.worker_name:
            for host in deploy.worker_hosts:
                if host.name == source.worker_name:
                    return host.ip
        return deploy.worker_hosts[source_index % len(deploy.worker_hosts)].ip

    raise ValueError(_("无法解析 source {} 的 DTS Worker IP，请在 myloader.dest_worker_ip 中指定").format(source.source_name))


def resolve_logical_backup(
    *,
    cluster_id: int,
    source_name: str,
    root_id: str,
    myloader: MyloaderSpec | None = None,
    dest_worker_ip: str = "",
    deadlines_days: int = 7,
) -> ResolvedLogicalBackup:
    """查询源集群最新（或指定）逻辑全备，供 myloader 导入使用。

    强制 backup_type == logical；物理备份直接失败。
    """
    ml = myloader or MyloaderSpec()
    backup_source = ml.backup_source or MySQLBackupSource.REMOTE.value
    handler = MySQLBackupHandler(
        cluster_id=cluster_id,
        is_full_backup=True,
        backup_id=ml.backup_id or None,
        backup_source=backup_source,
        deadlines_days=deadlines_days,
        shard_id=ml.shard_id,
    )
    backup_info = handler.get_tendb_latest_backup_info()
    if not backup_info:
        raise ValueError(_("获取集群 {} 逻辑全备失败: {}").format(cluster_id, handler.errmsg or _("无可用备份")))

    backup_type = backup_info.get("backup_type") or ""
    if backup_type != MySQLBackupTypeEnum.LOGICAL.value:
        raise ValueError(
            _("备份 {} 类型为 {}，myloader 仅支持 logical 备份，请更换 backup_id").format(
                backup_info.get("backup_id", ""),
                backup_type or _("未知"),
            )
        )

    worker_ip = dest_worker_ip or ml.dest_worker_ip
    if not worker_ip:
        raise ValueError(_("source {} 未指定 dest_worker_ip").format(source_name))

    myloader_dir = ml.myloader_dir or get_myloader_backup_dir(root_id, source_name)
    index = backup_info.get("index")
    if index is not None and not isinstance(index, dict):
        index = None

    return ResolvedLogicalBackup(
        cluster_id=cluster_id,
        source_name=source_name,
        backup_id=backup_info.get("backup_id", "") or "",
        backup_type=backup_type,
        backup_source=backup_source,
        task_ids=list(backup_info.get("task_ids") or []),
        local_files=list(backup_info.get("local_files") or []),
        backup_host=backup_info.get("backup_host", "") or "",
        myloader_dir=myloader_dir,
        dest_worker_ip=worker_ip,
        index=index,
        raw=backup_info if isinstance(backup_info, dict) else {},
    )


def resolve_task_logical_backups(
    *,
    root_id: str,
    migrate_plan: DtsMigratePlan,
    sources: list[SourceSpec],
    deadlines_days: int = 7,
) -> list[ResolvedLogicalBackup]:
    """为 task 下全部 source 解析逻辑全备，并回写 myloader_dir / myloader_path。"""
    resolved_list: list[ResolvedLogicalBackup] = []
    for idx, src in enumerate(sources):
        worker_ip = resolve_dest_worker_ip(migrate_plan, src, source_index=idx)
        resolved = resolve_logical_backup(
            cluster_id=src.cluster_id,
            source_name=src.source_name,
            root_id=root_id,
            myloader=src.myloader,
            dest_worker_ip=worker_ip,
            deadlines_days=deadlines_days,
        )
        if src.myloader is None:
            src.myloader = MyloaderSpec()
        src.myloader.myloader_dir = resolved.myloader_dir
        src.myloader.dest_worker_ip = resolved.dest_worker_ip
        if not src.myloader.myloader_path:
            src.myloader.myloader_path = DEFAULT_MYLOADER_PATH
        resolved_list.append(resolved)
    return resolved_list


def resolved_backups_to_context_payload(
    resolved_list: list[ResolvedLogicalBackup],
) -> tuple[dict[str, str], dict[str, dict], str]:
    """转换为 migrate_context 可落盘结构。"""
    dirs = {item.source_name: item.myloader_dir for item in resolved_list}
    backups = {item.source_name: item.to_context_dict() for item in resolved_list}
    return dirs, backups, DEFAULT_MYLOADER_PATH


def resolved_backup_asdict(item: ResolvedLogicalBackup) -> dict[str, Any]:
    """序列化（不含过大 raw），供 Component kwargs。"""
    data = asdict(item)
    data.pop("raw", None)
    return data
