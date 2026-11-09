# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
import logging
import time
from collections import defaultdict
from datetime import date, datetime
from datetime import time as dt_time
from datetime import timedelta
from datetime import timezone as dt_timezone
from typing import Dict, List, Optional, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api, DBConfigApi
from backend.components.dbconfig.constants import LevelName
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.kafka_check.disk_growth_analysis import KafkaDiskGrowthAnalysisTask
from backend.db_periodic_task.local_tasks.kafka_check.disk_growth_coverage import assess_day, is_valid_value
from backend.db_periodic_task.local_tasks.kafka_check.disk_growth_rule import (
    HISTORY_WINDOW_DAYS,
    REQUIRED_HISTORY_DAYS,
    GrowthHit,
    evaluate,
)
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.kafka_disk_growth_sub_type import KafkaDiskGrowthAiStatus, KafkaDiskGrowthRunKind
from backend.db_report.models import KafkaDiskGrowthReport
from backend.flow.consts import ConfigTypeEnum, NameSpaceEnum

logger = logging.getLogger("celery")

# 每批向监控查询的集群数。一个集群通常有 3~10 台 broker，批太大会撞上 slimit 被截断
QUERY_BATCH_SIZE = 50
# 批与批之间的间隔，监控 API 有限流（并发查询会触发 429），所以全部串行
QUERY_INTERVAL_SECONDS = 1
# 查询步长：每小时取一个值，再在本地按自然日求峰值
STEP_SECONDS = 3600
SERIES_LIMIT = UNIFY_QUERY_PARAMS["slimit"]

REPORT_KEEP_DAYS = 60
# AI 分析超过这个时长还没有结果，视为失败
PENDING_AI_EXPIRE_HOURS = 36

RETENTION_CONF_NAME = "retention_hours"
RETENTION_BATCH_SIZE = 20

# 与 db_monitor/constants.py 里 Kafka 的容量口径一致：只看 broker 的数据盘。PromQL 的 =~ 是全匹配，
# 所以文件系统要写成 ext.?|xfs 才能匹配到 ext4；排除系统盘和 /usr/local
DISK_PEAK_PROMQL = (
    "max by (cluster_domain, bk_target_ip, mount_point) ("
    "max_over_time(bkmonitor:dbm_system:disk:in_use{{"
    'db_type="kafka", instance_role="broker", device_type=~"ext.?|xfs", '
    'mount_point!="/", mount_point!="/usr/local", cluster_domain=~"{domains}"'
    "}}[1h]))"
)

# 覆盖不足的明细最多打印这么多条，其余只计数，避免日志刷屏
COVERAGE_DETAIL_LIMIT = 20

DiskKey = Tuple[str, str, str]


def _local_midnight(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, dt_time.min))


def _resolve_window(run_kind: str, now: datetime) -> Tuple[date, datetime, datetime]:
    """
    返回 (判定日期, 查询起点, 查询终点)。
    早间巡检判定昨天，终点是今天 00:00，不含今天的数据；午后巡检判定今天，终点是当前时刻。
    """
    today = timezone.localtime(now).date()
    if run_kind == KafkaDiskGrowthRunKind.MORNING.value:
        check_day = today - timedelta(days=1)
        end = _local_midnight(today)
    else:
        check_day = today
        end = now
    start = _local_midnight(check_day - timedelta(days=REQUIRED_HISTORY_DAYS))
    return check_day, start, end


def _point_slot(timestamp_ms: float) -> Tuple[date, int]:
    """数据点归属的 (自然日, 小时序号)，序号 h 表示 [h:00, h+1:00) 这个小时窗口。
    每个点是它之前一个步长内的最大值（时间戳为窗口结束时刻），所以整点 00:00 的点属于前一天，这里减 1 秒再取日期
    """
    point_time = timezone.localtime(datetime.fromtimestamp(timestamp_ms / 1000 - 1, tz=dt_timezone.utc))
    return point_time.date(), point_time.hour


