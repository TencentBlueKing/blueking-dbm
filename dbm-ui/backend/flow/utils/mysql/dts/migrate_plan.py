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
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from django.utils.translation import gettext as _

from backend.components.mysqldtsapi.types import TargetConfig
from backend.flow.utils.mysql.dts.constants import (
    DtsLifecycleMode,
    FullLoadEngine,
    MigrateTopology,
    MigrateType,
    get_default_deploy_path,
)
from backend.flow.utils.mysql.dts.context import DtsHostSpec, MysqlDtsDeploySubflowInput


def _resolve_task_name(raw_name: Any, *, require: bool) -> str:
    """解析 task_name；生产路径缺名显式失败，validate 路径允许为空。"""
    name = (raw_name or "").strip() if isinstance(raw_name, str) else (str(raw_name).strip() if raw_name else "")
    if name:
        return name
    if require:
        raise ValueError(_("迁移任务缺少 task_name，请确认单据已完成自动命名回写"))
    return ""


@dataclass
class TableRoute:
    """对应 DTS routes / OpenAPI table_migrate_rule / Go SyncScope.TableRoute。"""

    source_name: str = ""
    source_db: str = ""
    source_db_pattern: str = ""
    source_table: str = ""
    source_table_pattern: str = ""
    target_db: str = ""
    target_table: str = ""

    def source_schema(self) -> str:
        """源库匹配：pattern 优先于精确名（与 migrate_helper / Go 一致）。"""
        return (self.source_db_pattern or self.source_db or "").strip()

    def source_table_name(self) -> str:
        """源表匹配：pattern 优先；都空则默认 *。"""
        name = (self.source_table_pattern or self.source_table or "").strip()
        return name or "*"


@dataclass
class SyncScope:
    do_dbs: list[str] = field(default_factory=list)
    ignore_dbs: list[str] = field(default_factory=list)
    do_tables: list[dict] = field(default_factory=list)
    ignore_tables: list[dict] = field(default_factory=list)
    table_routes: list[TableRoute] = field(default_factory=list)
    binlog_filters: list[dict] = field(default_factory=list)

    def __post_init__(self):
        # 兼容单据/测试仍传入 list[dict] 的写法
        self.table_routes = [_parse_table_route(item) for item in (self.table_routes or [])]


@dataclass
class MyloaderSpec:
    backup_id: str = ""
    backup_source: str = "remote"
    myloader_path: str = ""
    myloader_dir: str = ""
    threads: int = 16
    regex: str = ""
    sourcedb: str = ""
    tablelist: str = ""
    setnames: str = ""
    defaultsfile: str = ""
    extraargs: str = ""
    dest_worker_ip: str = ""
    shard_id: int | None = None


@dataclass
class DtsTaskConfig:
    task_mode: str = "all"
    enable_validator: bool = False
    shard_mode: str = ""
    on_duplicate: str = "replace"
    meta_schema: str = "dm_meta"
    ignore_checking_items: list[str] = field(default_factory=list)
    full_migrate: dict = field(default_factory=dict)
    incr_migrate: dict = field(default_factory=dict)
    full_load_engine: str = FullLoadEngine.BUILTIN.value
    myloader: MyloaderSpec | None = None


@dataclass
class SourceSpec:
    cluster_id: int
    source_name: str
    sync_scope: SyncScope
    source_instance_id: int | None = None
    source_instance_role: str | None = None
    source_host: str | None = None
    myloader: MyloaderSpec | None = None
    # 内部字段：供 expand_tendbcluster_source_specs / assign_source_workers 使用，不由现网 HA 单据填写
    shard_index: int | None = None
    shard_count: int | None = None
    spider_cluster_id: str = ""
    worker_name: str = ""


@dataclass
class DtsTaskSpec:
    task_name: str
    target_cluster_id: int
    sources: list[SourceSpec]
    target_config: TargetConfig | None = None
    target_spider: str | None = None
    sync_scope_merged: list[dict] = field(default_factory=list)
    dts_task_config: DtsTaskConfig = field(default_factory=DtsTaskConfig)


