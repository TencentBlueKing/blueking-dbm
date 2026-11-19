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
import copy
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.db.models import Q

from backend import env
from backend.components import BKMonitorV3Api
from backend.constants import INT_MAX
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, Spec, StorageInstance
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_metrics import UNIFY_QUERY_PARAMS, _disk_host_ip
from backend.flow.utils.kafka.rebalance_throttle_util import (
    _BANDWIDTH_RAW_METRIC,
    BANDWIDTH_PROMQL,
    _query_steps_by_ip,
)
from backend.utils.time import timezone2timestamp

logger = logging.getLogger("root")

# 判定结果
VERDICT_DECOMMISSION = "decommission"  # 窗口内生产流量严格为0，可整集群下线
VERDICT_RIGHTSIZE = "rightsize"  # 非空，且按磁盘/网络反推的目标台数小于现有台数
VERDICT_KEEP = "keep"  # 判定后不建议缩容
VERDICT_UNCLEAR = "unclear"  # 缺少判定所需数据，需要人工查看

# keep / unclear 的原因
REASON_CPU_GUARD = "cpu_guard"
REASON_ALREADY_RIGHT_SIZED = "already_right_sized"
REASON_METRICS_MISSING = "metrics_missing"
REASON_METRICS_INCOMPLETE = "metrics_incomplete"  # 有数据，但上报的 broker 数少于集群的 broker 数
REASON_BANDWIDTH_UNKNOWN = "bandwidth_unknown"
REASON_DISK_CAPACITY_UNKNOWN = "disk_capacity_unknown"
REASON_NO_BROKER = "no_broker"

# 提示（不影响判定）
FLAG_CONSUMER_ACTIVE = "consumer_active"

# 目标台数的绑定约束
CONSTRAINT_DISK = "disk"
CONSTRAINT_NETWORK = "network"
CONSTRAINT_MIN_NODES = "min_nodes"

BYTES_PER_GB = 1024**3
# 带宽指标的单位是 Mbps。跟 rebalance 调速算利用率的口径一致：bit/s 除以 1024 再除以 1024 得到 Mbps
BITS_PER_MBPS = 1024 * 1024

# 单次查询的集群域名数。每个集群聚合后只有1条series，分批是为了不超过监控查询的 slimit，也避免正则过长
QUERY_DOMAIN_BATCH_SIZE = 40
# 单次查询涉及的 broker 总数上限。覆盖校验的查询每台 broker 返回一条series，监控查询有 slimit(500) 上限，
# 超过会被截断、把正常上报的 broker 误当成缺失，所以按 broker 数给批次设上限，留出余量
QUERY_BROKER_BUDGET = 400
# 单次查询的 broker IP 数。带宽指标按 IP 一条series，调速那边是全空间不过滤查询(slimit 500)，
# 这里一次评估很多集群，必须限定 IP 范围，否则超过 500 台主机时 broker 会被截掉
QUERY_IP_BATCH_SIZE = 40
# 带宽指标取点的窗口，跟 rebalance 调速的查询一致（最近5分钟）
BANDWIDTH_WINDOW_SECONDS = 300

# 子查询的步长。窗口内的峰值由 max_over_time(expr[Nd:5m]) 在监控侧算完，只取最近一个点，
# 避免把N天的时间序列拉回来（单集群7天的明细就有几十万字符）
SUBQUERY_STEP = "5m"
# 取点的窗口。跟 rebalance_throttle_util 的带宽查询一致：窗口内取最后一个非空点，末点为空是常见现象
LATEST_POINT_WINDOW_SECONDS = 600

