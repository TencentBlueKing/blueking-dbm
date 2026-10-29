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
from typing import List, Tuple

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import InstanceRole
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class DorisMetricName(StrStructuredEnum):
    """Doris 指标名。

    指标名只承载「语义」，不编码节点角色与聚合方式：
    节点角色由 instance_roles 参数指定，聚合方式由 aggregation 参数指定。
    这样同一个 cpu_usage 既能查 FE 也能查 BE，避免出现 fe_cpu_usage/be_cpu_usage
    这类随角色数量翻倍膨胀的指标名。

    每个指标的来源 PromQL 与告警阈值见 DORIS_METRIC_REGISTRY 中各指标的注释。
    """

    # 系统层指标（bkmonitor:dbm_system:*），FE / BE 共用同一底层字段
    CPU_USAGE = EnumField("cpu_usage", _("CPU 使用率(%)"))
    MEMORY_USAGE = EnumField("memory_usage", _("内存使用率(%)"))
    DISK_USAGE = EnumField("disk_usage", _("磁盘分区使用率(%)，已排除系统盘与安装盘"))
    SYSTEM_LOAD1 = EnumField("system_load1", _("系统 1 分钟平均负载"))
    TCP_ESTABLISHED = EnumField("tcp_established", _("TCP 已建立连接数"))
    NET_RECV = EnumField("net_recv", _("网络入流量"))
    NET_SENT = EnumField("net_sent", _("网络出流量"))

    # Doris 专有层指标（bkmonitor:pushgateway_dbm_doris_bkpull:*）
    CAPACITY_USAGE = EnumField("capacity_usage", _("BE 数据盘使用率(%)，按 1-可用/总量 计算，已换算为百分比"))
    JVM_HEAP_USAGE = EnumField("jvm_heap_usage", _("FE JVM 堆内存使用率(%)，已换算为百分比"))
    QUERY_ERR_RATE = EnumField("query_err_rate", _("单台 FE 查询失败速率(次/秒)，非百分比"))
    TXN_FAILED_RATE = EnumField("txn_failed_rate", _("FE 事务失败速率(次/秒)"))
    TXN_REJECT_RATE = EnumField("txn_reject_rate", _("FE 事务拒绝速率(次/秒)"))
    EDITLOG_WRITE_LATENCY = EnumField("editlog_write_latency", _("FE 元数据 editlog 写入延迟 P99(ms)"))
    IMAGE_PUSH_FAILED = EnumField("image_push_failed", _("FE 元数据镜像推送失败次数"))
    IMAGE_WRITE_FAILED = EnumField("image_write_failed", _("FE 元数据镜像写入失败次数"))
    COMPACTION_SCORE = EnumField("compaction_score", _("集群 Tablet 最大 Compaction 分数，取自 Master FE"))


class DorisMetricUnit(StrStructuredEnum):
    """指标数值单位。

    用单值枚举而非一组布尔标记（如 is_ratio / is_rate / is_bytes）：
    单位本质是多值互斥属性，布尔组合既无法表达互斥，也会随单位种类线性膨胀。
    单位会被智能体直接读进结论，错标比查不出数据更危险，
    故由 test_unit_is_valid 与 test_percent_unit_matches_whitelist 双重锁定。
    """

    PERCENT = EnumField("percent", _("百分比(%)，服务端已换算，调用方无需再做除法"))
    COUNT = EnumField("count", _("计数(次)"))
    COUNT_PER_SEC = EnumField("count_per_sec", _("次/秒"))
    CONNECTION = EnumField("connection", _("连接数(个)"))
    BYTES_PER_SEC = EnumField("bytes_per_sec", _("字节/秒(Bps)"))
    MILLISECOND = EnumField("ms", _("毫秒(ms)"))
    DIMENSIONLESS = EnumField("dimensionless", _("无量纲"))
    # 刻意保留：让「单位尚未经组件负责人确认」成为可被类型与测试识别的显式状态，
    # 而非散落在注释里的口头约定。新增指标若无法溯源单位，必须填此值而不是猜一个。
    UNVERIFIED = EnumField("unverified", _("单位未确认，不要据此换算或与其他指标横向比较"))


