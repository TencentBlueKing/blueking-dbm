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

from backend.db_meta.enums import InstanceRole
from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import PromQLMultiQueryBuilder, PromQLQueryBuilder
from backend.dbm_aiagent.mcp_tools.hdfs.enums import (
    DN_ROLES,
    METRIC_ALL_ROLES,
    NN_ROLES,
    HdfsAggFunction,
    HdfsMetricName,
    HdfsMetricUnit,
)

# HDFS 专有指标的数据源前缀。
#
# PromQLQueryBuilder._normalize_metric_name()（common/impl/promql_query.py）的前缀处理逻辑：
#   以 "mysql_" 开头       -> 补 mysqld exporter 前缀
#   不以 "bkmonitor:" 开头 -> 补 "bkmonitor:dbm_system:" 前缀
# 因此 HDFS 专有指标必须写全 "bkmonitor:" 前缀才能绕过 dbm_system 默认补全；
# 系统层指标则写短名（如 "cpu_summary:usage"），交由构造器自动补全。
#
# 取两段式（不带 "__default__:"）的依据：
#   db_monitor/constants.py  ClusterType.Hdfs 的容量 PromQL
#   db_periodic_task/local_tasks/hdfs/constants.py  MONITOR_QUERY_HDFS_TEMPLATE（Active NN 探测）
#   bk_dataview/dashboards/json/hdfs.json  「DataNode lastContact Top10」面板的原生 promql
#   告警模板 db_monitor/tpls/alarm/hdfs/*.json  data_label 为 exporter_dbm_hdfs_exporter
# 注：dashboard 另有「目录文件数」等面板用三段式 "...:__default__:"，两种写法在
# unify_query 侧等价，此处统一取两段式，与告警模板和周期任务保持一致。
HDFS_EXPORTER_PREFIX = "bkmonitor:exporter_dbm_hdfs_exporter:"

# NameNode 角色过滤条件。固化在 Active 相关子查询内部，不依赖外层注入。
NN_ROLE_FILTER: Dict = {
    "label_name": "instance_role",
    "op": "equal",
    "value": InstanceRole.HDFS_NAME_NODE.value,
}

# Active NameNode 过滤的向量匹配标签。
#
# 两侧子查询都必须在 group_by 中显式声明这些标签，否则生成的 by(...) 子句缺失该标签、
# on() 匹配恒为空且不会报错（静默返回空 series）—— 这是本模块最易静默失败的点。
#
# 原因：PromQLMultiQueryBuilder.build_promql()（common/impl/promql_query.py）
# 只把父级 filters extend 进子构造器，group_by 不传递；
# query_promql_metrics_with_roles()（common/views/promql_query.py）的
# group_by.append("cluster_domain") 也只作用于父级 builder，而父级在多查询场景下
# 并不产出 PromQL（metric_name 为空），其 group_by 不会出现在任何子查询里。
ACTIVE_NN_JOIN_LABELS: List[str] = ["cluster_domain", "instance_host"]

# Active NameNode State 子查询在表达式中的 alias。
# _build_query_builder 同步外层 aggregation 到子构造器时必须跳过该 alias，
# 以保留其固定的 min 聚合（照抄告警模板口径）。
ACTIVE_NN_STATE_ALIAS = "s"

# 默认采样步长
DEFAULT_STEP = "1m"

# 最小采样步长（秒）。与 HDFS exporter 60 秒采集周期对齐：更小步长不会得到更多数据点，
# 同时挡住 "0s" 这类在点数估算处除零的取值。
# 序列化器与 impl 的 step 校验共用此常量，调用处禁止写裸值（如 60 / "1m"）。
MIN_STEP_SECONDS = 60

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
# common 的构造器里有 MAX_QUERY_RANGE_SECONDS = 24h，但 PromQLQueryBuilder.prepare_promql()
# （common/impl/promql_query.py）中那处 raise 已被注释成 pass，对 HDFS 不生效；该构造器为公共构造器，
# 放开那处注释会连带改变其他调用方的现有行为，故在 HDFS 侧自行兜住。
MAX_QUERY_RANGE_SECONDS = 30 * 24 * 3600

# end_time 允许超出服务端当前时间的秒数，容忍调用方与服务端的时钟偏差。
END_TIME_MAX_FUTURE_SKEW_SECONDS = 300

# 单条时间线的点数上限。
MAX_DATAPOINTS = 1500