# 跨集群峰值查询。__SEL__ 会被替换成 cluster_domain=~"a|b|c"，只查本次要评估的集群。
# 各表达式的口径跟 kafka_metrics.py 里已有的单集群指标保持一致，区别只在于不固定单个 cluster_domain。
# host_net_bps 用主机侧 speed_*_bit（bit/s），跟 kafka Dashboard / rebalance 调速用的是同一套指标，
# 包含副本同步、多份消费等全部流量，不需要再按 RF 或消费份数估算。
PEAK_PROMQL = {
    # 客户端口径的生产/消费流量，bytes/s。仅用于判断集群是否有业务流量，不参与网络容量计算
    "producer_bps": (
        'sum by (cluster_domain) (rate(kafka_server_brokertopicmetrics_bytesin_total{__SEL__,topic!=""}[5m]))'
    ),
    "consumer_bps": (
        'sum by (cluster_domain) (rate(kafka_server_brokertopicmetrics_bytesout_total{__SEL__,topic!=""}[5m]))'
    ),
    # 最忙那台 broker 的 CPU 利用率(%)，不是集群平均，避免热点 broker 被平均掉
    "cpu_peak_pct": (
        'max by (cluster_domain) (bkmonitor:dbm_system:cpu_summary:usage{__SEL__,instance_role="broker"})'
    ),
    # 所有 broker 主机的 出+入 网卡流量之和，bit/s
    "host_net_bps": (
        "sum by (cluster_domain) ("
        'max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:net:speed_sent_bit{__SEL__,instance_role="broker"})'
        " + on (cluster_domain, bk_target_ip) "
        'max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:net:speed_recv_bit{__SEL__,instance_role="broker"})'
        ")"
    ),
    # 各 broker 上所有副本的日志大小之和(bytes)。只用于展示，不参与容量计算（不含日志以外的残留数据）
    "log_size_bytes": 'sum by (cluster_domain) (kafka_log_log_size{__SEL__,topic!=""})',
    # 所有 broker 数据盘的已用字节数之和。过滤口径跟 disk_usage_detail 一致，表达式跟 Kafka Dashboard「磁盘容量」
    # 面板的 sum(disk:used{...}) 同源（单位 bytes）；先按 (主机, 挂载点) 去重再求和，避免同一挂载点被重复累加。
    # 不能用"平均使用率 × 容量"估算：各挂载点大小不一致时平均使用率会严重失真
    "disk_used_bytes": (
        "sum by (cluster_domain) (max by (cluster_domain, bk_target_ip, mount_point) ("
        "bkmonitor:dbm_system:disk:used{"
        '__SEL__,instance_role="broker",device_type=~"ext.?|xfs",mount_point!~"^(/|/usr/local)$"}))'
    ),
}

# 覆盖校验：决策用的指标是否来自集群的每一台 broker。上面的 sum/max 会把缺失的 broker 静默吞掉
# （比如只剩一台空闲 broker 在上报，生产流量聚合出来就是 0），所以每个决策指标都要核对"哪些 broker 在上报"，
# 并且按身份（IP）逐台跟元数据里的 broker 比对，而不是只数台数：数台数会被重复序列（比如两个采集器都在采）
# 凑够数，反而把真正缺失的 broker 盖住。取的是最近的点，不是窗口峰值。
# 每条查询每台 broker 返回一条series，从标签里取 IP：主机类指标有 bk_target_ip；Kafka 的 JMX 指标没有主机标签，
# 用 instance（形如 "IP-端口"，Grafana 的 per-broker 面板也是 by (instance)），提取方式复用 _disk_host_ip。
# 生产流量用 topic="" 的汇总序列：没有 topic 的 broker 也有这条序列，而 topic!="" 的序列只在有 topic 时才有。
# 这里只看有没有序列，不对流量求和，所以不会出现汇总序列和分 topic 序列重复累加、流量翻倍的问题。
COVERAGE_PROMQL = {
    "producer_ips": (
        'max by (cluster_domain, instance) (kafka_server_brokertopicmetrics_bytesin_total{__SEL__,topic=""})'
    ),
    "cpu_ips": (
        'max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:cpu_summary:usage{__SEL__,instance_role="broker"})'
    ),
    # 出和入两个方向都有数据的主机才算（跟 host_net_bps 的 on(...) 连接一致）
    "net_ips": (
        'max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:net:speed_sent_bit{__SEL__,instance_role="broker"})'
        " + on (cluster_domain, bk_target_ip) "
        'max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:net:speed_recv_bit{__SEL__,instance_role="broker"})'
    ),
    "disk_ips": (
        "max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:disk:used{"
        '__SEL__,instance_role="broker",device_type=~"ext.?|xfs",mount_point!~"^(/|/usr/local)$"})'
    ),
}
# 覆盖校验各指标在输出里的名字
COVERAGE_LABELS = {"producer_ips": "producer", "cpu_ips": "cpu", "net_ips": "host_net", "disk_ips": "disk"}


