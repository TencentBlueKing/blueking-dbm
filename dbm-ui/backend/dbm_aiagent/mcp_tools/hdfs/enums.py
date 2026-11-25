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


class HdfsMetricName(StrStructuredEnum):
    """HDFS 指标名。

    指标名只承载「语义」，不编码节点角色与聚合方式：
    节点角色由 instance_roles 参数指定，聚合方式由 aggregation 参数指定。
    这样同一个 cpu_usage 既能查 NameNode 也能查 DataNode，避免出现
    nn_cpu_usage/dn_cpu_usage 这类随角色数量翻倍膨胀的指标名。

    每个指标的来源 PromQL 与告警阈值见 HDFS_METRIC_REGISTRY 中各指标的注释。
    """

    # 系统层指标（bkmonitor:dbm_system:*），NameNode / DataNode 共用同一底层字段
    CPU_USAGE = EnumField("cpu_usage", _("CPU 使用率(%)"))
    MEMORY_USAGE = EnumField("memory_usage", _("内存使用率(%)"))
    DISK_USAGE = EnumField("disk_usage", _("磁盘分区使用率(%)，已排除系统盘与安装盘"))
    SYSTEM_LOAD1 = EnumField("system_load1", _("系统 1 分钟平均负载"))
    TCP_ESTABLISHED = EnumField("tcp_established", _("TCP 已建立连接数"))
    NET_RECV = EnumField("net_recv", _("网络入流量"))
    NET_SENT = EnumField("net_sent", _("网络出流量"))

    # NameNode 专有指标（bkmonitor:exporter_dbm_hdfs_exporter:*）
    CAPACITY_USAGE = EnumField("capacity_usage", _("HDFS 集群容量使用率(%)，已换算为百分比，取自 Active NameNode"))
    CORRUPT_BLOCKS = EnumField("corrupt_blocks", _("损坏块数量(个)，取自 Active NameNode"))
    MISSING_BLOCKS = EnumField("missing_blocks", _("丢失块数量(个)，取自 Active NameNode"))
    UNCHECKPOINTED_TXNS = EnumField("uncheckpointed_txns", _("距上次 Checkpoint 的未合并事务数(个)，取自 Active NameNode"))
    DATANODE_LAST_CONTACT = EnumField(
        "datanode_last_contact", _("DataNode 与 NameNode 的失联时长(秒)，按 datanode 维度展开，取自 Active NameNode")
    )
    NAMENODE_STATE = EnumField("namenode_state", _("NameNode 主备状态原始值，1 表示 Active，按主机 IP 展开"))

    # DataNode 专有指标与 NameNode RPC 指标（bkmonitor:exporter_dbm_hdfs_exporter:*）
    DATANODE_JVM_HEAP_USAGE = EnumField("datanode_jvm_heap_usage", _("DataNode JVM 堆内存使用率(%)，已换算为百分比"))
    DATANODE_XCEIVER_COUNT = EnumField("datanode_xceiver_count", _("DataNode Xceiver 数据传输连接数(个)"))
    DATANODE_CALL_QUEUE_LENGTH = EnumField("datanode_call_queue_length", _("DataNode RPC 请求队列长度(个)"))
    NAMENODE_RPC_QUEUE_TIME = EnumField("namenode_rpc_queue_time", _("NameNode RPC 请求平均排队耗时(ms)，取自 Active NameNode"))


class HdfsMetricUnit(StrStructuredEnum):
    """指标数值单位。

    用单值枚举而非一组布尔标记（如 is_ratio / is_rate / is_bytes）：
    单位本质是多值互斥属性，布尔组合既无法表达互斥，也会随单位种类线性膨胀。
    单位会被智能体直接读进结论，错标比查不出数据更危险。
    """

    PERCENT = EnumField("percent", _("百分比(%)，服务端已换算，调用方无需再做除法"))
    COUNT = EnumField("count", _("计数(个)"))
    CONNECTION = EnumField("connection", _("连接数(个)"))
    BYTES_PER_SEC = EnumField("bytes_per_sec", _("字节/秒(Bps)"))
    MILLISECOND = EnumField("ms", _("毫秒(ms)"))
    SECOND = EnumField("second", _("秒(s)"))
    DIMENSIONLESS = EnumField("dimensionless", _("无量纲"))
    # 刻意保留：让「单位尚未经组件负责人确认」成为可被类型识别的显式状态，
    # 而非散落在注释里的口头约定。新增指标若无法溯源单位，必须填此值而不是猜一个。
    UNVERIFIED = EnumField("unverified", _("单位未确认，不要据此换算或与其他指标横向比较"))


class HdfsAggFunction(StrStructuredEnum):
    """聚合方式。取值需落在 common.impl.promql_query.AGGREGATION_FUNC_MAP 内。"""

    MAX = EnumField("max", _("峰值"))
    MIN = EnumField("min", _("谷值"))
    AVG = EnumField("avg", _("均值"))
    SUM = EnumField("sum", _("求和"))


class HdfsHealthLevel(StrStructuredEnum):
    """性能摘要中的健康判定结果。"""

    NORMAL = EnumField("normal", _("正常"))
    WARNING = EnumField("warning", _("预警"))
    FATAL = EnumField("fatal", _("致命"))
    UNKNOWN = EnumField("unknown", _("无数据或无既定阈值，未做判定"))


# NameNode 角色
NN_ROLES = frozenset({InstanceRole.HDFS_NAME_NODE.value})

# DataNode 角色
DN_ROLES = frozenset({InstanceRole.HDFS_DATA_NODE.value})

# 仅供指标查询使用的全部角色（指标侧角色白名单），不是 HDFS 的全部角色：
# 只含 NameNode 与 DataNode，不含 JournalNode 与 Zookeeper。
METRIC_ALL_ROLES = NN_ROLES | DN_ROLES


def get_hdfs_metric_choices() -> List[Tuple[str, str]]:
    """指标名 choices，label 为中文含义，供序列化器 ChoiceField 复用。

    完整的中文含义放在 choices 的 label 里，工具 description 只写短清单，
    避免 description 膨胀成数十行。
    """
    return HdfsMetricName.get_choices()


def get_hdfs_role_choices() -> List[Tuple[str, str]]:
    """节点角色 choices，取值为指标查询角色白名单 METRIC_ALL_ROLES，label 取自 InstanceRole。"""
    return [(role, InstanceRole.get_choice_label(role)) for role in sorted(METRIC_ALL_ROLES)]


def get_hdfs_aggregation_choices() -> List[Tuple[str, str]]:
    """聚合方式 choices。"""
    return HdfsAggFunction.get_choices()


def get_hdfs_unit_choices() -> List[Tuple[str, str]]:
    """单位 choices，供输出序列化器与文档复用。"""
    return HdfsMetricUnit.get_choices()
