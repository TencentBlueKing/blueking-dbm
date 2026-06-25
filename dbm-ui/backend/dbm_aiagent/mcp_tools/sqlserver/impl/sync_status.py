# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer 数据同步状态分析（Mirroring / AlwaysOn 统一入口）。

设计要点
- 单一 MCP 工具：`sqlserver_sync_status(cluster_domain)`，由后端按 db_meta 的
  `SqlserverClusterSyncMode.sync_mode` 自动识别集群是 mirroring 还是 always_on，
  调用方无须感知差异。
- 数据通道：仅访问 `sys.*` 系统视图 / DMV，使用 `DRSApi.sqlserver_sys_read_rpc`，
  与 `instance_summary` 同通道，**无须业务库权限**。
- 节点视角：集群内所有 storage 实例都下发采集；
    * mirroring：以 `mirroring_role_desc == 'PRINCIPAL'` 的视角为基准；
    * always_on：以 `is_primary_replica = 1` 的视角为基准。
  备端采集失败不影响整体可用性，单实例错误会落到 `results[i].error_msg`。
- 派生指标：原始 DMV 行 + 派生字段（MB 换算、估算追齐秒数、commit_lag、issues），
  方便 LLM 直接做结论性输出。

权限假设（依赖 `sqlserver_sys_read_rpc` 通道账号的实际授权情况）
- `VIEW SERVER STATE`：必备。本文件全部 DMV 都需要它，包括：
    `sys.dm_os_performance_counters`、
    `sys.dm_hadr_availability_group_states`、
    `sys.dm_hadr_availability_replica_states`、
    `sys.dm_hadr_availability_replica_cluster_states`、
    `sys.dm_hadr_database_replica_states`、
    `sys.dm_hadr_database_replica_cluster_states`、
    `sys.dm_hadr_cluster_members`。
    通道账号既然能跑 `top_requests/blocking_sessions/wait_stats_snapshot`，
    则该权限已实际到位。
- `VIEW ANY DATABASE` / `VIEW ANY DEFINITION`：必备。
    `sys.database_mirroring`、`sys.availability_groups`、`sys.availability_replicas`、
    `sys.availability_group_listeners` 等 catalog view 行可见性依赖此权限；
    若无，将只看到当前账号有 CONNECT 权限的 DB 那部分。
    通道账号既然能跑 `list_databases`（直接 `FROM sys.databases d` 列出全部库），
    则该权限已实际到位。
- `DB_NAME(database_id)` 返回 NULL 的兜底：
    AG secondary 端在 `secondary_role_allow_connections=NO` 的副本上，
    某些登录账号即使有 `VIEW ANY DATABASE`，`DB_NAME` 仍可能返回 NULL。
    本实现在 AG DB SQL 中同时取 `sys.dm_hadr_database_replica_cluster_states.database_name`
    作为兜底（见 `ag_database_name` 列）。
- 单 cmd 失败隔离：
    所有 SQL 拆分为多条 cmd 下发，`AlwaysOnAnalyzer._table_at` 对
    `cmd_results[idx].error_msg` 非空时静默返回空表，保证个别 DMV
    （如 `dm_hadr_cluster_members` 在小众版本上）权限差异不会让整批失败。

类结构（自上而下）
- `SyncStatusConstants`     ：经验阈值常量（与 serializer help_text 同源）。
- `SyncStatusSQL`           ：所有只读 SQL 片段，按 mirroring / always_on 分组。
- `SyncStatusValueCoercer`  ：标量值规范化（None / bool / datetime 解析等）。
- `MirroringAnalyzer`       ：mirroring 架构采集 + 格式化 + summary 计算。
- `AlwaysOnAnalyzer`        ：always_on 架构采集 + 格式化 + summary 计算。
- `SyncStatusAnalyzer`      ：顶层编排，识别 sync_mode 并分发到子分析器。
- `sqlserver_sync_status`   ：对外薄壳函数，保持原有 import 兼容。
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_sqlserver_addresses
from backend.flow.consts import SqlserverSyncMode


class SyncStatusConstants:
    """经验阈值常量集合。

    用途
        集中所有用于"判定健康度"的阈值；与 serializers/sync_status.py 中的
        help_text 必须保持同源，便于 LLM 拿到字段的同时读到判断规则。
    边界
        - 阈值偏经验值，不是 SQLServer 官方硬指标；
        - 修改任何阈值都需要同步修改 serializer 的 help_text，否则前后文档会漂移。
    """

    #: 日志队列高水位（MB）：超过即提示 warn
    QUEUE_WARN_MB: float = 100
    #: 日志队列严重水位（MB）：超过即认为重度滞后
    QUEUE_CRIT_MB: float = 1024
    #: AG commit_lag 警告阈值（秒）
    COMMIT_LAG_WARN_SEC: float = 5
    #: AG commit_lag 严重阈值（秒）
    COMMIT_LAG_CRIT_SEC: float = 60


