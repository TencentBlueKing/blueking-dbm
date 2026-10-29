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
import datetime
import logging
import math
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import parse_step_to_seconds
from backend.dbm_aiagent.mcp_tools.common.views.promql_query import query_promql_metrics_with_roles
from backend.dbm_aiagent.mcp_tools.doris.constants import (
    DEFAULT_STEP,
    DORIS_METRIC_REGISTRY,
    END_TIME_MAX_FUTURE_SKEW_SECONDS,
    MAX_DATAPOINTS,
    MAX_QUERY_RANGE_SECONDS,
    SUMMARY_DEFAULT_DAYS,
    SUMMARY_GROUP_NAMES,
    SUMMARY_KEY_METRICS,
    SUMMARY_STEP,
    DorisMetricSpec,
    get_all_metric_names,
    get_metric_spec,
)
from backend.dbm_aiagent.mcp_tools.doris.enums import BE_ROLES, FE_ROLES, DorisHealthLevel
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpClusterNotFoundException

logger = logging.getLogger("root")


def validate_doris_cluster(cluster_domain: str) -> Cluster:
    """校验集群存在且为 Doris 集群。

    同时拦住「传了非 Doris 集群域名」的误用：MySQL / Redis 等集群的指标
    与 Doris 完全不同，误传会静默返回空序列，难以排查。

    @param cluster_domain: 集群访问域名（immute_domain）
    @return: 集群对象
    """
    cluster = Cluster.objects.filter(immute_domain=cluster_domain, cluster_type=ClusterType.Doris).first()
    if not cluster:
        # 区分「域名不存在」与「域名存在但不是 Doris 集群」，便于智能体自我纠正
        exist_cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
        if exist_cluster:
            raise DBMMcpClusterNotFoundException(
                msg=_("集群 {} 的类型是 {}，不是 Doris 集群，无法使用 Doris 指标工具查询").format(cluster_domain, exist_cluster.cluster_type)
            )
        raise DBMMcpClusterNotFoundException(msg=_("Doris 集群 {} 未找到").format(cluster_domain))
    return cluster


def validate_metric_name(metric_name: str) -> DorisMetricSpec:
    """校验指标名合法，非法时回带全部合法指标名，便于智能体自我纠正。

    @param metric_name: 指标名
    @return: 指标声明
    """
    spec = get_metric_spec(metric_name)
    if not spec:
        raise DBMMcpBaseException(msg=_("无效的指标名: {}，可选值: {}").format(metric_name, ", ".join(get_all_metric_names())))
    return spec


def validate_metric_roles(metric_name: str, spec: DorisMetricSpec, instance_roles: List[str]) -> List[str]:
    """校验指标与节点角色的适用性。

    FE 专属指标（JVM 堆、查询错误率、事务、元数据、Compaction 分数）传入 BE 角色时
    直接报错并回带该指标的合法角色，而不是静默返回空数据 —— 后者会让智能体
    误判为「集群无此问题」。

    role_filter_builtin 的指标（PromQL 内已固化 instance_role）不支持按角色细分：
    传入角色会被外层忽略，若仍回显用户传入值会造成「响应与实际查询不符」，
    故直接报错说明其固定覆盖范围。

    @param metric_name: 指标名
    @param spec: 指标声明
    @param instance_roles: 用户指定的角色列表，为空时按指标适用范围自动填充
    @return: 实际生效的角色列表
    """
    # 未指定角色时，自动填充为该指标的适用角色，避免把 FE 指标下发到 BE 节点
    if not instance_roles:
        return sorted(spec.applicable_roles)

    if spec.role_filter_builtin:
        raise DBMMcpBaseException(
            msg=_("指标 {} 的节点角色已固化在查询内，固定覆盖 {}，不支持按角色细分；请不要传入 instance_roles").format(
                metric_name, ", ".join(sorted(spec.applicable_roles))
            )
        )

    invalid_roles = [role for role in instance_roles if role not in spec.applicable_roles]
    if invalid_roles:
        raise DBMMcpBaseException(
            msg=_("指标 {} 不适用于节点角色 {}，该指标的合法角色为: {}").format(
                metric_name, ", ".join(invalid_roles), ", ".join(sorted(spec.applicable_roles))
            )
        )
    return list(instance_roles)


