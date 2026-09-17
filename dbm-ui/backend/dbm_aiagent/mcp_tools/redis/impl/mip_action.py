"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import ast
import datetime
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.nosqlcomm.redis_cluster_repo import DbmClusterRepository
from backend.db_services.redis.capacity_evaluate_service.models.tb_capacity_evaluate import CapacityEvaluateRecord
from backend.db_services.redis.capacity_evaluate_service.models.tb_evaluate_history import CapacityEvaluateHistory
from backend.db_services.redis.capacity_evaluate_service.repositories.cluster_topo_repo import ClusterTopoInfo
from backend.db_services.redis.capacity_evaluate_service.services.capacity_cal import CapacityCalculateService
from backend.db_services.redis.capacity_evaluate_service.services.evaluate_service import (
    EVAL_QPS_MODEL,
    CapacityEvaluateService,
)
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpClusterNotFoundException

logger = logging.getLogger("root")

DateTimeLike = Union[str, datetime.datetime, None]


def _to_aware_datetime(value: DateTimeLike, default: Optional[datetime.datetime] = None) -> datetime.datetime:
    """将入参解析为 aware datetime；字符串支持 ISO；naive 按当前时区本地化。"""
    if value is None or value == "":
        return default if default is not None else timezone.now()
    if isinstance(value, datetime.datetime):
        dt = value
    else:
        dt = parse_datetime(str(value).strip())
        if dt is None:
            raise DBMMcpBaseException(msg=_("无法解析时间: %(value)s") % {"value": value})
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _dt_iso(dt: Optional[datetime.datetime]) -> Optional[str]:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.isoformat()


@dataclass
class ActWindow:
    """用于重叠峰值计算的时间窗需求。"""

    start_time: datetime.datetime
    end_time: datetime.datetime
    req_qps_k: int
    size_g: float


def max_sum_qps_with_window(
    act_list: List[ActWindow],
) -> Tuple[int, Optional[datetime.datetime], Optional[datetime.datetime]]:
    """计算任意时刻重叠区间的 QPS 总和最大值，及达到该最大值的区间 [best_start, best_end]。"""
    if not act_list:
        return 0, None, None

    events: List[Tuple[int, int]] = []
    end_ts_list: List[int] = []
    for d in act_list:
        st = int(d.start_time.timestamp())
        et = int(d.end_time.timestamp())
        end_ts_list.append(et)
        events.append((st, int(d.req_qps_k)))
        # end 视为闭区间，在 et+1 释放
        events.append((et + 1, -int(d.req_qps_k)))
    events.sort(key=lambda x: x[0])

    cur, best = 0, 0
    best_start_ts: Optional[int] = None
    best_end_ts: Optional[int] = None

    for t, delta in events:
        if best_start_ts is not None and best_end_ts is None and cur == best and best > 0:
            best_end_ts = t - 1
        cur += delta
        if cur > best:
            best = cur
            best_start_ts = t
            best_end_ts = None

    if best_start_ts is not None and best_end_ts is None:
        best_end_ts = max(end_ts_list)

    tz = timezone.get_current_timezone()
    best_start = datetime.datetime.fromtimestamp(best_start_ts, tz=tz) if best_start_ts is not None else None
    best_end = datetime.datetime.fromtimestamp(best_end_ts, tz=tz) if best_end_ts is not None else None
    return best, best_start, best_end


def sum_qps(act_list: List[ActWindow]) -> int:
    return sum(int(d.req_qps_k) for d in act_list)


def sum_capacity_g(act_list: List[ActWindow]) -> float:
    return float(sum(float(d.size_g) for d in act_list))


def _summary_from_acts(act_list: List[ActWindow]) -> Dict[str, Any]:
    peak, peak_start, peak_end = max_sum_qps_with_window(act_list)
    return {
        "count": len(act_list),
        "qps_peak": peak,
        "qps_peak_window": {
            "start_time": _dt_iso(peak_start),
            "end_time": _dt_iso(peak_end),
        },
        "qps_sum": sum_qps(act_list),
        "capacity_g_sum": round(sum_capacity_g(act_list), 2),
    }