@dataclass
class DtsMigratePlan:
    topology: str
    migrate_type: str
    dts_cluster_id: int | None
    dts_lifecycle: str
    auto_deploy_dts: bool
    deploy_subflow_inp: MysqlDtsDeploySubflowInput | None
    cleanup_after_migrate: bool
    recycle_dts_hosts: bool
    dts_task_config: DtsTaskConfig
    task_specs: list[DtsTaskSpec]
    worker_count_required: int
    bk_biz_id: int = 0
    bk_cloud_id: int = 0


def _parse_table_route(raw: dict | TableRoute | Any) -> TableRoute:
    if isinstance(raw, TableRoute):
        return raw
    if not isinstance(raw, dict):
        raise TypeError(_("table_routes 条目必须是 dict 或 TableRoute，实际为 {}").format(type(raw)))
    return TableRoute(
        source_name=(raw.get("source_name") or "").strip(),
        source_db=(raw.get("source_db") or "").strip(),
        source_db_pattern=(raw.get("source_db_pattern") or "").strip(),
        source_table=(raw.get("source_table") or "").strip(),
        source_table_pattern=(raw.get("source_table_pattern") or "").strip(),
        target_db=(raw.get("target_db") or "").strip(),
        target_table=(raw.get("target_table") or "").strip(),
    )


def _parse_sync_scope(raw: dict | None) -> SyncScope:
    raw = raw or {}
    return SyncScope(
        do_dbs=raw.get("do_dbs", []),
        ignore_dbs=raw.get("ignore_dbs", []),
        do_tables=raw.get("do_tables", []),
        ignore_tables=raw.get("ignore_tables", []),
        table_routes=[_parse_table_route(item) for item in (raw.get("table_routes") or [])],
        binlog_filters=raw.get("binlog_filters", []),
    )


def _parse_myloader_spec(raw: dict | None) -> MyloaderSpec | None:
    if not raw or not isinstance(raw, dict):
        return None
    return MyloaderSpec(
        backup_id=raw.get("backup_id", "") or "",
        backup_source=raw.get("backup_source", "remote") or "remote",
        myloader_path=raw.get("myloader_path", "") or "",
        myloader_dir=raw.get("myloader_dir") or raw.get("directory") or "",
        threads=int(raw.get("threads", 16) or 16),
        regex=raw.get("regex", "") or "",
        sourcedb=raw.get("sourcedb", "") or "",
        tablelist=raw.get("tablelist", "") or "",
        setnames=raw.get("setnames", "") or "",
        defaultsfile=raw.get("defaultsfile") or raw.get("defaults_file") or "",
        extraargs=raw.get("extraargs") or raw.get("extra_args") or "",
        dest_worker_ip=raw.get("dest_worker_ip", "") or "",
        shard_id=raw.get("shard_id"),
    )


def copy_myloader_spec(spec: MyloaderSpec | None) -> MyloaderSpec | None:
    if spec is None:
        return None
    return MyloaderSpec(
        backup_id=spec.backup_id,
        backup_source=spec.backup_source,
        myloader_path=spec.myloader_path,
        myloader_dir=spec.myloader_dir,
        threads=spec.threads,
        regex=spec.regex,
        sourcedb=spec.sourcedb,
        tablelist=spec.tablelist,
        setnames=spec.setnames,
        defaultsfile=spec.defaultsfile,
        extraargs=spec.extraargs,
        dest_worker_ip=spec.dest_worker_ip,
        shard_id=spec.shard_id,
    )


# 兼容旧名
_copy_myloader_spec = copy_myloader_spec


def _parse_dts_task_config(raw: dict | None) -> DtsTaskConfig:
    raw = raw or {}
    return DtsTaskConfig(
        task_mode=raw.get("task_mode", "all"),
        enable_validator=raw.get("enable_validator", False),
        shard_mode=raw.get("shard_mode", ""),
        on_duplicate=raw.get("on_duplicate", "replace"),
        meta_schema=raw.get("meta_schema", "dm_meta"),
        ignore_checking_items=raw.get("ignore_checking_items", []),
        full_migrate=raw.get("full_migrate", {}),
        incr_migrate=raw.get("incr_migrate", {}),
        full_load_engine=raw.get("full_load_engine", FullLoadEngine.BUILTIN.value),
        myloader=_parse_myloader_spec(raw.get("myloader")),
    )