class SyncStatusSQL:
    """只读 SQL 片段集合。

    用途
        集中本工具会下发到 SQLServer 的所有 SQL；不直接执行，仅作为常量被两个
        Analyzer 引用。
    边界
        - 全部为 `SELECT`，不带任何写入语义；
        - 不依赖业务库上下文（不会 `USE <user_db>`），仅访问 master 上下文里的
          系统视图 / DMV；
        - 表名、列名严格使用 SQLServer 自带 catalog view / DMV，名字不可改。
    """

    # 1) Mirroring：每个被镜像 DB 一行（含对端、见证、状态、安全级别等）
    MIRRORING: str = """
SELECT
    DB_NAME(dm.database_id)                                        AS database_name,
    dm.mirroring_role_desc                                         AS mirroring_role_desc,
    dm.mirroring_state_desc                                        AS mirroring_state_desc,
    dm.mirroring_safety_level_desc                                 AS mirroring_safety_level_desc,
    dm.mirroring_witness_state_desc                                AS mirroring_witness_state_desc
FROM sys.database_mirroring AS dm
WHERE dm.mirroring_guid IS NOT NULL
""".strip()

    # 2) Mirroring 性能计数器：每个被镜像 DB 一行（cntr_value 是当前实时值/累积值）
    #    Database Mirroring 实例下的若干指标，按白名单聚合
    MIRRORING_PERF: str = """
SELECT
    RTRIM(instance_name)                              AS database_name,
    RTRIM(counter_name)                               AS counter_name,
    cntr_value                                        AS cntr_value
FROM sys.dm_os_performance_counters
WHERE object_name LIKE '%Database Mirroring%'
  AND counter_name IN (
        'Log Send Queue KB',
        'Redo Queue KB',
        'Log Bytes Sent/sec',
        'Redo Bytes/sec'
  )
  AND instance_name <> '_Total'
""".strip()

    # 3) AG 级
    AG: str = """
SELECT
    CONVERT(NVARCHAR(36), ag.group_id)                AS group_id,
    ag.name                                           AS ag_name,
    ags.primary_replica                               AS primary_replica,
    ags.synchronization_health                        AS synchronization_health,
    ags.synchronization_health_desc                   AS synchronization_health_desc
FROM sys.availability_groups AS ag
LEFT JOIN sys.dm_hadr_availability_group_states AS ags
       ON ag.group_id = ags.group_id
""".strip()

    # 4) 副本级
    AG_REPLICA: str = """
SELECT
    CONVERT(NVARCHAR(36), ar.group_id)                AS group_id,
    CONVERT(NVARCHAR(36), ar.replica_id)              AS replica_id,
    ar.replica_server_name                            AS replica_server_name,
    ar.availability_mode_desc                         AS availability_mode_desc,
    ar.failover_mode_desc                             AS failover_mode_desc,
    ars.role_desc                                     AS role_desc,
    ars.operational_state_desc                        AS operational_state_desc,
    ars.connected_state_desc                          AS connected_state_desc,
    ars.synchronization_health_desc                   AS synchronization_health_desc
FROM sys.availability_replicas AS ar
LEFT JOIN sys.dm_hadr_availability_replica_states AS ars
       ON ar.replica_id = ars.replica_id
""".strip()

    # 5) DB 级（含滞后核心指标）
    AG_DB_REPLICA: str = """
SELECT
    CONVERT(NVARCHAR(36), drs.group_id)               AS group_id,
    CONVERT(NVARCHAR(36), drs.replica_id)             AS replica_id,
    drs.database_id                                   AS database_id,
    ar.replica_server_name                            AS replica_server_name,
    DB_NAME(drs.database_id)                          AS database_name,
    drcs.database_name                                AS ag_database_name,
    drs.is_primary_replica                            AS is_primary_replica,
    drs.synchronization_state_desc                    AS synchronization_state_desc,
    drs.synchronization_health_desc                   AS synchronization_health_desc,
    drs.suspend_reason_desc                           AS suspend_reason_desc,
    drs.is_suspended                                  AS is_suspended,
    drs.log_send_queue_size                           AS log_send_queue_size,
    drs.log_send_rate                                 AS log_send_rate,
    drs.redo_queue_size                               AS redo_queue_size,
    drs.redo_rate                                     AS redo_rate,
    drs.last_commit_time                              AS last_commit_time,
    drcs.is_failover_ready                            AS is_failover_ready
FROM sys.dm_hadr_database_replica_states AS drs
LEFT JOIN sys.availability_replicas AS ar
       ON drs.replica_id = ar.replica_id
LEFT JOIN sys.dm_hadr_database_replica_cluster_states AS drcs
       ON drs.replica_id = drcs.replica_id
      AND drs.group_database_id = drcs.group_database_id
""".strip()

    # 6) Listener
    AG_LISTENER: str = """
SELECT
    CONVERT(NVARCHAR(36), agl.group_id)               AS group_id,
    agl.dns_name                                      AS dns_name,
    agl.port                                          AS port,
    agls.state_desc                                   AS state_desc,
    agls.ip_address                                   AS ip_address
FROM sys.availability_group_listeners AS agl
LEFT JOIN sys.availability_group_listener_ip_addresses AS agls
       ON agl.listener_id = agls.listener_id
""".strip()

    # 7) WSFC 集群仲裁与成员
    AG_CLUSTER_MEMBERS: str = """
SELECT
    member_name                                       AS member_name,
    member_state_desc                                 AS member_state_desc,
    number_of_quorum_votes                            AS number_of_quorum_votes
FROM sys.dm_hadr_cluster_members
""".strip()