def serialize_active_action(record: CapacityEvaluateRecord) -> Dict[str, Any]:
    size_g = round(float(record.req_capacity_m or 0) / 1024, 2)
    return {
        "action_id": record.action_id,
        "action_name": record.action_name,
        "action_user": record.action_user or "",
        "start_time": _dt_iso(record.start_time),
        "end_time": _dt_iso(record.end_time),
        "req_qps_k": record.req_qps_k,
        "req_capacity_m": record.req_capacity_m,
        "size_g": size_g,
    }


def list_active_mip_actions(
    cluster_domain: str,
    current_time: DateTimeLike = None,
    stop_time: DateTimeLike = None,
) -> List[CapacityEvaluateRecord]:
    """查询时间窗内未结束的 MIP Action：end_time > current_time；可选 start_time <= stop_time。"""
    now_dt = _to_aware_datetime(current_time)
    qs = CapacityEvaluateRecord.objects.filter(cluster_domain=cluster_domain, end_time__gt=now_dt)
    if stop_time not in (None, ""):
        stop_dt = _to_aware_datetime(stop_time)
        qs = qs.filter(start_time__lte=stop_dt)
    return list(qs.order_by("end_time"))


def get_last_evaluate(cluster_domain: str) -> Optional[CapacityEvaluateHistory]:
    return CapacityEvaluateHistory.objects.filter(cluster_domain=cluster_domain).order_by("-id").first()


def serialize_last_evaluate(history: CapacityEvaluateHistory) -> Dict[str, Any]:
    total_g = round(float(history.total_size_mb or 0) / 1024, 2)
    free_g = round(float(history.free_size_mb or 0) / 1024, 2)
    req_g = round(float(history.req_capacity_m_total or 0) / 1024, 2)
    return {
        "action_id": history.action_id,
        "action_name": history.action_name,
        "action_user": history.action_user or "",
        "approved_status": history.approved_status,
        "approved_comment": history.approved_comment or "",
        "approved_user": history.approved_user or "",
        "evaluate_time": _dt_iso(history.evaluate_time),
        "cluster_domain": history.cluster_domain,
        "proxy_count": history.proxy_count,
        "req_qps_k": history.req_qps_k,
        "req_capacity_m": history.req_capacity_m,
        "req_qps_k_total": history.req_qps_k_total,
        "req_capacity_m_total": history.req_capacity_m_total,
        "total_g": total_g,
        "free_g": free_g,
        "req_g": req_g,
        "not_finished_records_json": history.not_finished_records_json or "",
    }


def build_expand_suggest(last_evaluate: Dict[str, Any]) -> Dict[str, Any]:
    """基于最近一次评估结果生成扩容建议；通过则需求差值为 0。"""
    proxy_qps_k = EVAL_QPS_MODEL["proxy_qps"] / 1000
    req_qps_k_total = float(last_evaluate.get("req_qps_k_total") or 0)
    proxy_count = int(last_evaluate.get("proxy_count") or 0)
    free_g = float(last_evaluate.get("free_g") or 0)
    req_g = float(last_evaluate.get("req_g") or 0)
    req_proxy_count = req_qps_k_total / proxy_qps_k if proxy_qps_k else 0
    proxy_count_diff = int(req_proxy_count - proxy_count)
    need_capacity_g = int(req_g - free_g)
    approved_ok = last_evaluate.get("approved_status") == "success"
    if approved_ok:
        proxy_count_diff = 0
        need_capacity_g = 0
    return {
        "suggest_type": "扩容建议",
        "cluster_domain": last_evaluate.get("cluster_domain"),
        "approved_status": last_evaluate.get("approved_status"),
        "proxy_count": proxy_count,
        "req_qps_k_total": req_qps_k_total,
        "req_proxy_count": round(req_proxy_count, 2),
        "proxy_count_diff": max(proxy_count_diff, 0) if not approved_ok else 0,
        "total_g": last_evaluate.get("total_g"),
        "free_g": free_g,
        "req_g": req_g,
        "need_capacity_g": max(need_capacity_g, 0) if not approved_ok else 0,
        "need_proxy_count": max(proxy_count_diff, 0) if not approved_ok else 0,
        "need_capacity": max(need_capacity_g, 0) if not approved_ok else 0,
    }


