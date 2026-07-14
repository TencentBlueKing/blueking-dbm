# -*- coding: utf-8 -*-
"""
SQLServer 日志备份链探针脚本（真实 DB，无 mock）。

用途：
    以真实 DB 数据驱动 LogBackupChainInspector，暴露：
      - 头部+中间段 / 尾部段 各自查到什么记录
      - 相邻两份的 LSN 衔接情况（哪一处断档）
      - inspect() 最终返回的 status / gaps / error_message
    帮助定位"提交时 validator 未拦、flow 执行期才报"的真实根因。

运行方式：
    在 dbm-ui 容器/环境内执行：
        python manage.py shell < scripts/probe_log_backup_chain.py

    执行前请按需修改文件底部 CASE 常量：
      - CASE_CLUSTER_ID：源集群 ID
      - CASE_DB_NAME：业务库名
      - CASE_RESTORE_TIME：目标构造时点（str，与单据 restore_time 一致）
      - CASE_FULL_END_TIME / CASE_FULL_LAST_LSN / CASE_FULL_FILE_NAME：
        全量备份对应字段（可从 restore_backup_file.logs 里对应 dbname 那条取）
"""

from datetime import datetime

from backend.db_meta.models import Cluster
from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult
from backend.db_services.sqlserver.rollback.log_backup_chain import LogBackupChainInspector
from backend.utils.time import str2datetime


# =============================================================================
# ⚠️ 运行前请按实际单据修改以下常量
# =============================================================================
# 源集群 ID
CASE_CLUSTER_ID: int = 32
# 业务库名（rename_infos 里的 db_name）
CASE_DB_NAME: str = "abcde111113333"
# 目标构造时点（带时区更稳；无时区也可）—— 与本次单据一致
CASE_RESTORE_TIME: str = "2026-07-18T01:05:11+08:00"
# 全量备份关键字段（来自 restore_backup_file.logs 对应 dbname 的那条）—— 与本次单据一致
CASE_FULL_END_TIME: str = "2026-07-17T03:26:05+08:00"
CASE_FULL_LAST_LSN: str = "35000008257100001"
CASE_FULL_FILE_NAME: str = "full.bak"


def _print_header(title: str) -> None:
    """打印分隔标题，便于阅读输出。

    :param title: 段落标题
    :return: None
    """
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _dump_rows(rows: list, label: str) -> None:
    """打印一组日志备份记录的关键字段。

    :param rows: 记录列表（dict 或 QuerySet.values() 结果）
    :param label: 输出标签
    :return: None
    """
    print("{label} 共 {n} 条：".format(label=label, n=len(rows)))
    for i, r in enumerate(rows, 1):
        print(
            "  [{i:>2}] end={end} first_lsn={fl} last_lsn={ll} file={f}".format(
                i=i,
                end=r.get("backup_end_time"),
                fl=r.get("first_lsn"),
                ll=r.get("last_lsn"),
                f=r.get("file_name"),
            )
        )


def _check_lsn_chain(rows: list) -> None:
    """按时间序两两比对相邻两份 last_lsn / first_lsn，逐行标注是否衔接。

    :param rows: 按 backup_end_time 升序的记录列表
    :return: None
    """
    print("LSN 衔接检查（相邻两份 prev.last_lsn == cur.first_lsn？）：")
    prev = None
    for i, r in enumerate(rows, 1):
        if prev is None:
            prev = r
            continue
        prev_last = str(prev.get("last_lsn"))
        cur_first = str(r.get("first_lsn"))
        ok = prev_last == cur_first
        mark = "OK " if ok else "❌ GAP"
        print(
            "  [{a}->{b}] {mark}  prev.last={pl} vs cur.first={cf}  ({pf} -> {cf_file})".format(
                a=i - 1,
                b=i,
                mark=mark,
                pl=prev_last,
                cf=cur_first,
                pf=prev.get("file_name"),
                cf_file=r.get("file_name"),
            )
        )
        prev = r