def _parse_deploy_subflow_inp(details: dict[str, Any]) -> MysqlDtsDeploySubflowInput | None:
    """从单据 details 解析自动部署入参。"""
    if details.get("deploy_subflow_inp") and isinstance(details["deploy_subflow_inp"], MysqlDtsDeploySubflowInput):
        return details["deploy_subflow_inp"]

    raw = details.get("deploy_subflow") or details.get("deploy_subflow_inp")
    if not raw or not isinstance(raw, dict):
        return None

    cluster_name = (
        raw.get("cluster_name") or details.get("cluster_name") or f"dts-migrate-{details.get('ticket_id', 0)}"
    )
    master_hosts = [
        DtsHostSpec(ip=h["ip"], bk_cloud_id=h["bk_cloud_id"], name=h.get("name")) for h in raw.get("master_hosts", [])
    ]
    worker_hosts = [
        DtsHostSpec(ip=h["ip"], bk_cloud_id=h["bk_cloud_id"], name=h.get("name")) for h in raw.get("worker_hosts", [])
    ]
    if not master_hosts or not worker_hosts:
        return None
    return MysqlDtsDeploySubflowInput(
        root_id=raw.get("root_id", ""),
        bk_biz_id=int(raw.get("bk_biz_id") or details.get("bk_biz_id", 0)),
        bk_cloud_id=int(raw.get("bk_cloud_id") or details.get("bk_cloud_id", 0)),
        cluster_name=cluster_name,
        master_hosts=master_hosts,
        worker_hosts=worker_hosts,
        deploy_path=raw.get("deploy_path") or get_default_deploy_path(cluster_name),
        master_ha=bool(raw.get("master_ha", False)),
        # 介质默认取最新包，不由单据指定
        creator=raw.get("creator", ""),
    )


def _generate_default_source_name(cluster_id: int | str, used_names: set[str] | None = None) -> str:
    """内部默认 source_name：``source-{cluster_id}-{uuid4 hex 前12位}``，同单内唯一。

    不由建单契约传入；含 cluster_id 便于关联，12 hex 熵保证一眼可区分且碰撞极低。
    """
    used = used_names if used_names is not None else set()
    while True:
        name = f"source-{cluster_id}-{uuid.uuid4().hex[:12]}"
        if name not in used:
            used.add(name)
            return name


def _parse_source_spec(
    raw: dict,
    task_myloader: MyloaderSpec | None = None,
    *,
    used_names: set[str] | None = None,
) -> SourceSpec:
    myloader = _parse_myloader_spec(raw.get("myloader"))
    if myloader is None:
        myloader = _copy_myloader_spec(task_myloader)
    # source_name 不由建单契约传入，一律内部生成
    return SourceSpec(
        cluster_id=raw["cluster_id"],
        source_name=_generate_default_source_name(raw["cluster_id"], used_names),
        sync_scope=_parse_sync_scope(raw.get("sync_scope")),
        source_instance_id=raw.get("source_instance_id"),
        source_instance_role=raw.get("source_instance_role"),
        source_host=raw.get("source_host"),
        myloader=myloader,
    )


def _build_one_to_one_plan(details: dict[str, Any], *, require_task_name: bool = True) -> DtsMigratePlan:
    spec = details["one_to_one"]
    task_cfg = _parse_dts_task_config(details.get("dts_task_config"))
    src = _parse_source_spec(spec["src_info"], task_myloader=task_cfg.myloader)
    task_spec = DtsTaskSpec(
        task_name=_resolve_task_name(spec.get("task_name"), require=require_task_name),
        target_cluster_id=spec["dst_info"]["cluster_id"],
        sources=[src],
        target_spider=spec["dst_info"].get("target_spider"),
        dts_task_config=task_cfg,
    )
    return _wrap_plan(details, [task_spec], worker_count=1)