def _parse_history_time(raw: Any) -> Optional[datetime.datetime]:
    """解析 history JSON 中的时间（可能带 :UTC 后缀）。"""
    if raw is None:
        return None
    if isinstance(raw, datetime.datetime):
        return _to_aware_datetime(raw)
    text = str(raw).replace(":UTC", "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return timezone.make_aware(dt, datetime.timezone.utc)
        except ValueError:
            continue
    try:
        return _to_aware_datetime(text)
    except DBMMcpBaseException:
        return None


def _related_actions_from_history(
    history: CapacityEvaluateHistory,
    cluster_domain: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """解析 not_finished_records_json 并并入本次 action；失败时返回空列表与说明。"""
    note = ""
    related: List[Dict[str, Any]] = []
    raw = history.not_finished_records_json or ""
    try:
        loaded = json.loads(raw) if raw else []
        if not isinstance(loaded, list):
            raise ValueError("not_finished_records_json is not a list")
        for item in loaded:
            if not isinstance(item, dict):
                continue
            req_capacity_m = int(item.get("req_capacity_m") or 0)
            related.append(
                {
                    "action_id": item.get("action_id") or "",
                    "action_name": item.get("action_name") or "",
                    "action_user": item.get("action_user") or "",
                    "start_time": _dt_iso(_parse_history_time(item.get("start_time"))),
                    "end_time": _dt_iso(_parse_history_time(item.get("end_time"))),
                    "req_qps_k": int(item.get("req_qps_k") or 0),
                    "req_capacity_m": req_capacity_m,
                    "size_g": round(req_capacity_m / 1024, 2),
                }
            )
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        note = f"parse not_finished_records_json failed: {exc}"
        return [], note

    # 并入本次 history 对应的 action（脚本从 request 表补全时间窗）
    current = (
        CapacityEvaluateRecord.objects.filter(action_id=history.action_id, cluster_domain=cluster_domain)
        .order_by("start_time")
        .first()
    )
    if current:
        related.append(serialize_active_action(current))
    else:
        related.append(
            {
                "action_id": history.action_id,
                "action_name": history.action_name,
                "action_user": history.action_user or "",
                "start_time": None,
                "end_time": None,
                "req_qps_k": history.req_qps_k,
                "req_capacity_m": history.req_capacity_m,
                "size_g": round(float(history.req_capacity_m or 0) / 1024, 2),
            }
        )
        note = (note + "; " if note else "") + "current action request record not found; times omitted"

    related = sorted(related, key=lambda x: x.get("start_time") or "")
    return related, note


def _acts_from_serialized(rows: List[Dict[str, Any]]) -> List[ActWindow]:
    acts: List[ActWindow] = []
    for row in rows:
        raw_start, raw_end = row.get("start_time"), row.get("end_time")
        if not raw_start or not raw_end:
            continue
        try:
            start = _to_aware_datetime(raw_start)
            end = _to_aware_datetime(raw_end)
        except DBMMcpBaseException:
            start = _parse_history_time(raw_start)
            end = _parse_history_time(raw_end)
            if start is None or end is None:
                continue
        acts.append(
            ActWindow(
                start_time=start,
                end_time=end,
                req_qps_k=int(row.get("req_qps_k") or 0),
                size_g=float(row.get("size_g") or 0),
            )
        )
    return acts


def analyze_mip_capacity(
    cluster_domain: str,
    current_time: DateTimeLike = None,
    stop_time: DateTimeLike = None,
) -> Dict[str, Any]:
    """MIP 容量分析：进行中 Action、重叠峰值、最近评估与扩容建议。"""
    now_dt = _to_aware_datetime(current_time)
    stop_dt = _to_aware_datetime(stop_time) if stop_time not in (None, "") else None

    records = list_active_mip_actions(cluster_domain, current_time=now_dt, stop_time=stop_dt)
    active_actions = [serialize_active_action(r) for r in records]
    active_acts = [
        ActWindow(
            start_time=r.start_time,
            end_time=r.end_time,
            req_qps_k=int(r.req_qps_k or 0),
            size_g=float(r.req_capacity_m or 0) / 1024,
        )
        for r in records
    ]
    active_summary = _summary_from_acts(active_acts)

    history = get_last_evaluate(cluster_domain)
    last_evaluate = serialize_last_evaluate(history) if history else None
    suggest = build_expand_suggest(last_evaluate) if last_evaluate else None

    related_actions: List[Dict[str, Any]] = []
    related_note = ""
    if history:
        related_actions, related_note = _related_actions_from_history(history, cluster_domain)
    related_summary = _summary_from_acts(_acts_from_serialized(related_actions))
    if related_note:
        related_summary["note"] = related_note

    return {
        "cluster_domain": cluster_domain,
        "current_time": _dt_iso(now_dt),
        "stop_time": _dt_iso(stop_dt),
        "active_actions": active_actions,
        "active_summary": active_summary,
        "last_evaluate": last_evaluate,
        "suggest": suggest,
        "related_actions": related_actions,
        "related_summary": related_summary,
    }


def get_cluster_spec(cluster_domain: str) -> Dict[str, Any]:
    """按域名返回 Redis 集群精简拓扑规格。"""
    cluster = DbmClusterRepository.get_cluster_by_domain(cluster_domain)
    if not cluster:
        raise DBMMcpClusterNotFoundException(msg=_("集群未找到: %(domain)s") % {"domain": cluster_domain})
    info = CapacityCalculateService.get_cluster_info(cluster.bk_biz_id, cluster.id)
    ci = info["cluster_info"]
    tmp = ClusterTopoInfo(ci["cluster_id"], ci["bk_biz_id"])
    tmp.cluster_type = ci.get("cluster_type") or cluster.cluster_type
    return {
        "cluster_domain": ci.get("cluster_domain") or cluster_domain,
        "cluster_id": ci.get("cluster_id") or cluster.id,
        "bk_biz_id": ci.get("bk_biz_id") or cluster.bk_biz_id,
        "cluster_type": ci.get("cluster_type") or cluster.cluster_type,
        "storage_type": tmp.storage_type,
        "proxy_num": ci.get("proxy_num") or 0,
        "shard_num": ci.get("shard_num") or 0,
        "proxy_spec": ci.get("proxy_spec") or "",
        "shard_spec": ci.get("shard_spec") or "",
        "proxy_cpu_total": ci.get("proxy_cpu_total") or 0,
        "proxy_mem_total": ci.get("proxy_mem_total") or 0,
        "storage_cpu_total": ci.get("storage_cpu_total") or 0,
        "storage_mem_total_m": ci.get("storage_mem_total_m") or 0,
        "storage_disk_total": ci.get("storage_disk_total") or 0,
        "shard_cpu_core_m": ci.get("shard_cpu_core_m") or 0,
    }


# 最近一次评估视为失败的状态（非 success）
_LAST_EVAL_FAILED_STATUSES = ("failed", "error")


def list_last_failed_clusters(bk_biz_id: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    """
    列出「每个集群最近一次评估」为 failed/error 的 cluster_domain。
    bk_biz_id 有值时限定业务；为空时查全库（需 DBA 鉴权，由 View 层保证）。
    """
    filters = {}
    if bk_biz_id is not None:
        filters["bk_biz_id"] = bk_biz_id
    qs = CapacityEvaluateHistory.objects.filter(**filters)
    latest_id_by_domain = qs.values("cluster_domain").annotate(max_id=Max("id")).values_list("max_id", flat=True)
    # 物化 id 列表，避免部分 MySQL 对子查询 in 的限制
    latest_ids = list(latest_id_by_domain)
    if not latest_ids:
        return {"bk_biz_id": bk_biz_id, "count": 0, "cluster_domains": [], "records": []}

    failed_qs = CapacityEvaluateHistory.objects.filter(
        id__in=latest_ids, approved_status__in=_LAST_EVAL_FAILED_STATUSES
    ).order_by("-evaluate_time", "-id")[:limit]
    records = []
    cluster_domains = []
    for h in failed_qs:
        cluster_domains.append(h.cluster_domain)
        records.append(
            {
                "cluster_domain": h.cluster_domain,
                "cluster_id": h.cluster_id,
                "bk_biz_id": h.bk_biz_id,
                "approved_status": h.approved_status,
                "approved_comment": h.approved_comment or "",
                "action_id": h.action_id,
                "action_name": h.action_name,
                "evaluate_time": _dt_iso(h.evaluate_time),
                "req_qps_k_total": h.req_qps_k_total,
                "req_capacity_m_total": h.req_capacity_m_total,
            }
        )
    return {
        "bk_biz_id": bk_biz_id,
        "count": len(records),
        "cluster_domains": cluster_domains,
        "records": records,
    }


def parse_key_pattern(raw) -> List[str]:
    """将库表 CharField 形式的 key_pattern 尽量还原为 list。"""
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if not isinstance(raw, str):
        return [str(raw)]
    text = raw.strip()
    if not text:
        return []
    for loader in (json.loads, ast.literal_eval):
        try:
            loaded = loader(text)
            if isinstance(loaded, list):
                return [str(x) for x in loaded]
            if loaded is None:
                return []
            return [str(loaded)]
        except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
            continue
    return [text]


def serialize_record(record: CapacityEvaluateRecord) -> Dict[str, Any]:
    data = record.__data__()
    data["evaluate_method"] = record.evaluate_method
    data["last_approved_user"] = record.last_approved_user
    data["last_approved_status"] = record.last_approved_status
    data["last_approved_time"] = record.last_approved_time
    return data


def list_mip_actions(
    bk_biz_id: int,
    action_id: Optional[str] = None,
    cluster_domain: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    qs = CapacityEvaluateRecord.objects.filter(bk_biz_id=bk_biz_id)
    if action_id:
        qs = qs.filter(action_id=action_id)
    if cluster_domain:
        qs = qs.filter(cluster_domain=cluster_domain)
    records = list(qs.order_by("-start_time")[:limit])
    return {"count": len(records), "records": [serialize_record(r) for r in records]}


def rebuild_action_info(record: CapacityEvaluateRecord, is_force: Optional[int] = None) -> Dict[str, Any]:
    force = is_force if is_force is not None else (record.is_force or 0)
    action_user = record.action_user or ""
    return {
        "action_id": record.action_id,
        "action_name": record.action_name,
        "action_type": record.action_type,
        "action_user": action_user,
        "bk_biz_id": record.bk_biz_id,
        "bk_biz_name": record.bk_biz_name or "",
        "start_time": record.start_time,
        "end_time": record.end_time,
        "evaluate_method": record.evaluate_method or "",
        "is_force": force,
        "user": action_user or "mcp",
    }


def rebuild_req(record: CapacityEvaluateRecord, is_force: Optional[int] = None) -> Dict[str, Any]:
    """从已有记录还原 req；is_force 写入 req，避免 update_or_create 覆盖为 0。"""
    force = is_force if is_force is not None else (record.is_force or 0)
    return {
        "cluster_domain": record.cluster_domain,
        "req_capacity_m": record.req_capacity_m,
        "req_qps_k": record.req_qps_k,
        "key_pattern": parse_key_pattern(record.key_pattern),
        "req_flag_no_big_key_with_a_lot_of_member": int(record.req_flag_no_big_key_with_a_lot_of_member),
        "req_flag_no_big_result": int(record.req_flag_no_big_result),
        "req_flag_no_big_value": int(record.req_flag_no_big_value),
        "req_flag_no_hot_key": int(record.req_flag_no_hot_key),
        "req_flag_no_use_dns": record.req_flag_no_use_dns,
        "is_force": force,
    }


def evaluate_mip_action(
    bk_biz_id: int,
    action_id: str,
    cluster_domain: Optional[str] = None,
    is_force: Optional[int] = None,
) -> Dict[str, Any]:
    """
    仅对已提交记录重评。
    使用记录上的 cluster_id，避免域名变更导致 update_or_create 插入新的 (cluster_id, action_id)。
    """
    qs = CapacityEvaluateRecord.objects.filter(bk_biz_id=bk_biz_id, action_id=action_id)
    if cluster_domain:
        qs = qs.filter(cluster_domain=cluster_domain)
    records = list(qs)
    if not records:
        raise DBMMcpBaseException(
            msg=_(
                "未找到已提交的 action 记录: bk_biz_id=%(bk_biz_id)s action_id=%(action_id)s "
                "cluster_domain=%(cluster_domain)s"
            )
            % {"bk_biz_id": bk_biz_id, "action_id": action_id, "cluster_domain": cluster_domain or ""}
        )

    results = []
    for record in records:
        # 校验域名仍指向同一集群，防止错配后写入新主键
        cluster = DbmClusterRepository.get_cluster_by_domain(record.cluster_domain)
        if not cluster:
            raise DBMMcpClusterNotFoundException(msg=_("集群未找到: %(domain)s") % {"domain": record.cluster_domain})
        if cluster.id != record.cluster_id:
            raise DBMMcpBaseException(
                msg=_(
                    "集群 ID 与已提交记录不一致，拒绝重评以免新建 action: domain=%(domain)s "
                    "record_cluster_id=%(record_id)s current_cluster_id=%(current_id)s"
                )
                % {
                    "domain": record.cluster_domain,
                    "record_id": record.cluster_id,
                    "current_id": cluster.id,
                }
            )
        if cluster.bk_biz_id != bk_biz_id:
            raise DBMMcpBaseException(
                msg=_(
                    "集群业务与请求业务不一致，拒绝重评: domain=%(domain)s "
                    "req_bk_biz_id=%(req_biz)s cluster_bk_biz_id=%(cluster_biz)s"
                )
                % {
                    "domain": record.cluster_domain,
                    "req_biz": bk_biz_id,
                    "cluster_biz": cluster.bk_biz_id,
                }
            )

        action_info = rebuild_action_info(record, is_force=is_force)
        one_req = rebuild_req(record, is_force=is_force)
        resp = CapacityEvaluateService.evaluate_one(action_info, one_req, bk_biz_id, record.cluster_id)
        results.append(resp.to_dict())
    return {"action_id": action_id, "results": results}


def calc_supported_qps_from_topo(topo_info: ClusterTopoInfo, model: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """按评估公式计算集群可支持 QPS（单位 K），不写库。"""
    model = model or EVAL_QPS_MODEL
    proxy_qps_k = model["proxy_qps"] / 1000
    proxy_qps_k_total = proxy_qps_k * topo_info.proxy_num

    if topo_info.is_tendis_ssd() or topo_info.is_tendisplus():
        shard_qps_per_core = model["ssd_shard_qps_per_core"]
    else:
        shard_qps_per_core = model["shard_qps_per_core"]

    shard_cpu_core_m = min(topo_info.shard_cpu_core_m, topo_info.get_shard_cpu_core_limit())
    shard_qps_k = shard_qps_per_core * (shard_cpu_core_m / 1000) / 1000
    backend_qps_k_total = shard_qps_k * topo_info.shard_num
    supported_qps_k = min(proxy_qps_k_total, backend_qps_k_total)

    return {
        "cluster_domain": topo_info.cluster_domain,
        "supported_qps_k": supported_qps_k,
        "proxy_qps_k_total": proxy_qps_k_total,
        "backend_qps_k_total": backend_qps_k_total,
        "proxy_num": topo_info.proxy_num,
        "shard_num": topo_info.shard_num,
        "shard_spec": topo_info.shard_spec or "",
        "model": dict(model),
    }


def get_supported_qps(cluster_domain: str) -> Dict[str, Any]:
    cluster = DbmClusterRepository.get_cluster_by_domain(cluster_domain)
    if not cluster:
        raise DBMMcpClusterNotFoundException(msg=_("集群未找到: %(domain)s") % {"domain": cluster_domain})
    topo_info = ClusterTopoInfo(cluster.id, cluster.bk_biz_id)
    topo_info.fetch_data()
    return calc_supported_qps_from_topo(topo_info)
