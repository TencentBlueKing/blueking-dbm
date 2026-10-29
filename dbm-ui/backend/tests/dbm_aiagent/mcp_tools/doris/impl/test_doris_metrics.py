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
from unittest.mock import patch

# 本文件覆盖指标注册表、构造器工厂隔离性与参数校验，
# 用例自身不访问 ORM（集群校验一律 mock），因此无需 django_db 标记。
#
# 注意：backend/tests/conftest.py 中存在若干 scope="session" 且 autouse=True 的
# 数据库初始化 fixture（__init_city / __init_package / __init_db_module /
# __init_app / __init_spec），它们依赖 django_db_setup，因此运行本文件需要可用的 MySQL。
#
# 不需要 ENABLE_DBM_AI=true：conftest.py 顶部已 import backend.tests.aidev_handler_stub，
# 在该开关为 false 时为 AgentHandler 安装测试桩，CI（scripts/ci/env.sh）也未设置该变量。
import pytest

from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import (
    AGGREGATION_FUNC_MAP,
    RANGE_FUNC_MAP,
    PromQLMultiQueryBuilder,
    parse_step_to_seconds,
)
from backend.dbm_aiagent.mcp_tools.doris.constants import (
    DORIS_METRIC_REGISTRY,
    DORIS_PUSHGATEWAY_PREFIX,
    END_TIME_MAX_FUTURE_SKEW_SECONDS,
    MAX_DATAPOINTS,
    MAX_QUERY_RANGE_SECONDS,
    PERCENT_METRICS,
    SUMMARY_KEY_METRICS,
    SUMMARY_MAX_DAYS,
    SUMMARY_STEP,
    get_all_metric_names,
    get_metric_spec,
)
from backend.dbm_aiagent.mcp_tools.doris.enums import (
    ALL_ROLES,
    BE_ROLES,
    FE_ROLES,
    DorisAggFunction,
    DorisGroupBy,
    DorisHealthLevel,
    DorisMetricName,
    DorisMetricsRole,
    DorisMetricUnit,
)
from backend.dbm_aiagent.mcp_tools.doris.impl import doris_metrics as mod
from backend.dbm_aiagent.mcp_tools.doris.serializers.doris_metrics import (
    DorisMetricsInputSerializer,
    DorisMetricsOutputSerializer,
    DorisPerformanceSummaryInputSerializer,
    DorisPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

CLUSTER_DOMAIN = "doris.test.dba.db"


class TestRegistryIntegrity:
    """注册表与枚举必须严格一一对应，避免枚举可选但查询时报 KeyError。"""

    def test_every_enum_has_spec(self):
        for metric_name in DorisMetricName.get_values():
            assert get_metric_spec(metric_name) is not None, f"指标 {metric_name} 缺少注册表声明"

    def test_no_orphan_spec(self):
        enum_values = set(DorisMetricName.get_values())
        assert set(DORIS_METRIC_REGISTRY) == enum_values

    def test_every_spec_builds_promql(self):
        """每个指标都必须能产出合法 PromQL，防止 filters / range_function 写错。"""
        for metric_name, spec in DORIS_METRIC_REGISTRY.items():
            builder = spec.builder_factory()
            promql_dict = builder.prepare_promql()
            promql_dict.pop("expression", None)
            assert promql_dict, f"指标 {metric_name} 未产出 PromQL"
            for one_promql in promql_dict.values():
                assert one_promql, f"指标 {metric_name} 的 PromQL 为空"

    def test_roles_are_valid(self):
        """适用角色必须落在 Doris 角色枚举内，不能出现拼写错误的角色值。"""
        valid_roles = set(DorisMetricsRole.get_values())
        for metric_name, spec in DORIS_METRIC_REGISTRY.items():
            assert spec.applicable_roles, f"指标 {metric_name} 未声明适用角色"
            assert spec.applicable_roles <= valid_roles, f"指标 {metric_name} 存在非法角色"

    def test_aggregations_are_supported_by_builder(self):
        """默认与可选聚合方式必须被底层 PromQL 构造器支持。"""
        for metric_name, spec in DORIS_METRIC_REGISTRY.items():
            assert spec.default_aggregation in AGGREGATION_FUNC_MAP, f"指标 {metric_name} 默认聚合非法"
            assert spec.default_aggregation in spec.supported_aggregations
            for aggregation in spec.supported_aggregations:
                assert aggregation in AGGREGATION_FUNC_MAP

    def test_threshold_method_is_valid(self):
        """阈值比较方式只允许 gte / gt，且与告警模板保持一致。"""
        for metric_name, spec in DORIS_METRIC_REGISTRY.items():
            assert spec.threshold_method in ("gte", "gt"), f"指标 {metric_name} 阈值比较方式非法"

    def test_unit_is_valid(self):
        """单位必须落在 DorisMetricUnit 枚举内。

        单位会被智能体直接读进结论，错标比查不出数据更危险，
        故与 threshold_method 同级锁定，不允许写自由文本。
        """
        valid_units = set(DorisMetricUnit.get_values())
        for metric_name, spec in DORIS_METRIC_REGISTRY.items():
            assert spec.unit in valid_units, f"指标 {metric_name} 单位非法: {spec.unit!r}"

    def test_percent_unit_matches_whitelist(self):
        """标为百分比的指标必须与显式白名单一致。

        白名单依据是 dashboard 对应面板的 unit 为 percent / percentunit。
        想给新指标标 PERCENT 必须同步改 PERCENT_METRICS，从而被迫走一遍溯源，
        避免凭常识误标。query_err_rate 曾被误标为百分比（实为次/秒），
        正是本用例要防的回归。
        """
        actual = {name for name, spec in DORIS_METRIC_REGISTRY.items() if spec.unit == DorisMetricUnit.PERCENT.value}
        assert actual == set(PERCENT_METRICS), "百分比指标集合与白名单不一致: {}".format(
            actual.symmetric_difference(set(PERCENT_METRICS))
        )

    def test_is_percent_property_follows_unit(self):
        """is_percent 由 unit 派生，不再有独立的 is_ratio 布尔字段。"""
        for spec in DORIS_METRIC_REGISTRY.values():
            assert spec.is_percent == (spec.unit == DorisMetricUnit.PERCENT.value)
        assert not hasattr(get_metric_spec(DorisMetricName.CPU_USAGE.value), "is_ratio")

    def test_factory_aggregation_matches_declared_default(self):
        """工厂实际使用的聚合必须与 default_aggregation 声明一致。

        两者脱节时，工具返回的 aggregation 字段会与实际 PromQL 不符，
        让智能体误读数据含义（例如声明峰值实际取的是均值）。
        """
        for metric_name, spec in DORIS_METRIC_REGISTRY.items():
            builder = spec.builder_factory()
            assert builder.get_aggregation() == spec.default_aggregation, (
                f"指标 {metric_name} 工厂聚合 {builder.get_aggregation()} " f"与声明的默认聚合 {spec.default_aggregation} 不一致"
            )

    def test_summary_key_metrics_all_registered(self):
        for metric_name in SUMMARY_KEY_METRICS:
            spec = get_metric_spec(metric_name)
            assert spec is not None
            # 摘要指标必须有平台既定阈值，否则健康判定无意义
            assert (
                spec.warning_threshold is not None or spec.fatal_threshold is not None
            ), f"摘要指标 {metric_name} 无告警阈值，无法做健康判定"


class TestMetricSourcePrefix:
    """指标名前缀决定数据源，写错会查到完全不同的表。"""

    # 系统层指标：写短名，由 build_promql 自动补 bkmonitor:dbm_system: 前缀
    SYSTEM_METRICS = {
        DorisMetricName.CPU_USAGE.value,
        DorisMetricName.DISK_USAGE.value,
        DorisMetricName.MEMORY_USAGE.value,
        DorisMetricName.SYSTEM_LOAD1.value,
        DorisMetricName.TCP_ESTABLISHED.value,
        DorisMetricName.NET_RECV.value,
        DorisMetricName.NET_SENT.value,
    }

    def test_system_metrics_use_dbm_system(self):
        for metric_name in self.SYSTEM_METRICS:
            builder = get_metric_spec(metric_name).builder_factory()
            promql = list(builder.prepare_promql().values())[0]
            assert "bkmonitor:dbm_system:" in promql, f"指标 {metric_name} 未落在 dbm_system"

    def test_doris_metrics_use_pushgateway(self):
        for metric_name in set(DORIS_METRIC_REGISTRY) - self.SYSTEM_METRICS:
            builder = get_metric_spec(metric_name).builder_factory()
            promql_dict = builder.prepare_promql()
            promql_dict.pop("expression", None)
            joined = " ".join(promql_dict.values())
            assert DORIS_PUSHGATEWAY_PREFIX in joined, f"指标 {metric_name} 未落在 pushgateway 数据源"


class TestBuilderFactoryIsolation:
    """构造器工厂必须每次产出全新实例。

    query_promql_metrics_with_roles 会对构造器原地 append filters 且无去重，
    若注册表持有模块级单例，第二次请求时 filters 会累积上一次的 cluster_domain
    与 instance_role，产生互斥条件导致查不出数据甚至跨请求串数据。
    """

    def test_factory_returns_new_instance(self):
        spec = get_metric_spec(DorisMetricName.CPU_USAGE.value)
        first, second = spec.builder_factory(), spec.builder_factory()
        assert first is not second
        assert first.filters is not second.filters
        assert first.group_by is not second.group_by

    def test_filters_do_not_accumulate_across_calls(self):
        spec = get_metric_spec(DorisMetricName.CPU_USAGE.value)

        first = spec.builder_factory()
        first.filters.append({"label_name": "cluster_domain", "op": "equal", "value": "cluster-a"})
        first_count = len(first.filters)

        second = spec.builder_factory()
        second.filters.append({"label_name": "cluster_domain", "op": "equal", "value": "cluster-b"})

        assert len(second.filters) == first_count
        domains = [f["value"] for f in second.filters if f["label_name"] == "cluster_domain"]
        assert domains == ["cluster-b"], "上一次请求的 cluster_domain 泄漏到了本次请求"

    def test_group_by_do_not_accumulate_across_calls(self):
        spec = get_metric_spec(DorisMetricName.CPU_USAGE.value)

        first = spec.builder_factory()
        baseline = len(first.group_by)
        first.group_by.append("instance_role")

        second = spec.builder_factory()
        assert len(second.group_by) == baseline

    def test_ratio_sub_builders_are_isolated(self):
        """比率型指标的子构造器同样不能共享。

        PromQLMultiQueryBuilder.build_promql 会把父级 filters extend 进子构造器，
        子构造器被共享时会被反复污染。
        """
        spec = get_metric_spec(DorisMetricName.CAPACITY_USAGE.value)
        first, second = spec.builder_factory(), spec.builder_factory()
        assert isinstance(first, PromQLMultiQueryBuilder)

        for alias, sub_builder in first.queries.items():
            assert sub_builder is not second.queries[alias]
            assert sub_builder.filters is not second.queries[alias].filters

        first.filters.append({"label_name": "cluster_domain", "op": "equal", "value": "cluster-a"})
        first.prepare_promql()

        second.filters.append({"label_name": "cluster_domain", "op": "equal", "value": "cluster-b"})
        promql_dict = second.prepare_promql()
        promql_dict.pop("expression", None)
        joined = " ".join(promql_dict.values())
        assert "cluster-a" not in joined, "上一次请求的 cluster_domain 泄漏到了比率型指标的子查询"

    def test_repeated_query_does_not_pollute_registry(self):
        """连续两次走完整查询链路，第二次的 PromQL 不应残留第一次的条件。"""
        captured = []

        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            captured.append(" ".join(prom_queries.values()))
            return {"promql": prom_queries, "series": []}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            mod.query_doris_metrics(
                cluster_domain="cluster-a.dba.db",
                metric_name=DorisMetricName.CPU_USAGE.value,
                instance_roles=[DorisMetricsRole.FOLLOWER.value],
            )
            mod.query_doris_metrics(
                cluster_domain="cluster-b.dba.db",
                metric_name=DorisMetricName.CPU_USAGE.value,
                instance_roles=[DorisMetricsRole.BACKEND_HOT.value],
            )

        assert len(captured) == 2
        assert "cluster-a.dba.db" not in captured[1], "第二次查询残留了第一次的 cluster_domain"
        assert DorisMetricsRole.FOLLOWER.value not in captured[1], "第二次查询残留了第一次的 instance_role"


class TestRatioAndSemanticTraps:
    """语义陷阱：比率换算、容量口径、Compaction 仅取 Master、内置角色过滤。"""

    def test_percent_metrics_convert_to_percentage(self):
        """两指标相除的百分比指标必须在服务端换算成百分比。"""
        for metric_name in (DorisMetricName.CAPACITY_USAGE.value, DorisMetricName.JVM_HEAP_USAGE.value):
            spec = get_metric_spec(metric_name)
            assert spec.is_percent is True
            builder = spec.builder_factory()
            assert "100" in builder.expression
            assert "/" in builder.expression

    def test_capacity_uses_avail_not_local_used(self):
        """容量使用率必须按 1-可用/总量 计算。

        口径经组件负责人确认：local_used 只统计 Doris 本地数据占用，
        不含 BE 预留空间与同盘非 Doris 文件，会低估真实水位。
        告警模板 Doris Capacity.json 已同步为该口径。
        """
        spec = get_metric_spec(DorisMetricName.CAPACITY_USAGE.value)
        builder = spec.builder_factory()
        assert builder.expression == "100 * (1 - {a} / {b})"

        promql_dict = builder.prepare_promql()
        promql_dict.pop("expression", None)
        joined = " ".join(promql_dict.values())
        assert "doris_be_disks_avail_capacity" in joined
        assert "doris_be_disks_total_capacity" in joined
        assert "local_used" not in joined, "不应再使用 local_used 口径"

    def test_capacity_groups_by_instance_role(self):
        """容量使用率必须能按角色分组 —— 扩缩容是按热/温/冷分层进行的，
        若只按主机分组则无法判断哪一层水位告急。

        注意 PromQLMultiQueryBuilder.build_promql 不会把父级 group_by 下传子查询，
        因此 instance_role 必须在子构造器上显式声明。
        """
        spec = get_metric_spec(DorisMetricName.CAPACITY_USAGE.value)
        builder = spec.builder_factory()
        for alias, sub_builder in builder.queries.items():
            assert "instance_role" in sub_builder.group_by, f"{alias} 侧缺少 instance_role 分组"
            assert "cluster_domain" in sub_builder.group_by, f"{alias} 侧缺少 cluster_domain 分组"

    def test_ratio_metrics_report_aggregation(self):
        """PromQLMultiQueryBuilder.get_aggregation 取首个子构造器的 aggregation，
        子构造器必须显式设置，否则对外返回 None。"""
        for metric_name in (DorisMetricName.CAPACITY_USAGE.value, DorisMetricName.JVM_HEAP_USAGE.value):
            builder = get_metric_spec(metric_name).builder_factory()
            assert builder.get_aggregation() is not None

    def test_compaction_score_uses_cluster_aggregated_metric(self):
        """compaction 分数取 FE 汇总的集群级指标。

        指标选择经组件负责人确认：用 doris_fe_max_tablet_compaction_score
        （FE 汇总出的集群最大分数）而非 doris_fe_tablet_max_compaction_score
        （按 backend 维度逐 BE 上报，需额外把 backend 标签映射回节点）。
        两者仅词序不同，极易混淆，故单独锁定。
        """
        builder = get_metric_spec(DorisMetricName.COMPACTION_SCORE.value).builder_factory()
        promql_dict = builder.prepare_promql()
        promql_dict.pop("expression", None)
        joined = " ".join(promql_dict.values())
        assert "doris_fe_max_tablet_compaction_score" in joined
        assert "doris_fe_tablet_max_compaction_score" not in joined, "用错了按 backend 维度上报的那个指标"

    def test_compaction_score_joins_master_node_info(self):
        """compaction_score 必须关联 node_info{type="is_master"}。

        master 是会切换的，不能从元数据取静态 master 节点，
        而要靠 node_info{type="is_master"} 这条时序按时间点动态判定：
        当时的 master 取值 1、非 master 取值 0，相乘后非 master 分数归零，
        master 切换时结果自动跟随。
        """
        builder = get_metric_spec(DorisMetricName.COMPACTION_SCORE.value).builder_factory()
        assert "{a}" in builder.expression and "{b}" in builder.expression
        assert "*" in builder.expression

        promql_dict = builder.prepare_promql()
        promql_dict.pop("expression", None)
        joined = " ".join(promql_dict.values())
        assert "node_info" in joined
        assert "is_master" in joined

    def test_compaction_score_join_dimensions_align(self):
        """join 两侧必须按完全相同的维度分组。

        换用集群汇总指标后不再有 backend 维度差，PromQL 默认向量匹配即可逐实例对齐，
        不需要 ignoring/group_left；但右侧仍必须分组 —— 若聚合成整集群标量会恒等于 1，
        master 过滤将完全静默失效，所有 FE 的分数都被原样返回。
        """
        spec = get_metric_spec(DorisMetricName.COMPACTION_SCORE.value)
        builder = spec.builder_factory()

        left, right = builder.queries["a"], builder.queries["b"]
        # 两侧维度完全一致，因此无需 ignoring 抹平
        assert set(left.group_by) == set(right.group_by)
        assert "ignoring" not in builder.expression
        assert "group_left" not in builder.expression
        # 右侧必须有分组，不能退化成整集群标量
        assert right.group_by, "node_info 侧未分组，乘法将退化为乘以标量 1"

        promql_dict = builder.prepare_promql()
        promql_dict.pop("expression", None)
        for alias, one_promql in promql_dict.items():
            assert " by(" in one_promql, f"compaction_score 的 {alias} 侧缺少 by 分组"

    def test_jvm_heap_has_builtin_role_filter(self):
        """jvm_heap_usage 的 instance_role 已固化在 PromQL 内，
        标记 role_filter_builtin 以跳过外层注入，避免重复条件。"""
        spec = get_metric_spec(DorisMetricName.JVM_HEAP_USAGE.value)
        assert spec.role_filter_builtin is True

        builder = spec.builder_factory()
        promql_dict = builder.prepare_promql()
        promql_dict.pop("expression", None)
        joined = " ".join(promql_dict.values())
        assert "doris_follower" in joined and "doris_observer" in joined

    def test_jvm_heap_skips_outer_role_injection(self):
        captured = []

        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            captured.append(" ".join(prom_queries.values()))
            return {"promql": prom_queries, "series": []}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            mod.query_doris_metrics(
                cluster_domain=CLUSTER_DOMAIN,
                metric_name=DorisMetricName.JVM_HEAP_USAGE.value,
            )

        # 内置过滤只出现一次（used/max 两个子查询各一次），不应因外层注入而重复
        assert captured[0].count("doris_follower|doris_observer") == 2

    def test_disk_usage_excludes_system_mounts(self):
        """磁盘使用率必须排除系统盘与安装盘，否则系统盘水位会混入数据盘判断。"""
        builder = get_metric_spec(DorisMetricName.DISK_USAGE.value).builder_factory()
        promql = list(builder.prepare_promql().values())[0]
        assert 'mount_point!="/"' in promql
        assert 'mount_point!="/usr/local"' in promql

    def test_txn_rate_uses_irate_not_rate(self):
        """事务速率必须用 irate 而非 rate。

        事务失败/拒绝是突发型故障：rate 取窗口首尾做线性拟合会把峰值摊薄
        （1 分钟内 90 次、2m 窗口下 irate≈1.5/s 而 rate≈0.75/s），
        在阈值 1/5 下会直接漏报。告警模板用的也是 irate。
        """
        for metric_name in (DorisMetricName.TXN_FAILED_RATE.value, DorisMetricName.TXN_REJECT_RATE.value):
            spec = get_metric_spec(metric_name)
            builder = spec.builder_factory()
            assert builder.range_function == "irate", f"指标 {metric_name} 未使用 irate"
            assert "irate" in RANGE_FUNC_MAP, "common 层缺少 irate 支持"

            promql = list(builder.prepare_promql().values())[0]
            assert "irate(" in promql

    def test_txn_rate_keeps_declared_time_window(self):
        """事务速率的 irate 窗口固定为 2m，不应被用户传入的 step 覆盖，
        否则会改变速率计算窗口。"""
        for metric_name in (DorisMetricName.TXN_FAILED_RATE.value, DorisMetricName.TXN_REJECT_RATE.value):
            spec = get_metric_spec(metric_name)
            builder = spec.builder_factory()
            assert builder.time_window == "2m"
            assert builder.range_function in RANGE_FUNC_MAP

            builder = mod._build_query_builder(
                spec=spec,
                aggregation=spec.default_aggregation,
                group_by=None,
                start_time=None,
                end_time=None,
                step="1h",
            )
            promql = list(builder.prepare_promql().values())[0]
            assert "[2m]" in promql, f"指标 {metric_name} 的 irate 窗口被 step 覆盖"

    def test_query_err_rate_is_not_percent(self):
        """query_err_rate 是单台 FE 的查询失败速率（次/秒），不是错误占比。

        原实现误标为 unit="%" + is_ratio=True，会让智能体把「3 次/秒」
        读成「3%」。语义经组件负责人确认。
        """
        spec = get_metric_spec(DorisMetricName.QUERY_ERR_RATE.value)
        assert spec.unit == DorisMetricUnit.COUNT_PER_SEC.value
        assert spec.is_percent is False
        assert DorisMetricName.QUERY_ERR_RATE.value not in PERCENT_METRICS


class TestRoleApplicability:
    """FE / BE 专属指标传错角色必须报错，而不是静默返回空数据 ——
    后者会让智能体误判为「集群无此问题」。"""

    # jvm_heap_usage 虽也是 FE 专属，但其角色已固化在 PromQL 内，
    # 走的是「拒绝传入任何角色」的分支，故单独测试
    FE_ONLY_METRICS = (
        DorisMetricName.QUERY_ERR_RATE.value,
        DorisMetricName.TXN_FAILED_RATE.value,
        DorisMetricName.TXN_REJECT_RATE.value,
        DorisMetricName.EDITLOG_WRITE_LATENCY.value,
        DorisMetricName.IMAGE_PUSH_FAILED.value,
        DorisMetricName.IMAGE_WRITE_FAILED.value,
        DorisMetricName.COMPACTION_SCORE.value,
    )

    def test_fe_only_metrics_declare_fe_roles(self):
        for metric_name in self.FE_ONLY_METRICS + (DorisMetricName.JVM_HEAP_USAGE.value,):
            assert get_metric_spec(metric_name).applicable_roles == FE_ROLES

    def test_be_only_metric_declares_be_roles(self):
        assert get_metric_spec(DorisMetricName.CAPACITY_USAGE.value).applicable_roles == BE_ROLES

    def test_system_metrics_apply_to_all_roles(self):
        assert get_metric_spec(DorisMetricName.CPU_USAGE.value).applicable_roles == ALL_ROLES
        assert get_metric_spec(DorisMetricName.MEMORY_USAGE.value).applicable_roles == ALL_ROLES

    @pytest.mark.parametrize("metric_name", FE_ONLY_METRICS)
    def test_fe_metric_rejects_be_role(self, metric_name):
        spec = get_metric_spec(metric_name)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_metric_roles(metric_name, spec, [DorisMetricsRole.BACKEND_HOT.value])

        message = str(exc_info.value)
        assert DorisMetricsRole.BACKEND_HOT.value in message
        # 错误信息必须回带合法角色，便于智能体自我纠正
        assert DorisMetricsRole.FOLLOWER.value in message

    def test_be_metric_rejects_fe_role(self):
        metric_name = DorisMetricName.CAPACITY_USAGE.value
        spec = get_metric_spec(metric_name)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_metric_roles(metric_name, spec, [DorisMetricsRole.OBSERVER.value])

        message = str(exc_info.value)
        assert DorisMetricsRole.OBSERVER.value in message
        assert DorisMetricsRole.BACKEND_HOT.value in message

    def test_builtin_role_filter_metric_rejects_any_role(self):
        """role_filter_builtin 的指标不支持按角色细分。

        外层角色注入会被跳过，若放过用户传入值则返回的是全部 FE 的数据，
        而响应里却回显用户指定的那一个角色 —— 属「响应与实际查询不符」，
        比直接报错更危险。
        """
        metric_name = DorisMetricName.JVM_HEAP_USAGE.value
        spec = get_metric_spec(metric_name)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_metric_roles(metric_name, spec, [DorisMetricsRole.OBSERVER.value])

        message = str(exc_info.value)
        # 必须说明其固定覆盖范围，便于智能体改为留空重试
        assert DorisMetricsRole.FOLLOWER.value in message
        assert DorisMetricsRole.OBSERVER.value in message

    def test_builtin_role_filter_metric_accepts_empty(self):
        metric_name = DorisMetricName.JVM_HEAP_USAGE.value
        spec = get_metric_spec(metric_name)
        assert set(mod.validate_metric_roles(metric_name, spec, None)) == FE_ROLES

    def test_builtin_role_filter_echoes_applicable_roles(self):
        """响应回显的 instance_roles 必须是实际生效的全部适用角色。"""

        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            return {"promql": prom_queries, "series": []}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            result = mod.query_doris_metrics(
                cluster_domain=CLUSTER_DOMAIN,
                metric_name=DorisMetricName.JVM_HEAP_USAGE.value,
            )

        assert set(result["instance_roles"]) == FE_ROLES
        assert result["instance_roles"] == result["applicable_roles"]

    def test_empty_roles_fallback_to_applicable(self):
        """留空角色时自动填充为该指标的适用角色，避免把 FE 指标下发到 BE 节点。"""
        metric_name = DorisMetricName.QUERY_ERR_RATE.value
        spec = get_metric_spec(metric_name)
        assert set(mod.validate_metric_roles(metric_name, spec, [])) == FE_ROLES
        assert set(mod.validate_metric_roles(metric_name, spec, None)) == FE_ROLES

    def test_system_metric_accepts_mixed_roles(self):
        metric_name = DorisMetricName.CPU_USAGE.value
        spec = get_metric_spec(metric_name)
        roles = [DorisMetricsRole.FOLLOWER.value, DorisMetricsRole.BACKEND_COLD.value]
        assert mod.validate_metric_roles(metric_name, spec, roles) == roles

    def test_warm_role_is_queryable(self):
        """温节点是冷节点的新命名，必须可查（不再标注为未验证）。"""
        spec = get_metric_spec(DorisMetricName.CAPACITY_USAGE.value)
        roles = [DorisMetricsRole.BACKEND_WARM.value]
        assert mod.validate_metric_roles(DorisMetricName.CAPACITY_USAGE.value, spec, roles) == roles


class TestParamValidation:
    def test_invalid_metric_name_lists_all_valid(self):
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_metric_name("not_exist_metric")

        message = str(exc_info.value)
        assert "not_exist_metric" in message
        # 必须回带全部合法指标名
        for metric_name in get_all_metric_names():
            assert metric_name in message

    def test_invalid_aggregation_lists_supported(self):
        metric_name = DorisMetricName.CPU_USAGE.value
        spec = get_metric_spec(metric_name)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_aggregation(metric_name, spec, "p95")

        message = str(exc_info.value)
        assert "p95" in message
        assert DorisAggFunction.AVG.value in message

    def test_empty_aggregation_uses_default(self):
        metric_name = DorisMetricName.TCP_ESTABLISHED.value
        spec = get_metric_spec(metric_name)
        assert mod.validate_aggregation(metric_name, spec, None) == spec.default_aggregation
        # 连接数取峰值更有意义，dashboard 中亦用 max
        assert spec.default_aggregation == DorisAggFunction.MAX.value


class TestTimeRangeValidation:
    """时间跨度与点数规模校验。

    common 构造器里的 24h 上限 raise 已被注释且不能放开（MySQL 共用该构造器），
    故这些保护由 Doris 侧提供，必须有测试锁住。
    """

    def test_no_start_time_skips_span_check(self):
        # start_time 为空时底层只查最近 5 分钟，跨度必然安全，不应报错
        mod.validate_time_range(None, None, "1m")

    def test_future_end_time_rejected(self):
        future = datetime.datetime.now() + datetime.timedelta(seconds=END_TIME_MAX_FUTURE_SKEW_SECONDS + 600)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_time_range(None, future, "1m")
        assert "end_time" in str(exc_info.value)

    def test_small_clock_skew_tolerated(self):
        # 容忍调用方时钟略快，避免因几十秒偏差拒绝正常请求
        slightly_future = datetime.datetime.now() + datetime.timedelta(seconds=60)
        mod.validate_time_range(slightly_future - datetime.timedelta(hours=1), slightly_future, "1m")

    def test_start_not_before_end_rejected(self):
        now = datetime.datetime.now()
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_time_range(now, now - datetime.timedelta(hours=1), "1m")
        assert "start_time" in str(exc_info.value)

    def test_span_over_limit_rejected(self):
        end = datetime.datetime.now()
        start = end - datetime.timedelta(seconds=MAX_QUERY_RANGE_SECONDS + 3600)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            # 步长足够大，确保触发的是跨度校验而非点数校验
            mod.validate_time_range(start, end, "1d")
        assert str(MAX_QUERY_RANGE_SECONDS // 86400) in str(exc_info.value)

    def test_span_at_limit_allowed(self):
        end = datetime.datetime.now()
        start = end - datetime.timedelta(seconds=MAX_QUERY_RANGE_SECONDS)
        mod.validate_time_range(start, end, "1h")

    def test_one_day_with_default_step_allowed(self):
        """最高频的排障场景不能被误伤：1 天 @1m = 1440 点，必须放过。

        这是 MAX_DATAPOINTS 取 1500 而非 Redis 的 500 的理由，锁住以防被调小。
        """
        end = datetime.datetime.now()
        mod.validate_time_range(end - datetime.timedelta(days=1), end, "1m")

    def test_too_many_points_rejected_with_suggestion(self):
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=7)
        with pytest.raises(DBMMcpBaseException) as exc_info:
            mod.validate_time_range(start, end, "1m")

        message = str(exc_info.value)
        assert str(MAX_DATAPOINTS) in message
        # 必须给出建议 step，否则智能体只能反复试
        assert "step=" in message

    @pytest.mark.parametrize("days", [1, 2, 7, 15, 30])
    def test_suggested_step_actually_passes(self, days):
        """建议值必须真的能通过校验，否则智能体照抄后仍失败。"""
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=days)
        span_seconds = int((end - start).total_seconds())

        suggested = mod._suggest_step(span_seconds)
        assert span_seconds // parse_step_to_seconds(suggested) <= MAX_DATAPOINTS
        # 用建议值重新校验不应再报错
        mod.validate_time_range(start, end, suggested)

    def test_summary_step_fits_max_days(self):
        """摘要路径强制 SUMMARY_STEP，在天数上限下也不能触发点数校验。"""
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=SUMMARY_MAX_DAYS)
        mod.validate_time_range(start, end, SUMMARY_STEP)


