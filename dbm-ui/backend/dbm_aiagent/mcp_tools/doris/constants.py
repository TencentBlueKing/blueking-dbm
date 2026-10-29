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
from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import PromQLMultiQueryBuilder, PromQLQueryBuilder
from backend.dbm_aiagent.mcp_tools.doris.enums import (
    ALL_ROLES,
    BE_ROLES,
    FE_ROLES,
    DorisAggFunction,
    DorisMetricName,
    DorisMetricUnit,
)

# Doris 专有指标的数据源前缀。
#
# PromQLQueryBuilder.build_promql() 的前缀处理逻辑（common/impl/promql_query.py:118-123）：
#   命中 exporter 专用前缀分支 -> 补 exporter 前缀
#   不以 "bkmonitor:" 开头     -> 补 "bkmonitor:dbm_system:" 前缀
# 因此 Doris 专有指标必须写全 "bkmonitor:" 前缀才能绕过 dbm_system 默认补全；
# 系统层指标则写短名（如 "cpu_summary:usage"），交由构造器自动补全。
DORIS_PUSHGATEWAY_PREFIX = "bkmonitor:pushgateway_dbm_doris_bkpull:"

# 默认采样步长
DEFAULT_STEP = "1m"

# 性能摘要的采样步长。
#
# 7 天 x 1m 约 1 万个点会撑爆 LLM 上下文，故摘要路径强制使用大步长
# （7 天约 168 点/指标，上限 30 天约 720 点，在 MAX_DATAPOINTS 之内），
# 且只返回统计值不返回原始点位。
SUMMARY_STEP = "1h"

# 性能摘要默认天数与上限
SUMMARY_DEFAULT_DAYS = 7
SUMMARY_MAX_DAYS = 30

# 单次查询的时间跨度上限（30 天）。
#
# common 的构造器里有 MAX_QUERY_RANGE_SECONDS = 24h，但那处 raise 已被注释成 pass
# （common/impl/promql_query.py:210-212），对 Doris 不生效；MySQL 走同一个构造器，
# 放开那处注释会连带改变 MySQL 的现有行为，故在 Doris 侧自行兜住。
MAX_QUERY_RANGE_SECONDS = 30 * 24 * 3600

# end_time 允许超出服务端当前时间的秒数，容忍调用方与服务端的时钟偏差。
# 取值对齐 Redis（redis/constants.py:46 METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS）。
END_TIME_MAX_FUTURE_SKEW_SECONDS = 300

# 单条时间线的点数上限。
MAX_DATAPOINTS = 1500


@dataclass(frozen=True)
class DorisMetricSpec:
    """单个 Doris 指标的声明。

    使用 builder_factory 而非 builder 实例，原因：
    query_promql_metrics_with_roles()(common/views/promql_query.py:33,38) 会对传入的
    构造器原地 append filters 且无去重，PromQLMultiQueryBuilder.build_promql()
    (common/impl/promql_query.py:253) 还会把父级 filters extend 进子构造器。
    若注册表持有模块级单例，第二次请求时 filters 会累积上一次的 cluster_domain 与
    instance_role，产生互斥条件导致查不出数据，甚至跨请求串数据。
    工厂函数保证每次请求都拿到全新实例，无深拷贝开销，也避免嵌套子构造器被共享。
    """

    # 产出全新 PromQL 构造器的工厂
    builder_factory: Callable[[], PromQLQueryBuilder]
    # 适用角色集合
    applicable_roles: FrozenSet[str]
    # 中文含义，进 ChoiceField 的 label 与摘要输出
    desc: str
    # 数值单位，取值必须落在 DorisMetricUnit 内（由 test_unit_is_valid 锁定）。
    # 单位用单值枚举而非布尔标记：它是多值互斥属性，且会被智能体直接读进结论。
    unit: str
    # 默认聚合方式
    default_aggregation: str
    # 支持的聚合方式
    supported_aggregations: FrozenSet[str]
    # True 表示 PromQL 内已固化 instance_role 过滤，外层不应再追加，
    # 否则会产生重复甚至冲突的 label 条件
    role_filter_builtin: bool = False
    # 健康判定阈值。多数取自 db_monitor/tpls/alarm/doris/*.json，None 表示不判定
    warning_threshold: Optional[float] = None
    fatal_threshold: Optional[float] = None
    # 阈值比较方式：gte 表示 >= 命中，gt 表示 > 命中（照抄告警模板，不做统一）
    threshold_method: str = "gte"
    # 摘要中的归类
    summary_group: str = ""
    # 面向智能体的补充说明，通用输出为响应的 note 字段（不限于某个指标）
    extra_note: str = ""

    @property
    def is_percent(self) -> bool:
        """是否为百分比量纲。替代原先冗余的 is_ratio 布尔字段。"""
        return self.unit == DorisMetricUnit.PERCENT.value