def _build_many_to_one_plan(details: dict[str, Any], *, require_task_name: bool = True) -> DtsMigratePlan:
    spec = details["many_to_one"]
    task_cfg = _parse_dts_task_config(details.get("dts_task_config"))
    used_names: set[str] = set()
    sources = [
        _parse_source_spec(src, task_myloader=task_cfg.myloader, used_names=used_names) for src in spec["src_infos"]
    ]
    task_spec = DtsTaskSpec(
        task_name=_resolve_task_name(spec.get("task_name"), require=require_task_name),
        target_cluster_id=spec["dst_info"]["cluster_id"],
        sources=sources,
        target_spider=spec["dst_info"].get("target_spider"),
        dts_task_config=task_cfg,
    )
    return _wrap_plan(details, [task_spec], worker_count=len(sources))


def _build_one_to_many_plan(details: dict[str, Any], *, require_task_name: bool = True) -> DtsMigratePlan:
    spec = details["one_to_many"]
    src_info = spec["src_info"]
    task_cfg = _parse_dts_task_config(details.get("dts_task_config"))
    used_names: set[str] = set()
    task_specs = []
    for dst in spec["dst_infos"]:
        src = _parse_source_spec(src_info, task_myloader=task_cfg.myloader, used_names=used_names)
        task_specs.append(
            DtsTaskSpec(
                task_name=_resolve_task_name(dst.get("task_name"), require=require_task_name),
                target_cluster_id=dst["cluster_id"],
                sources=[src],
                target_spider=dst.get("target_spider"),
                dts_task_config=task_cfg,
            )
        )
    return _wrap_plan(details, task_specs, worker_count=len(task_specs))


def _wrap_plan(details: dict[str, Any], task_specs: list[DtsTaskSpec], worker_count: int) -> DtsMigratePlan:
    dts_lifecycle = details.get("dts_lifecycle")
    if not dts_lifecycle:
        if details.get("dts_cluster_id"):
            dts_lifecycle = DtsLifecycleMode.USE_EXISTING.value
        elif details.get("auto_deploy_dts"):
            dts_lifecycle = DtsLifecycleMode.DEPLOY_EPHEMERAL.value
        else:
            dts_lifecycle = DtsLifecycleMode.USE_EXISTING.value
    return DtsMigratePlan(
        topology=details["migrate_topology"],
        migrate_type=details.get("migrate_type", MigrateType.MYSQL_TO_MYSQL.value),
        dts_cluster_id=details.get("dts_cluster_id"),
        dts_lifecycle=dts_lifecycle,
        auto_deploy_dts=details.get("auto_deploy_dts", False),
        deploy_subflow_inp=_parse_deploy_subflow_inp(details),
        cleanup_after_migrate=details.get(
            "cleanup_after_migrate", dts_lifecycle == DtsLifecycleMode.DEPLOY_EPHEMERAL.value
        ),
        recycle_dts_hosts=details.get("recycle_dts_hosts", True),
        dts_task_config=_parse_dts_task_config(details.get("dts_task_config")),
        task_specs=task_specs,
        worker_count_required=max(worker_count, details.get("worker_count_required") or worker_count),
        bk_biz_id=details.get("bk_biz_id", 0),
        bk_cloud_id=details.get("bk_cloud_id", 0),
    )


def _is_layered_ticket_details(details: dict[str, Any]) -> bool:
    """是否为分层单据契约（dts_resource / migrate / task）。"""
    return "dts_resource" in details or "migrate" in details