class TestHealthJudgement:
    """健康判定阈值与告警模板保持一致。

    多数阈值照抄模板；少数经组件负责人确认后偏离，
    这些偏离已同步修改告警模板，两侧必须一致。
    """

    def test_capacity_thresholds_match_alarm_template(self):
        """容量阈值随口径变更调整为 80/90（1-avail/total 普遍高于 local_used/total）。"""
        spec = get_metric_spec(DorisMetricName.CAPACITY_USAGE.value)
        assert (spec.warning_threshold, spec.fatal_threshold) == (80, 90)

    def test_txn_thresholds_tightened(self):
        """事务速率阈值经确认后由 5/10 收紧为 1/5，告警模板已同步。"""
        for metric_name in (DorisMetricName.TXN_FAILED_RATE.value, DorisMetricName.TXN_REJECT_RATE.value):
            spec = get_metric_spec(metric_name)
            assert (spec.warning_threshold, spec.fatal_threshold) == (1, 5)

    def test_cpu_threshold_match_alarm_template(self):
        spec = get_metric_spec(DorisMetricName.CPU_USAGE.value)
        assert spec.warning_threshold == 80
        assert spec.fatal_threshold is None

    def test_image_push_uses_gt_and_write_uses_gte(self):
        """image_push_failed 用 gt、image_write_failed 用 gte，
        两者在告警模板中不同，必须照抄不做统一。"""
        push_spec = get_metric_spec(DorisMetricName.IMAGE_PUSH_FAILED.value)
        write_spec = get_metric_spec(DorisMetricName.IMAGE_WRITE_FAILED.value)
        assert push_spec.threshold_method == "gt"
        assert write_spec.threshold_method == "gte"

        # 值恰好等于 1 时：gt 不命中，gte 命中
        assert mod._judge_health(push_spec, 1) == DorisHealthLevel.NORMAL.value
        assert mod._judge_health(write_spec, 1) == DorisHealthLevel.FATAL.value

    def test_judge_health_levels(self):
        spec = get_metric_spec(DorisMetricName.DISK_USAGE.value)
        assert (spec.warning_threshold, spec.fatal_threshold) == (75, 80)
        assert mod._judge_health(spec, 50) == DorisHealthLevel.NORMAL.value
        assert mod._judge_health(spec, 75) == DorisHealthLevel.WARNING.value
        assert mod._judge_health(spec, 85) == DorisHealthLevel.FATAL.value

    def test_judge_health_unknown_without_threshold(self):
        """无对应告警模板的指标不做判定，返回 unknown。"""
        for metric_name in (DorisMetricName.SYSTEM_LOAD1.value, DorisMetricName.MEMORY_USAGE.value):
            spec = get_metric_spec(metric_name)
            assert spec.warning_threshold is None and spec.fatal_threshold is None
            assert mod._judge_health(spec, 999) == DorisHealthLevel.UNKNOWN.value

    def test_judge_health_unknown_without_value(self):
        spec = get_metric_spec(DorisMetricName.CPU_USAGE.value)
        assert mod._judge_health(spec, None) == DorisHealthLevel.UNKNOWN.value