@dataclass(frozen=True)
class RightsizeParams:
    """判定参数。默认值跟 DBA 手工评估时用的口径一致"""

    disk_target_pct: float = 60.0  # 缩容后磁盘使用率目标上限
    net_watermark_pct: float = 50.0  # 缩容后单机网卡带宽使用率上限
    cpu_guard_pct: float = 40.0  # 当前峰值 CPU 超过该值就不再缩容
    min_nodes: int = 3  # 高可用下限


@dataclass
class ClusterInventory:
    """集群在元数据里的当前规模。per_node 的值取各 broker 的最小值（木桶效应），取不到时为 None/0"""

    cluster_id: int
    bk_biz_id: int
    immute_domain: str
    alias: str
    region: str
    nodes: int
    cpu_cores_per_node: int = 0
    mem_gb_per_node: int = 0
    disk_gb_per_node: float = 0
    bandwidth_mbps_per_node: Optional[float] = None
    # 参与带宽查询的 broker IP，以及其中没有取到有效带宽的 IP（任何一台缺失，整个集群的带宽按未知处理）
    broker_ips: List[str] = field(default_factory=list)
    bandwidth_missing_ips: List[str] = field(default_factory=list)


@dataclass
class ClusterPeaks:
    """窗口内的峰值，None 表示监控里没有查到"""

    producer_bps: Optional[float] = None
    consumer_bps: Optional[float] = None
    cpu_peak_pct: Optional[float] = None
    host_net_bps: Optional[float] = None
    log_size_bytes: Optional[float] = None
    disk_used_bytes: Optional[float] = None
    # 当前在上报对应指标的 broker IP，None 表示查询失败
    producer_ips: Optional[List[str]] = None
    cpu_ips: Optional[List[str]] = None
    net_ips: Optional[List[str]] = None
    disk_ips: Optional[List[str]] = None


@dataclass
class Decision:
    verdict: str
    reasons: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    target_nodes: Optional[int] = None
    binding_constraint: Optional[str] = None
    nodes_by_disk: Optional[int] = None
    nodes_by_network: Optional[int] = None
    projected_disk_pct: Optional[float] = None
    projected_net_pct: Optional[float] = None
    reclaim_nodes: int = 0


def _ceil(value: float) -> int:
    # 先取整到6位小数，避免 2.0000000000000004 这类浮点误差被向上取成 3
    return int(math.ceil(round(value, 6)))


def missing_brokers(inv: ClusterInventory, peaks: ClusterPeaks) -> Dict[str, List[str]]:
    """各决策指标里没有在上报的 broker IP（按元数据里的 broker 逐台比对），没有缺失的指标不出现。查询失败视为全部缺失"""
    result = {}
    for field_name, label in COVERAGE_LABELS.items():
        reported = set(getattr(peaks, field_name) or [])
        missing = [ip for ip in inv.broker_ips if ip not in reported]
        if missing:
            result[label] = missing
    return result


def reporting_broker_counts(inv: ClusterInventory, peaks: ClusterPeaks) -> Dict[str, int]:
    """各决策指标里，元数据中的 broker 有多少台在上报"""
    expected = set(inv.broker_ips)
    return {
        label: len(expected & set(getattr(peaks, field_name) or [])) for field_name, label in COVERAGE_LABELS.items()
    }