_ALL_AGGREGATIONS = frozenset(DorisAggFunction.get_values())


def _system_metric_factory(
    metric_name: str,
    aggregation: str,
    range_function: str = None,
    group_by: List[str] = None,
) -> Callable[[], PromQLQueryBuilder]:
    """系统层指标（bkmonitor:dbm_system:*）的构造器工厂。

    metric_name 写短名，由 build_promql() 自动补 bkmonitor:dbm_system: 前缀。
    group_by 传空列表表示不额外分组（注意区别于 None，后者才取默认维度）。
    """

    default_group_by = ["bk_target_ip"] if group_by is None else group_by

    def _factory() -> PromQLQueryBuilder:
        return PromQLQueryBuilder(
            metric_name=metric_name,
            group_by=list(default_group_by),
            aggregation=aggregation,
            range_function=range_function,
            step=DEFAULT_STEP,
            filters=[],
        )

    return _factory


def _doris_metric_factory(
    metric_field: str,
    aggregation: str,
    filters: List[Dict] = None,
    range_function: str = None,
    time_window: str = None,
    group_by: List[str] = None,
) -> Callable[[], PromQLQueryBuilder]:
    """Doris 专有指标（pushgateway_dbm_doris_bkpull）的构造器工厂。

    group_by 传空列表表示不额外分组（注意区别于 None，后者才取默认维度）。
    """

    default_group_by = ["instance_host"] if group_by is None else group_by

    def _factory() -> PromQLQueryBuilder:
        return PromQLQueryBuilder(
            metric_name=DORIS_PUSHGATEWAY_PREFIX + metric_field,
            group_by=list(default_group_by),
            aggregation=aggregation,
            range_function=range_function,
            time_window=time_window,
            step=DEFAULT_STEP,
            filters=[dict(f) for f in (filters or [])],
        )

    return _factory


def _ratio_metric_factory(
    numerator: Callable[[], PromQLQueryBuilder],
    denominator: Callable[[], PromQLQueryBuilder],
    expression: str,
) -> Callable[[], PromQLMultiQueryBuilder]:
    """比率型指标的构造器工厂（两个子查询做表达式计算）。

    execute_promql()(common/impl/promql_query.py:298-300) 对 expression 的处理是
    expr.format(**prom_queries) 纯字符串渲染，因此不止支持四则运算，
    也能表达 group_left 这类向量匹配。

    注意 PromQLMultiQueryBuilder.get_aggregation()(common/impl/promql_query.py:263)
    取的是第一个子构造器的 aggregation，故子构造器必须显式设置 aggregation，
    否则对外返回的 aggregation 为 None。
    """

    def _factory() -> PromQLMultiQueryBuilder:
        return PromQLMultiQueryBuilder(
            queries={
                "a": numerator(),
                "b": denominator(),
            },
            expression=expression,
            step=DEFAULT_STEP,
            filters=[],
        )

    return _factory


# ---------------------------------------------------------------------------
# 系统层指标
#
# FE 与 BE 共用同一底层字段，仅靠 instance_role 标签区分角色。
# 依据：Doris FE CPU Used Rate.json 与 Doris BE CPU Used Rate.json 的 metric_field
# 同为 usage、result_table_id 同为 dbm_system.cpu_summary，差异只在 agg_condition。
# ---------------------------------------------------------------------------

# 磁盘使用率需排除系统盘与安装盘，否则系统盘水位会混入数据盘判断。
# 依据：dashboard 中 disk:in_use 的 promql 带 mount_point!="/" 与 mount_point!="/usr/local"，
# 告警模板 Doris Backend Disk Usage.json 的 agg_condition 亦有 mount_point neq "/"。
DISK_USAGE_EXCLUDE_MOUNTS = [
    {"label_name": "mount_point", "op": "not_equal", "value": "/"},
    {"label_name": "mount_point", "op": "not_equal", "value": "/usr/local"},
]