class TestExtractValues:
    def test_filters_none_datapoints(self):
        """unify_query 返回的数据点可能为 None（该时刻无数据），必须过滤。"""
        series = [
            {"datapoints": [[1.0, 1000], [None, 2000], [3.0, 3000]]},
            {"datapoints": [[5.0, 1000]]},
            {"datapoints": None},
            {},
        ]
        assert mod._extract_values(series) == [1.0, 3.0, 5.0]

    def test_empty_series(self):
        assert mod._extract_values([]) == []
        assert mod._extract_values(None) == []


class TestSerializers:
    def test_input_defaults(self):
        slz = DorisMetricsInputSerializer(
            data={"cluster_domain": CLUSTER_DOMAIN, "metric_name": DorisMetricName.CPU_USAGE.value}
        )
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["step"] == "1m"
        assert slz.validated_data["instance_roles"] is None

    def test_input_rejects_unknown_metric(self):
        slz = DorisMetricsInputSerializer(data={"cluster_domain": CLUSTER_DOMAIN, "metric_name": "unknown"})
        assert not slz.is_valid()
        assert "metric_name" in slz.errors

    def test_input_rejects_unknown_role(self):
        slz = DorisMetricsInputSerializer(
            data={
                "cluster_domain": CLUSTER_DOMAIN,
                "metric_name": DorisMetricName.CPU_USAGE.value,
                "instance_roles": ["doris_unknown_role"],
            }
        )
        assert not slz.is_valid()
        assert "instance_roles" in slz.errors

    def test_input_has_no_bk_biz_id(self):
        """底层固定用 DBA 业务查询监控，不应要求智能体填 bk_biz_id。"""
        assert "bk_biz_id" not in DorisMetricsInputSerializer().fields

    def test_metric_choices_cover_registry(self):
        choices = dict(DorisMetricsInputSerializer().fields["metric_name"].choices)
        assert set(choices) == set(DORIS_METRIC_REGISTRY)
        # 完整中文含义放在 choices label 里，工具 description 才能保持精简
        for label in choices.values():
            assert str(label).strip()

    def test_group_by_choices_are_valid(self):
        choices = dict(DorisMetricsInputSerializer().fields["group_by"].child.choices)
        assert set(choices) == set(DorisGroupBy.get_values())

    def test_summary_days_range(self):
        slz = DorisPerformanceSummaryInputSerializer(data={"cluster_domain": CLUSTER_DOMAIN})
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["days"] == 7

        assert not DorisPerformanceSummaryInputSerializer(
            data={"cluster_domain": CLUSTER_DOMAIN, "days": 0}
        ).is_valid()
        assert not DorisPerformanceSummaryInputSerializer(
            data={"cluster_domain": CLUSTER_DOMAIN, "days": 31}
        ).is_valid()

    def test_query_output_keys_declared(self):
        """实际响应字段必须都在输出 serializer 中声明，避免文档与实现不一致。"""

        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            return {"promql": prom_queries, "series": []}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            result = mod.query_doris_metrics(
                cluster_domain=CLUSTER_DOMAIN,
                metric_name=DorisMetricName.DISK_USAGE.value,
            )

        declared = set(DorisMetricsOutputSerializer().fields)
        assert set(result) <= declared, "未声明的响应字段: {}".format(set(result) - declared)

    def test_summary_output_keys_declared(self):
        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            return {"promql": prom_queries, "series": []}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            result = mod.get_doris_performance_summary(cluster_domain=CLUSTER_DOMAIN, days=1)

        declared = set(DorisPerformanceSummaryOutputSerializer().fields)
        assert set(result) <= declared, "未声明的响应字段: {}".format(set(result) - declared)


