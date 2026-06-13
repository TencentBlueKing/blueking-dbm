"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import copy
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.db_report.models.sqlserver_full_backup_result import SQLServerBackupResult
from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult
from backend.flow.consts import SQLSERVER_CUSTOM_SYS_DB

logger = logging.getLogger("root")

# backup_id 合法格式白名单：
#   1) 32 位无连字符的十六进制串（uuid.uuid1().hex / 备份 actuator 生成的随机 hex）
#   2) 36 位标准 GUID（8-4-4-4-12，含连字符，str(uuid.uuid1()) 形态）
# 仅允许 [0-9a-fA-F-]，从根源上隔离单引号/分号/空格/注释符等 SQL 注入危险字符。
_BACKUP_ID_PATTERN = re.compile(
    r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)


def _validate_backup_id(backup_id: str) -> str:
    """
    校验 backup_id 是否符合白名单格式（32 位 hex 或 36 位 GUID）。

    @param backup_id: 待校验的 backup_id
    @return: 原始 backup_id（校验通过时原样返回，便于链式赋值）
    @raises ValueError: 格式非法
    """
    if not isinstance(backup_id, str) or not _BACKUP_ID_PATTERN.match(backup_id):
        raise ValueError(
            f"invalid backup_id format: {backup_id!r}, "
            f"expected 32-hex or 8-4-4-4-12 GUID (only [0-9a-fA-F-] allowed)"
        )
    return backup_id


# 修复结果分类
class RepairCase:
    OK = "OK"  # report 与 BACKUP_TRACE 一致，无需修复（理论上不会进修复入口，留作 dry-run 兜底）
    REPAIRED = "REPAIRED"  # 已成功补录
    DB_SIDE_MISSING = "DB_SIDE_MISSING"  # BACKUP_TRACE 也没有（DB 端真缺）
    DATA_POLLUTION = "DATA_POLLUTION"  # report 中存在 BACKUP_TRACE 不存在的 dbname
    PARTIAL = "PARTIAL"  # report ⊄ trace 且 trace ⊄ report，互有差集
    LOG_REPAIR_FUSED = "LOG_REPAIR_FUSED"  # log 单次缺失数量超过阈值，熔断
    MSDB_LSN_MISSING = "MSDB_LSN_MISSING"  # 关联到了行但 LSN 为空
    DRS_ERROR = "DRS_ERROR"  # 远端查询异常


# log 备份单次熔断阈值（单 backup_id 一次可补录的 missing 上限）
LOG_REPAIR_MAX_MISSING = 1000