def _query_series(domains: List[str], start: datetime, end: datetime) -> List[dict]:
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start.timestamp())
    params["end_time"] = int(end.timestamp())
    params["type"] = "range"
    params["down_sample_range"] = "1h"
    query_config = params["query_configs"][0]
    query_config["interval"] = STEP_SECONDS
    # 蓝鲸监控的正则匹配需要显式加首尾锚点，否则会匹配到更多数据
    query_config["promql"] = DISK_PEAK_PROMQL.format(domains="^(" + "|".join(domains) + ")$")
    return BKMonitorV3Api.unify_query(params, use_admin=True)["series"]


def _collect_series(domains: List[str], start: datetime, end: datetime, stats: dict) -> List[dict]:
    """查询一批集群的序列。结果数达到 slimit 说明被截断了，把这批对半拆开重查"""
    try:
        series = _query_series(domains, start, end)
    except Exception:
        logger.exception("kafka disk growth: query batch failed, domains=%d", len(domains))
        stats["failed_batches"] += 1
        return []
    finally:
        time.sleep(QUERY_INTERVAL_SECONDS)

    if len(series) >= SERIES_LIMIT:
        if len(domains) > 1:
            middle = len(domains) // 2
            return _collect_series(domains[:middle], start, end, stats) + _collect_series(
                domains[middle:], start, end, stats
            )
        logger.warning("kafka disk growth: series truncated for single cluster %s", domains[0])
    return series