def decide_cluster(inv: ClusterInventory, peaks: ClusterPeaks, params: RightsizeParams) -> Decision:
    """
    单个集群的判定，纯函数，不访问数据库和监控。
    顺序：无 broker -> 缺生产流量指标或上报的 broker 不全 -> 生产流量严格为0(下线) -> 其余指标缺失或不全
    -> CPU 门槛 -> 按磁盘/网络反推台数
    CPU 只用来做门槛，不参与目标台数的计算，也不做缩容后的 CPU 推算（CPU 与台数不是线性关系）。
    """
    if inv.nodes <= 0:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_NO_BROKER])

    if peaks.producer_bps is None:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_METRICS_MISSING])
    # 下线不可逆，必须确认每台 broker 都在上报：只剩空闲 broker 在上报时，聚合出来的 0 不代表整个集群没流量
    missing = missing_brokers(inv, peaks)
    if "producer" in missing:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_METRICS_INCOMPLETE])

    if peaks.producer_bps == 0:
        flags = [FLAG_CONSUMER_ACTIVE] if (peaks.consumer_bps or 0) > 0 else []
        return Decision(VERDICT_DECOMMISSION, flags=flags, reclaim_nodes=inv.nodes)

    if peaks.cpu_peak_pct is None or peaks.host_net_bps is None or peaks.disk_used_bytes is None:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_METRICS_MISSING])
    # CPU 取的是 max，网络和磁盘取的是 sum，少一台都会低估（漏掉热点 broker / 少算流量和数据量）
    if missing:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_METRICS_INCOMPLETE])

    if peaks.cpu_peak_pct > params.cpu_guard_pct:
        return Decision(VERDICT_KEEP, reasons=[REASON_CPU_GUARD])

    if inv.disk_gb_per_node <= 0:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_DISK_CAPACITY_UNKNOWN])
    if not inv.bandwidth_mbps_per_node:
        return Decision(VERDICT_UNCLEAR, reasons=[REASON_BANDWIDTH_UNKNOWN])

    # 数据量取数据盘已用字节数，包含 Kafka 日志以外的残留数据
    data_gb = peaks.disk_used_bytes / BYTES_PER_GB
    disk_cap_per_node = inv.disk_gb_per_node * params.disk_target_pct / 100
    net_cap_per_node = inv.bandwidth_mbps_per_node * BITS_PER_MBPS * params.net_watermark_pct / 100

    nodes_by_disk = _ceil(data_gb / disk_cap_per_node)
    nodes_by_network = _ceil(peaks.host_net_bps / net_cap_per_node)
    candidates = [
        (CONSTRAINT_DISK, nodes_by_disk),
        (CONSTRAINT_NETWORK, nodes_by_network),
        (CONSTRAINT_MIN_NODES, params.min_nodes),
    ]
    target = max(value for _name, value in candidates)
    binding = next(name for name, value in candidates if value == target)

    decision = Decision(
        VERDICT_RIGHTSIZE,
        target_nodes=target,
        binding_constraint=binding,
        nodes_by_disk=nodes_by_disk,
        nodes_by_network=nodes_by_network,
        projected_disk_pct=round(data_gb / (target * inv.disk_gb_per_node) * 100, 2),
        projected_net_pct=round(peaks.host_net_bps / (target * inv.bandwidth_mbps_per_node * BITS_PER_MBPS) * 100, 2),
        reclaim_nodes=max(inv.nodes - target, 0),
    )
    if target >= inv.nodes:
        decision.verdict = VERDICT_KEEP
        decision.reasons = [REASON_ALREADY_RIGHT_SIZED]
        decision.reclaim_nodes = 0
    return decision