def normalize_migrate_ticket_details(details: dict[str, Any]) -> dict[str, Any]:
    """将分层单据 details 归一化为 build_migrate_plan 使用的扁平结构。

    分层契约：
    - dts_resource: DTS 集群来源与生命周期
    - migrate: 拓扑与源/目标
    - task: 任务运行参数
    """
    if not _is_layered_ticket_details(details):
        return details

    dts_resource = details.get("dts_resource") or {}
    migrate = details.get("migrate") or {}
    task = details.get("task") or {}

    mode = dts_resource.get("mode") or DtsLifecycleMode.USE_EXISTING.value
    if mode == DtsLifecycleMode.USE_EXISTING.value:
        if not dts_resource.get("cluster_id"):
            raise ValueError(_("dts_resource.mode=use_existing 时必须提供 cluster_id"))
        auto_deploy = False
        dts_cluster_id = dts_resource.get("cluster_id")
        deploy_subflow = None
        default_cleanup = False
    elif mode in (DtsLifecycleMode.DEPLOY_EPHEMERAL.value, DtsLifecycleMode.DEPLOY_PERSISTENT.value):
        deploy = dts_resource.get("deploy")
        if not deploy:
            raise ValueError(_("dts_resource.mode={} 时必须提供 deploy").format(mode))
        auto_deploy = True
        dts_cluster_id = dts_resource.get("cluster_id")
        deploy_subflow = deploy
        default_cleanup = mode == DtsLifecycleMode.DEPLOY_EPHEMERAL.value
    else:
        raise ValueError(_("不支持的 dts_resource.mode: {}").format(mode))

    topology = migrate.get("topology")
    if not topology:
        raise ValueError(_("migrate.topology 不能为空"))

    flat: dict[str, Any] = {
        "migrate_topology": topology,
        "dts_cluster_id": dts_cluster_id,
        "auto_deploy_dts": auto_deploy,
        "dts_lifecycle": mode,
        "cleanup_after_migrate": dts_resource.get("cleanup_after_migrate", default_cleanup),
        "recycle_dts_hosts": dts_resource.get("recycle_hosts", True),
        "bk_biz_id": details.get("bk_biz_id", 0),
        "bk_cloud_id": details.get("bk_cloud_id") or (deploy_subflow or {}).get("bk_cloud_id", 0),
    }
    if details.get("migrate_type"):
        flat["migrate_type"] = details["migrate_type"]
    if details.get("ticket_id") is not None:
        flat["ticket_id"] = details["ticket_id"]
    if details.get("worker_count_required") is not None:
        flat["worker_count_required"] = details["worker_count_required"]
    if deploy_subflow is not None:
        flat["deploy_subflow"] = deploy_subflow

    # migrate 拓扑块 → 旧 one_to_one / many_to_one / one_to_many
    if topology == MigrateTopology.ONE_TO_ONE.value:
        block = migrate.get("one_to_one") or {}
        flat["one_to_one"] = {
            "task_name": block.get("task_name"),
            "src_info": _normalize_source_block(block.get("source") or {}),
            "dst_info": _normalize_target_block(block.get("target") or {}),
        }
    elif topology == MigrateTopology.MANY_TO_ONE.value:
        block = migrate.get("many_to_one") or {}
        flat["many_to_one"] = {
            "task_name": block.get("task_name"),
            "src_infos": [_normalize_source_block(s) for s in (block.get("sources") or [])],
            "dst_info": _normalize_target_block(block.get("target") or {}),
        }
    elif topology == MigrateTopology.ONE_TO_MANY.value:
        block = migrate.get("one_to_many") or {}
        flat["one_to_many"] = {
            "src_info": _normalize_source_block(block.get("source") or {}),
            "dst_infos": [_normalize_target_block(t) for t in (block.get("targets") or [])],
        }
    else:
        raise ValueError(_("不支持的 migrate.topology: {}").format(topology))

    full_load = task.get("full_load") or {}
    engine_options = task.get("engine_options") or {}
    flat["dts_task_config"] = {
        "task_mode": task.get("task_mode", "all"),
        "enable_validator": task.get("enable_validator", False),
        "shard_mode": task.get("shard_mode", ""),
        "on_duplicate": task.get("on_duplicate", "replace"),
        "meta_schema": task.get("meta_schema", "dm_meta"),
        "ignore_checking_items": task.get("ignore_checking_items", []),
        "full_migrate": engine_options.get("full_migrate", {}),
        "incr_migrate": engine_options.get("incr_migrate", {}),
        "full_load_engine": full_load.get("engine", FullLoadEngine.BUILTIN.value),
        "myloader": full_load.get("myloader"),
    }
    return flat