class RepairBackupRecords(object):
    """
    备份记录修复器（基于 backup_id 做单条修复）

    功能：
        - 对比 report 表 与 远端 BACKUP_TRACE+msdb 的 dbname 集合差异
        - trace ⊃ report 时把缺失 dbname 补录进 report
        - 其他差异形态归类为不可自动修复 case，仅返回诊断信息

    使用方式：
        repairer = RepairBackupRecords(cluster_id=xx, backup_id="xxx", backup_type="log", dry_run=True)
        case, info = repairer.repair()
    """

    def __init__(
        self,
        cluster_id: int,
        backup_id: str,
        backup_type: str,
        dry_run: bool = True,
    ):
        """
        初始化修复器，加载 cluster 元数据但不发起任何远端/DB 查询。

        @param cluster_id: 集群 id
        @param backup_id:  出问题的 backup_id（DBM 侧 GUID，与 SQLServer msdb 无直接关联）
        @param backup_type: "full" 或 "log"
        @param dry_run:    True 仅诊断不写库；False 真正补录

        Raises:
            ValueError: backup_type 非法 / backup_id 格式非法
            Cluster.DoesNotExist: cluster_id 不存在

        边界:
            - 不在 __init__ 校验 cluster 中是否存在该 backup_id；放到 _load_report_records 之后再判
            - self.backup_address 此时为空，后续在 _resolve_backup_address 中按 真值填充
        """
        if backup_type not in ("full", "log"):
            raise ValueError(f"invalid backup_type: {backup_type}")

        # 白名单校验：拒绝任何含有引号/分号/注释符/空格等 SQL 危险字符的 backup_id，
        # 防止 management command 等用户入口带来的潜在 SQL 注入。
        _validate_backup_id(backup_id)

        self.cluster_id = cluster_id
        self.backup_id = backup_id
        self.backup_type = backup_type
        self.dry_run = dry_run

        self.cluster: Cluster = Cluster.objects.get(id=cluster_id)
        # 注意：备份机不一定是 master，绝对不能拿 master 节点去查 BACKUP_TRACE。
        # 真正的备份机由 report 表里的 backup_host:backup_port（full）/ host:port（log）决定，
        # 在 _load_report_records() 之后从 report 中提取（见 self.backup_address）。
        self.backup_address: str = ""

        # 中间结果（按调用顺序填充，外部不应直接读写）
        self.report_records: List[dict] = []  # report 表中已有的记录（dict 列表）
        self.trace_rows: List[dict] = []  # BACKUP_TRACE + msdb 关联出的远端记录
        self.report_dbnames: Set[str] = set()
        self.trace_dbnames: Set[str] = set()
        self.missing_dbnames: Set[str] = set()  # 待补录的 dbname

    # ==================== 入口 ====================

    def repair(self) -> Tuple[str, dict]:
        """
        修复主入口：加载数据 → 计算差集 → 决策分类 → 执行补录。

        @return: (case, info_dict)
            case: RepairCase 中的某个常量字符串
            info_dict: 见 _info()，包含 report/trace/missing dbname、补录条数、原因等

        边界/异常:
            - 任何阶段抛错都被捕获并归类为 DRS_ERROR 返回，不向上抛
            - log 类型一次缺失超过 LOG_REPAIR_MAX_MISSING 时熔断，避免误补海量脏数据
        """
        # 1. 查 report 表当前已有的 dbname 列表
        self._load_report_records()

        # 1.1 从 report 记录中提取出真正的备份机地址（一个 backup_id 理论上只对应一台备份机）
        try:
            self._resolve_backup_address()
        except Exception as err:
            logger.exception("[repair] resolve backup address failed: %s", err)
            return RepairCase.DRS_ERROR, self._info(reason=str(err))

        # 2. 查远端 BACKUP_TRACE + msdb 关联结果
        try:
            self._load_trace_rows()
        except Exception as err:
            logger.exception("[repair] load trace rows failed: %s", err)
            return RepairCase.DRS_ERROR, self._info(reason=str(err))

        # 3. 计算差集 + 决策
        self.report_dbnames = {r["dbname"] for r in self.report_records}
        self.trace_dbnames = {r["DBNAME"] for r in self.trace_rows}

        # 3.1 完全一致：DB 端真缺
        if self.report_dbnames == self.trace_dbnames:
            return RepairCase.DB_SIDE_MISSING, self._info(reason="report == trace, db side really missing")

        # 3.2 report 多于 trace（脏数据，不修）
        report_only = self.report_dbnames - self.trace_dbnames
        trace_only = self.trace_dbnames - self.report_dbnames

        if report_only and not trace_only:
            return RepairCase.DATA_POLLUTION, self._info(
                reason=f"report has dbnames not in trace: {sorted(report_only)}"
            )

        if report_only and trace_only:
            return RepairCase.PARTIAL, self._info(
                reason=f"report_only={sorted(report_only)}, trace_only={sorted(trace_only)}"
            )

        # 3.3 trace ⊃ report：可补录
        self.missing_dbnames = trace_only

        # log 类型熔断
        if self.backup_type == "log" and len(self.missing_dbnames) > LOG_REPAIR_MAX_MISSING:
            return RepairCase.LOG_REPAIR_FUSED, self._info(
                reason=f"log missing {len(self.missing_dbnames)} > {LOG_REPAIR_MAX_MISSING}"
            )

        # 4. 执行补录
        repaired_count = self._do_repair()
        return RepairCase.REPAIRED, self._info(repaired_count=repaired_count)

    # ==================== 步骤 1: 加载 report 已有记录 ====================

    def _load_report_records(self):
        """
        从 report 表加载当前 cluster + backup_id 下已存在的所有记录。

        @input:  无（依赖 self.cluster_id / self.backup_id / self.backup_type）
        @output: 写入 self.report_records: List[dict]（可能为空）

        边界:
            - 空列表是合法状态，由 _resolve_backup_address / _do_repair 各自再做兜底
            - 使用 .values() 拿 dict 是为了后续 _build_new_record 里 deepcopy 当模板
        """
        if self.backup_type == "full":
            qs = SQLServerBackupResult.objects.filter(cluster_id=self.cluster_id, backup_id=self.backup_id).values()
        else:
            qs = SQLServerBinlogResult.objects.filter(cluster_id=self.cluster_id, backup_id=self.backup_id).values()
        self.report_records = list(qs)

    # ==================== 步骤 1.1: 从 report 中提取真正的备份机 ====================

    def _resolve_backup_address(self):
        """
        从已加载的 report 记录中解析出真正执行备份的机器地址 (host:port)。

        @input:  无（依赖 self.report_records / self.backup_type）
        @output: 写入 self.backup_address: str，形如 "1.2.3.4:48352"

        @raises Exception:
            - report_records 为空，无法推导地址
            - report_records 字段缺失 host/port

        边界:
            - full 表字段:  backup_host / backup_port
            - log  表字段:  host / port
            - 一个 backup_id 在一个集群内理论上只来自唯一一台备份机；若出现多组 (host, port)，
              视为脏数据，仅记 warning，仍以 report_records[0] 为准（避免修复器过度脆弱）
        """
        if not self.report_records:
            # 没有任何 report 记录时，无法推导备份机地址，
            # 与 _do_repair 中 "无模板可参考" 的兜底语义一致，直接抛异常上层会归类为 DRS_ERROR。
            raise Exception(
                f"backup_id={self.backup_id} has zero record in report, " f"cannot infer backup_host/backup_port"
            )

        if self.backup_type == "full":
            host_field, port_field = "backup_host", "backup_port"
        else:
            host_field, port_field = "host", "port"

        addr_set = {
            f"{r[host_field]}:{r[port_field]}" for r in self.report_records if r.get(host_field) and r.get(port_field)
        }
        if not addr_set:
            raise Exception(f"backup_id={self.backup_id} report records missing {host_field}/{port_field}")
        if len(addr_set) > 1:
            logger.warning(
                "[repair] backup_id=%s found multiple backup addresses in report: %s, use the first one",
                self.backup_id,
                sorted(addr_set),
            )

        # 选第一条 report 记录的地址（多数情况下整组只有一个）
        first = self.report_records[0]
        self.backup_address = f"{first[host_field]}:{first[port_field]}"
        logger.info(
            "[repair] backup_id=%s resolved backup_address=%s",
            self.backup_id,
            self.backup_address,
        )

    # ==================== 步骤 2: 远端查 BACKUP_TRACE + msdb ====================

    def _load_trace_rows(self):
        """
        通过 DRS 在备份机上查询 BACKUP_TRACE 与 msdb.backupset 的关联结果。

        @input:  无（依赖 self.backup_id / self.backup_address / self.cluster.bk_cloud_id）
        @output: 写入 self.trace_rows: List[dict]（可能为空 list）

        @raises Exception: DRS 调用失败 / 返回 error_msg 非空

        关联规则:
            BACKUP_TRACE.PATH+FILENAME == msdb.backupmediafamily.physical_device_name
            额外按 bs.database_name = bt.DBNAME 二次约束，避免一份 backupmediafamily
            被多个 backupset 关联（同一文件被多次写入时 msdb 会有多行）

        边界:
            - bt.PATH 通常以反斜杠结尾，physical_device_name 不重复反斜杠，因此用 PATH+FILENAME
              直接拼接而非 PATH+'\\'+FILENAME
            - msdb 内若条目被清理（默认 30 天 retention），LSN 字段会为 None，由调用方按空串保底
            - 这里用 f-string 拼 backup_id 进 SQL：backup_id 已在 __init__ 中通过 _validate_backup_id
              做过白名单校验（仅允许 [0-9a-fA-F-]，且必须匹配 32-hex 或 36-GUID 格式），不存在
              SQL 注入风险；如未来新增非 hex 形态的 backup_id，需同步更新 _BACKUP_ID_PATTERN
              或改用参数化查询
        """
        sql = f"""
SELECT
    bt.BACKUP_ID, bt.DBNAME, bt.[FILENAME],
    bmf.physical_device_name,
    bs.type AS backup_type_code,
    CAST(bs.first_lsn           AS VARCHAR(30)) AS first_lsn,
    CAST(bs.last_lsn            AS VARCHAR(30)) AS last_lsn,
    CAST(bs.checkpoint_lsn      AS VARCHAR(30)) AS checkpoint_lsn,
    CAST(bs.database_backup_lsn AS VARCHAR(30)) AS database_backup_lsn,
    bs.backup_start_date, bs.backup_finish_date,
    bs.compatibility_level,
    bs.backup_size, bs.compressed_backup_size
FROM [{SQLSERVER_CUSTOM_SYS_DB}].[dbo].[BACKUP_TRACE](NOLOCK) bt
LEFT JOIN msdb.dbo.backupmediafamily(NOLOCK) bmf
       ON bmf.physical_device_name = bt.PATH + bt.[FILENAME]
LEFT JOIN msdb.dbo.backupset(NOLOCK) bs
       ON bs.media_set_id = bmf.media_set_id
      AND bs.database_name = bt.DBNAME
WHERE bt.BACKUP_ID = '{self.backup_id}'
ORDER BY bt.DBNAME;
""".strip()

        ret = DRSApi.sqlserver_rpc(
            {
                "bk_cloud_id": self.cluster.bk_cloud_id,
                "addresses": [self.backup_address],
                "cmds": [sql],
                "force": False,
            }
        )
        if ret[0]["error_msg"]:
            raise Exception(f"[{self.backup_address}] query trace failed: {ret[0]['error_msg']}")

        self.trace_rows = ret[0]["cmd_results"][0]["table_data"] or []

    # ==================== 步骤 4: 执行补录 ====================
    def _do_repair(self) -> int:
        """
        把 self.missing_dbnames 中的每个 dbname 以一条记录形式补录进 report 表。

        @input:  无（依赖 self.report_records / self.trace_rows / self.missing_dbnames / self.dry_run）
        @output: int，本次补录成功的条数（dry_run 模式下也按"假装成功"计数）

        @raises Exception: report_records 为空（无模板可参考）

        边界:
            - 单条 ORM create 失败时仅记日志、不阻塞剩余 dbname；transaction.atomic 包裹
              意味着任意一条失败抛出会回滚整批 —— 这里我们用 try/except 吞掉单条异常以保证
              "尽力补录"，请知悉：dry_run=False 模式下若有单条 fail，本批前面成功的 create
              依然会随事务整体提交（因 except 不重新抛出）
            - dry_run=True 时不调用 ORM，仅打印日志，repaired 计数仍递增以反馈"将会补录的条数"
        """
        if not self.report_records:
            # 极端情况：report 一条都没有，无法取到 cluster_domain/host/port 等模板字段
            # 这种已经不属于"巡检数量不一致"场景（属于 _check_backup_info_from_model 的 "找不到任何记录"）
            # 修复器谨慎起见拒绝处理
            raise Exception(
                f"backup_id={self.backup_id} has zero record in report, cannot infer template, refuse to repair"
            )

        template = self.report_records[0]
        # 把 trace_rows 按 dbname 索引
        trace_by_db: Dict[str, dict] = {r["DBNAME"]: r for r in self.trace_rows}

        repaired = 0
        for dbname in sorted(self.missing_dbnames):
            trace_row = trace_by_db[dbname]
            new_record = self._build_new_record(template, dbname, trace_row)

            if self.dry_run:
                logger.info("[repair][dry-run] would insert: %s", new_record)
                repaired += 1
                continue

            try:
                if self.backup_type == "full":
                    SQLServerBackupResult.objects.create(**new_record)
                else:
                    SQLServerBinlogResult.objects.create(**new_record)
                repaired += 1
            except Exception as err:
                # 单条失败不阻塞其他 dbname 的补录
                logger.error("[repair] insert dbname=%s failed: %s", dbname, err)

        return repaired

    def _build_new_record(self, template: dict, dbname: str, trace_row: dict) -> dict:
        """
        基于已有 report 记录（模板）+ 远端 trace_row 拼装一条待写入的新记录 dict。

        @param template:  同 backup_id 的任意一条 report 记录（提供 cluster_domain/host/port/role 等共性字段）
        @param dbname:    本次要补录的 db 名
        @param trace_row: BACKUP_TRACE + msdb 关联结果的一行（提供 file_name / 4 个 LSN / size 等真值）
        @return:          dict，可直接用于 SQLServerBackupResult/BinlogResult 的 .objects.create(**ret)

        覆盖策略:
            - 主键/时间戳: 移除 id / created_at / updated_at，让 ORM 重新生成
            - 共性字段:    继承 template
            - 差异字段:    dbname / file_name / 4 个 LSN 用 trace_row 真值
            - is_repaired: 强制 True，便于后续统计自动修复命中率与告警时区分

        边界:
            - msdb 关联不到的 LSN 字段会是 None，统一用空串保底（与模型 default="" 对齐）
            - trace_row.backup_size 单位是 byte，模型里 file_size_kb / size 单位是 KB，需 //1024
            - log 表没有 compatibility_level / file_size_kb 字段，仅写 size
            - file_cnt / task_id 等保留模板值不动；巡检 file_cnt 异常正是要修复的对象，
              这里若覆盖反而会污染原始巡检证据
        """
        new_record = copy.deepcopy(template)
        # 移除主键和 ORM 自动管理字段
        new_record.pop("id", None)
        new_record.pop("created_at", None)
        new_record.pop("updated_at", None)

        # 通用覆盖
        new_record["dbname"] = dbname
        new_record["file_name"] = trace_row.get("FILENAME") or new_record.get("file_name", "")
        new_record["is_repaired"] = True

        # LSN 覆盖（msdb 关联不到时可能为 None，按空串保底）
        new_record["first_lsn"] = trace_row.get("first_lsn") or ""
        new_record["last_lsn"] = trace_row.get("last_lsn") or ""
        new_record["checkpoint_lsn"] = trace_row.get("checkpoint_lsn") or ""
        new_record["database_backup_lsn"] = trace_row.get("database_backup_lsn") or ""

        # full 备份独有字段补充
        if self.backup_type == "full":
            if trace_row.get("compatibility_level"):
                new_record["compatibility_level"] = trace_row["compatibility_level"]
            if trace_row.get("backup_size"):
                # backup_size 单位 byte，模板里 file_size_kb 单位 KB
                new_record["file_size_kb"] = int(trace_row["backup_size"]) // 1024
            # task_id / file_cnt 等保留模板值（巡检 file_cnt 异常正是要修复的，这里不动）

        # log 备份独有字段补充
        if self.backup_type == "log":
            if trace_row.get("backup_size"):
                new_record["size"] = int(trace_row["backup_size"]) // 1024
            # backup_status / backup_status_info / file_cnt / task_id 全部沿用模板

        return new_record

    # ==================== 工具 ====================

    def _info(self, reason: Optional[str] = None, repaired_count: int = 0) -> dict:
        """
        汇总本次修复的诊断信息，统一作为 repair() 的第二个返回值。

        @param reason:         本次 case 的解释（DB 端真缺 / 脏数据 / 熔断 / 异常 …）
        @param repaired_count: 本次实际/dry-run 补录条数
        @return: dict（字段固定，便于上层 management command 直接 dump 成日志或告警）
        """
        return {
            "cluster_id": self.cluster_id,
            "cluster_domain": self.cluster.immute_domain,
            "backup_id": self.backup_id,
            "backup_type": self.backup_type,
            "dry_run": self.dry_run,
            "backup_address": self.backup_address,
            "report_dbnames": sorted(self.report_dbnames),
            "trace_dbnames": sorted(self.trace_dbnames),
            "missing_dbnames": sorted(self.missing_dbnames),
            "repaired_count": repaired_count,
            "reason": reason or "",
        }