def collect_inventory(bk_biz_ids: Optional[List[int]] = None, city: Optional[str] = None) -> List[ClusterInventory]:
    """
    从元数据取集群规模：broker 数量和 IP、单机 CPU/内存/磁盘（规格）。单机带宽见 collect_bandwidth
    bk_biz_ids 为 None 表示不限业务（跨业务评估，调用方要求 DBA 权限）；传了就只看这些业务。
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Kafka)
    if bk_biz_ids is not None:
        clusters = clusters.filter(bk_biz_id__in=bk_biz_ids)
    if city:
        # Cluster.region 标注了即将废弃，老集群可能为空，用 broker 机器所在的逻辑城市兜底
        clusters = clusters.filter(
            Q(region=city) | Q(storageinstance__machine__bk_city__logical_city__name=city)
        ).distinct()
    clusters = list(clusters)
    if not clusters:
        return []

    # StorageInstance.cluster 是 ManyToManyField，没有 cluster_id 字段。走中间表一次查出 (集群, broker) 的对应关系：
    # 一个实例属于多个集群时会分别归到每个集群下，不会漏
    brokers_by_cluster: Dict[int, List[StorageInstance]] = defaultdict(list)
    relations = StorageInstance.cluster.through.objects.filter(
        cluster_id__in=[c.id for c in clusters], storageinstance__instance_role=InstanceRole.BROKER.value
    ).select_related("storageinstance__machine")
    for relation in relations:
        brokers_by_cluster[relation.cluster_id].append(relation.storageinstance)

    spec_ids = {b.machine.spec_id for items in brokers_by_cluster.values() for b in items if b.machine.spec_id}
    specs = Spec.objects.in_bulk(spec_ids)

    inventories = []
    for cluster in clusters:
        items = brokers_by_cluster.get(cluster.id, [])
        inv = ClusterInventory(
            cluster_id=cluster.id,
            bk_biz_id=cluster.bk_biz_id,
            immute_domain=cluster.immute_domain,
            alias=cluster.alias or "",
            region=cluster.region or "",
            nodes=len(items),
            broker_ips=[b.machine.ip for b in items],
        )
        node_specs = [specs.get(b.machine.spec_id) for b in items]
        if items and all(node_specs):
            inv.cpu_cores_per_node = min(int((s.cpu or {}).get("min") or 0) for s in node_specs)
            inv.mem_gb_per_node = min(int((s.mem or {}).get("min") or 0) for s in node_specs)
            inv.disk_gb_per_node = min(_spec_disk_gb(s) for s in node_specs)
        inventories.append(inv)
    return inventories


def _spec_disk_gb(spec: Spec) -> float:
    """规格里所有数据盘挂载点的容量之和(GB)"""
    storage_spec = spec.storage_spec if isinstance(spec.storage_spec, list) else []
    return float(sum(int(disk.get("min") or 0) for disk in storage_spec if isinstance(disk, dict)))


def _regex_selector(label: str, values: List[str]) -> str:
    # 值里的点要转义成正则的 \.，PromQL 双引号字符串里反斜杠本身也要再转义一次
    pattern = "|".join(value.replace(".", "\\\\.") for value in values)
    return f'{label}=~"{pattern}"'


def _domain_selector(domains: List[str]) -> str:
    return _regex_selector("cluster_domain", domains)


def _bandwidth_promql(ips: List[str]) -> str:
    """
    跟 rebalance 自动调速用的 BANDWIDTH_PROMQL 是同一份表达式（同一个指标、聚合算子、窗口），
    唯一区别是给指标加了 bk_target_ip 选择器，把查询限定在要评估的 broker 上。
    """
    return BANDWIDTH_PROMQL.replace(
        _BANDWIDTH_RAW_METRIC, f"{_BANDWIDTH_RAW_METRIC}{{{_regex_selector('bk_target_ip', ips)}}}", 1
    )


def collect_bandwidth(ips: List[str]) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    查询 broker 主机的带宽(Mbps)，返回 ({ip: 带宽}, {"bandwidth": 错误信息})。
    指标值是部署时写入 /etc/dbm_bandwidth 的机型带宽，是个常量，取窗口内最后一个非空点。
    值为 0 或 >= INT_MAX（机型没有配置带宽时写入的默认值）都不是有效带宽，不放进结果，调用方会当作未知。
    """
    ips = sorted(set(ips))
    end_timestamp = int(timezone2timestamp(datetime.now()))
    start_timestamp = end_timestamp - BANDWIDTH_WINDOW_SECONDS
    bandwidth_by_ip: Dict[str, float] = {}
    errors: Dict[str, str] = {}
    for start in range(0, len(ips), QUERY_IP_BATCH_SIZE):
        batch = ips[start : start + QUERY_IP_BATCH_SIZE]
        try:
            # 监控查询统一用 DBA 数据空间，跟集群所属业务无关
            _series_count, steps_by_ip = _query_steps_by_ip(
                env.DBA_APP_BK_BIZ_ID, _bandwidth_promql(batch), start_timestamp, end_timestamp
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error("kafka rightsize query bandwidth failed: %s", e)
            errors["bandwidth"] = str(e)
            continue
        for ip, steps in steps_by_ip.items():
            if ip not in batch or not steps:
                continue
            value = steps[max(steps)]
            if value and value < INT_MAX:
                bandwidth_by_ip[ip] = value
    return bandwidth_by_ip, errors


def apply_bandwidth(inventories: List[ClusterInventory], bandwidth_by_ip: Dict[str, float]) -> None:
    """把带宽写回集群规模：取各 broker 的最小值（木桶效应）；只要有一台没有有效带宽，整个集群按未知处理"""
    for inv in inventories:
        if not inv.broker_ips:
            continue
        inv.bandwidth_missing_ips = [ip for ip in inv.broker_ips if ip not in bandwidth_by_ip]
        if inv.bandwidth_missing_ips:
            inv.bandwidth_mbps_per_node = None
        else:
            inv.bandwidth_mbps_per_node = min(bandwidth_by_ip[ip] for ip in inv.broker_ips)


def _peak_promql(metric: str, domains: List[str], days: int) -> str:
    expr = PEAK_PROMQL[metric].replace("__SEL__", _domain_selector(domains))
    return f"max_over_time({expr}[{days}d:{SUBQUERY_STEP}])"


def _coverage_promql(metric: str, domains: List[str]) -> str:
    return COVERAGE_PROMQL[metric].replace("__SEL__", _domain_selector(domains))


def _unify_query(promql: str) -> Dict:
    """在监控数据空间里查一条 PromQL，取最近一小段时间里的点"""
    end_timestamp = int(timezone2timestamp(datetime.now()))
    query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    # 监控查询统一用 DBA 数据空间，跟集群所属业务无关
    query_params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    query_params["start_time"] = end_timestamp - LATEST_POINT_WINDOW_SECONDS
    query_params["end_time"] = end_timestamp
    query_params["down_sample_range"] = "3m"
    query_params["query_configs"][0]["promql"] = promql
    return BKMonitorV3Api.unify_query(query_params) or {}


def _non_null_points(series: Dict) -> List[float]:
    return [p[0] for p in series.get("datapoints", []) if p and p[0] is not None]


def _query_cluster_values(promql: str) -> Dict[str, float]:
    """执行一条按 cluster_domain 聚合的查询，返回 {cluster_domain: 最后一个非空点}。没有数据的集群不会出现在结果里"""
    values: Dict[str, float] = {}
    for series in _unify_query(promql).get("series", []):
        domain = (series.get("dimensions") or {}).get("cluster_domain")
        points = _non_null_points(series)
        if domain and points:
            values[domain] = points[-1]
    return values


def _query_reporting_ips(promql: str) -> Dict[str, List[str]]:
    """
    执行一条每台 broker 返回一条series的查询，返回 {cluster_domain: [在上报的 broker IP]}。
    只有最近有非空点的series才算在上报；series 里取不出 IP 的忽略（对应的 broker 会被当成缺失，方向是安全的）。
    返回的series数碰到监控查询的 slimit 说明被截断了，这时"没看到的 broker"不代表没上报，必须报错，不能当成缺失来下结论。
    """
    series_list = _unify_query(promql).get("series", [])
    if len(series_list) >= UNIFY_QUERY_PARAMS["slimit"]:
        raise RuntimeError("monitor series truncated at slimit {}".format(UNIFY_QUERY_PARAMS["slimit"]))
    ips_by_domain: Dict[str, set] = defaultdict(set)
    for series in series_list:
        dimensions = series.get("dimensions") or {}
        domain = dimensions.get("cluster_domain")
        ip = _disk_host_ip(dimensions)
        if domain and ip and _non_null_points(series):
            ips_by_domain[domain].add(ip)
    return {domain: sorted(ips) for domain, ips in ips_by_domain.items()}


def _batches(domains: List[str], nodes_by_domain: Optional[Dict[str, int]] = None):
    """把集群域名分批：每批不超过 QUERY_DOMAIN_BATCH_SIZE 个集群，且 broker 总数不超过 QUERY_BROKER_BUDGET"""
    batch: List[str] = []
    weight = 0
    for domain in domains:
        domain_weight = max((nodes_by_domain or {}).get(domain, 1), 1)
        if batch and (len(batch) >= QUERY_DOMAIN_BATCH_SIZE or weight + domain_weight > QUERY_BROKER_BUDGET):
            yield batch
            batch, weight = [], 0
        batch.append(domain)
        weight += domain_weight
    if batch:
        yield batch


def collect_peaks(
    domains: List[str], days: int, nodes_by_domain: Optional[Dict[str, int]] = None
) -> Tuple[Dict[str, ClusterPeaks], Dict[str, str]]:
    """
    查询所有集群的窗口峰值和各决策指标里在上报的 broker，返回 ({cluster_domain: ClusterPeaks}, {指标名: 错误信息})。
    某个指标查询失败不会中断整体，对应集群的该字段保持 None，最终会被判成 metrics_missing / metrics_incomplete。
    nodes_by_domain 用来按 broker 数给批次设上限，不传时每个集群按 1 台算。
    """
    peaks = {domain: ClusterPeaks() for domain in domains}
    errors: Dict[str, str] = {}
    for metric in PEAK_PROMQL:
        for batch in _batches(domains, nodes_by_domain):
            try:
                values = _query_cluster_values(_peak_promql(metric, batch, days))
            except Exception as e:  # pylint: disable=broad-except
                logger.error("kafka rightsize query %s failed: %s", metric, e)
                errors[metric] = str(e)
                continue
            for domain, value in values.items():
                if domain in peaks:
                    setattr(peaks[domain], metric, float(value))
    for metric in COVERAGE_PROMQL:
        for batch in _batches(domains, nodes_by_domain):
            try:
                ips_by_domain = _query_reporting_ips(_coverage_promql(metric, batch))
            except Exception as e:  # pylint: disable=broad-except
                logger.error("kafka rightsize query %s failed: %s", metric, e)
                errors[metric] = str(e)
                continue
            for domain in batch:
                # 查询成功但这个集群没有任何序列，就是一台都没上报
                setattr(peaks[domain], metric, ips_by_domain.get(domain, []))
    return peaks, errors


def _reclaim_resources(inv: ClusterInventory, nodes: int) -> Dict:
    return {
        "cpu_cores": nodes * inv.cpu_cores_per_node,
        "memory_gb": nodes * inv.mem_gb_per_node,
        "disk_gb": round(nodes * inv.disk_gb_per_node, 2),
    }


def _round(value: Optional[float], digits: int = 2) -> Optional[float]:
    return None if value is None else round(value, digits)


def build_cluster_item(inv: ClusterInventory, peaks: ClusterPeaks, decision: Decision, days: int) -> Dict:
    log_size_gb = peaks.log_size_bytes / BYTES_PER_GB if peaks.log_size_bytes is not None else None
    disk_used_gb = peaks.disk_used_bytes / BYTES_PER_GB if peaks.disk_used_bytes is not None else None
    return {
        "cluster_id": inv.cluster_id,
        "bk_biz_id": inv.bk_biz_id,
        "immute_domain": inv.immute_domain,
        "alias": inv.alias,
        "region": inv.region,
        "verdict": decision.verdict,
        "reasons": decision.reasons,
        "flags": decision.flags,
        "current": {
            "nodes": inv.nodes,
            "cpu_cores_per_node": inv.cpu_cores_per_node,
            "memory_gb_per_node": inv.mem_gb_per_node,
            "disk_gb_per_node": inv.disk_gb_per_node,
            "bandwidth_mbps_per_node": inv.bandwidth_mbps_per_node,
            "bandwidth_missing_ips": inv.bandwidth_missing_ips,
        },
        "observed": {
            "window_days": days,
            "producer_peak_bytes_per_sec": _round(peaks.producer_bps),
            "consumer_peak_bytes_per_sec": _round(peaks.consumer_bps),
            "host_net_peak_bits_per_sec": _round(peaks.host_net_bps),
            "cpu_peak_percent": _round(peaks.cpu_peak_pct),
            "log_size_gb": _round(log_size_gb),
            "disk_used_gb": _round(disk_used_gb),
            "reporting_brokers": reporting_broker_counts(inv, peaks),
            "missing_brokers": missing_brokers(inv, peaks),
        },
        "recommendation": {
            "target_nodes": decision.target_nodes,
            "binding_constraint": decision.binding_constraint,
            "nodes_by_disk": decision.nodes_by_disk,
            "nodes_by_network": decision.nodes_by_network,
            "projected_disk_percent": decision.projected_disk_pct,
            "projected_net_percent": decision.projected_net_pct,
            "reclaim_nodes": decision.reclaim_nodes,
            "reclaim": _reclaim_resources(inv, decision.reclaim_nodes),
        },
    }


def _summarize(items: List[Dict]) -> Dict:
    by_verdict: Dict[str, int] = defaultdict(int)
    reclaim = {
        VERDICT_DECOMMISSION: {"clusters": 0, "nodes": 0, "cpu_cores": 0, "memory_gb": 0, "disk_gb": 0.0},
        VERDICT_RIGHTSIZE: {"clusters": 0, "nodes": 0, "cpu_cores": 0, "memory_gb": 0, "disk_gb": 0.0},
    }
    by_biz: Dict[int, Dict] = {}
    for item in items:
        verdict = item["verdict"]
        by_verdict[verdict] += 1
        biz = by_biz.setdefault(
            item["bk_biz_id"], {"bk_biz_id": item["bk_biz_id"], "clusters": 0, "actionable_clusters": 0, "nodes": 0}
        )
        biz["clusters"] += 1
        if verdict not in reclaim:
            continue
        rec = item["recommendation"]
        bucket = reclaim[verdict]
        bucket["clusters"] += 1
        bucket["nodes"] += rec["reclaim_nodes"]
        bucket["cpu_cores"] += rec["reclaim"]["cpu_cores"]
        bucket["memory_gb"] += rec["reclaim"]["memory_gb"]
        bucket["disk_gb"] = round(bucket["disk_gb"] + rec["reclaim"]["disk_gb"], 2)
        biz["actionable_clusters"] += 1
        biz["nodes"] += rec["reclaim_nodes"]

    total = {key: sum(bucket[key] for bucket in reclaim.values()) for key in ("nodes", "cpu_cores", "memory_gb")}
    total["disk_gb"] = round(sum(bucket["disk_gb"] for bucket in reclaim.values()), 2)
    return {
        "cluster_count": len(items),
        "by_verdict": dict(by_verdict),
        "reclaimable": {"total": total, **reclaim},
        "by_biz": sorted(by_biz.values(), key=lambda b: b["nodes"], reverse=True),
    }


def _sort_key(item: Dict):
    actionable = item["verdict"] in (VERDICT_DECOMMISSION, VERDICT_RIGHTSIZE)
    rank = {VERDICT_UNCLEAR: 1, VERDICT_KEEP: 2}.get(item["verdict"], 0)
    return (0 if actionable else rank, -item["recommendation"]["reclaim_nodes"], item["immute_domain"])


def kafka_cluster_rightsize(
    bk_biz_ids: Optional[List[int]] = None,
    city: Optional[str] = None,
    days: int = 30,
    params: Optional[RightsizeParams] = None,
    limit: int = 20,
    include_keep: bool = False,
) -> Dict:
    """
    评估 Kafka 集群的下线/缩容空间。

    Args:
        bk_biz_ids: 要评估的业务列表，调用方负责鉴权；None 表示不限业务（仅 DBA 可以这样调用）
        city: 城市（Cluster.region），不传则不按城市过滤
        days: 峰值统计窗口（天）
        params: 判定参数
        limit: 最多返回多少个集群明细，汇总始终覆盖全部集群
        include_keep: 是否返回判定为 keep 的集群，默认只返回可下线/可缩容/需人工查看的

    Returns:
        {"params", "summary", "clusters", "query_errors"}
    """
    params = params or RightsizeParams()
    inventories = collect_inventory(bk_biz_ids, city)
    domains = [inv.immute_domain for inv in inventories]
    nodes_by_domain = {inv.immute_domain: inv.nodes for inv in inventories}
    peaks_by_domain, query_errors = collect_peaks(domains, days, nodes_by_domain) if domains else ({}, {})

    broker_ips = [ip for inv in inventories for ip in inv.broker_ips]
    if broker_ips:
        bandwidth_by_ip, bandwidth_errors = collect_bandwidth(broker_ips)
        apply_bandwidth(inventories, bandwidth_by_ip)
        query_errors.update(bandwidth_errors)

    items = []
    for inv in inventories:
        peaks = peaks_by_domain[inv.immute_domain]
        items.append(build_cluster_item(inv, peaks, decide_cluster(inv, peaks, params), days))
    items.sort(key=_sort_key)

    shown = [item for item in items if include_keep or item["verdict"] != VERDICT_KEEP]
    return {
        "params": {
            "window_days": days,
            "city": city,
            "disk_target_percent": params.disk_target_pct,
            "net_watermark_percent": params.net_watermark_pct,
            "cpu_guard_percent": params.cpu_guard_pct,
            "min_nodes": params.min_nodes,
        },
        "summary": _summarize(items),
        "returned_cluster_count": min(len(shown), limit),
        "clusters": shown[:limit],
        "query_errors": query_errors,
    }