def _disk_usage_factory() -> PromQLQueryBuilder:
    return PromQLQueryBuilder(
        metric_name="disk:in_use",
        group_by=["bk_target_ip", "mount_point"],
        aggregation="max",
        range_function="avg",
        step=DEFAULT_STEP,
        filters=[dict(f) for f in DISK_USAGE_EXCLUDE_MOUNTS],
    )


# ---------------------------------------------------------------------------
# Doris 专有层指标
# ---------------------------------------------------------------------------

# BE 数据盘使用率 = 100 * (1 - avail / total)
#
# 用「1 - 可用/总量」而非告警模板原先的 local_used/total。
# local_used 只统计 Doris 本地数据占用，不含 BE 预留空间与同盘非 Doris 文件，
# 会低估真实水位；avail 是文件系统实际可用量，与运维扩容决策一致。
# dashboard 的 Backend Hot/Cold「Disk Usage」面板用的也是 avail + total。
#
# 分组带 instance_role：扩缩容需按角色区分（热/温/冷节点分别扩容），
# 若只按 instance_host 分组，无法判断是哪一层水位告急。
_CAPACITY_GROUP_BY = ["cluster_domain", "instance_host", "instance_role"]

_capacity_avail_factory = _doris_metric_factory(
    metric_field="doris_be_disks_avail_capacity",
    aggregation="avg",
    group_by=list(_CAPACITY_GROUP_BY),
)
_capacity_total_factory = _doris_metric_factory(
    metric_field="doris_be_disks_total_capacity",
    aggregation="avg",
    group_by=list(_CAPACITY_GROUP_BY),
)

# JVM 堆使用率 = 100 * heap{type="used"} / heap{type="max"}
# 依据：Doris FE JVM Heap Percentage.json，expression="a * 100 / b"，
#       a/b 同为 jvm_heap_size_bytes，a 条件 type eq [used]、b 条件 type eq [max]，
#       两者均带 instance_role include [doris_follower, doris_observer]。
# instance_role 固化在子查询 filters 内，故该指标 role_filter_builtin=True。
_jvm_heap_role_filter = {
    "label_name": "instance_role",
    "op": "match",
    "value": "doris_follower|doris_observer",
}
_JVM_HEAP_GROUP_BY = ["cluster_domain", "instance_host", "instance_role"]

_jvm_heap_used_factory = _doris_metric_factory(
    metric_field="jvm_heap_size_bytes",
    aggregation="avg",
    filters=[{"label_name": "type", "op": "equal", "value": "used"}, _jvm_heap_role_filter],
    group_by=list(_JVM_HEAP_GROUP_BY),
)
_jvm_heap_max_factory = _doris_metric_factory(
    metric_field="jvm_heap_size_bytes",
    aggregation="avg",
    filters=[{"label_name": "type", "op": "equal", "value": "max"}, _jvm_heap_role_filter],
    group_by=list(_JVM_HEAP_GROUP_BY),
)

# Compaction 分数：集群级汇总指标，取 Master FE 上报的值。
#
# 指标选择 doris_fe_max_tablet_compaction_score
# （FE 汇总出的集群最大分数，维度为 FE 实例）而非 doris_fe_tablet_max_compaction_score
#
# 仍需与 node_info{type="is_master"} 相乘来取 Master：master 会切换，
# 不能从元数据取静态 master 节点。node_info{type="is_master"} 本身是一条时序，
# 在当时的 master FE 上取值 1、非 master 上取 0，相乘后非 master 归零，
# master 切换时结果自动跟随。
#
# 两侧按完全相同的维度分组，PromQL 默认向量匹配即可逐实例对齐，
# 无需 ignoring/group_left —— 这是换用集群汇总指标后的直接收益。
# 右侧必须分组：若聚合成整集群标量会恒等于 1，master 过滤将静默失效。
_COMPACTION_JOIN_DIMENSIONS = ["cluster_domain", "instance_host"]

_compaction_score_factory = _doris_metric_factory(
    metric_field="doris_fe_max_tablet_compaction_score",
    aggregation="max",
    group_by=list(_COMPACTION_JOIN_DIMENSIONS),
)
_node_info_master_factory = _doris_metric_factory(
    metric_field="node_info",
    aggregation="max",
    filters=[{"label_name": "type", "op": "equal", "value": "is_master"}],
    group_by=list(_COMPACTION_JOIN_DIMENSIONS),
)