# ==================== 批量入口（便于 management command 调用）====================


def repair_one(cluster_id: int, backup_id: str, backup_type: str, dry_run: bool = True) -> Tuple[str, dict]:
    """单 backup_id 修复"""
    return RepairBackupRecords(
        cluster_id=cluster_id,
        backup_id=backup_id,
        backup_type=backup_type,
        dry_run=dry_run,
    ).repair()


def repair_by_cluster(
    cluster_id: int, backup_type: str, dry_run: bool = True, since_days: int = 1
) -> List[Tuple[str, str, dict]]:
    """
    扫描 cluster 最近 since_days 天内的 backup_id，逐个调用 repair_one
    返回 [(backup_id, case, info), ...]
    """
    from datetime import timedelta

    from django.utils import timezone

    end_time = timezone.now()
    start_time = end_time - timedelta(days=since_days)

    if backup_type == "full":
        qs = (
            SQLServerBackupResult.objects.filter(
                cluster_id=cluster_id,
                backup_end_time__gte=start_time,
                backup_end_time__lte=end_time,
            )
            .values_list("backup_id", flat=True)
            .distinct()
        )
    else:
        qs = (
            SQLServerBinlogResult.objects.filter(
                cluster_id=cluster_id,
                backup_end_time__gte=start_time,
                backup_end_time__lte=end_time,
            )
            .values_list("backup_id", flat=True)
            .distinct()
        )

    results = []
    for backup_id in qs:
        try:
            case, info = repair_one(cluster_id, backup_id, backup_type, dry_run=dry_run)
        except Exception as err:
            logger.exception("[repair] backup_id=%s exception: %s", backup_id, err)
            case, info = RepairCase.DRS_ERROR, {"backup_id": backup_id, "reason": str(err)}
        results.append((backup_id, case, info))
    return results
