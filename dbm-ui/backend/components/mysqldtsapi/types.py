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
from typing import NamedTuple

from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field


class DtsBinlogCoord(NamedTuple):
    """DTS 位点字符串解析结果。格式示例：\"(binlog20000.002894, 12105)\"。"""

    file: str
    position: int


def parse_dts_binlog_coord(raw: str | None) -> DtsBinlogCoord | None:
    """解析 DTS sync_status 中的 binlog 位点字符串。

    期望形态：\"(binlog20000.002894, 12105)\" 或 \"binlog20000.002894, 12105\"。
    空串 / 缺逗号 / position 非整数 → 返回 None（调用方视为本轮未追平，勿直接失败节点）。
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    if "," not in text:
        return None
    file_part, pos_part = text.split(",", 1)
    file_name = file_part.strip()
    pos_text = pos_part.strip()
    if not file_name or not pos_text:
        return None
    try:
        position = int(pos_text)
    except (TypeError, ValueError):
        return None
    if position < 0:
        return None
    return DtsBinlogCoord(file=file_name, position=position)


def _binlog_file_seq(file_name: str) -> int | None:
    """取 binlog 文件序号（最后一个 '.' 后的数字）。"""
    if "." not in file_name:
        return None
    suffix = file_name.rsplit(".", 1)[-1]
    if not suffix.isdigit():
        return None
    return int(suffix)


def compare_dts_binlog_coord(left: DtsBinlogCoord, right: DtsBinlogCoord) -> int:
    """比较位点：-1 left<right，0 相等，1 left>right（先 file 序号，再 position）。"""
    left_seq = _binlog_file_seq(left.file)
    right_seq = _binlog_file_seq(right.file)
    if left_seq is not None and right_seq is not None:
        if left_seq < right_seq:
            return -1
        if left_seq > right_seq:
            return 1
    elif left.file != right.file:
        return -1 if left.file < right.file else 1
    if left.position < right.position:
        return -1
    if left.position > right.position:
        return 1
    return 0


# ============================================================
# 通用 Schema
# ============================================================


class PurgeConfig(BaseModel):
    interval: int = Field(default=3600, description=_("检查间隔(秒)"))
    expires: int = Field(default=0, description=_("N小时后过期, 0=禁用"))
    remain_space: int = Field(default=15, description=_("剩余空间<NB时清理, 0=禁用"))


class RelayConfig(BaseModel):
    enable_relay: bool = Field(default=False, description=_("是否启用 relay"))
    relay_binlog_name: str = Field(default="", description=_("起始 binlog 文件"))
    relay_binlog_gtid: str = Field(default="", description=_("起始 GTID"))
    relay_dir: str = Field(default="./relay_log", description=_("relay 日志目录"))


class SpiderInfo(BaseModel):
    cluster_id: str = Field(description=_("集群标识"))
    shard_index: int = Field(description=_("分片号(0-based)"))
    shard_count: int = Field(description=_("总分片数"))
    logical_db_pattern: str | None = Field(default=None, description=_("库名模板"))


class SecurityConfig(BaseModel):
    ssl_ca_content: str = Field(default="", description=_("PEM CA证书内容"))
    ssl_cert_content: str = Field(default="", description=_("PEM 客户端证书"))
    ssl_key_content: str = Field(default="", description=_("PEM 私钥"))
    cert_allowed_cn: list[str] = Field(default_factory=list, description=_("允许的证书CN"))


class RelayStatus(BaseModel):
    master_binlog: str = Field(default="", description=_("上游 binlog 位点"))
    master_binlog_gtid: str = Field(default="", description=_("上游 GTID"))
    relay_dir: str = Field(default="", description=_("relay 目录"))
    relay_binlog_gtid: str = Field(default="", description=_("relay GTID"))
    relay_catch_up_master: bool = Field(default=False, description=_("是否追上上游"))
    stage: str = Field(default="", description=_("当前阶段"))


# ============================================================
# Source 请求类型
# ============================================================


class Source(BaseModel):
    source_name: str = Field(description=_("数据源名称, 全局唯一"))
    host: str = Field(description=_("上游 MySQL 地址"))
    port: int = Field(description=_("上游 MySQL 端口"))
    user: str = Field(description=_("用户名"))
    password: str | None = Field(default=None, description=_("密码"))
    enable_gtid: bool = Field(description=_("是否启用 GTID"))
    enable: bool = Field(description=_("是否启用"))
    flavor: str | None = Field(default=None, description=_("mysql/mariadb"))
    cluster_type: str = Field(default="", description=_("集群类型"))
    spider: SpiderInfo | None = Field(default=None, description=_("Spider 配置"))
    security: SecurityConfig | None = Field(default=None, description=_("TLS 配置"))
    purge: PurgeConfig | None = Field(default=None, description=_("relay 日志清理策略"))
    relay_config: RelayConfig | None = Field(default=None, description=_("relay 配置"))


class CreateSourceRequest(BaseModel):
    source: Source = Field(description=_("数据源配置"))
    worker_name: str | None = Field(default=None, description=_("指定绑定 worker"))


class UpdateSourceRequest(BaseModel):
    source: Source = Field(description=_("数据源配置(完整字段)"))


class TransferSourceRequest(BaseModel):
    worker_name: str = Field(description=_("目标 worker 名称"))


class EnableRelayRequest(BaseModel):
    worker_name_list: list[str] | None = Field(default=None, description=_("指定 worker"))
    relay_binlog_name: str | None = Field(default=None, description=_("起始 binlog 文件"))
    relay_binlog_gtid: str | None = Field(default=None, description=_("起始 GTID"))
    relay_dir: str | None = Field(default=None, description=_("relay 目录"))


class DisableRelayRequest(BaseModel):
    worker_name_list: list[str] | None = Field(default=None, description=_("指定 worker"))


class PurgeRelayRequest(BaseModel):
    relay_binlog_name: str = Field(description=_("清理到此文件之前"))
    relay_dir: str | None = Field(default=None, description=_("relay 子目录"))


# ============================================================
# Source 响应类型
# ============================================================


class SourceStatus(BaseModel):
    source_name: str = Field(description=_("数据源名称"))
    worker_name: str = Field(description=_("绑定的 worker 名称"))
    relay_status: RelayStatus | None = Field(default=None, description=_("relay 状态"))
    error_msg: str | None = Field(default=None, description=_("错误信息"))


class GetSourceResponse(BaseModel):
    source_name: str
    host: str
    port: int
    user: str
    password: str = Field(default="", description=_("密码(始终返回混淆值)"))
    enable_gtid: bool
    enable: bool
    flavor: str | None = None
    cluster_type: str = ""
    spider: SpiderInfo | None = None
    security: SecurityConfig | None = None
    purge: PurgeConfig | None = None
    relay_config: RelayConfig | None = None
    task_name_list: list[str] = Field(default_factory=list, description=_("关联的 task 列表"))
    status_list: list[SourceStatus] = Field(default_factory=list, description=_("状态列表(with_status=true时返回)"))


class ListSourcesResponse(BaseModel):
    total: int
    data: list[GetSourceResponse]


class SourceStatusListResponse(BaseModel):
    total: int
    data: list[SourceStatus]


# ============================================================
# Task 内部类型 — 目标端
# ============================================================


class TargetDBConfig(BaseModel):
    """tdbctl 节点配置"""

    host: str = Field(description=_("tdbctl 地址"))
    port: int = Field(description=_("tdbctl 端口"))
    user: str = Field(description=_("用户名"))
    password: str = Field(description=_("密码"))
    security: SecurityConfig | None = Field(default=None, description=_("TLS 配置"))


class TargetSpiderShard(BaseModel):
    host: str = Field(description=_("后端 MySQL 地址"))
    port: int = Field(description=_("端口"))
    user: str = Field(description=_("用户名"))
    password: str = Field(description=_("密码"))


class TargetSpiderConfig(BaseModel):
    """目标端 Spider 集群配置"""

    tdbctl: TargetDBConfig = Field(description=_("tdbctl 节点"))
    mode: str = Field(default="", description=_("写入模式: proxy | direct"))
    shards: list[TargetSpiderShard] = Field(default_factory=list, description=_("后端 MySQL 分片列表"))


class TargetConfig(BaseModel):
    host: str = Field(description=_("目标 MySQL 地址"))
    port: int = Field(description=_("目标 MySQL 端口"))
    user: str = Field(description=_("用户名"))
    password: str = Field(description=_("密码"))
    cluster_type: str = Field(default="", description=_("集群类型: '' | mysql | spider"))
    spider: TargetSpiderConfig | None = Field(default=None, description=_("Spider 配置"))


# ============================================================
# Task 内部类型 — 源端
# ============================================================


class SourceConfItem(BaseModel):
    source_name: str = Field(description=_("已注册的 source 名称"))
    binlog_name: str = Field(default="", description=_("增量起始 binlog 文件"))
    binlog_pos: int = Field(default=0, description=_("增量起始位点"))
    binlog_gtid: str = Field(default="", description=_("增量起始 GTID"))
    myloader_config_name: str = Field(default="", description=_("引用 myloaders 命名配置"))


class FullMigrateConfig(BaseModel):
    export_threads: int = Field(default=4, description=_("导出并发数"))
    import_threads: int = Field(default=16, description=_("导入并发数"))
    data_dir: str = Field(default="./exported_data", description=_("dump 文件目录"))
    consistency: str = Field(default="auto", description=_("导出一致性: auto | flush | lock | none"))
    import_mode: str = Field(default="logical", description=_("导入模式: logical | physical"))
    on_duplicate_logical: str = Field(default="replace", description=_("logical 冲突策略: replace | error | ignore"))
    on_duplicate_physical: str = Field(default="none", description=_("physical 冲突策略: none | manual"))
    sorting_dir: str = Field(default="./sort_dir", description=_("physical 排序目录"))
    disk_quota: str = Field(default="", description=_("physical 磁盘配额"))
    checksum: str = Field(default="optional", description=_("physical checksum: required | optional | off"))
    analyze: str = Field(default="optional", description=_("physical analyze: required | optional | off"))
    range_concurrency: int = Field(default=0, description=_("physical range 并发"))
    compress_kv_pairs: str = Field(default="", alias="compress-kv-pairs", description=_("physical compress-kv-pairs"))
    pd_addr: str = Field(default="", description=_("physical PD 地址"))


class MyLoaderConfig(BaseModel):
    """DTS 0.0.2+ myloader 全量导入配置（对齐引擎 myloaders 段）。"""

    myloader_path: str = Field(description=_("Worker 上 myloader 可执行路径"))
    myloader_dir: str = Field(description=_("全备数据目录"))
    myloader_threads: int = Field(default=16, description=_("--threads"))
    myloader_regex: str = Field(default="", description=_("--regex"))
    myloader_sourcedb: str = Field(default="", description=_("--source-db"))
    myloader_tablelist: str = Field(default="", description=_("--tables-list"))
    myloader_setnames: str = Field(default="", description=_("--set-names"))
    myloader_defaultsfile: str = Field(default="", description=_("--defaults-file"))
    myloader_extraargs: str = Field(default="", description=_("扩展透传参数"))


class IncrMigrateConfig(BaseModel):
    repl_threads: int = Field(default=16, description=_("syncer DML worker 数"))
    repl_batch: int = Field(default=100, description=_("syncer 每批 SQL 行数"))


class SourceConfig(BaseModel):
    source_conf: list[SourceConfItem] = Field(default_factory=list, description=_("源端实例列表"))
    full_migrate_conf: FullMigrateConfig | None = Field(default=None, description=_("全量迁移配置"))
    incr_migrate_conf: IncrMigrateConfig | None = Field(default=None, description=_("增量同步配置"))
    myloader_conf: MyLoaderConfig | None = Field(default=None, description=_("共享 myloader 配置"))
    myloaders: dict[str, MyLoaderConfig] = Field(default_factory=dict, description=_("myloader 命名配置池"))


# ============================================================
# Task 内部类型 — 过滤 & 迁移规则
# ============================================================


class BinlogFilterRuleEntry(BaseModel):
    ignore_event: list[str] = Field(default_factory=list, description=_("忽略的 binlog 事件类型"))
    ignore_sql: list[str] = Field(default_factory=list, description=_("忽略的 SQL 正则"))


class TableMigrateSource(BaseModel):
    source_name: str = Field(description=_("对应 source_conf 中的 source_name"))
    schema: str = Field(description=_("源库名, 支持 * 通配"))
    table: str = Field(description=_("源表名, 支持 * 通配"))


class TableMigrateTarget(BaseModel):
    schema: str | None = Field(default=None, description=_("目标库名, 不填=不变"))
    table: str | None = Field(default=None, description=_("目标表名, 不填=不变"))


class TableMigrateRule(BaseModel):
    source: TableMigrateSource = Field(description=_("源库表匹配"))
    target: TableMigrateTarget | None = Field(default=None, description=_("目标库表映射"))
    binlog_filter_rule: list[str] = Field(default_factory=list, description=_("引用的过滤器规则名"))


# ============================================================
# Task 对象 (创建/更新用)
# ============================================================


class Task(BaseModel):
    name: str = Field(description=_("任务名称, 全局唯一, ≤64字符"))
    task_mode: str = Field(
        description=_("任务模式: all | full | incremental | myloader | myloader&sync | dump | load&sync")
    )
    shard_mode: str = Field(default="", description=_("分片模式: '' | pessimistic | optimistic"))
    strict_optimistic_shard_mode: bool = Field(default=False, description=_("严格spider模式"))
    enhance_online_schema_change: bool = Field(default=True, description=_("启用 online-DDL"))
    on_duplicate: str = Field(default="replace", description=_("冲突策略: replace | error | ignore"))
    meta_schema: str = Field(default="dm_meta", description=_("元数据库名"))
    ignore_checking_items: list[str] = Field(default_factory=list, description=_("忽略的检查项"))
    target_config: TargetConfig = Field(description=_("目标端配置"))
    source_config: SourceConfig = Field(description=_("源端配置"))
    binlog_filter_rule: dict[str, BinlogFilterRuleEntry] = Field(default_factory=dict, description=_("Binlog 过滤器命名池"))
    table_migrate_rule: list[TableMigrateRule] = Field(default_factory=list, description=_("表迁移规则"))


# ============================================================
# Task 请求类型
# ============================================================


class CreateTaskRequest(BaseModel):
    task: Task = Field(description=_("任务配置"))


class UpdateTaskRequest(BaseModel):
    task: Task = Field(description=_("任务配置(完整字段)"))


class StartTaskRequest(BaseModel):
    remove_meta: bool = Field(default=False, description=_("是否删除下游 dm_meta"))
    source_name_list: list[str] | None = Field(default=None, description=_("仅启动指定 source 的 subtask"))
    start_time: str | None = Field(default=None, description=_("指定启动时间"))
    safe_mode_time_duration: str | None = Field(default=None, description=_("safe-mode 持续时间"))


class StopTaskRequest(BaseModel):
    source_name_list: list[str] | None = Field(default=None, description=_("仅停止指定 source"))
    timeout_duration: str | None = Field(default=None, description=_("等待超时时间"))


class OperateTaskSchemaRequest(BaseModel):
    sql_content: str = Field(description=_("SQL 内容, 或 'get' / 'remove'"))
    flush: bool = Field(default=True, description=_("写入 checkpoint"))
    sync: bool = Field(default=False, description=_("optimistic 模式广播到其他 worker"))


# ============================================================
# Task 响应类型
# ============================================================


class CreateTaskResponse(BaseModel):
    task: dict  # Task 对象, 字段不完全确定, 用 dict 兜底
    check_result: str = Field(default="", description=_("预检查结果"))


class UpdateTaskResponse(BaseModel):
    task: dict
    check_result: str = Field(default="")


class TaskItem(BaseModel):
    """列表/获取单个任务时返回的 Task 对象"""

    name: str
    task_mode: str = ""
    shard_mode: str = ""
    target_config: dict | None = None
    source_config: dict | None = None
    status_list: list[dict] = Field(default_factory=list, description=_("subtask 状态列表"))


class ListTasksResponse(BaseModel):
    total: int
    data: list[TaskItem]


# ============================================================
# Task 状态
# ============================================================


class LoadStatus(BaseModel):
    finished_bytes: int = 0
    total_bytes: int = 0
    progress: str = ""
    meta_binlog: str = ""
    meta_binlog_gtid: str = ""


class UnresolvedGroup(BaseModel):
    target: str = ""
    ddl_list: list[str] = Field(default_factory=list)
    first_location: str = ""
    synced: list[str] = Field(default_factory=list)
    unsynced: list[str] = Field(default_factory=list)


class SyncStatus(BaseModel):
    total_events: int = 0
    total_tps: int = 0
    recent_tps: int = 0
    master_binlog: str = ""
    master_binlog_gtid: str = ""
    syncer_binlog: str = ""
    syncer_binlog_gtid: str = ""
    blocking_ddls: list[str] | None = Field(default_factory=list)
    unresolved_groups: list[UnresolvedGroup] | None = Field(default_factory=list)
    synced: bool = False
    binlog_type: str = ""
    seconds_behind_master: int = 0

    def master_coord(self) -> DtsBinlogCoord | None:
        return parse_dts_binlog_coord(self.master_binlog)

    def syncer_coord(self) -> DtsBinlogCoord | None:
        return parse_dts_binlog_coord(self.syncer_binlog)

    def is_same_binlog_file(self) -> bool:
        """master/syncer 的 binlog 文件名相同（不要求 position）。"""
        master = self.master_coord()
        syncer = self.syncer_coord()
        if master is None or syncer is None:
            return False
        return master.file == syncer.file

    def is_master_not_behind_syncer(self) -> bool:
        """部分同步允许 master 超前：master.file/pos >= syncer.file/pos。"""
        master = self.master_coord()
        syncer = self.syncer_coord()
        if master is None or syncer is None:
            return False
        return compare_dts_binlog_coord(master, syncer) >= 0

    def is_poll_caught_up(self) -> bool:
        """Flow wait_catchup 轮询：SBM==0 且 master>=syncer（与 cutover 持锁快照语义不同）。"""
        return self.seconds_behind_master == 0 and self.is_master_not_behind_syncer()


class DumpStatus(BaseModel):
    total_tables: float = 0.0
    completed_tables: float = 0.0
    finished_bytes: float = 0.0
    finished_rows: float = 0.0
    estimate_total_rows: float = 0.0


class TaskStatusItem(BaseModel):
    name: str = ""
    source_name: str = ""
    worker_name: str = ""
    stage: str = ""
    unit: str = ""
    unresolved_ddl_lock_id: str = ""
    load_status: LoadStatus | None = None
    sync_status: SyncStatus | None = None
    dump_status: DumpStatus | None = None
    error_msg: str | None = None


class TaskStatusListResponse(BaseModel):
    total: int
    data: list[TaskStatusItem]


# ============================================================
# 迁移表映射
# ============================================================


class MigrateTargetItem(BaseModel):
    source_schema: str = ""
    source_table: str = ""
    target_schema: str = ""
    target_table: str = ""


class MigrateTargetListResponse(BaseModel):
    total: int
    data: list[MigrateTargetItem]


# ============================================================
# 表结构
# ============================================================


class TableStructureResponse(BaseModel):
    schema_name: str = ""
    table_name: str = ""
    table_create_sql: str = ""


# ============================================================
# 3. Task Template (与 Task 共用 Task schema, 请求/响应均为裸 Task 对象)
# ============================================================


class ImportTemplatesRequest(BaseModel):
    overwrite: bool = Field(default=False, description=_("是否覆盖同名模板"))


class ImportTemplatesFailedItem(BaseModel):
    task_name: str = ""
    error_msg: str = ""


class ImportTemplatesResponse(BaseModel):
    success_task_list: list[str] = Field(default_factory=list, description=_("成功导入的模板名列表"))
    failed_task_list: list[ImportTemplatesFailedItem] = Field(default_factory=list, description=_("失败列表"))


# ============================================================
# 4. 任务格式转换
# ============================================================


class ConvertTaskRequest(BaseModel):
    task: dict | None = Field(default=None, description=_("OpenAPI Task 对象 → 转 YAML"))
    task_config_file: str | None = Field(default=None, description=_("YAML 配置 → 转 OpenAPI Task"))


class ConvertTaskResponse(BaseModel):
    task: dict | None = None
    task_config_file: str | None = None


# ============================================================
# 5. 集群管理
# ============================================================


class TopologyNode(BaseModel):
    name: str = ""
    host: str = ""
    port: int = 0


class ClusterTopology(BaseModel):
    master_topology_list: list[TopologyNode] = Field(default_factory=list)
    worker_topology_list: list[TopologyNode] = Field(default_factory=list)
    grafana_topology: TopologyNode | None = None
    prometheus_topology: TopologyNode | None = None
    alert_manager_topology: TopologyNode | None = None


class ClusterInfoResponse(BaseModel):
    cluster_id: int = 0
    topology: ClusterTopology = Field(default_factory=ClusterTopology)


class MasterItem(BaseModel):
    name: str = ""
    alive: bool = False
    leader: bool = False
    addr: str = ""


class ListMastersResponse(BaseModel):
    total: int = 0
    data: list[MasterItem] = Field(default_factory=list)


class WorkerItem(BaseModel):
    name: str = ""
    addr: str = ""
    bound_stage: str = ""
    bound_source_name: str = ""


class ListWorkersResponse(BaseModel):
    total: int = 0
    data: list[WorkerItem] = Field(default_factory=list)