class DorisMetricsRole(StrStructuredEnum):
    """Doris 节点角色，取值与 db_meta.enums.InstanceRole 中的 Doris 角色严格一致。"""

    FOLLOWER = EnumField(InstanceRole.DORIS_FOLLOWER.value, _("Follower(FE)"))
    OBSERVER = EnumField(InstanceRole.DORIS_OBSERVER.value, _("Observer(FE)"))
    BACKEND_HOT = EnumField(InstanceRole.DORIS_BACKEND_HOT.value, _("热节点(BE)"))
    # warm 是 cold 的新命名，用于逐步取代 cold；两者当前并存，查询冷数据节点时建议同时传
    BACKEND_WARM = EnumField(InstanceRole.DORIS_BACKEND_WARM.value, _("温节点(BE)，冷节点的新命名"))
    BACKEND_COLD = EnumField(InstanceRole.DORIS_BACKEND_COLD.value, _("冷节点(BE)，旧命名，逐步由温节点取代"))


class DorisAggFunction(StrStructuredEnum):
    """聚合方式。取值需落在 common.impl.promql_query.AGGREGATION_FUNC_MAP 内。"""

    MAX = EnumField("max", _("峰值"))
    MIN = EnumField("min", _("谷值"))
    AVG = EnumField("avg", _("均值"))
    SUM = EnumField("sum", _("求和"))


class DorisGroupBy(StrStructuredEnum):
    """分组维度。

    cluster_domain 与 instance_role 由 query_promql_metrics_with_roles 自动注入，
    无需在此显式指定。
    """

    INSTANCE_HOST = EnumField("instance_host", _("按主机 IP 分组"))
    BK_TARGET_IP = EnumField("bk_target_ip", _("按采集目标 IP 分组，系统层指标适用"))
    MOUNT_POINT = EnumField("mount_point", _("按磁盘挂载点分组，仅 disk_usage 适用"))


class DorisHealthLevel(StrStructuredEnum):
    """性能摘要中的健康判定结果。"""

    NORMAL = EnumField("normal", _("正常"))
    WARNING = EnumField("warning", _("预警"))
    FATAL = EnumField("fatal", _("致命"))
    UNKNOWN = EnumField("unknown", _("无数据或无既定阈值，未做判定"))


# FE 层角色（Follower + Observer）
FE_ROLES = frozenset(
    {
        DorisMetricsRole.FOLLOWER.value,
        DorisMetricsRole.OBSERVER.value,
    }
)

# BE 层角色（热 / 温 / 冷节点）
BE_ROLES = frozenset(
    {
        DorisMetricsRole.BACKEND_HOT.value,
        DorisMetricsRole.BACKEND_WARM.value,
        DorisMetricsRole.BACKEND_COLD.value,
    }
)

# 全部 Doris 角色
ALL_ROLES = FE_ROLES | BE_ROLES


def get_doris_metric_choices() -> List[Tuple[str, str]]:
    """指标名 choices，label 为中文含义，供序列化器 ChoiceField 复用。

    完整的中文含义放在 choices 的 label 里，工具 description 只写短清单，
    避免 description 膨胀成数十行。
    """
    return DorisMetricName.get_choices()


def get_doris_role_choices() -> List[Tuple[str, str]]:
    """节点角色 choices。"""
    return DorisMetricsRole.get_choices()


def get_doris_aggregation_choices() -> List[Tuple[str, str]]:
    """聚合方式 choices。"""
    return DorisAggFunction.get_choices()


def get_doris_group_by_choices() -> List[Tuple[str, str]]:
    """分组维度 choices。"""
    return DorisGroupBy.get_choices()


def get_doris_unit_choices() -> List[Tuple[str, str]]:
    """单位 choices，供输出序列化器与文档复用。"""
    return DorisMetricUnit.get_choices()