@dataclass(frozen=True)
class HdfsMetricSpec:
    """单个 HDFS 指标的声明。

    使用 builder_factory 而非 builder 实例，原因：
    query_promql_metrics_with_roles()（common/views/promql_query.py）会对传入的
    构造器原地 append filters 且无去重，PromQLMultiQueryBuilder.build_promql()
    （common/impl/promql_query.py）还会把父级 filters extend 进子构造器。
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
    # 数值单位，取值必须落在 HdfsMetricUnit 内。
    # 单位用单值枚举而非布尔标记：它是多值互斥属性，且会被智能体直接读进结论。
    unit: str
    # 默认聚合方式
    default_aggregation: str
    # 支持的聚合方式
    supported_aggregations: FrozenSet[str]
    # True 表示 PromQL 内已固化 instance_role 过滤（以及 Active NameNode 筛选），
    # 外层不应再追加角色条件，否则会产生重复甚至冲突的 label 条件；
    # 调用方传入 instance_roles 时直接报错并说明固定覆盖范围
    role_filter_builtin: bool = False
    # 健康判定阈值。取自 db_monitor/tpls/alarm/ 下的告警模板，None 表示不判定
    warning_threshold: Optional[float] = None
    fatal_threshold: Optional[float] = None
    # 阈值比较方式：gte 表示 >= 命中，gt 表示 > 命中（照抄告警模板，不做统一）
    threshold_method: str = "gte"
    # 摘要中的归类
    summary_group: str = ""
    # 面向智能体的补充说明，输出为响应的 note 字段
    extra_note: str = ""


_ALL_AGGREGATIONS = frozenset(HdfsAggFunction.get_values())


def _system_metric_factory(
    metric_name: str,
    aggregation: str,
    range_function: str = None,
    time_window: str = None,
    group_by: List[str] = None,
    filters: List[Dict] = None,
) -> Callable[[], PromQLQueryBuilder]:
    """系统层指标（bkmonitor:dbm_system:*）的构造器工厂。

    metric_name 写短名，由 build_promql() 自动补 bkmonitor:dbm_system: 前缀。
    group_by 传空列表表示不额外分组（注意区别于 None，后者才取默认维度 bk_target_ip）。
    """

    default_group_by = ["bk_target_ip"] if group_by is None else group_by

    def _factory() -> PromQLQueryBuilder:
        return PromQLQueryBuilder(
            metric_name=metric_name,
            group_by=list(default_group_by),
            aggregation=aggregation,
            range_function=range_function,
            time_window=time_window,
            step=DEFAULT_STEP,
            filters=[dict(f) for f in (filters or [])],
        )

    return _factory


def _hdfs_metric_factory(
    metric_field: str,
    aggregation: str,
    filters: List[Dict] = None,
    range_function: str = None,
    time_window: str = None,
    group_by: List[str] = None,
) -> Callable[[], PromQLQueryBuilder]:
    """HDFS 专有指标（exporter_dbm_hdfs_exporter）的构造器工厂。

    group_by 传空列表表示不额外分组（注意区别于 None，后者才取默认维度 instance_host）。
    """

    default_group_by = ["instance_host"] if group_by is None else group_by

    def _factory() -> PromQLQueryBuilder:
        return PromQLQueryBuilder(
            metric_name=HDFS_EXPORTER_PREFIX + metric_field,
            group_by=list(default_group_by),
            aggregation=aggregation,
            range_function=range_function,
            time_window=time_window,
            step=DEFAULT_STEP,
            filters=[dict(f) for f in (filters or [])],
        )

    return _factory


def _expr_metric_factory(
    sub_factories: Dict[str, Callable[[], PromQLQueryBuilder]],
    expression: str,
) -> Callable[[], PromQLMultiQueryBuilder]:
    """多子查询表达式型指标的构造器工厂。

    execute_promql()（common/impl/promql_query.py）对 expression 的处理是
    expr.format(**prom_queries) 纯字符串渲染、不做语法解析，因此不止支持四则运算，
    也能直接书写 and on(...)、== 1 这类原生 PromQL 集合与比较运算。
    注意 expression 自身不得含除占位符以外的花括号（否则 str.format 会报错），
    label 选择器只出现在被渲染进来的子查询字符串里。

    注意 PromQLMultiQueryBuilder.get_aggregation() 取的是第一个子构造器的 aggregation，
    故每个子构造器必须显式设置 aggregation，否则对外返回的 aggregation 为 None。

    另注意 PromQLMultiQueryBuilder.build_promql() 会用父级 time_window
    覆盖子构造器的 time_window，子构造器自己设的 time_window 不生效。
    本模块的父级不设 time_window，由 PromQLQueryBuilder.prepare_promql() 取 step 兜底，
    因此子查询的 range_function 窗口随 step 变化（摘要 1h、默认 1m）。
    """

    def _factory() -> PromQLMultiQueryBuilder:
        return PromQLMultiQueryBuilder(
            queries={alias: factory() for alias, factory in sub_factories.items()},
            expression=expression,
            step=DEFAULT_STEP,
            filters=[],
        )

    return _factory


def _namenode_state_factory(group_by: List[str] = None) -> Callable[[], PromQLQueryBuilder]:
    """hadoop_namenode_State 子查询工厂。

    固定 min 聚合，与告警模板一致（原模板为 MIN(hadoop_namenode_State)）。
    group_by 默认显式含 ACTIVE_NN_JOIN_LABELS —— 这是 on() 向量匹配成立的前提，
    详见 ACTIVE_NN_JOIN_LABELS 的注释。

    刻意不设 range_function：State 用来判断每个时间点谁是 Active，必须取瞬时值。
    若改为 max_over_time，窗口内发生过主备切换时两台 NameNode 都会被算作 Active。
    代价是业务侧取窗口峰值、State 侧取窗口末尾的瞬时值：切换所在窗口内，
    原 Active 的峰值会被过滤掉。影响仅限切换所在的一个窗口，可以接受。
    """
    default_group_by = list(ACTIVE_NN_JOIN_LABELS) if group_by is None else group_by
    return _hdfs_metric_factory(
        metric_field="hadoop_namenode_State",
        aggregation="min",
        filters=[dict(NN_ROLE_FILTER)],
        group_by=list(default_group_by),
    )


def _active_namenode_factory(
    business_factories: Dict[str, Callable[[], PromQLQueryBuilder]],
    business_expr: str,
) -> Callable[[], PromQLMultiQueryBuilder]:
    """Active NameNode 专有指标的构造器工厂。

    自动注入 alias 为 's' 的 hadoop_namenode_State 子查询，并把业务表达式包成：

        (<business_expr>) and on(cluster_domain, instance_host) ({s} == 1)

    Active = 1 的语义依据：db_periodic_task/local_tasks/hdfs/constants.py 中的
    MONITOR_QUERY_HDFS_TEMPLATE（平台用 hadoop_namenode_State ... == 1 探测当前主节点）。
    主备切换时右侧时间线自动跟随，调用方无需也无法指定主节点。

    为何用集合运算符 and on() 而不照抄告警模板原先的算术写法
    （已于本次改造统一修正为过滤语义，见 db_monitor/tpls/alarm/hdfs/*.json）：

      写法                      Standby 时间线的结果            左右维度不一致时
      ------------------------  ------------------------------  ----------------------
      {a} * {s}                 值变成 0，会稀释性能摘要的       向量匹配失败，被迫补
                                min/avg，制造虚假的「健康」      ignoring(...) group_left
      {a} / {s}                 State=0 时产出 +Inf，直接       同上
                                触发假致命判定
      {a} and on(...) ({s}==1)  整条时间线被丢弃，左侧值与       on() 只比对列出的标签、
                                标签原样保留                     忽略其余，天然兼容

    and 是集合交运算符：保留左侧那些在右侧存在标签匹配的样本，只过滤、不改值、不丢标签。
    {s} == 1 中的 == 作用于 instant vector 且无 bool 修饰符时是 filter 语义
    （只保留取值为 1 的样本），因此是白名单过滤，不依赖 Standby 上 State 的具体取值
    （取 0、2 或无上报都不影响正确性）。

    两个额外收益：
      1. datanode_last_contact 不需要 ignoring(datanode) group_left。告警模板原先要加
         是因为乘法要求两侧标签集匹配而 State 侧没有 datanode 维度；on() 只比对列出的
         标签，左侧的 datanode 标签原样保留。group_left 的语义是「多对一连接并保留左侧
         标签」，适用于需要右侧值参与运算的场景，我们既不要右侧的值也不要右侧的标签。
      2. and / or / unless 这三个集合运算符允许多对多匹配，故左侧按 datanode 展开的
         多条时间线匹配右侧单条 State 时间线不会报 many-to-many 错误。

    运算符优先级：PromQL 中 and 低于算术与比较运算符，故
    100 * {a} / {b} and on(...) ({s} == 1) 会正确解析为
    (100 * {a} / {b}) and on(...) ({s} == 1)；为可读性仍显式加括号。
    """
    sub_factories = dict(business_factories)
    sub_factories[ACTIVE_NN_STATE_ALIAS] = _namenode_state_factory()

    # 用字符串拼接而非 f-string / str.format 构造：business_expr 自身含 {a} 这类
    # 占位符，走 format 会被二次替换掉。
    join_labels = ", ".join(ACTIVE_NN_JOIN_LABELS)
    state_placeholder = "{" + ACTIVE_NN_STATE_ALIAS + "}"
    expression = "(" + business_expr + ") and on(" + join_labels + ") (" + state_placeholder + " == 1)"
    return _expr_metric_factory(sub_factories=sub_factories, expression=expression)


# ---------------------------------------------------------------------------
# 系统层指标
#
# NameNode 与 DataNode 共用同一底层 dbm_system 表，仅靠 instance_role 标签区分角色。
# 依据：bk_dataview/dashboards/json/hdfs.json 中 NameNode 行与 DataNode 行的「CPU使用率」面板，
# 两者的 cpu_summary:usage 完全同构，差异只在 instance_role。
# 其余短名依据同一 dashboard：
#   netstat:cur_tcp_estab  「连接数」面板（max by bk_target_ip）
#   load:load1             DataNode 行「系统负载（1m）」面板（avg by bk_target_ip）
#   net:speed_recv         DataNode 行「入流量」面板（avg by bk_target_ip）
#   net:speed_sent         DataNode 行「出流量」面板（avg by bk_target_ip）
# ---------------------------------------------------------------------------

# 区间函数口径（每个指标在注册表中显式声明 range_function）：
# 本模块指标均为瞬时值型（使用率、块数、时长、连接数、队列长度），统一取 max_over_time，
# 窗口不设、由 prepare_promql() 取 step。摘要（step=1h）因此得到「每小时内的峰值」
# 而不是「每小时抽一个瞬时样本」，短时尖峰不会漏掉；时序查询默认 step=1m，
# 与 HDFS exporter 60 秒的采集周期对齐。
# 例外：hadoop_namenode_State（Active 判定子查询与 namenode_state 指标）保持瞬时值，
# 理由见 _namenode_state_factory()。
# 新增累计型计数器时不能照抄 max，应按语义改用 rate / increase。

# 磁盘使用率需排除系统盘与安装盘，否则系统盘水位会混入数据盘判断。
# 依据：dashboard DataNode 行「总磁盘使用率」面板带 mount_point!="/" 与 mount_point!="/usr/local"。
DISK_USAGE_EXCLUDE_MOUNTS: List[Dict] = [
    {"label_name": "mount_point", "op": "not_equal", "value": "/"},
    {"label_name": "mount_point", "op": "not_equal", "value": "/usr/local"},
]


def _disk_usage_factory() -> PromQLQueryBuilder:
    """磁盘分区使用率。

    取 dbm_system:disk:in_use（分区级百分比）而非 dashboard「总磁盘使用率」面板的
    sum(disk:used)/sum(disk:total)：后者是整集群加权比值且量纲为 0~1 的比例，
    会把单块告急的数据盘摊薄掉；in_use 配合 max 聚合与 mount_point 分组可直接
    定位水位最高的分区，且与平台各组件的主机磁盘告警模板同指标（dbm_system.disk in_use）。

    range_function 取 max 而非 avg：摘要健康判定看峰值是否越线，avg_over_time 会把窗口内的
    毛刺平均掉，判断偏乐观。
    """
    return PromQLQueryBuilder(
        metric_name="disk:in_use",
        group_by=["bk_target_ip", "mount_point"],
        aggregation="max",
        range_function="max",
        # 刻意不设 time_window：PromQLQueryBuilder.prepare_promql()
        # 会在 time_window 为空时取 step，这样摘要路径（step=1h）的 max_over_time 窗口
        # 自动跟随为 1h；若在此硬编码 1m，摘要会退化成「每小时抽一个 1 分钟样本」，
        # 丢掉窗口内的毛刺。
        step=DEFAULT_STEP,
        filters=[dict(f) for f in DISK_USAGE_EXCLUDE_MOUNTS],
    )


# ---------------------------------------------------------------------------
# NameNode 专有层指标
#
# 除 namenode_state 外全部固化 Active 过滤（role_filter_builtin=True）：
# Standby NameNode 的这些指标值无业务意义，混入会直接污染结论。
# ---------------------------------------------------------------------------

# 集群容量使用率 = 100 * capacity_used / capacity_total
# 依据：db_monitor/tpls/alarm/hdfs/HDFS 容量使用率.json 的 promql
#       db_monitor/constants.py 中 ClusterType.Hdfs 的容量 PromQL（平台容量采集用同一对字段）
# 分子分母各自取窗口峰值；capacity_total 只在扩缩容时变化，窗口内近似常量，比值即窗口内使用率峰值。
_capacity_used_factory = _hdfs_metric_factory(
    metric_field="hadoop_namenode_capacity_used",
    aggregation="avg",
    range_function="max",
    filters=[dict(NN_ROLE_FILTER)],
    group_by=list(ACTIVE_NN_JOIN_LABELS),
)
_capacity_total_factory = _hdfs_metric_factory(
    metric_field="hadoop_namenode_capacity_total",
    aggregation="avg",
    range_function="max",
    filters=[dict(NN_ROLE_FILTER)],
    group_by=list(ACTIVE_NN_JOIN_LABELS),
)

# DataNode 失联时长：业务侧额外带 datanode 维度（不进 on()），
# 以便智能体直接定位是哪台 DataNode 失联。
_DATANODE_LAST_CONTACT_GROUP_BY = ACTIVE_NN_JOIN_LABELS + ["datanode"]

# ---------------------------------------------------------------------------
# DataNode 专有层指标
# ---------------------------------------------------------------------------

# DataNode JVM 堆使用率 = 100 * mem_heap_used_m / mem_heap_max_m
# 依据：dashboard DataNode 行「jvm heap使用率」面板的 hadoop_datanode_mem_heap_used_m 与
# hadoop_datanode_mem_heap_max_m。该面板 unit 为 percentunit（0~1 比值），这里乘 100 输出百分比。
# 不固化角色：DataNode 无主备概念，外层按 instance_roles 注入即可。
# 分子分母各自取窗口峰值；mem_heap_max_m 是 JVM 配置上限，进程不重启即为常量，比值即窗口内使用率峰值。
_DN_HEAP_GROUP_BY = ["cluster_domain", "instance_host", "instance_role"]
_DN_ROLE_FILTER: Dict = {
    "label_name": "instance_role",
    "op": "equal",
    "value": InstanceRole.HDFS_DATA_NODE.value,
}

_dn_heap_used_factory = _hdfs_metric_factory(
    metric_field="hadoop_datanode_mem_heap_used_m",
    aggregation="avg",
    range_function="max",
    filters=[dict(_DN_ROLE_FILTER)],
    group_by=list(_DN_HEAP_GROUP_BY),
)
_dn_heap_max_factory = _hdfs_metric_factory(
    metric_field="hadoop_datanode_mem_heap_max_m",
    aggregation="avg",
    range_function="max",
    filters=[dict(_DN_ROLE_FILTER)],
    group_by=list(_DN_HEAP_GROUP_BY),
)


HDFS_METRIC_REGISTRY: Dict[str, HdfsMetricSpec] = {
    # ------------------------------ 系统层 ------------------------------
    HdfsMetricName.CPU_USAGE.value: HdfsMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="cpu_summary:usage", aggregation="avg", range_function="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=METRIC_ALL_ROLES,
        desc="CPU 使用率",
        unit=HdfsMetricUnit.PERCENT.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=90,
        fatal_threshold=None,
        threshold_method="gte",
        summary_group="resource",
    ),
    HdfsMetricName.MEMORY_USAGE.value: HdfsMetricSpec(
        # bkmonitor:dbm_system:mem:pct_used 是平台级操作系统指标表。
        # hdfs.json 自身没有内存面板，故此处无 HDFS 专属证据，但表与过滤方式通用。
        builder_factory=_system_metric_factory(
            metric_name="mem:pct_used", aggregation="max", range_function="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=METRIC_ALL_ROLES,
        desc="内存使用率",
        unit=HdfsMetricUnit.PERCENT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 平台各组件均无主机内存告警模板，不做健康判定
        summary_group="resource",
        extra_note="系统内存使用率，含堆外与页缓存；DataNode 堆内使用率请查 datanode_jvm_heap_usage",
    ),
    HdfsMetricName.DISK_USAGE.value: HdfsMetricSpec(
        builder_factory=_disk_usage_factory,
        applicable_roles=METRIC_ALL_ROLES,
        desc="磁盘分区使用率",
        unit=HdfsMetricUnit.PERCENT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        warning_threshold=80,
        fatal_threshold=90,
        threshold_method="gte",
        summary_group="resource",
        extra_note=(
            "已排除 / 与 /usr/local 挂载点（与 HDFS 仪表盘「总磁盘使用率」面板一致）。"
            "本指标是操作系统分区水位，结果按 mount_point 展开，可定位具体磁盘；"
            "HDFS 逻辑容量水位请查 capacity_usage。"
        ),
    ),
    HdfsMetricName.SYSTEM_LOAD1.value: HdfsMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="load:load1", aggregation="avg", range_function="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=METRIC_ALL_ROLES,
        desc="系统 1 分钟平均负载",
        unit=HdfsMetricUnit.DIMENSIONLESS.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 无对应告警模板，不做健康判定
        summary_group="resource",
        extra_note="需结合机器 CPU 核数解读，负载值本身无统一阈值",
    ),
    HdfsMetricName.TCP_ESTABLISHED.value: HdfsMetricSpec(
        # dashboard hdfs.json 中 NameNode 行与 DataNode 行的「连接数」面板均用 max 聚合而非 avg
        # （连接数取峰值更有意义）
        builder_factory=_system_metric_factory(
            metric_name="netstat:cur_tcp_estab", aggregation="max", range_function="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=METRIC_ALL_ROLES,
        desc="TCP 已建立连接数",
        unit=HdfsMetricUnit.CONNECTION.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="resource",
    ),
    HdfsMetricName.NET_RECV.value: HdfsMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="net:speed_recv", aggregation="avg", range_function="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=METRIC_ALL_ROLES,
        desc="网络入流量",
        unit=HdfsMetricUnit.BYTES_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="resource",
    ),
    HdfsMetricName.NET_SENT.value: HdfsMetricSpec(
        builder_factory=_system_metric_factory(
            metric_name="net:speed_sent", aggregation="avg", range_function="max", group_by=["bk_target_ip"]
        ),
        applicable_roles=METRIC_ALL_ROLES,
        desc="网络出流量",
        unit=HdfsMetricUnit.BYTES_PER_SEC.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="resource",
    ),
    # --------------------------- NameNode 专有层 ---------------------------
    HdfsMetricName.CAPACITY_USAGE.value: HdfsMetricSpec(
        builder_factory=_active_namenode_factory(
            business_factories={"a": _capacity_used_factory, "b": _capacity_total_factory},
            business_expr="100 * {a} / {b}",
        ),
        applicable_roles=NN_ROLES,
        desc="HDFS 集群容量使用率",
        unit=HdfsMetricUnit.PERCENT.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        role_filter_builtin=True,
        # 依据 db_monitor/tpls/alarm/hdfs/HDFS 容量使用率.json（warning 80 / fatal 86）
        warning_threshold=80,
        fatal_threshold=86,
        threshold_method="gte",
        summary_group="capacity",
        extra_note=(
            "HDFS 文件系统逻辑容量水位（已计入副本放大），区别于 disk_usage 的操作系统分区水位。" "已固化只取当前 Active NameNode，主备切换自动跟随，不支持传 instance_roles"
        ),
    ),
    HdfsMetricName.CORRUPT_BLOCKS.value: HdfsMetricSpec(
        builder_factory=_active_namenode_factory(
            business_factories={
                "a": _hdfs_metric_factory(
                    metric_field="hadoop_namenode_corrupt_blocks",
                    aggregation="avg",
                    range_function="max",
                    filters=[dict(NN_ROLE_FILTER)],
                    group_by=list(ACTIVE_NN_JOIN_LABELS),
                )
            },
            business_expr="{a}",
        ),
        applicable_roles=NN_ROLES,
        desc="损坏块数量",
        unit=HdfsMetricUnit.COUNT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        role_filter_builtin=True,
        # 依据 db_monitor/tpls/alarm/hdfs/HDFS CorruptBlocks.json（warning 10 / fatal 500）
        warning_threshold=10,
        fatal_threshold=500,
        threshold_method="gte",
        summary_group="block",
        extra_note="损坏块仍有其他可用副本，但需尽快修复；已固化只取 Active NameNode，不支持传 instance_roles",
    ),
    HdfsMetricName.MISSING_BLOCKS.value: HdfsMetricSpec(
        builder_factory=_active_namenode_factory(
            business_factories={
                "a": _hdfs_metric_factory(
                    metric_field="hadoop_namenode_missing_blocks",
                    aggregation="avg",
                    range_function="max",
                    filters=[dict(NN_ROLE_FILTER)],
                    group_by=list(ACTIVE_NN_JOIN_LABELS),
                )
            },
            business_expr="{a}",
        ),
        applicable_roles=NN_ROLES,
        desc="丢失块数量",
        unit=HdfsMetricUnit.COUNT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        role_filter_builtin=True,
        # 依据 db_monitor/tpls/alarm/hdfs/HDFS MissingBlocks.json（warning 10 / fatal 500）
        warning_threshold=10,
        fatal_threshold=500,
        threshold_method="gte",
        summary_group="block",
        extra_note="丢失块意味着所有副本均不可用、数据已实际丢失，比 corrupt_blocks 更严重；" "已固化只取 Active NameNode，不支持传 instance_roles",
    ),
    HdfsMetricName.UNCHECKPOINTED_TXNS.value: HdfsMetricSpec(
        builder_factory=_active_namenode_factory(
            business_factories={
                "a": _hdfs_metric_factory(
                    metric_field="hadoop_namenode_transactions_since_last_checkpoint",
                    aggregation="avg",
                    range_function="max",
                    filters=[dict(NN_ROLE_FILTER)],
                    group_by=list(ACTIVE_NN_JOIN_LABELS),
                )
            },
            business_expr="{a}",
        ),
        applicable_roles=NN_ROLES,
        desc="距上次 Checkpoint 的未合并事务数",
        unit=HdfsMetricUnit.COUNT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        role_filter_builtin=True,
        # 依据 db_monitor/tpls/alarm/hdfs/HDFS EditLogRoll.json（warning 5e6 / fatal 6e6）
        warning_threshold=5000000,
        fatal_threshold=6000000,
        threshold_method="gte",
        summary_group="metadata",
        extra_note="持续偏高说明 Checkpoint（EditLog 合并）未正常进行，会拉长 NameNode 重启恢复时间；"
        "已固化只取 Active NameNode，不支持传 instance_roles",
    ),
    HdfsMetricName.DATANODE_LAST_CONTACT.value: HdfsMetricSpec(
        builder_factory=_active_namenode_factory(
            business_factories={
                "a": _hdfs_metric_factory(
                    metric_field="hadoop_namenode_live_nodes_last_contact",
                    aggregation="max",
                    range_function="max",
                    filters=[dict(NN_ROLE_FILTER)],
                    # 额外带 datanode 维度以定位具体节点；该标签不进 on()，
                    # 靠 on() 的部分标签匹配特性天然兼容，无需 ignoring(datanode) group_left
                    group_by=list(_DATANODE_LAST_CONTACT_GROUP_BY),
                )
            },
            business_expr="{a}",
        ),
        applicable_roles=NN_ROLES,
        desc="DataNode 与 NameNode 的失联时长",
        unit=HdfsMetricUnit.SECOND.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        role_filter_builtin=True,
        # 依据 db_monitor/tpls/alarm/hdfs/HDFS DataNode Last Contact.json（warning 570）
        warning_threshold=570,
        fatal_threshold=None,
        threshold_method="gte",
        summary_group="block",
        extra_note="由 Active NameNode 视角上报，按 datanode 标签区分具体 DataNode；"
        "超过 570 秒接近默认的 DataNode 判死阈值，会触发块复制风暴；"
        "已固化只取 Active NameNode，不支持传 instance_roles",
    ),
    HdfsMetricName.NAMENODE_STATE.value: HdfsMetricSpec(
        # 刻意不做 Active 固化，也不做 delta：
        # 告警模板 HDFS NameNode Failover.json 用 delta(MIN(State), 2m) 做切换检测，
        # 但把「状态变化量」做成 MCP 指标对智能体极不友好（它读到的不是状态本身）。
        # 此处直接暴露原始值并按 instance_host 展开，让智能体看到主备分布；
        # 切换检测仍交由平台告警。
        # 刻意不设 range_function：主备状态需要瞬时值，理由同 _namenode_state_factory()。
        builder_factory=_hdfs_metric_factory(
            metric_field="hadoop_namenode_State",
            aggregation="min",
            group_by=["instance_host"],
        ),
        applicable_roles=NN_ROLES,
        desc="NameNode 主备状态原始值",
        unit=HdfsMetricUnit.DIMENSIONLESS.value,
        default_aggregation="min",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 不设阈值，健康判定为 unknown
        summary_group="metadata",
        extra_note="取值 1 表示该实例为 Active NameNode；按 instance_host 分组可看到主备分布。"
        "语义与平台 Active NameNode 探测（hadoop_namenode_State == 1）一致。"
        "本指标不做健康判定，主备切换告警由平台 HDFS NameNode Failover 策略负责",
    ),
    # --------------------------- DataNode 与 RPC ---------------------------
    HdfsMetricName.DATANODE_JVM_HEAP_USAGE.value: HdfsMetricSpec(
        builder_factory=_expr_metric_factory(
            sub_factories={"a": _dn_heap_used_factory, "b": _dn_heap_max_factory},
            expression="100 * {a} / {b}",
        ),
        applicable_roles=DN_ROLES,
        desc="DataNode JVM 堆内存使用率",
        unit=HdfsMetricUnit.PERCENT.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        # 子查询 filters 已固化 instance_role=hdfs_datanode，外层不再追加
        role_filter_builtin=True,
        # 无对应告警模板，不做健康判定
        summary_group="capacity",
        extra_note="固定覆盖全部 DataNode，不支持传 instance_roles；仅反映堆内使用，系统内存请查 memory_usage",
    ),
    HdfsMetricName.DATANODE_XCEIVER_COUNT.value: HdfsMetricSpec(
        # 依据 dashboard hdfs.json DataNode 行「XceiverCount 连接数」面板
        builder_factory=_hdfs_metric_factory(
            metric_field="hadoop_datanode_xceiver_count",
            aggregation="max",
            range_function="max",
            group_by=["instance_host"],
        ),
        applicable_roles=DN_ROLES,
        desc="DataNode Xceiver 数据传输连接数",
        unit=HdfsMetricUnit.CONNECTION.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="rpc",
        extra_note="反映单台 DataNode 并发读写流数；接近 dfs.datanode.max.transfer.threads 配置上限时会拒绝新连接",
    ),
    HdfsMetricName.DATANODE_CALL_QUEUE_LENGTH.value: HdfsMetricSpec(
        # 依据 dashboard hdfs.json DataNode 行「CallQueueLength」面板
        builder_factory=_hdfs_metric_factory(
            metric_field="hadoop_datanode_call_queue_length",
            aggregation="max",
            range_function="max",
            group_by=["instance_host"],
        ),
        applicable_roles=DN_ROLES,
        desc="DataNode RPC 请求队列长度",
        unit=HdfsMetricUnit.COUNT.value,
        default_aggregation="max",
        supported_aggregations=_ALL_AGGREGATIONS,
        summary_group="rpc",
        extra_note="队列持续非空说明 DataNode RPC 处理能力已成瓶颈",
    ),
    HdfsMetricName.NAMENODE_RPC_QUEUE_TIME.value: HdfsMetricSpec(
        # 依据 dashboard hdfs.json「Queue & Processing Time」面板，面板 unit 为 ms
        builder_factory=_active_namenode_factory(
            business_factories={
                "a": _hdfs_metric_factory(
                    metric_field="hadoop_namenode_rpc_queue_time_avg_time",
                    aggregation="avg",
                    range_function="max",
                    filters=[dict(NN_ROLE_FILTER)],
                    group_by=list(ACTIVE_NN_JOIN_LABELS),
                )
            },
            business_expr="{a}",
        ),
        applicable_roles=NN_ROLES,
        desc="NameNode RPC 请求平均排队耗时",
        unit=HdfsMetricUnit.MILLISECOND.value,
        default_aggregation="avg",
        supported_aggregations=_ALL_AGGREGATIONS,
        role_filter_builtin=True,
        # 无对应告警模板，不做健康判定
        summary_group="rpc",
        extra_note="排队耗时（不含处理耗时）升高是 NameNode 过载的早期信号；" "已固化只取 Active NameNode，不支持传 instance_roles",
    ),
}


# 性能摘要采集的关键指标。
#
# 控制在 8 个以内：get_hdfs_performance_summary 是串行 N 次 unify_query 调用，
# 指标过多会让摘要接口过慢。选取原则为「有既定告警阈值因而可做健康判定」+ 系统资源基线。
SUMMARY_KEY_METRICS: Tuple[str, ...] = (
    HdfsMetricName.CPU_USAGE.value,
    HdfsMetricName.DISK_USAGE.value,
    HdfsMetricName.CAPACITY_USAGE.value,
    HdfsMetricName.CORRUPT_BLOCKS.value,
    HdfsMetricName.MISSING_BLOCKS.value,
    HdfsMetricName.UNCHECKPOINTED_TXNS.value,
    HdfsMetricName.DATANODE_LAST_CONTACT.value,
    HdfsMetricName.DATANODE_JVM_HEAP_USAGE.value,
)

# 摘要分组的中文名
SUMMARY_GROUP_NAMES: Dict[str, str] = {
    "resource": "系统资源",
    "capacity": "容量与内存",
    "block": "数据块",
    "metadata": "元数据",
    "rpc": "RPC 与连接",
}


def get_metric_spec(metric_name: str) -> Optional[HdfsMetricSpec]:
    """按指标名取声明，不存在返回 None。"""
    return HDFS_METRIC_REGISTRY.get(metric_name)


def get_all_metric_names() -> List[str]:
    """全部合法指标名，用于错误提示中回带合法值。"""
    return list(HDFS_METRIC_REGISTRY.keys())