DORIS_METRIC_REGISTRY: Dict[str, DorisMetricSpec] = {
    # ------------------------------ 系统层 ------------------------------
    DorisMetricName.CPU_USAGE.value: DorisMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="cpu_summary:usage", aggregation="avg", group_by=["bk_target_ip"]
        ),
        applicable_roles=ALL_ROLES,
        desc="CPU 使用率",
        unit=DorisMetricUnit.PERCENT.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=80,
        fatal_threshold=None,
        threshold_method="gte",
        summary_group="resource",
    ),
    DorisMetricName.MEMORY_USAGE.value: DorisMetricSpec(
        # 沿用 Kafka 组件的内存指标口径（kafka/impl/kafka_metrics.py 的 memory_usage_*）：
        # bkmonitor:dbm_system:mem:pct_used，该表在 kafka/pulsar/redis 三个组件均在使用。
        builder_factory=_system_metric_factory(
            metric_name="mem:pct_used", aggregation="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=ALL_ROLES,
        desc="内存使用率",
        unit=DorisMetricUnit.PERCENT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 无对应告警模板，不做健康判定（同 Kafka，其内存指标亦无阈值）
        summary_group="resource",
        extra_note="系统内存使用率，含堆外与页缓存；FE 堆内使用率请查 jvm_heap_usage",
    ),
    DorisMetricName.DISK_USAGE.value: DorisMetricSpec(
        builder_factory=_disk_usage_factory,
        applicable_roles=ALL_ROLES,
        desc="磁盘分区使用率",
        unit=DorisMetricUnit.PERCENT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=75,
        fatal_threshold=80,
        threshold_method="gte",
        summary_group="resource",
        extra_note="已排除 / 与 /usr/local 挂载点。本指标是操作系统分区水位；" "BE 数据盘水位请查 capacity_usage",
    ),
    DorisMetricName.SYSTEM_LOAD1.value: DorisMetricSpec(
        builder_factory=_system_metric_factory(metric_name="load:load1", aggregation="avg", group_by=["bk_target_ip"]),
        applicable_roles=ALL_ROLES,
        desc="系统 1 分钟平均负载",
        unit=DorisMetricUnit.DIMENSIONLESS.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 无对应告警模板，不做健康判定
        summary_group="resource",
    ),
    DorisMetricName.TCP_ESTABLISHED.value: DorisMetricSpec(
        # dashboard 中该指标用 max 聚合而非 avg（连接数取峰值更有意义）
        builder_factory=_system_metric_factory(
            metric_name="netstat:cur_tcp_estab", aggregation="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=ALL_ROLES,
        desc="TCP 已建立连接数",
        unit=DorisMetricUnit.CONNECTION.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="resource",
    ),
    DorisMetricName.NET_RECV.value: DorisMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="net:speed_recv", aggregation="avg", group_by=["bk_target_ip"]
        ),
        applicable_roles=ALL_ROLES,
        desc="网络入流量",
        unit=DorisMetricUnit.BYTES_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="resource",
    ),
    DorisMetricName.NET_SENT.value: DorisMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="net:speed_sent", aggregation="avg", group_by=["bk_target_ip"]
        ),
        applicable_roles=ALL_ROLES,
        desc="网络出流量",
        unit=DorisMetricUnit.BYTES_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="resource",
    ),
    # ---------------------------- Doris 专有层 ----------------------------
    DorisMetricName.CAPACITY_USAGE.value: DorisMetricSpec(
        builder_factory=_ratio_metric_factory(
            numerator=_capacity_avail_factory,
            denominator=_capacity_total_factory,
            expression="100 * (1 - {a} / {b})",
        ),
        applicable_roles=BE_ROLES,
        desc="BE 数据盘使用率",
        unit=DorisMetricUnit.PERCENT.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 阈值经组件负责人确认后调整为 80/90，并已同步修改 Doris Capacity.json。
        # 换用 1-avail/total 口径后数值普遍高于原 local_used/total，故阈值相应上调。
        warning_threshold=80,
        fatal_threshold=90,
        threshold_method="gte",
        summary_group="capacity",
        extra_note="按 1-可用/总量 计算，已计入 BE 预留空间与同盘非 Doris 占用；" "可按 instance_role 分组区分热/温/冷节点，作为分层扩容依据",
    ),
    DorisMetricName.JVM_HEAP_USAGE.value: DorisMetricSpec(
        builder_factory=_ratio_metric_factory(
            numerator=_jvm_heap_used_factory,
            denominator=_jvm_heap_max_factory,
            expression="100 * {a} / {b}",
        ),
        applicable_roles=FE_ROLES,
        desc="FE JVM 堆内存使用率",
        unit=DorisMetricUnit.PERCENT.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # PromQL 内已固化 instance_role 限定 follower|observer，外层不再追加
        role_filter_builtin=True,
        warning_threshold=80,
        fatal_threshold=None,
        threshold_method="gte",
        summary_group="capacity",
        extra_note="固定覆盖 follower 与 observer 全部 FE，不支持按单一 FE 角色过滤；" "仅反映堆内使用，系统内存请查 memory_usage",
    ),
    DorisMetricName.QUERY_ERR_RATE.value: DorisMetricSpec(
        builder_factory=_doris_metric_factory(
            metric_field="doris_fe_query_err_rate",
            aggregation="avg",
            group_by=["instance_host"],
        ),
        applicable_roles=FE_ROLES,
        # 语义经组件负责人确认：单台 FE 上查询失败次数的每秒速率，不是错误占比。
        # 原先标为 unit="%" 属误标 —— 告警模板与采集配置均无单位信息，
        # dashboard「Query Error [1m]」面板该 target 的 unit 为 short 而非 percent
        # （同 dashboard 的 12 个真百分比面板一律标 percent）。
        desc="单台 FE 查询失败速率",
        unit=DorisMetricUnit.COUNT_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=5,
        fatal_threshold=None,
        threshold_method="gte",
        summary_group="query",
        extra_note="单实例失败速率（次/秒），不是错误占比，不要按百分比解读",
    ),
    DorisMetricName.TXN_FAILED_RATE.value: DorisMetricSpec(
        # 依据 Doris Transaction failed rate.json：irate(doris_fe_txn_counter{type="failed"}[2m])
        # 必须用 irate 而非 rate：事务失败是突发型故障，rate 会把窗口内的峰值摊薄
        # （1 分钟内 90 次、2m 窗口下 irate≈1.5/s 而 rate≈0.75/s），导致漏报。
        builder_factory=_doris_metric_factory(
            metric_field="doris_fe_txn_counter",
            aggregation="avg",
            filters=[{"label_name": "type", "op": "equal", "value": "failed"}],
            range_function="irate",
            time_window="2m",
            group_by=[],
        ),
        applicable_roles=FE_ROLES,
        desc="FE 事务失败速率",
        unit=DorisMetricUnit.COUNT_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 阈值经组件负责人确认后由 5/10 收紧为 1/5，已同步修改告警模板
        warning_threshold=1,
        fatal_threshold=5,
        threshold_method="gte",
        summary_group="transaction",
    ),
    DorisMetricName.TXN_REJECT_RATE.value: DorisMetricSpec(
        # 依据 Doris Transaction reject rate.json：irate(doris_fe_txn_counter{type="reject"}[2m])
        builder_factory=_doris_metric_factory(
            metric_field="doris_fe_txn_counter",
            aggregation="avg",
            filters=[{"label_name": "type", "op": "equal", "value": "reject"}],
            range_function="irate",
            time_window="2m",
            group_by=[],
        ),
        applicable_roles=FE_ROLES,
        desc="FE 事务拒绝速率",
        unit=DorisMetricUnit.COUNT_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 阈值经组件负责人确认后由 5/10 收紧为 1/5，已同步修改告警模板
        warning_threshold=1,
        fatal_threshold=5,
        threshold_method="gte",
        summary_group="transaction",
    ),
    DorisMetricName.EDITLOG_WRITE_LATENCY.value: DorisMetricSpec(
        builder_factory=_doris_metric_factory(
            metric_field="doris_fe_editlog_write_latency_ms",
            aggregation="avg",
            filters=[{"label_name": "quantile", "op": "equal", "value": "0.99"}],
            group_by=["instance_host"],
        ),
        applicable_roles=FE_ROLES,
        desc="FE 元数据 editlog 写入延迟 P99",
        unit=DorisMetricUnit.MILLISECOND.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=None,
        fatal_threshold=1000,
        threshold_method="gte",
        summary_group="metadata",
    ),
    DorisMetricName.IMAGE_PUSH_FAILED.value: DorisMetricSpec(
        builder_factory=_doris_metric_factory(
            metric_field="doris_fe_image_push",
            aggregation="max",
            filters=[{"label_name": "type", "op": "equal", "value": "failed"}],
            group_by=["instance_host"],
        ),
        applicable_roles=FE_ROLES,
        desc="FE 元数据镜像推送失败次数",
        unit=DorisMetricUnit.COUNT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=None,
        fatal_threshold=1,
        # 注意：image_push 用 gt、image_write 用 gte，两者不同，照抄告警模板不做统一
        threshold_method="gt",
        summary_group="metadata",
    ),
    DorisMetricName.IMAGE_WRITE_FAILED.value: DorisMetricSpec(
        builder_factory=_doris_metric_factory(
            metric_field="doris_fe_image_write",
            aggregation="max",
            filters=[{"label_name": "type", "op": "equal", "value": "failed"}],
            group_by=["instance_host"],
        ),
        applicable_roles=FE_ROLES,
        desc="FE 元数据镜像写入失败次数",
        unit=DorisMetricUnit.COUNT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=None,
        fatal_threshold=1,
        threshold_method="gte",
        summary_group="metadata",
    ),
    DorisMetricName.COMPACTION_SCORE.value: DorisMetricSpec(
        builder_factory=_ratio_metric_factory(
            numerator=_compaction_score_factory,
            denominator=_node_info_master_factory,
            # 两侧维度完全一致，PromQL 默认向量匹配即可逐实例对齐，
            # 无需 ignoring/group_left（换用集群汇总指标后不再有 backend 维度差）
            expression="{a} * {b}",
        ),
        applicable_roles=FE_ROLES,
        desc="集群 Tablet 最大 Compaction 分数（取自 Master FE）",
        unit=DorisMetricUnit.DIMENSIONLESS.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=None,
        fatal_threshold=250,
        threshold_method="gte",
        summary_group="metadata",
    ),
}