def probe() -> None:
    """真实 DB 探针主流程：暴露查询与判定的中间态。"""

    _print_header("[0] 探针参数")
    print("cluster_id      = {v}".format(v=CASE_CLUSTER_ID))
    print("db_name         = {v}".format(v=CASE_DB_NAME))
    print("restore_time    = {v}".format(v=CASE_RESTORE_TIME))
    print("full_end_time   = {v}".format(v=CASE_FULL_END_TIME))
    print("full_last_lsn   = {v}".format(v=CASE_FULL_LAST_LSN))

    restore_time: datetime = str2datetime(CASE_RESTORE_TIME)
    full_end_time: datetime = str2datetime(CASE_FULL_END_TIME)

    # 1) 原始 DB 数据：全量结束到 restore_time 之间所有日志记录（不去重，方便看全貌）
    _print_header("[1] 原始 DB 数据（full_end_time <= backup_end_time <= restore_time）")
    raw_head_middle = list(
        SQLServerBinlogResult.objects.filter(
            cluster_id=CASE_CLUSTER_ID,
            dbname=CASE_DB_NAME,
            backup_end_time__gte=full_end_time,
            backup_end_time__lte=restore_time,
        )
        .order_by("backup_end_time")
        .values()
    )
    _dump_rows(raw_head_middle, "head_middle 原始")
    _check_lsn_chain(raw_head_middle)

    # 2) 原始 DB 数据：restore_time 之后首个 backup_end_time 的记录（tail 候选）
    _print_header("[2] 原始 DB 数据（backup_end_time > restore_time，取首个）")
    raw_tail = (
        SQLServerBinlogResult.objects.filter(
            cluster_id=CASE_CLUSTER_ID,
            dbname=CASE_DB_NAME,
            backup_end_time__gt=restore_time,
        )
        .order_by("backup_end_time")
        .values()
        .first()
    )
    if raw_tail:
        _dump_rows([raw_tail], "tail 候选")
    else:
        print("tail 候选：**None**（restore_time 晚于最新备份 end_time）")

    # 3) 让 Inspector 完整跑一次 inspect()，看看真实产出
    _print_header("[3] Inspector.inspect() 完整判定")
    cluster = Cluster.objects.get(id=CASE_CLUSTER_ID)
    full_backup_info = {
        "db_name": CASE_DB_NAME,
        "backup_full_end_time": CASE_FULL_END_TIME,
        "cluster_address": cluster.immute_domain,
        "full_last_lsn": CASE_FULL_LAST_LSN,
        "full_file_name": CASE_FULL_FILE_NAME,
    }
    inspector = LogBackupChainInspector(
        cluster=cluster,
        full_backup_info=full_backup_info,
        restore_time=restore_time,
    )
    result = inspector.inspect()
    print("status         = {v}".format(v=result.status))
    print("db_name        = {v}".format(v=result.db_name))
    print("gaps           = {v}".format(v=result.gaps))
    print("backup_infos 数= {v}".format(v=len(result.backup_infos)))
    if result.error_message:
        print("error_message:\n{v}".format(v=result.error_message))

    _print_header("[4] 判断建议")
    if not raw_head_middle:
        print("→ head_middle 原始为空：可能 full_end_time 太晚 / dbname 不匹配 / 日志未上报")
    else:
        gaps_in_raw = 0
        prev = None
        for r in raw_head_middle:
            if prev is not None and str(prev["last_lsn"]) != str(r["first_lsn"]):
                gaps_in_raw += 1
            prev = r
        print("→ head_middle 原始序列 LSN 断档处数：{n}".format(n=gaps_in_raw))
        if gaps_in_raw > 0 and result.status == "ok":
            print("→ ⚠️ 明显异常：原始序列有断档但 inspect() 返回 OK，请贴出 [1]/[3] 输出定位")
        elif gaps_in_raw == 0 and result.status != "ok":
            print("→ ⚠️ 明显异常：原始序列无断档但 inspect() 非 OK，请贴出 [1]/[3] 输出定位")
        else:
            print("→ 原始序列与 inspect() 结论一致")


probe()