class SyncStatusValueCoercer:
    """标量值规范化工具。

    用途
        把来自 DRS 的原始字段（GUID / bit / datetime 字符串 / None）转成稳定的
        Python 标量，避免下游 JSON 序列化时出现 NaN / 类型异常。
    边界
        - 所有方法均为静态方法，无状态；
        - 不在此处做任何阈值判断或业务推断；
        - 不抛异常，输入异常时返回 None 或合理默认值。
    """

    #: `_parse_datetime` 支持的时间格式列表（按顺序尝试匹配）
    _DATETIME_FORMATS = (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )

    @staticmethod
    def to_str(value) -> Optional[str]:
        """把任意值转成字符串，None 保持为 None。

        功能：用于 GUID / bigint LSN 这类需要被 LLM 当字符串引用的字段。
        输入：任意类型 value
        输出：None 或 str
        边界：不对 value 做任何裁剪/截断；不处理编码差异（默认 utf-8 隐式）。
        """
        if value is None:
            return None
        return str(value)

    @staticmethod
    def to_bool(value) -> Optional[bool]:
        """把 bit/int/str 等转成 Python bool。

        功能：用于 SQLServer 的 bit 列（0/1）以及部分 DMV 返回的字符串布尔。
        输入：任意类型 value，常见为 0/1/True/False/"0"/"1"/"true"/"false"
        输出：None（输入为 None 时）/ True / False
        边界：
            - 数字 0 -> False，非 0 -> True；
            - 字符串识别白名单：("1", "true", "yes", "y")（不区分大小写）；
            - 不在白名单的字符串会走 Python 的 bool() 兜底，可能返回 True。
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "y")
        return bool(value)

    @classmethod
    def parse_datetime(cls, value) -> Optional[datetime]:
        """把字符串时间戳解析成 datetime 对象。

        功能：用于 commit_lag 这类需要相减得到秒差的字段。
        输入：字符串（兼容多种 ISO/T 分隔格式）或 None
        输出：datetime 或 None
        边界：
            - 任一识别失败/类型不匹配 -> 返回 None，**不抛异常**；
            - 不处理时区；上游 DRS 返回的时间均为实例本地时间，且全集群一致。
        """
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        for fmt in cls._DATETIME_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                continue
        return None

    @staticmethod
    def row_richness(row: Dict) -> int:
        """统计字典中非空/非零字段的数量。

        功能：在"多节点同时返回同一行"时挑信息更全的那份。
        输入：dict
        输出：int（非空字段数）
        边界：把 None / "" / 0 都视作"无信息"；对于布尔 False 也会被算成"无"。
        """
        return sum(1 for v in row.values() if v not in (None, "", 0))


class MirroringAnalyzer:
    """Database Mirroring 架构同步状态分析器。

    用途
        - 下发 mirroring 相关 SQL 到集群内所有实例；
        - 合并主端 / 备端视角；
        - 计算派生指标（MB 换算、估算追齐秒数、is_healthy、issues）；
        - 汇总顶层 summary。
    输入
        bk_cloud_id: 集群所在云区域
        instances:   [{"address": "ip:port", "role": "master|slave", "is_stand_by": bool}, ...]
    输出
        通过 `analyze()` 返回 (data, per_instance_results, summary)，结构详见
        SQLServerSyncStatusOutputSerializer 中 `mirroring` / `results` / `summary` 字段。
    边界
        - 只读，不修改任何 SQLServer 对象；
        - 单实例 RPC 失败只影响 per_instance_results[i].error_msg，不抛出；
        - mirroring 不是 AG 概念，summary.node_count / max_commit_lag_seconds 固定为 None。
    """

    def __init__(self, bk_cloud_id: int, instances: List[Dict]):
        self._bk_cloud_id = bk_cloud_id
        self._instances = instances

    # ---------- public ----------
    def analyze(self, db_filter: Optional["DatabaseFilter"] = None) -> Tuple[Dict, List[Dict], Dict]:
        """执行采集 + 组装 + summary 计算。

        功能：MirroringAnalyzer 的唯一对外入口。
        输入：
            - 使用构造参数 bk_cloud_id / instances；
            - 可选 db_filter：用户传入的库名白名单过滤器；为 None 表示全量返回。
        输出：(mirroring_data, per_instance_results, summary)
            - mirroring_data: {"databases": [...]}
            - per_instance_results: [{"address","role","is_stand_by","error_msg"}, ...]
            - summary: 见 SQLServerSyncStatusSummarySerializer
        边界：
            - 当集群没有任何镜像 DB 时，summary 走 _empty_summary，overall_health=N/A；
            - 应用 db_filter 后没有任何命中 DB 时，summary.reason 写明原因；
            - 过滤动作发生在 assemble 之后，SQL 仍然全量采集，避免动态拼 SQL。
        """
        principal_dbs, mirror_dbs, perf_by_db, per_instance_results = self._collect_raw()
        data = self._assemble_data(principal_dbs, mirror_dbs, perf_by_db)
        if db_filter is not None and db_filter.is_active():
            data = {"databases": db_filter.apply(data.get("databases") or [])}
            if not data["databases"]:
                return (
                    data,
                    per_instance_results,
                    _empty_summary(reason="no mirrored databases matched the requested name list"),
                )
        summary = self._summarize(data)
        return data, per_instance_results, summary

    # ---------- internal: collect ----------
    def _collect_raw(self) -> Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, Dict[str, int]], List[Dict]]:
        """下发 2 条 SQL，按"该实例视角下的 mirroring 角色"分桶。

        功能：把多实例的原始返回汇总为主端桶 / 备端桶 / 性能计数器桶。
        输入：无（使用 self._bk_cloud_id / self._instances）
        输出：(principal_dbs, mirror_dbs, perf_by_db, per_instance_results)
            - principal_dbs[db]:    {...mirroring 行..., "source_address": ip:port}
                                    （source_address = 看到该 DB 为 PRINCIPAL 的实例）
            - mirror_dbs[db]:       同上，但 source_address 为备端实例
            - perf_by_db[db][cnt]:  来自 perf counters，仅采集 principal 端的数值
            - per_instance_results: 每实例采集结果（含 error_msg）
        边界：
            - 单实例 RPC 失败 / cmd 失败均不抛异常，写入 error_msg；
            - 性能计数器仅在该实例就是 PRINCIPAL 时才采集（备端的 perf 值无意义）。
        """
        rpc_results = DRSApi.sqlserver_sys_read_rpc(
            {
                "bk_cloud_id": self._bk_cloud_id,
                "addresses": [item["address"] for item in self._instances],
                "cmds": [SyncStatusSQL.MIRRORING, SyncStatusSQL.MIRRORING_PERF],
            }
        )
        address_to_rpc = {res["address"]: res for res in rpc_results}

        principal_dbs: Dict[str, Dict] = {}
        mirror_dbs: Dict[str, Dict] = {}
        perf_by_db: Dict[str, Dict[str, int]] = {}
        per_instance_results: List[Dict] = []

        for item in self._instances:
            rpc_res = address_to_rpc.get(item["address"])
            if rpc_res is None:
                per_instance_results.append({**item, "error_msg": "no rpc response"})
                continue
            if rpc_res.get("error_msg"):
                per_instance_results.append({**item, "error_msg": rpc_res["error_msg"]})
                continue

            cmd_results = rpc_res.get("cmd_results") or []
            mirroring_rows = self._extract_table(cmd_results, 0)
            perf_rows = self._extract_table(cmd_results, 1)

            for row in mirroring_rows:
                db = row.get("database_name")
                if not db:
                    continue
                role_desc = (row.get("mirroring_role_desc") or "").upper()
                row_with_src = {**row, "source_address": item["address"]}
                if role_desc == "PRINCIPAL":
                    principal_dbs[db] = row_with_src
                    for p in perf_rows:
                        if p.get("database_name") == db:
                            perf_by_db.setdefault(db, {})[p["counter_name"]] = p.get("cntr_value")
                elif role_desc == "MIRROR":
                    mirror_dbs[db] = row_with_src

            per_instance_results.append({**item, "error_msg": ""})

        return principal_dbs, mirror_dbs, perf_by_db, per_instance_results

    @staticmethod
    def _extract_table(cmd_results: List[Dict], idx: int) -> List[Dict]:
        """从 cmd_results 中安全取出第 idx 条 cmd 的 table_data。

        功能：屏蔽 cmd_results 越界 / 某条 cmd 自身报错的情况。
        输入：cmd_results 整体列表 + 下标
        输出：list[dict]（失败时返回 []）
        边界：cmd 报错时静默返回 []，错误不会冒泡。
        """
        if idx >= len(cmd_results):
            return []
        cr = cmd_results[idx]
        if cr.get("error_msg"):
            return []
        return cr.get("table_data") or []

    # ---------- internal: assemble ----------
    def _assemble_data(
        self,
        principal_dbs: Dict[str, Dict],
        mirror_dbs: Dict[str, Dict],
        perf_by_db: Dict[str, Dict[str, int]],
    ) -> Dict:
        """以 principal 视角为主，合并 mirror 视角，按 DB 名字升序排列。

        功能：把分桶后的原始数据组装为对外的 `mirroring.databases` 列表。
        输入：principal_dbs / mirror_dbs / perf_by_db（来自 _collect_raw）
        输出：{"databases": [格式化后的 DB 行...]}
        边界：principal 视角缺失（仅备端能看到）时仍记录一行，方便排查异常拓扑。
        """
        databases: List[Dict] = []
        seen = set()
        for db, row in principal_dbs.items():
            seen.add(db)
            databases.append(self._format_database(row, mirror_dbs.get(db), perf_by_db.get(db, {})))
        for db, row in mirror_dbs.items():
            if db in seen:
                continue
            databases.append(self._format_database(None, row, {}))
        databases.sort(key=lambda x: (x.get("database_name") or ""))
        return {"databases": databases}

    @staticmethod
    def _format_database(
        principal_row: Optional[Dict],
        mirror_row: Optional[Dict],
        perf: Dict[str, int],
    ) -> Dict:
        """格式化单个被镜像 DB 的最终对外行（含派生字段）。

        功能：换算 KB->MB、估算追齐秒数、生成 is_healthy / issues。
        输入：
            principal_row: 来自主端视角的 sys.database_mirroring 行（可能为 None）
            mirror_row:    来自备端视角的同一行（可能为 None）
            perf:          性能计数器 dict，仅 principal 端有效
        输出：单条 dict，结构对应 SQLServerMirroringDatabaseSerializer。
        边界：
            - principal_row / mirror_row 不会同时为 None；
            - 速率为 0 时，estimated_send_seconds / estimated_redo_seconds 返回 None；
            - state_desc 缺失时不会被算成 SYNCHRONIZED；
            - issues 是清单形态，便于 LLM 直接复述。
        """
        base = principal_row or mirror_row or {}

        log_send_queue_kb = perf.get("Log Send Queue KB") or 0
        redo_queue_kb = perf.get("Redo Queue KB") or 0
        log_bytes_sent_per_sec = perf.get("Log Bytes Sent/sec") or 0
        redo_bytes_per_sec = perf.get("Redo Bytes/sec") or 0

        log_send_queue_mb = round(log_send_queue_kb / 1024.0, 2)
        redo_queue_mb = round(redo_queue_kb / 1024.0, 2)

        log_send_kbps = log_bytes_sent_per_sec / 1024.0 if log_bytes_sent_per_sec else 0
        redo_kbps = redo_bytes_per_sec / 1024.0 if redo_bytes_per_sec else 0
        est_send_sec = round(log_send_queue_kb / log_send_kbps, 1) if log_send_kbps > 0 else None
        est_redo_sec = round(redo_queue_kb / redo_kbps, 1) if redo_kbps > 0 else None

        state_desc = (base.get("mirroring_state_desc") or "").upper()
        issues: List[str] = []
        if state_desc and state_desc != "SYNCHRONIZED":
            issues.append(f"state={state_desc}")
        MirroringAnalyzer._append_queue_issue(issues, "log_send_queue", log_send_queue_mb)
        MirroringAnalyzer._append_queue_issue(issues, "redo_queue", redo_queue_mb)

        is_healthy = (
            state_desc == "SYNCHRONIZED"
            and log_send_queue_mb < SyncStatusConstants.QUEUE_WARN_MB
            and redo_queue_mb < SyncStatusConstants.QUEUE_WARN_MB
        )

        return {
            "database_name": base.get("database_name"),
            "principal_address": principal_row.get("source_address") if principal_row else None,
            "mirror_address": mirror_row.get("source_address") if mirror_row else None,
            "mirroring_role_desc": base.get("mirroring_role_desc"),
            "mirroring_state_desc": base.get("mirroring_state_desc"),
            "mirroring_safety_level_desc": base.get("mirroring_safety_level_desc"),
            "mirroring_witness_state_desc": base.get("mirroring_witness_state_desc"),
            "log_send_queue_mb": log_send_queue_mb,
            "redo_queue_mb": redo_queue_mb,
            "log_send_rate_kbps": round(log_send_kbps, 2),
            "redo_rate_kbps": round(redo_kbps, 2),
            "estimated_send_seconds": est_send_sec,
            "estimated_redo_seconds": est_redo_sec,
            "is_healthy": is_healthy,
            "issues": issues,
        }

    @staticmethod
    def _append_queue_issue(issues: List[str], name: str, value_mb: float) -> None:
        """根据队列水位阈值往 issues 追加一条警告/严重提示。

        功能：把"队列 MB 数 vs 阈值"的判定外提，让 mirroring/always_on 共用。
        输入：现成的 issues 列表 / 指标名 / 当前 MB 数
        输出：None（直接对 issues 做 append）
        边界：value_mb 必须为非负数；< warn 阈值则不追加任何元素。
        """
        if value_mb >= SyncStatusConstants.QUEUE_CRIT_MB:
            issues.append(f"{name}={value_mb}MB(critical)")
        elif value_mb >= SyncStatusConstants.QUEUE_WARN_MB:
            issues.append(f"{name}={value_mb}MB(warn)")

    # ---------- internal: summary ----------
    @staticmethod
    def _summarize(data: Dict) -> Dict:
        """根据已格式化的 databases 计算顶层 summary。

        功能：聚合 unhealthy 数量 / 最大队列 / 顶层健康度 / 顶层 issues。
        输入：_assemble_data 返回的 {"databases": [...]}
        输出：summary dict，对应 SQLServerSyncStatusSummarySerializer。
        边界：
            - mirroring 不属于 AG 范畴，因此 node_count / max_commit_lag_seconds 固定为 None；
            - 任一 DB 处于非 SYNCHRONIZED 状态 -> overall_health=NOT_HEALTHY；
            - 否则按队列阈值降级。
        """
        dbs = data.get("databases") or []
        if not dbs:
            return _empty_summary(reason="no mirrored databases found")

        unhealthy = [d for d in dbs if not d.get("is_healthy")]
        max_log_send = max((d.get("log_send_queue_mb") or 0) for d in dbs)
        max_redo = max((d.get("redo_queue_mb") or 0) for d in dbs)

        not_synced = [d for d in dbs if (d.get("mirroring_state_desc") or "").upper() != "SYNCHRONIZED"]
        if not_synced:
            overall = "NOT_HEALTHY"
        elif max_log_send >= SyncStatusConstants.QUEUE_CRIT_MB or max_redo >= SyncStatusConstants.QUEUE_CRIT_MB:
            overall = "NOT_HEALTHY"
        elif max_log_send >= SyncStatusConstants.QUEUE_WARN_MB or max_redo >= SyncStatusConstants.QUEUE_WARN_MB:
            overall = "PARTIALLY_HEALTHY"
        else:
            overall = "HEALTHY"

        issues: List[str] = []
        for d in unhealthy:
            for it in d.get("issues") or []:
                issues.append(f"{d.get('database_name')}: {it}")

        return {
            "overall_health": overall,
            "node_count": None,
            "unhealthy_database_count": len(unhealthy),
            "database_count": len(dbs),
            "max_log_send_queue_mb": max_log_send,
            "max_redo_queue_mb": max_redo,
            "max_commit_lag_seconds": None,
            "issues": issues,
            "reason": "",
        }


class AlwaysOnAnalyzer:
    """AlwaysOn Availability Group 同步状态分析器。

    用途
        - 下发 5 条 AG 相关 SQL；
        - 跨节点合并同一份元数据（按 AG/replica/db 去重，挑信息更全的版本）；
        - 计算各 DB 的滞后队列、估算追齐秒数、AG 顶层 commit_lag；
        - 汇总顶层 summary。
    输入
        bk_cloud_id / instances 同 MirroringAnalyzer。
    输出
        通过 `analyze()` 返回 (data, per_instance_results, summary)。
    边界
        - 只读；单实例失败不影响整体；
        - listener / cluster_members 跨 AG 共享（实际生产里 1 集群通常只有 1 AG，这样最稳妥）。
    """

    def __init__(self, bk_cloud_id: int, instances: List[Dict]):
        self._bk_cloud_id = bk_cloud_id
        self._instances = instances

    # ---------- public ----------
    def analyze(self, db_filter: Optional["DatabaseFilter"] = None) -> Tuple[Dict, List[Dict], Dict]:
        """AG 分析的唯一对外入口。

        功能：完成采集 + 组装 + summary 一条龙。
        输入：
            - 依赖构造参数；
            - 可选 db_filter：库名白名单过滤器；为 None / 未启用时全量返回。
        输出：(always_on_data, per_instance_results, summary)。
        边界：
            - 当集群没有任何 AG 时，summary 走 _empty_summary；
            - 应用 db_filter 后所有 AG 下的 DB 行均被过滤掉时，summary.reason
              写明"用户库名未命中"，避免被误读为"无同步关系"；
            - listener / cluster_members / replicas 元信息**不会**被库名过滤
              影响，仍保留供 LLM 判断仲裁与拓扑健康度。
        """
        buckets, per_instance_results = self._collect_raw()
        data = self._assemble_data(buckets)
        if db_filter is not None and db_filter.is_active():
            self._apply_db_filter(data, db_filter)
            if not self._has_any_database(data):
                return (
                    data,
                    per_instance_results,
                    _empty_summary(reason="no AG databases matched the requested name list"),
                )
        summary = self._summarize(data)
        return data, per_instance_results, summary

    @staticmethod
    def _apply_db_filter(data: Dict, db_filter: "DatabaseFilter") -> None:
        """对 always_on 装配结果原地做白名单过滤。

        功能：仅过滤每个 replica 下的 databases 列表，保留 AG / 副本 / Listener /
              cluster_members 等结构性元信息。
        输入：_assemble_data 返回的 data + 已启用的 db_filter
        输出：None（原地修改 data）
        边界：过滤后 databases=[] 的 replica 仍保留，避免 LLM 误判副本消失。
        """
        for ag in data.get("availability_groups") or []:
            for replica in ag.get("replicas") or []:
                replica["databases"] = db_filter.apply(replica.get("databases") or [])

    @staticmethod
    def _has_any_database(data: Dict) -> bool:
        """判断 always_on 装配结果里是否还存在任意 DB 行。

        功能：用于过滤后早退判断。
        输入：_assemble_data 返回的 data
        输出：bool
        边界：data 缺字段时按"无 DB"处理，不抛异常。
        """
        for ag in data.get("availability_groups") or []:
            for replica in ag.get("replicas") or []:
                if replica.get("databases"):
                    return True
        return False

    # ---------- internal: collect ----------
    def _collect_raw(self) -> Tuple[Dict[str, Dict], List[Dict]]:
        """下发 5 条 SQL，按对象主键去重合并多节点的返回。

        功能：把"每个节点都返回一份相同元数据"的情况合并成一份"信息最全"的视图。
        输入：无（使用 self.*）。
        输出：(buckets, per_instance_results)
            buckets:
                "ag":       { group_id: ag_row }
                "replica":  { replica_id: replica_row }
                "db":       { (replica_id, database_id): db_row }
                "listener": { (listener_id, ip_address): listener_row }
                "member":   { member_name: cluster_member_row }
            per_instance_results: 每实例采集结果。
        边界：
            - "信息最全"的判定基于 `SyncStatusValueCoercer.row_richness`；
            - 个别节点的某段 SQL 失败（如权限缺失）会被静默跳过，不影响其他段；
            - 单节点的全部 cmd 都失败 -> 仅 error_msg 标记，不抛异常。
        """
        rpc_results = DRSApi.sqlserver_sys_read_rpc(
            {
                "bk_cloud_id": self._bk_cloud_id,
                "addresses": [item["address"] for item in self._instances],
                "cmds": [
                    SyncStatusSQL.AG,
                    SyncStatusSQL.AG_REPLICA,
                    SyncStatusSQL.AG_DB_REPLICA,
                    SyncStatusSQL.AG_LISTENER,
                    SyncStatusSQL.AG_CLUSTER_MEMBERS,
                ],
            }
        )
        address_to_rpc = {res["address"]: res for res in rpc_results}

        buckets: Dict[str, Dict] = {
            "ag": {},
            "replica": {},
            "db": {},
            "listener": {},
            "member": {},
        }
        per_instance_results: List[Dict] = []

        for item in self._instances:
            rpc_res = address_to_rpc.get(item["address"])
            if rpc_res is None:
                per_instance_results.append({**item, "error_msg": "no rpc response"})
                continue
            if rpc_res.get("error_msg"):
                per_instance_results.append({**item, "error_msg": rpc_res["error_msg"]})
                continue

            cmd_results = rpc_res.get("cmd_results") or []
            self._merge_ag_rows(buckets["ag"], self._table_at(cmd_results, 0))
            self._merge_richer_rows(
                buckets["replica"], self._table_at(cmd_results, 1), key_fn=lambda r: r.get("replica_id")
            )
            self._merge_richer_rows(
                buckets["db"],
                self._table_at(cmd_results, 2),
                key_fn=lambda r: (r.get("replica_id"), r.get("database_id"))
                if r.get("replica_id") and r.get("database_id") is not None
                else None,
            )
            for row in self._table_at(cmd_results, 3):
                lid = row.get("listener_id")
                if not lid:
                    continue
                buckets["listener"][(lid, row.get("ip_address") or "")] = row
            for row in self._table_at(cmd_results, 4):
                name = row.get("member_name")
                if not name:
                    continue
                buckets["member"][name] = row

            per_instance_results.append({**item, "error_msg": ""})

        return buckets, per_instance_results

    @staticmethod
    def _table_at(cmd_results: List[Dict], idx: int) -> List[Dict]:
        """安全获取第 idx 段 cmd 的 table_data。

        功能：屏蔽下标越界 / 单段 cmd 报错。
        输入：cmd_results 整体 + 下标
        输出：list[dict]
        边界：失败时返回 []，错误不会抛出。
        """
        if idx >= len(cmd_results):
            return []
        cr = cmd_results[idx]
        if cr.get("error_msg"):
            return []
        return cr.get("table_data") or []

    @staticmethod
    def _merge_ag_rows(bucket: Dict[str, Dict], rows: List[Dict]) -> None:
        """合并 AG 行：相同 group_id 时，优先保留 primary_replica 非空的版本。

        功能：跨节点合并 AG 信息，避免备端视角看到 primary_replica=NULL 的问题。
        输入：现成的 bucket 字典 + 新一批行
        输出：无（原地修改 bucket）
        边界：group_id 为空的行被忽略。
        """
        for row in rows:
            gid = row.get("group_id")
            if not gid:
                continue
            cur = bucket.get(gid)
            if cur is None or (not cur.get("primary_replica") and row.get("primary_replica")):
                bucket[gid] = row

    @staticmethod
    def _merge_richer_rows(bucket: Dict, rows: List[Dict], key_fn) -> None:
        """按 key_fn 去重；同 key 时保留 row_richness 更高的版本。

        功能：通用合并器，给 replica / db_replica 复用。
        输入：bucket / rows / key_fn(row)->hashable_key|None
        输出：无（原地修改）
        边界：key_fn 返回 None 的行会被丢弃。
        """
        for row in rows:
            key = key_fn(row)
            if key is None:
                continue
            cur = bucket.get(key)
            if cur is None or SyncStatusValueCoercer.row_richness(row) > SyncStatusValueCoercer.row_richness(cur):
                bucket[key] = row

    # ---------- internal: assemble ----------
    def _assemble_data(self, buckets: Dict[str, Dict]) -> Dict:
        """把合并后的 buckets 组装成嵌套结构：AG -> replicas -> databases。

        功能：生成对外的 `always_on` 字段内容。
        输入：_collect_raw 返回的 buckets
        输出：{"availability_groups": [...]}
        边界：listener / cluster_members 同时挂到所有 AG 下（生产场景通常只 1 AG）。
        """
        listeners_all = [self._format_listener(r) for r in buckets["listener"].values()]
        cluster_members_all = [self._format_cluster_member(r) for r in buckets["member"].values()]

        availability_groups: List[Dict] = []
        for gid, ag_row in buckets["ag"].items():
            ag_replicas: List[Dict] = []
            for rid, replica_row in buckets["replica"].items():
                if replica_row.get("group_id") != gid:
                    continue
                dbs_for_replica = [
                    self._format_ag_database(drow) for (rid2, _did), drow in buckets["db"].items() if rid2 == rid
                ]
                dbs_for_replica.sort(key=lambda x: (x.get("database_name") or ""))
                ag_replicas.append(self._format_ag_replica(replica_row, dbs_for_replica))

            ag_replicas.sort(
                key=lambda r: (
                    0 if (r.get("role_desc") or "").upper() == "PRIMARY" else 1,
                    r.get("replica_server_name") or "",
                )
            )

            availability_groups.append(self._format_ag(ag_row, ag_replicas, listeners_all, cluster_members_all))

        return {"availability_groups": availability_groups}

    @staticmethod
    def _format_ag(
        ag_row: Dict,
        replicas: List[Dict],
        listeners: List[Dict],
        cluster_members: List[Dict],
    ) -> Dict:
        """格式化单个 AG 节点。

        功能：组装 AG 的对外结构。
        输入：原始 ag 行 + 已格式化的下挂列表
        输出：对应 SQLServerAGSerializer 的 dict
        边界：group_id 强制转字符串，防止 UUID 类型在 JSON 中歧义。
        """
        return {
            "ag_name": ag_row.get("ag_name"),
            "group_id": SyncStatusValueCoercer.to_str(ag_row.get("group_id")),
            "primary_replica": ag_row.get("primary_replica"),
            "synchronization_health_desc": ag_row.get("synchronization_health_desc"),
            "replicas": replicas,
            "listeners": listeners,
            "cluster_members": cluster_members,
        }

    @staticmethod
    def _format_ag_replica(row: Dict, databases: List[Dict]) -> Dict:
        """格式化单个 AG 副本。

        功能：组装副本的对外结构。
        输入：原始 replica 行 + 已格式化的 databases。
        输出：对应 SQLServerAGReplicaSerializer 的 dict。
        边界：replica_id 强制字符串化。
        """
        return {
            "replica_id": SyncStatusValueCoercer.to_str(row.get("replica_id")),
            "replica_server_name": row.get("replica_server_name"),
            "role_desc": row.get("role_desc"),
            "availability_mode_desc": row.get("availability_mode_desc"),
            "failover_mode_desc": row.get("failover_mode_desc"),
            "operational_state_desc": row.get("operational_state_desc"),
            "connected_state_desc": row.get("connected_state_desc"),
            "synchronization_health_desc": row.get("synchronization_health_desc"),
            "databases": databases,
        }

    @staticmethod
    def _format_ag_database(row: Dict) -> Dict:
        """格式化单个 AG 副本上的 DB 行（含派生字段）。

        功能：换算 KB->MB、估算追齐秒数、产出 is_healthy / issues。
        输入：来自 sys.dm_hadr_database_replica_states 的合并行
        输出：对应 SQLServerAGDatabaseSerializer 的 dict
        边界：
            - 异步副本 (`SYNCHRONIZING`) 不算异常，仅在队列水位高时由队列阈值兜底；
            - DB_NAME 返回 NULL 时使用 `ag_database_name` 兜底；
            - 速率为 0 时估算秒数返回 None，避免除零。
        """
        log_send_queue_kb = row.get("log_send_queue_size") or 0
        redo_queue_kb = row.get("redo_queue_size") or 0
        log_send_rate_kbps = row.get("log_send_rate") or 0
        redo_rate_kbps = row.get("redo_rate") or 0

        log_send_queue_mb = round(log_send_queue_kb / 1024.0, 2)
        redo_queue_mb = round(redo_queue_kb / 1024.0, 2)
        est_send_sec = round(log_send_queue_kb / log_send_rate_kbps, 1) if log_send_rate_kbps else None
        est_redo_sec = round(redo_queue_kb / redo_rate_kbps, 1) if redo_rate_kbps else None

        sync_state_desc = (row.get("synchronization_state_desc") or "").upper()
        sync_health_desc = (row.get("synchronization_health_desc") or "").upper()
        is_suspended = bool(row.get("is_suspended"))

        issues: List[str] = []
        if sync_state_desc and sync_state_desc not in ("SYNCHRONIZED", "SYNCHRONIZING"):
            issues.append(f"sync_state={sync_state_desc}")
        if sync_health_desc and sync_health_desc != "HEALTHY":
            issues.append(f"health={sync_health_desc}")
        if is_suspended:
            issues.append(f"suspended:{row.get('suspend_reason_desc') or ''}")
        MirroringAnalyzer._append_queue_issue(issues, "log_send_queue", log_send_queue_mb)
        MirroringAnalyzer._append_queue_issue(issues, "redo_queue", redo_queue_mb)

        is_healthy = (
            sync_health_desc == "HEALTHY"
            and sync_state_desc in ("SYNCHRONIZED", "SYNCHRONIZING")
            and not is_suspended
            and log_send_queue_mb < SyncStatusConstants.QUEUE_WARN_MB
            and redo_queue_mb < SyncStatusConstants.QUEUE_WARN_MB
        )

        return {
            "database_name": row.get("database_name") or row.get("ag_database_name"),
            "replica_server_name": row.get("replica_server_name"),
            "is_primary_replica": SyncStatusValueCoercer.to_bool(row.get("is_primary_replica")),
            "synchronization_state_desc": row.get("synchronization_state_desc"),
            "synchronization_health_desc": row.get("synchronization_health_desc"),
            "suspend_reason_desc": row.get("suspend_reason_desc"),
            "is_suspended": is_suspended,
            "log_send_queue_mb": log_send_queue_mb,
            "redo_queue_mb": redo_queue_mb,
            "log_send_rate_kbps": log_send_rate_kbps,
            "redo_rate_kbps": redo_rate_kbps,
            "last_commit_time": SyncStatusValueCoercer.to_str(row.get("last_commit_time")),
            "estimated_send_seconds": est_send_sec,
            "estimated_redo_seconds": est_redo_sec,
            "is_failover_ready": SyncStatusValueCoercer.to_bool(row.get("is_failover_ready")),
            "is_healthy": is_healthy,
            "issues": issues,
        }

    @staticmethod
    def _format_listener(row: Dict) -> Dict:
        """格式化单个 Listener。

        功能：把原始 listener 行降级为前端友好的字段集。
        输入：sys.availability_group_listeners 合并 sys.availability_group_listener_ip_addresses 的行
        输出：对应 SQLServerAGListenerSerializer 的 dict
        边界：is_dhcp 走 bool 规范化。
        """
        return {
            "dns_name": row.get("dns_name"),
            "port": row.get("port"),
            "ip_address": row.get("ip_address"),
            "state_desc": row.get("state_desc"),
        }

    @staticmethod
    def _format_cluster_member(row: Dict) -> Dict:
        """格式化单个 WSFC 节点。

        功能：仅保留判断仲裁所需的最小字段。
        输入：sys.dm_hadr_cluster_members 行
        输出：对应 SQLServerAGClusterMemberSerializer 的 dict
        边界：DMV 缺权限时本字段会整体缺失（已在 docstring 说明）。
        """
        return {
            "member_name": row.get("member_name"),
            "member_state_desc": row.get("member_state_desc"),
            "number_of_quorum_votes": row.get("number_of_quorum_votes"),
        }

    # ---------- internal: summary ----------
    @classmethod
    def _summarize(cls, data: Dict) -> Dict:
        """根据已组装的 AG 数据计算顶层 summary。

        功能：聚合所有 AG / 副本 / DB 的健康度，给出顶层结论。
        输入：_assemble_data 返回的 {"availability_groups": [...]}
        输出：summary dict，对应 SQLServerSyncStatusSummarySerializer。
        边界：
            - 没有任何 AG 行 -> 走 _empty_summary；
            - 顶层健康度按"AG 状态 + 队列阈值 + commit_lag 阈值"三档降级；
            - max_commit_lag_seconds 在所有副本/库无 last_commit_time 时为 None。
        """
        ags = data.get("availability_groups") or []
        if not ags:
            return _empty_summary(reason="no availability groups found")

        all_dbs: List[Dict] = []
        replica_count = 0
        for ag in ags:
            replica_count += len(ag.get("replicas") or [])
            for r in ag.get("replicas") or []:
                for d in r.get("databases") or []:
                    all_dbs.append({**d, "_ag_name": ag.get("ag_name")})

        if not all_dbs:
            return _empty_summary(reason="availability groups have no database rows")

        unhealthy = [d for d in all_dbs if not d.get("is_healthy")]
        max_log_send = max((d.get("log_send_queue_mb") or 0) for d in all_dbs)
        max_redo = max((d.get("redo_queue_mb") or 0) for d in all_dbs)
        max_commit_lag = cls._compute_max_commit_lag(ags)

        ag_health_levels = [(ag.get("synchronization_health_desc") or "").upper() for ag in ags]
        has_critical = any(
            d for d in all_dbs if not d.get("is_healthy") and "critical" in " ".join(d.get("issues") or [])
        )
        if "NOT_HEALTHY" in ag_health_levels or has_critical:
            overall = "NOT_HEALTHY"
        elif "PARTIALLY_HEALTHY" in ag_health_levels or unhealthy:
            overall = "PARTIALLY_HEALTHY"
        elif max_log_send >= SyncStatusConstants.QUEUE_CRIT_MB or max_redo >= SyncStatusConstants.QUEUE_CRIT_MB:
            overall = "NOT_HEALTHY"
        elif max_log_send >= SyncStatusConstants.QUEUE_WARN_MB or max_redo >= SyncStatusConstants.QUEUE_WARN_MB:
            overall = "PARTIALLY_HEALTHY"
        elif max_commit_lag is not None and max_commit_lag >= SyncStatusConstants.COMMIT_LAG_CRIT_SEC:
            overall = "NOT_HEALTHY"
        elif max_commit_lag is not None and max_commit_lag >= SyncStatusConstants.COMMIT_LAG_WARN_SEC:
            overall = "PARTIALLY_HEALTHY"
        else:
            overall = "HEALTHY"

        issues: List[str] = []
        for d in unhealthy:
            for it in d.get("issues") or []:
                issues.append(f"[{d.get('_ag_name')}] {d.get('replica_server_name')}/{d.get('database_name')}: {it}")
        if max_commit_lag is not None and max_commit_lag >= SyncStatusConstants.COMMIT_LAG_WARN_SEC:
            issues.append(f"commit_lag={max_commit_lag}s (warn>={SyncStatusConstants.COMMIT_LAG_WARN_SEC}s)")

        return {
            "overall_health": overall,
            "node_count": replica_count,
            "unhealthy_database_count": len(unhealthy),
            "database_count": len(all_dbs),
            "max_log_send_queue_mb": max_log_send,
            "max_redo_queue_mb": max_redo,
            "max_commit_lag_seconds": max_commit_lag,
            "issues": issues,
            "reason": "",
        }

    @staticmethod
    def _compute_max_commit_lag(ags: List[Dict]) -> Optional[float]:
        """计算所有 (primary_db, secondary_db) 对中 last_commit_time 的最大差值。

        功能：作为 RPO 的近似估算，给到 summary.max_commit_lag_seconds。
        输入：组装后的 ags 列表（含每个 replica 的 databases）
        输出：float（秒）或 None
        边界：
            - 任一时间戳无法解析或缺失，则该对跳过；
            - 时间差为负数会被夹到 0（防止 secondary 比 primary 时间略超前导致负值）；
            - 全部对都无法计算时返回 None。
        """
        max_lag: Optional[float] = None
        for ag in ags:
            primary_commit: Dict[str, datetime] = {}
            secondary_commit: Dict[Tuple[str, str], datetime] = {}
            for r in ag.get("replicas") or []:
                role = (r.get("role_desc") or "").upper()
                for d in r.get("databases") or []:
                    ts = SyncStatusValueCoercer.parse_datetime(d.get("last_commit_time"))
                    if ts is None:
                        continue
                    db = d.get("database_name")
                    if role == "PRIMARY" and d.get("is_primary_replica"):
                        primary_commit[db] = ts
                    elif role == "SECONDARY":
                        secondary_commit[(r.get("replica_server_name"), db)] = ts
            for (_replica, db), sec_ts in secondary_commit.items():
                pri_ts = primary_commit.get(db)
                if pri_ts is None:
                    continue
                lag = (pri_ts - sec_ts).total_seconds()
                if lag < 0:
                    lag = 0
                if max_lag is None or lag > max_lag:
                    max_lag = lag
        return None if max_lag is None else round(max_lag, 1)


def _empty_summary(reason: str) -> Dict:
    """空 summary 模板。

    功能：用于"未发现同步关系"等场景，让顶层结构始终满足 serializer。
    输入：reason —— 给到 summary.reason，便于 LLM 直接复述原因
    输出：summary dict
    边界：overall_health 固定 "N/A"；不与正常分支的判定混淆。
    """
    return {
        "overall_health": "N/A",
        "node_count": None,
        "unhealthy_database_count": 0,
        "database_count": 0,
        "max_log_send_queue_mb": 0,
        "max_redo_queue_mb": 0,
        "max_commit_lag_seconds": None,
        "issues": [],
        "reason": reason,
    }


class DatabaseFilter:
    """数据库白名单过滤器。

    用途
        - 解析用户传入的 `databases` 入参，规范化为不区分大小写的小写集合；
        - 对 mirroring / always_on 装配后的 `databases` 列表做白名单过滤；
        - 同步生成 filter 回显（requested / matched / missing），便于 LLM 知道
          "用户问的库哪些存在、哪些不在集群里"。
    输入
        databases: 来自入参的原始字符串列表（可能为 None / 空 list / 含空白）
    输出
        - is_active(): bool，是否启用过滤
        - apply(rows, key="database_name"): 过滤后的子列表（保留原顺序）
        - record_matched(name): 把命中的真实库名记录到 matched
        - to_filter_info(): dict，对应 SQLServerSyncStatusOutputSerializer.filter
    边界
        - 不区分大小写：matched/missing 比较时统一小写；
        - matched 保留集群侧返回的原始大小写（首次出现为准），便于 LLM 复述；
        - 用户重复传同一个库名（大小写不同）会被去重；
        - 当 is_active() 为 False 时 apply 直接原样返回，filter 字段输出 null。
    """

    def __init__(self, databases: Optional[List[str]]):
        self._raw: List[str] = [d.strip() for d in (databases or []) if d and d.strip()]
        # 去重并保留首次出现顺序
        seen = set()
        self._requested_lower: List[str] = []
        for name in self._raw:
            low = name.lower()
            if low in seen:
                continue
            seen.add(low)
            self._requested_lower.append(low)
        self._whitelist = set(self._requested_lower)
        # 命中过的真实库名（保留集群侧大小写）
        self._matched_actual: Dict[str, str] = {}

    def is_active(self) -> bool:
        """是否启用过滤；False 表示用户未指定白名单，全量返回。"""
        return bool(self._whitelist)

    def hit(self, name: Optional[str]) -> bool:
        """判断单个库名是否命中白名单。

        功能：底层匹配工具，过滤未启用时统一返回 True（全放行）。
        输入：单个库名（可能为 None）
        输出：bool
        边界：name 为 None / 空字符串时，未启用过滤返回 True；启用过滤返回 False。
        """
        if not self.is_active():
            return True
        if not name:
            return False
        low = name.lower()
        if low in self._whitelist:
            self._matched_actual.setdefault(low, name)
            return True
        return False

    def apply(self, rows: List[Dict], key: str = "database_name") -> List[Dict]:
        """对一批 dict 行做白名单过滤。

        功能：在 assemble 之后过滤 mirroring.databases / replicas[].databases。
        输入：rows + key（默认 "database_name"）
        输出：过滤后的子列表（保留原顺序）；过滤未启用时直接返回原列表。
        边界：行内 key 缺失或为 None 时视为未命中。
        """
        if not self.is_active():
            return rows
        return [r for r in rows if self.hit(r.get(key))]

    def to_filter_info(self) -> Optional[Dict]:
        """生成对外的 filter 回显信息。

        功能：让 LLM 看到"requested vs matched vs missing"。
        输入：无
        输出：dict 或 None（未启用过滤时返回 None）
        边界：missing 顺序与 requested 一致，便于人工对照。
        """
        if not self.is_active():
            return None
        matched_lower = set(self._matched_actual.keys())
        return {
            "requested": list(self._requested_lower),
            "matched": [self._matched_actual[low] for low in self._requested_lower if low in matched_lower],
            "missing": [low for low in self._requested_lower if low not in matched_lower],
        }


class SyncStatusAnalyzer:
    """顶层编排：识别集群同步模式并分发到对应子分析器。

    用途
        - 读 db_meta 获取 cluster_type / sync_mode；
        - 单节点 / 没有 sync_mode 记录 / 未知 sync_mode 走快速失败或空响应；
        - HA 集群按 sync_mode 选 MirroringAnalyzer 或 AlwaysOnAnalyzer。
    输入
        - cluster_domain: 集群不可变域名；
        - databases: 可选，库名白名单（不区分大小写）；不传 / 空列表表示全量返回，
          传入后 mirroring / always_on 详细数据中仅保留命中的库，summary 也会
          基于过滤后的子集重算。
    输出
        通过 `analyze()` 返回 dict，结构对应 SQLServerSyncStatusOutputSerializer。
    边界
        - 单节点集群：直接返回 sync_mode=None / summary=N/A 的空响应，不抛异常；
        - HA 但缺 SqlserverClusterSyncMode 记录：抛 DBMMcpBaseException（视为元数据异常）；
        - 未知 sync_mode：抛 DBMMcpBaseException（防止静默漏处理新增模式）；
        - 当用户传入了白名单但全部未命中时，summary.reason 会写明，filter 字段
          回显 requested / matched / missing 三项，便于 LLM 复述"哪些库不存在"。
    """

    def __init__(self, cluster_domain: str, databases: Optional[List[str]] = None):
        self._cluster_domain = cluster_domain
        self._db_filter = DatabaseFilter(databases)

    def analyze(self) -> Dict:
        """执行顶层分发。

        功能：本类唯一对外方法。
        输入：使用构造参数 cluster_domain / databases（库名白名单）。
        输出：完整的同步状态分析结果 dict（详见类 docstring）。
        边界：见类 docstring 中的三条快速失败路径。
        """
        cluster = Cluster.objects.get(immute_domain=self._cluster_domain)

        if cluster.cluster_type == ClusterType.SqlserverSingle:
            return self._build_standalone_response(cluster)

        sync_mode = self._resolve_sync_mode(cluster.id)
        bk_cloud_id, instances = resolve_sqlserver_addresses(
            cluster_domain=self._cluster_domain, address=None, default_role="all"
        )

        if sync_mode == SqlserverSyncMode.MIRRORING:
            data, results, summary = MirroringAnalyzer(bk_cloud_id, instances).analyze(db_filter=self._db_filter)
            return self._build_response(cluster, sync_mode, summary, mirroring=data, always_on=None, results=results)

        if sync_mode == SqlserverSyncMode.ALWAYS_ON:
            data, results, summary = AlwaysOnAnalyzer(bk_cloud_id, instances).analyze(db_filter=self._db_filter)
            return self._build_response(cluster, sync_mode, summary, mirroring=None, always_on=data, results=results)

        raise DBMMcpBaseException(msg=f"unsupported sync_mode: {sync_mode}")

    def _resolve_sync_mode(self, cluster_id: int) -> str:
        """从 db_meta 读取集群的 sync_mode。

        功能：拿到 SqlserverClusterSyncMode.sync_mode 字段值。
        输入：cluster_id
        输出：sync_mode 字符串
        边界：记录不存在时抛 DBMMcpBaseException，由上层转译为前端错误。
        """
        row = SqlserverClusterSyncMode.objects.filter(cluster_id=cluster_id).first()
        if row is None:
            raise DBMMcpBaseException(msg=f"cluster {self._cluster_domain} has no SqlserverClusterSyncMode record")
        return row.sync_mode

    def _build_standalone_response(self, cluster) -> Dict:
        """单节点集群的快速响应。

        功能：在不发起任何 RPC 的情况下返回一个完整 schema。
        输入：cluster 实例
        输出：dict 同 `analyze` 的输出。
        边界：summary.reason 写明"standalone"，便于 LLM 在结论里直接引用。
        """
        return {
            "cluster_domain": self._cluster_domain,
            "cluster_type": cluster.cluster_type,
            "sync_mode": None,
            "summary": _empty_summary(reason="standalone cluster, no sync relationship"),
            "mirroring": None,
            "always_on": None,
            "results": [],
            "filter": self._db_filter.to_filter_info(),
        }

    def _build_response(
        self,
        cluster,
        sync_mode: str,
        summary: Dict,
        *,
        mirroring: Optional[Dict],
        always_on: Optional[Dict],
        results: List[Dict],
    ) -> Dict:
        """生成 HA 集群的最终响应。

        功能：把子分析器的输出拼装成顶层 dict。
        输入：cluster / sync_mode / summary / mirroring / always_on / results
        输出：dict 同 `analyze` 的输出。
        边界：mirroring 与 always_on 在调用点保证互斥，本方法不再校验。
        """
        return {
            "cluster_domain": self._cluster_domain,
            "cluster_type": cluster.cluster_type,
            "sync_mode": sync_mode,
            "summary": summary,
            "mirroring": mirroring,
            "always_on": always_on,
            "results": results,
            "filter": self._db_filter.to_filter_info(),
        }


def sqlserver_sync_status(cluster_domain: str, databases: Optional[List[str]] = None) -> Dict:
    """对外薄壳函数（保持原有 import 兼容）。

    功能：MCP 工具 `sqlserver_sync_status` 的真实入口。
    输入：
        - cluster_domain: 集群不可变域名
        - databases: 可选，库名白名单（不区分大小写）；不传 / 空列表表示全量返回
    输出：dict，结构详见 SQLServerSyncStatusOutputSerializer
    边界：本函数仅做一次 SyncStatusAnalyzer 的实例化与转发，所有业务/异常逻辑在类里。
    """
    return SyncStatusAnalyzer(cluster_domain=cluster_domain, databases=databases).analyze()