# 性能摘要采集的关键指标。
#
# 控制在 8 个以内：get_doris_performance_summary 是串行 N 次 unify_query 调用，
# 指标过多会让摘要接口过慢。选取原则为「有平台既定告警阈值因而可做健康判定」。
SUMMARY_KEY_METRICS: Tuple[str, ...] = (
    DorisMetricName.CPU_USAGE.value,
    DorisMetricName.DISK_USAGE.value,
    DorisMetricName.CAPACITY_USAGE.value,
    DorisMetricName.JVM_HEAP_USAGE.value,
    DorisMetricName.QUERY_ERR_RATE.value,
    DorisMetricName.TXN_FAILED_RATE.value,
    DorisMetricName.EDITLOG_WRITE_LATENCY.value,
    DorisMetricName.COMPACTION_SCORE.value,
)

# 摘要分组的中文名
SUMMARY_GROUP_NAMES: Dict[str, str] = {
    "resource": "系统资源",
    "capacity": "容量与内存",
    "query": "查询",
    "transaction": "事务",
    "metadata": "元数据",
}

# 单位标注为百分比的指标白名单。
#
# 由 test_percent_unit_matches_whitelist 锁定：新增指标若想标 PERCENT，
# 必须同步更新本白名单，从而被迫走一遍溯源确认，避免凭常识误标。
# 本白名单的依据是 dashboard 中对应面板的 unit 为 percent / percentunit。
PERCENT_METRICS: FrozenSet[str] = frozenset(
    {
        DorisMetricName.CPU_USAGE.value,
        DorisMetricName.MEMORY_USAGE.value,
        DorisMetricName.DISK_USAGE.value,
        DorisMetricName.CAPACITY_USAGE.value,
        DorisMetricName.JVM_HEAP_USAGE.value,
    }
)


def get_metric_spec(metric_name: str) -> Optional[DorisMetricSpec]:
    """按指标名取声明，不存在返回 None。"""
    return DORIS_METRIC_REGISTRY.get(metric_name)


def get_all_metric_names() -> List[str]:
    """全部合法指标名，用于错误提示中回带合法值。"""
    return list(DORIS_METRIC_REGISTRY.keys())