def validate_aggregation(metric_name: str, spec: DorisMetricSpec, aggregation: Optional[str]) -> str:
    """校验聚合方式，未指定时取指标默认值。"""
    if not aggregation:
        return spec.default_aggregation

    if aggregation not in spec.supported_aggregations:
        raise DBMMcpBaseException(
            msg=_("指标 {} 不支持聚合方式 {}，可选值: {}").format(
                metric_name, aggregation, ", ".join(sorted(spec.supported_aggregations))
            )
        )
    return aggregation


def _suggest_step(span_seconds: int) -> str:
    """给出能把 span 控制在 MAX_DATAPOINTS 以内的最小 step 字符串。

    一律向上取整，保证建议值真的满足限制（而不是刚好卡在边界外），
    让智能体照抄一次即可通过，不必反复试。
    """
    min_step_seconds = math.ceil(span_seconds / MAX_DATAPOINTS)

    minutes = math.ceil(min_step_seconds / 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = math.ceil(minutes / 60)
    if hours < 24:
        return f"{hours}h"
    return f"{math.ceil(hours / 24)}d"


def validate_time_range(
    start_time: Optional[datetime.datetime],
    end_time: Optional[datetime.datetime],
    step: str,
) -> None:
    """校验查询时间范围与点数规模。

    common 构造器里的 24 小时上限 raise 已被注释（common/impl/promql_query.py:210-212），
    MySQL 走同一个构造器、放开会改变其行为，故在 Doris 侧自行拦住。

    start_time 为空时底层默认只查最近 5 分钟，跨度必然安全，故跳过跨度与点数校验，
    只保留 end_time 的未来时间校验。

    @param start_time: 开始时间，为空表示由底层取最近 5 分钟
    @param end_time: 结束时间，为空表示取当前时间
    @param step: 采样步长，已由调用方补齐默认值
    """
    now = datetime.datetime.now()

    if end_time and (end_time - now).total_seconds() > END_TIME_MAX_FUTURE_SKEW_SECONDS:
        raise DBMMcpBaseException(
            msg=_("end_time 不能超出当前时间 {} 秒以上，请检查是否误传了未来时间").format(END_TIME_MAX_FUTURE_SKEW_SECONDS)
        )

    if not start_time:
        return

    effective_end = end_time or now
    if start_time >= effective_end:
        raise DBMMcpBaseException(msg=_("start_time 必须早于 end_time"))

    span_seconds = int((effective_end - start_time).total_seconds())
    if span_seconds > MAX_QUERY_RANGE_SECONDS:
        raise DBMMcpBaseException(msg=_("查询时间跨度不能超过 {} 天，请缩小时间范围或分多次查询").format(MAX_QUERY_RANGE_SECONDS // 86400))

    # 点数估算用于拦住「大跨度 + 小步长」把 LLM 上下文打爆的组合。
    # 不静默放大 step，而是报错并给出建议值，避免降采样摊薄毛刺导致误判。
    step_seconds = parse_step_to_seconds(step)
    estimated_points = span_seconds // step_seconds
    if estimated_points > MAX_DATAPOINTS:
        raise DBMMcpBaseException(
            msg=_(
                "时间跨度 {span} 秒搭配步长 {step} 约产生 {points} 个点，超过单条时间线上限 {limit}；"
                "请改用 step='{suggest}' 或缩小时间范围。"
                "注意不要指望系统自动降采样——放大步长会摊薄毛刺，需由你确认该精度可接受"
            ).format(
                span=span_seconds,
                step=step,
                points=estimated_points,
                limit=MAX_DATAPOINTS,
                suggest=_suggest_step(span_seconds),
            )
        )


def _build_query_builder(
    spec: DorisMetricSpec,
    aggregation: str,
    group_by: Optional[List[str]],
    start_time: Optional[datetime.datetime],
    end_time: Optional[datetime.datetime],
    step: Optional[str],
):
    """由工厂产出全新构造器并注入本次请求参数。

    必须经 builder_factory 取新实例：query_promql_metrics_with_roles 会对构造器
    原地 append filters 且无去重，复用实例会导致跨请求条件累积。
    """
    builder = spec.builder_factory()

    # 比率型指标（PromQLMultiQueryBuilder）的聚合由子构造器决定，
    # get_aggregation() 取的是第一个子构造器的 aggregation，故需同步到子构造器
    sub_queries = getattr(builder, "queries", None)
    if sub_queries:
        for sub_builder in sub_queries.values():
            sub_builder.aggregation = aggregation
            if group_by:
                for label in group_by:
                    if label not in sub_builder.group_by:
                        sub_builder.group_by.append(label)
    else:
        builder.aggregation = aggregation
        if group_by:
            for label in group_by:
                if label not in builder.group_by:
                    builder.group_by.append(label)

    if start_time:
        builder.start_time = start_time
    if end_time:
        builder.end_time = end_time
    if step:
        builder.step = step
        # time_window 已在注册表中显式声明的指标（如事务速率的 2m）不应被 step 覆盖，
        # 否则会改变 irate 的计算窗口；未声明的由 prepare_promql 用 step 兜底
        if sub_queries:
            for sub_builder in sub_queries.values():
                if not sub_builder.time_window:
                    sub_builder.step = step

    return builder


def query_doris_metrics(
    cluster_domain: str,
    metric_name: str,
    instance_roles: Optional[List[str]] = None,
    aggregation: Optional[str] = None,
    group_by: Optional[List[str]] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    step: Optional[str] = None,
) -> Dict:
    """查询 Doris 集群监控指标时序数据。

    @param cluster_domain: 集群访问域名
    @param metric_name: 指标名，见 DORIS_METRIC_REGISTRY
    @param instance_roles: 节点角色列表，为空时自动取该指标的全部适用角色
    @param aggregation: 聚合方式，为空时取指标默认值
    @param group_by: 额外的分组维度，cluster_domain 与 instance_role 由底层自动注入
    @param start_time: 开始时间，为空时默认最近 5 分钟
    @param end_time: 结束时间，为空时取当前时间
    @param step: 采样步长，为空时取 1m
    @return: 时序数据与实际执行的 PromQL
    """
    validate_doris_cluster(cluster_domain)
    spec = validate_metric_name(metric_name)
    effective_roles = validate_metric_roles(metric_name, spec, instance_roles)
    effective_aggregation = validate_aggregation(metric_name, spec, aggregation)
    effective_step = step or DEFAULT_STEP
    validate_time_range(start_time, end_time, effective_step)

    builder = _build_query_builder(
        spec=spec,
        aggregation=effective_aggregation,
        group_by=group_by,
        start_time=start_time,
        end_time=end_time,
        step=effective_step,
    )

    # role_filter_builtin 的指标（如 jvm_heap_usage）PromQL 内已固化 instance_role 过滤，
    # 外层再追加会产生重复甚至冲突条件，故传空角色跳过注入
    roles_for_query = [] if spec.role_filter_builtin else effective_roles

    logger.info(
        "query_doris_metrics cluster=%s metric=%s roles=%s aggregation=%s",
        cluster_domain,
        metric_name,
        roles_for_query,
        effective_aggregation,
    )

    result = query_promql_metrics_with_roles(cluster_domain, roles_for_query, builder)

    result.update(
        {
            "cluster_domain": cluster_domain,
            "metric_name": metric_name,
            "description": spec.desc,
            "unit": spec.unit,
            "aggregation": effective_aggregation,
            # 回显实际生效的角色：role_filter_builtin 的指标由 PromQL 内置条件决定，
            # 等于其全部适用角色，不能回显用户传入值（校验阶段已拒绝传入）
            "instance_roles": sorted(spec.applicable_roles) if spec.role_filter_builtin else effective_roles,
            "applicable_roles": sorted(spec.applicable_roles),
        }
    )
    if spec.extra_note:
        result["note"] = spec.extra_note
    return result


def _extract_values(series: List[Dict]) -> List[float]:
    """
    从 unify_query 返回的 series 中提取全部非空数值。
    series 格式为 [{"datapoints": [[value, timestamp], ...]}, ...]，
    value 可能为 None（该时间点无数据），需过滤。
    """
    values = []
    for one_series in series or []:
        for datapoint in one_series.get("datapoints") or []:
            if not datapoint:
                continue
            value = datapoint[0]
            if value is not None:
                values.append(value)
    return values


def _judge_health(spec: DorisMetricSpec, peak_value: Optional[float]) -> str:
    """
    按既定阈值判定健康状态。
    阈值主要来自 db_monitor/tpls/alarm/doris/*.json，阈值为空时不做判定。
    """
    if peak_value is None:
        return DorisHealthLevel.UNKNOWN.value

    if spec.warning_threshold is None and spec.fatal_threshold is None:
        return DorisHealthLevel.UNKNOWN.value

    def _hit(threshold: Optional[float]) -> bool:
        if threshold is None:
            return False
        # gt 与 gte 严格照抄告警模板：image_push_failed 用 gt，image_write_failed 用 gte
        return peak_value > threshold if spec.threshold_method == "gt" else peak_value >= threshold

    if _hit(spec.fatal_threshold):
        return DorisHealthLevel.FATAL.value
    if _hit(spec.warning_threshold):
        return DorisHealthLevel.WARNING.value
    return DorisHealthLevel.NORMAL.value


def get_doris_performance_summary(cluster_domain: str, days: int = SUMMARY_DEFAULT_DAYS) -> Dict:
    """获取 Doris 集群最近 N 天的性能摘要与健康状态。

    强制使用大步长（SUMMARY_STEP）并且只返回统计值不返回原始点位，
    否则 7 天 x 1m 约 1 万个点会撑爆 LLM 上下文。

    单个指标查询失败不中断整体，该项返回 error 字段并继续，
    避免一个指标无采集就让整个摘要不可用。

    @param cluster_domain: 集群访问域名
    @param days: 查询天数
    @return: 按资源/容量/查询/事务/元数据分组的摘要
    """
    validate_doris_cluster(cluster_domain)

    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(days=days)

    summary: Dict = {
        "cluster_domain": cluster_domain,
        "time_range": _("最近 {} 天").format(days),
        "step": SUMMARY_STEP,
        "groups": {},
        "abnormal_metrics": [],
    }

    for metric_name in SUMMARY_KEY_METRICS:
        spec = get_metric_spec(metric_name)
        if not spec:
            continue

        group_key = spec.summary_group or "other"
        group = summary["groups"].setdefault(
            group_key,
            {"name": SUMMARY_GROUP_NAMES.get(group_key, group_key), "metrics": {}},
        )

        try:
            result = query_doris_metrics(
                cluster_domain=cluster_domain,
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time,
                step=SUMMARY_STEP,
            )
            values = _extract_values(result.get("series"))
        except Exception as err:  # noqa
            logger.error("get_doris_performance_summary metric=%s failed: %s", metric_name, err)
            group["metrics"][metric_name] = {
                "description": spec.desc,
                "unit": spec.unit,
                "error": str(err),
            }
            continue

        if not values:
            group["metrics"][metric_name] = {
                "description": spec.desc,
                "unit": spec.unit,
                "health": DorisHealthLevel.UNKNOWN.value,
                "message": _("该指标在查询时间范围内无数据"),
            }
            continue

        peak = max(values)
        health = _judge_health(spec, peak)
        metric_summary = {
            "description": spec.desc,
            "unit": spec.unit,
            "max": peak,
            "min": min(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "count": len(values),
            "health": health,
            "warning_threshold": spec.warning_threshold,
            "fatal_threshold": spec.fatal_threshold,
        }
        group["metrics"][metric_name] = metric_summary

        if health in (DorisHealthLevel.WARNING.value, DorisHealthLevel.FATAL.value):
            summary["abnormal_metrics"].append(
                {
                    "metric_name": metric_name,
                    "description": spec.desc,
                    "health": health,
                    "peak_value": peak,
                    "unit": spec.unit,
                }
            )

    # 集群整体健康：任一指标致命则整体致命，任一预警则整体预警
    healths = [
        one_metric.get("health") for group in summary["groups"].values() for one_metric in group["metrics"].values()
    ]
    if DorisHealthLevel.FATAL.value in healths:
        summary["overall_health"] = DorisHealthLevel.FATAL.value
    elif DorisHealthLevel.WARNING.value in healths:
        summary["overall_health"] = DorisHealthLevel.WARNING.value
    elif DorisHealthLevel.NORMAL.value in healths:
        summary["overall_health"] = DorisHealthLevel.NORMAL.value
    else:
        summary["overall_health"] = DorisHealthLevel.UNKNOWN.value

    return summary


def get_fe_metric_names() -> List[str]:
    """FE 层适用的指标名，供工具描述与错误提示使用。"""
    return [name for name, spec in DORIS_METRIC_REGISTRY.items() if spec.applicable_roles & FE_ROLES]


def get_be_metric_names() -> List[str]:
    """BE 层适用的指标名。"""
    return [name for name, spec in DORIS_METRIC_REGISTRY.items() if spec.applicable_roles & BE_ROLES]