def fetch_hourly_peaks(
    domains: List[str], start: datetime, end: datetime, stats: Optional[dict] = None
) -> Dict[DiskKey, Dict[date, Dict[int, float]]]:
    """查询所有集群 [start, end] 内每个 broker 挂载点每个小时的峰值，按 (自然日, 小时) 去重，只保留有效值"""
    stats = stats if stats is not None else {"failed_batches": 0}
    end_timestamp = end.timestamp()
    result: Dict[DiskKey, Dict[date, Dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for offset in range(0, len(domains), QUERY_BATCH_SIZE):
        batch = domains[offset : offset + QUERY_BATCH_SIZE]
        for item in _collect_series(batch, start, end, stats):
            dimensions = item.get("dimensions") or {}
            key = (dimensions.get("cluster_domain"), dimensions.get("bk_target_ip"), dimensions.get("mount_point"))
            if not all(key):
                continue
            days = result[key]
            for value, timestamp_ms in item.get("datapoints") or []:
                if not is_valid_value(value) or timestamp_ms / 1000 > end_timestamp + 1:
                    continue
                day, hour = _point_slot(timestamp_ms)
                hours = days[day]
                if hour not in hours or value > hours[hour]:
                    hours[hour] = value
    return result


def _expected_hours(day: date, end_local: datetime) -> int:
    """day 这天到查询终点为止已经走完的小时窗口数：终点之前的日子是 24，终点当天是已走完的小时数"""
    if day < end_local.date():
        return 24
    if day == end_local.date():
        return end_local.hour
    return 0


def _record_coverage_failure(stats: dict, key: DiskKey, day: date, coverage) -> None:
    stats.setdefault("dropped_days", defaultdict(set))[key].add(day)
    reasons = stats.setdefault("coverage_reasons", defaultdict(int))
    for reason in coverage.reasons:
        reasons[reason] += 1
    details = stats.setdefault("coverage_details", [])
    if len(details) < COVERAGE_DETAIL_LIMIT:
        details.append(
            "domain=%s ip=%s mount=%s day=%s valid=%d expected=%d longest_gap=%d reasons=%s"
            % (*key, day, coverage.valid, coverage.expected, coverage.longest_gap, ",".join(coverage.reasons))
        )


def fetch_daily_peaks(
    domains: List[str], start: datetime, end: datetime, stats: Optional[dict] = None
) -> Dict[DiskKey, Dict[date, float]]:
    """
    查询所有集群 [start, end] 内每个 broker 挂载点的日峰值（东八区自然日）。
    小时点覆盖不足的日子不返回（用残缺数据算的峰值会偏低），并把原因记在 stats 里：
    dropped_days（{挂载点: 被丢弃的日期}）、coverage_reasons、coverage_details。
    """
    stats = stats if stats is not None else {"failed_batches": 0}
    end_local = timezone.localtime(end)
    first_day = timezone.localtime(start).date()
    # 查询范围内所有应检查的日子；终点当天还没走完任何一个小时（expected=0）的不检查
    check_days = [
        first_day + timedelta(days=offset)
        for offset in range((end_local.date() - first_day).days + 1)
        if _expected_hours(first_day + timedelta(days=offset), end_local) > 0
    ]
    result: Dict[DiskKey, Dict[date, float]] = {}
    for key, days in fetch_hourly_peaks(domains, start, end, stats).items():
        day_peaks = result.setdefault(key, {})
        for day in check_days:
            # 整天没有任何有效点的日子不在 days 里，也要当作覆盖不足记录下来
            hours = days.get(day, {})
            coverage = assess_day(hours, _expected_hours(day, end_local), require_last=day == end_local.date())
            if coverage.ok:
                day_peaks[day] = max(hours.values())
            else:
                _record_coverage_failure(stats, key, day, coverage)
    return result


def _batch_query_retention(clusters: List[Cluster]) -> Dict[str, int]:
    """
    批量读取集群级 retention_hours（只读）。取不到不影响巡检，topic 级别的保留期交给 AI 判断。
    注意不能用扩容流程里的 GENERATE_AND_PUBLISH 方式读取，那个会触发配置发布。
    """
    groups: Dict[str, List[Cluster]] = defaultdict(list)
    for cluster in clusters:
        groups[cluster.major_version].append(cluster)

    retention: Dict[str, int] = {}
    for major_version, group in groups.items():
        for offset in range(0, len(group), RETENTION_BATCH_SIZE):
            chunk = group[offset : offset + RETENTION_BATCH_SIZE]
            try:
                data = DBConfigApi.batch_get_conf_item(
                    params={
                        "conf_file": major_version,
                        "conf_name": RETENTION_CONF_NAME,
                        "conf_type": ConfigTypeEnum.DBConf,
                        "level_name": LevelName.CLUSTER,
                        "level_values": [cluster.immute_domain for cluster in chunk],
                        "namespace": NameSpaceEnum.Kafka.value,
                    }
                )
            except Exception:
                logger.warning("kafka disk growth: query retention failed, version=%s", major_version, exc_info=True)
                continue
            content = (data or {}).get("content") or {}
            for cluster in chunk:
                row = content.get(cluster.immute_domain) if isinstance(content, dict) else None
                if not isinstance(row, dict):
                    continue
                try:
                    retention[cluster.immute_domain] = int(row.get(RETENTION_CONF_NAME))
                except (TypeError, ValueError):
                    continue
    return retention


def _previous_failed_days(domains: List[str], check_day: date) -> Dict[DiskKey, int]:
    """
    前一个判定日已经命中的挂载点及其连续命中天数，一次查询取完，避免命中多时逐条查库。
    只有前一天命中过才能接着累加，更早的不算连续，所以只取 check_day - 1 这一天；
    同一天早晚各一行时按 id 取最后一行。
    """
    rows = (
        KafkaDiskGrowthReport.objects.filter(domain__in=domains, check_day=check_day - timedelta(days=1))
        .order_by("id")
        .values_list("domain", "ip", "mount_point", "failed_days")
    )
    return {(domain, ip, mount_point): failed_days for domain, ip, mount_point, failed_days in rows}


def _write_reports(
    hits: List[Tuple[Cluster, str, str, GrowthHit]], check_day: date, run_kind: str
) -> List[KafkaDiskGrowthReport]:
    if not hits:
        return []
    retention = _batch_query_retention(list({cluster.id: cluster for cluster, *_rest in hits}.values()))
    app_names: Dict[int, str] = {}
    dbas: Dict[int, list] = {}
    previous_failed_days = _previous_failed_days(
        sorted({cluster.immute_domain for cluster, *_rest in hits}), check_day
    )

    reports = []
    for cluster, ip, mount_point, hit in hits:
        biz_id = cluster.bk_biz_id
        if biz_id not in app_names:
            app_cache = AppCache.objects.filter(bk_biz_id=biz_id).first()
            app_names[biz_id] = app_cache.db_app_abbr if app_cache else ""
            dbas[biz_id] = DBAdministrator().get_biz_db_type_admins(biz_id, DBType.Kafka)
        msg = _("日峰值 {peak}%，比此前7天最高值高 {excess} 个点，近3天日均涨 {growth} 个点").format(
            peak=hit.peak, excess=hit.excess, growth=hit.daily_growth
        )
        # 同一挂载点、同一判定日、同一时段只保留一行：重跑只刷新判定数据，AI 状态和结论保持原样，
        # 否则 AI 任务去重后，新建的重复行永远收不到回写
        report, _created = KafkaDiskGrowthReport.objects.update_or_create(
            domain=cluster.immute_domain,
            ip=ip,
            mount_point=mount_point,
            check_day=check_day,
            run_kind=run_kind,
            defaults={
                "bk_biz_id": biz_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "state": ReportStateType.WARNING.value,
                "cluster_type": ClusterType.Kafka,
                "msg": msg,
                "app": app_names[biz_id],
                "dba": dbas[biz_id],
                "failed_days": previous_failed_days.get((cluster.immute_domain, ip, mount_point), 0) + 1,
                "rule": hit.rule,
                "peaks": hit.peaks,
                "peak": hit.peak,
                "excess": hit.excess,
                "daily_growth": hit.daily_growth,
                "retention_hours": retention.get(cluster.immute_domain),
            },
        )
        reports.append(report)
    return reports


def _build_analysis_item(cluster: Cluster, rows: List[KafkaDiskGrowthReport], check_day: date, run_kind: str) -> dict:
    return {
        "cluster_id": cluster.id,
        "domain": cluster.immute_domain,
        "bk_biz_id": cluster.bk_biz_id,
        "check_day": check_day.isoformat(),
        "run_kind": run_kind,
        "retention_hours": rows[0].retention_hours,
        "report_ids": [row.id for row in rows],
        "hits": [
            {
                "ip": row.ip,
                "mount_point": row.mount_point,
                "rule": row.rule,
                "peak": row.peak,
                "excess": row.excess,
                "daily_growth": row.daily_growth,
                "peaks": row.peaks,
            }
            for row in rows
        ],
    }


def _submit_ai_analysis(
    reports: List[KafkaDiskGrowthReport], cluster_by_domain: Dict[str, Cluster], check_day: date, run_kind: str
) -> int:
    """
    把命中的集群提交给 AI 分析，返回成功入队的集群数。
    框架的任务开关默认关闭；关闭、超过提交上限或入队失败的行保持“未提交”，不影响报告本身。
    """
    if not reports:
        return 0
    task = KafkaDiskGrowthAnalysisTask()
    config = task.config
    if not config.enabled:
        logger.info("kafka disk growth: analysis task %s is disabled, skip AI analysis", task.task_key)
        return 0

    # 重跑时已经在分析或已有结论的行不重复提交
    grouped: Dict[str, List[KafkaDiskGrowthReport]] = defaultdict(list)
    for report in reports:
        if report.ai_status == KafkaDiskGrowthAiStatus.NOT_SUBMITTED.value:
            grouped[report.domain].append(report)
    if not grouped:
        return 0
    # 峰值最高的优先分析，超出上限的不提交
    ordered = sorted(grouped.items(), key=lambda entry: max(row.peak for row in entry[1]), reverse=True)
    ordered = ordered[: config.max_submit_per_run]

    items = [_build_analysis_item(cluster_by_domain[domain], rows, check_day, run_kind) for domain, rows in ordered]
    try:
        outcomes = task.submit(items)
    except Exception:
        logger.exception("kafka disk growth: submit AI analysis failed")
        return 0

    submitted = 0
    for item, outcome in zip(items, outcomes):
        if outcome.outcome != DispatchOutcomeType.ENQUEUED:
            logger.info(
                "kafka disk growth: analysis not enqueued, cluster=%s outcome=%s", item["domain"], outcome.outcome
            )
            continue
        # worker 可能在入队返回之前就已经写入 success / skipped，所以只改还没被推进过的行
        KafkaDiskGrowthReport.objects.filter(
            id__in=item["report_ids"], ai_status=KafkaDiskGrowthAiStatus.NOT_SUBMITTED.value
        ).update(ai_status=KafkaDiskGrowthAiStatus.PENDING.value)
        submitted += 1
    return submitted


def _cleanup(now: datetime) -> None:
    KafkaDiskGrowthReport.objects.filter(create_at__lt=now - timedelta(days=REPORT_KEEP_DAYS)).delete()
    # 排队过期等原因拿不到 AI 结果的行，不让它一直显示“分析中”
    KafkaDiskGrowthReport.objects.filter(
        ai_status=KafkaDiskGrowthAiStatus.PENDING.value,
        create_at__lt=now - timedelta(hours=PENDING_AI_EXPIRE_HOURS),
    ).update(
        ai_status=KafkaDiskGrowthAiStatus.FAILED.value,
        ai_analysis=_("AI 分析超时未返回"),
        update_at=now,
    )


def check_kafka_disk_growth(run_kind: str, now: Optional[datetime] = None) -> dict:
    """
    Kafka 磁盘持续增长巡检：
    1. 向监控查询所有在线 Kafka 集群最近 10 天的磁盘峰值，在本地按自然日求日峰值（不落库）
    2. 按 broker 挂载点判定是否命中“持续增长”规则，命中的写入巡检报告
    3. 对命中的集群提交 AI 分析，结论回写到报告行
    """
    now = now or timezone.now()
    check_day, start, end = _resolve_window(run_kind, now)

    clusters = list(Cluster.objects.filter(cluster_type=ClusterType.Kafka, phase=ClusterPhase.ONLINE.value))
    cluster_by_domain = {cluster.immute_domain: cluster for cluster in clusters}

    stats = {"failed_batches": 0}
    peaks = fetch_daily_peaks(sorted(cluster_by_domain), start, end, stats)

    # 判定当天和此前 7 天里只要有一天因覆盖不足被丢弃，这个挂载点本轮就不判定
    required_days = {check_day - timedelta(days=offset) for offset in range(HISTORY_WINDOW_DAYS + 1)}
    dropped_days = stats.get("dropped_days", {})
    coverage_skipped = 0
    hits: List[Tuple[Cluster, str, str, GrowthHit]] = []
    for (domain, ip, mount_point), day_peaks in sorted(peaks.items()):
        cluster = cluster_by_domain.get(domain)
        if cluster is None:
            continue
        if required_days & dropped_days.get((domain, ip, mount_point), set()):
            coverage_skipped += 1
            continue
        hit = evaluate(day_peaks, check_day)
        if hit:
            hits.append((cluster, ip, mount_point, hit))

    reports = _write_reports(hits, check_day, run_kind)
    submitted = _submit_ai_analysis(reports, cluster_by_domain, check_day, run_kind)
    _cleanup(now)

    summary = {
        "check_day": check_day.isoformat(),
        "run_kind": run_kind,
        "clusters": len(clusters),
        "series": len(peaks),
        "hits": len(reports),
        "ai_submitted": submitted,
        "failed_batches": stats["failed_batches"],
        "coverage_dropped_days": sum(len(days) for days in dropped_days.values()),
        "coverage_skipped": coverage_skipped,
        "coverage_reasons": dict(stats.get("coverage_reasons", {})),
    }
    for detail in stats.get("coverage_details", []):
        logger.info("kafka disk growth: coverage insufficient, %s", detail)
    logger.info("kafka disk growth check done: %s", summary)
    return summary