class TestPerformanceSummary:
    def test_summary_uses_hour_step_and_drops_datapoints(self):
        """摘要必须用大步长且只返回统计值，否则 7 天 x 1m 会撑爆上下文。"""
        steps = []

        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            steps.append(step)
            return {
                "promql": prom_queries,
                "series": [{"datapoints": [[10.0, 1000], [20.0, 2000], [30.0, 3000]]}],
            }

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            summary = mod.get_doris_performance_summary(cluster_domain=CLUSTER_DOMAIN, days=7)

        assert steps and set(steps) == {"1h"}
        for group in summary["groups"].values():
            for metric_summary in group["metrics"].values():
                assert "datapoints" not in metric_summary
                assert metric_summary["max"] == 30.0
                assert metric_summary["min"] == 10.0
                assert metric_summary["latest"] == 30.0

    def test_summary_collects_abnormal_metrics(self):
        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            # 90 会同时命中 cpu(80) / disk(80 fatal) / capacity(85 fatal) 等阈值
            return {"promql": prom_queries, "series": [{"datapoints": [[90.0, 1000]]}]}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            summary = mod.get_doris_performance_summary(cluster_domain=CLUSTER_DOMAIN, days=1)

        assert summary["overall_health"] == DorisHealthLevel.FATAL.value
        assert summary["abnormal_metrics"]
        for item in summary["abnormal_metrics"]:
            assert item["health"] in (DorisHealthLevel.WARNING.value, DorisHealthLevel.FATAL.value)

    def test_summary_single_metric_failure_does_not_break_all(self):
        """单指标查询失败不应中断整个摘要，否则一个指标无采集就让摘要不可用。"""
        call_count = {"n": 0}

        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("monitor api timeout")
            return {"promql": prom_queries, "series": [{"datapoints": [[1.0, 1000]]}]}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            summary = mod.get_doris_performance_summary(cluster_domain=CLUSTER_DOMAIN, days=1)

        errors = [
            metric_summary
            for group in summary["groups"].values()
            for metric_summary in group["metrics"].values()
            if "error" in metric_summary
        ]
        assert len(errors) == 1
        assert "monitor api timeout" in errors[0]["error"]
        # 其余指标仍有结果
        assert call_count["n"] == len(SUMMARY_KEY_METRICS)

    def test_summary_marks_unknown_when_no_data(self):
        def _fake_execute(prom_queries, expr, start_time, end_time, step):
            return {"promql": prom_queries, "series": []}

        with mock_cluster_ok(), mock_execute_promql(_fake_execute):
            summary = mod.get_doris_performance_summary(cluster_domain=CLUSTER_DOMAIN, days=1)

        assert summary["overall_health"] == DorisHealthLevel.UNKNOWN.value
        for group in summary["groups"].values():
            for metric_summary in group["metrics"].values():
                assert metric_summary["health"] == DorisHealthLevel.UNKNOWN.value


# --------------------------- 测试辅助 ---------------------------


def mock_cluster_ok():
    """跳过集群校验，避免测试依赖 ORM。"""
    return patch.object(mod, "validate_doris_cluster", return_value=None)


def mock_execute_promql(fake_func):
    """替换监控查询出口，不依赖真实监控环境。

    注意需 patch query_promql_metrics_with_roles 实际引用的 execute_promql。
    """
    return patch(
        "backend.dbm_aiagent.mcp_tools.common.views.promql_query.execute_promql",
        side_effect=fake_func,
    )