def _normalize_source_block(raw: dict[str, Any]) -> dict[str, Any]:
    # source_name 非建单契约字段，解析阶段由 _parse_source_spec 内部生成
    return {
        "cluster_id": raw.get("cluster_id"),
        "sync_scope": raw.get("sync_scope") or {},
        "source_instance_id": raw.get("source_instance_id"),
        "source_instance_role": raw.get("source_instance_role"),
        "source_host": raw.get("source_host"),
        "myloader": raw.get("myloader"),
    }


def _normalize_target_block(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "cluster_id": raw.get("cluster_id"),
        "task_name": raw.get("task_name"),
        "target_spider": raw.get("target_spider"),
    }


def build_migrate_plan(ticket_details: dict[str, Any], *, require_task_name: bool = True) -> DtsMigratePlan:
    """构建迁移计划。

    require_task_name:
      - True（默认）：生产路径，details 中必须已有回写的 task_name
      - False：单据 validate 阶段（尚无 ticket.id），允许空名仅做结构校验
    """
    details = (
        normalize_migrate_ticket_details(ticket_details)
        if _is_layered_ticket_details(ticket_details)
        else ticket_details
    )
    topology = details["migrate_topology"]
    builders = {
        MigrateTopology.ONE_TO_ONE.value: _build_one_to_one_plan,
        MigrateTopology.MANY_TO_ONE.value: _build_many_to_one_plan,
        MigrateTopology.ONE_TO_MANY.value: _build_one_to_many_plan,
    }
    builder = builders.get(topology)
    if not builder:
        raise ValueError(_("不支持的迁移拓扑: {}").format(topology))
    return builder(details, require_task_name=require_task_name)


def _target_config_to_dict(target_config: Any) -> dict | None:
    if target_config is None:
        return None
    if isinstance(target_config, dict):
        return target_config
    if hasattr(target_config, "model_dump"):
        return target_config.model_dump()
    if hasattr(target_config, "dict"):
        return target_config.dict()
    raise TypeError(_("不支持的 TargetConfig 类型: {}").format(type(target_config)))


def _target_config_from_dict(raw: Any) -> TargetConfig | None:
    if raw is None:
        return None
    if isinstance(raw, TargetConfig):
        return raw
    if isinstance(raw, dict):
        return TargetConfig(**raw)
    raise TypeError(_("无法还原 TargetConfig: {}").format(type(raw)))


def _source_spec_from_dict(raw: dict | SourceSpec, used_names: set[str] | None = None) -> SourceSpec:
    if isinstance(raw, SourceSpec):
        return raw
    source_name = raw.get("source_name") or _generate_default_source_name(raw["cluster_id"], used_names)
    if used_names is not None:
        used_names.add(source_name)
    return SourceSpec(
        cluster_id=raw["cluster_id"],
        source_name=source_name,
        sync_scope=_parse_sync_scope(raw.get("sync_scope")),
        source_instance_id=raw.get("source_instance_id"),
        source_instance_role=raw.get("source_instance_role"),
        source_host=raw.get("source_host"),
        myloader=_parse_myloader_spec(raw.get("myloader")),
        shard_index=raw.get("shard_index"),
        shard_count=raw.get("shard_count"),
        spider_cluster_id=raw.get("spider_cluster_id") or "",
        worker_name=raw.get("worker_name") or "",
    )


def dts_task_spec_to_dict(spec: DtsTaskSpec) -> dict[str, Any]:
    """将 DtsTaskSpec 转为 pipeline Act kwargs 可 JSON 序列化的 dict。"""
    data = asdict(spec)
    data["target_config"] = _target_config_to_dict(spec.target_config)
    return data


def dts_task_spec_from_dict(raw: dict | DtsTaskSpec) -> DtsTaskSpec:
    """从 pipeline kwargs / asdict 快照还原 DtsTaskSpec。"""
    if isinstance(raw, DtsTaskSpec):
        return raw
    if not isinstance(raw, dict):
        raise TypeError(_("task_spec 必须是 dict 或 DtsTaskSpec，实际为 {}").format(type(raw)))
    used_names: set[str] = set()
    sources = [_source_spec_from_dict(src, used_names=used_names) for src in (raw.get("sources") or [])]
    return DtsTaskSpec(
        task_name=raw.get("task_name") or "",
        target_cluster_id=int(raw["target_cluster_id"]),
        sources=sources,
        target_config=_target_config_from_dict(raw.get("target_config")),
        target_spider=raw.get("target_spider"),
        sync_scope_merged=list(raw.get("sync_scope_merged") or []),
        dts_task_config=_parse_dts_task_config(raw.get("dts_task_config")),
    )


def dts_migrate_plan_to_dict(plan: DtsMigratePlan) -> dict[str, Any]:
    """将 DtsMigratePlan 转为 pipeline Act kwargs 可 JSON 序列化的 dict。"""
    data = asdict(plan)
    data["task_specs"] = [dts_task_spec_to_dict(spec) for spec in plan.task_specs]
    return data


def dts_migrate_plan_from_dict(raw: dict | DtsMigratePlan) -> DtsMigratePlan:
    """从 pipeline kwargs / asdict 快照还原 DtsMigratePlan。"""
    if isinstance(raw, DtsMigratePlan):
        return raw
    if not isinstance(raw, dict):
        raise TypeError(_("migrate_plan 必须是 dict 或 DtsMigratePlan，实际为 {}").format(type(raw)))
    deploy_inp = raw.get("deploy_subflow_inp")
    if isinstance(deploy_inp, MysqlDtsDeploySubflowInput):
        parsed_deploy = deploy_inp
    elif isinstance(deploy_inp, dict):
        parsed_deploy = _parse_deploy_subflow_inp(
            {
                "deploy_subflow_inp": deploy_inp,
                "bk_biz_id": raw.get("bk_biz_id", 0),
                "bk_cloud_id": raw.get("bk_cloud_id", 0),
                "ticket_id": 0,
            }
        )
    else:
        parsed_deploy = None
    return DtsMigratePlan(
        topology=raw.get("topology") or "",
        migrate_type=raw.get("migrate_type") or MigrateType.MYSQL_TO_MYSQL.value,
        dts_cluster_id=raw.get("dts_cluster_id"),
        dts_lifecycle=raw.get("dts_lifecycle") or "",
        auto_deploy_dts=bool(raw.get("auto_deploy_dts", False)),
        deploy_subflow_inp=parsed_deploy,
        cleanup_after_migrate=bool(raw.get("cleanup_after_migrate", False)),
        recycle_dts_hosts=bool(raw.get("recycle_dts_hosts", True)),
        dts_task_config=_parse_dts_task_config(raw.get("dts_task_config")),
        task_specs=[dts_task_spec_from_dict(spec) for spec in (raw.get("task_specs") or [])],
        worker_count_required=int(raw.get("worker_count_required") or 0),
        bk_biz_id=int(raw.get("bk_biz_id") or 0),
        bk_cloud_id=int(raw.get("bk_cloud_id") or 0),
    )


def contains_dataclass(obj: Any) -> bool:
    """检测对象树中是否仍含 dataclass 实例（pipeline inputs 自检用）。"""
    if obj is None or isinstance(obj, (str, bytes, int, float, bool)):
        return False
    if is_dataclass(obj) and not isinstance(obj, type):
        return True
    if isinstance(obj, dict):
        return any(contains_dataclass(v) for v in obj.values())
    if isinstance(obj, (list, tuple, set)):
        return any(contains_dataclass(v) for v in obj)
    return False


def resolve_migrate_plan_from_ticket_data(data: dict[str, Any]) -> DtsMigratePlan:
    """从 Flow ticket_data 解析 plan，并 pop 掉 migrate_plan 避免污染 Builder global_data。"""
    raw_plan = data.pop("migrate_plan", None)
    if isinstance(raw_plan, DtsMigratePlan):
        return raw_plan
    if isinstance(raw_plan, dict):
        return dts_migrate_plan_from_dict(raw_plan)
    return build_migrate_plan(data)
