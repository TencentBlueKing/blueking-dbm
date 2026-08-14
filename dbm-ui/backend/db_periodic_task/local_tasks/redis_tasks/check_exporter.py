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
import datetime
import logging
import time
from collections import defaultdict
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.db_meta.api.cluster.nosqlcomm.redis_cluster_repo import DbmClusterRepository
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisCheckReportBatchOps, RedisClusterReport
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_abnormal_cluster_rows
from backend.db_report.repo.task_record_repo import get_report_day_from_time

logger = logging.getLogger("root")

# redis_up 指标名与 PromQL 片段（按 cluster_domain / ip 列表查询共用）
_REDIS_UP_METRICS_NAME = "bkmonitor:exporter_dbm_redis_exporter:redis_up"
_REDIS_UP_COUNT_BY = "count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)"


def _metric_series_for_addr(metric_val: dict | None, addr: str) -> list:
    """从监控查询结果中取 ip:port 对应的序列；兼容旧版 value 为单 dict。"""
    if not metric_val:
        return []
    raw = metric_val.get(addr)
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return raw
    return []


def _aggregate_metric_for_addr(metric_val: dict | None, addr: str) -> dict | None:
    """同一 ip:port 多条 series 时合并 value（求和），用于 exporter up / duplicate 判定。"""
    items = _metric_series_for_addr(metric_val, addr)
    if not items:
        return None
    total_value = sum(float(x.get("value", 0) or 0) for x in items)
    first = items[0]
    return {
        "instance": first.get("instance"),
        "instance_role": first.get("instance_role", "redis"),
        "instance_port": first.get("instance_port"),
        "bk_target_ip": first.get("bk_target_ip"),
        "cluster_domain": first.get("cluster_domain"),
        "value": total_value,
    }


def _first_instance_role_for_addr(metric_val: dict | None, addr: str) -> str:
    """冗余节点路径上取第一条 series 的 instance_role。"""
    items = _metric_series_for_addr(metric_val, addr)
    if not items:
        return "redis"
    return items[0].get("instance_role", "redis")


def _promql_redis_up_by_cluster(cluster_domain: str) -> str:
    return f"""{_REDIS_UP_COUNT_BY}
        ({_REDIS_UP_METRICS_NAME}{{cluster_domain="{cluster_domain}"}}
        ) """


def _promql_redis_up_by_iplist(iplist: list) -> str:
    pattern = build_promql_regex_pattern(iplist)
    return f"""{_REDIS_UP_COUNT_BY}
        ({_REDIS_UP_METRICS_NAME}{{bk_target_ip=~"{pattern}"}}
        ) """


def _metric_query_window() -> tuple[datetime.datetime, datetime.datetime]:
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    return start_time, end_time


def check_one_cluster(cluster_domain: str, print_result: bool = False) -> list:
    """
    检查一个集群, 返回检查结果,用于shell发起检查
    """
    report_day = get_report_day_from_time(timezone.now())
    cluster = Cluster.objects.get(immute_domain=cluster_domain)
    checker = CheckRedisUpMetricTask()
    rows = checker.check_cluster(cluster, report_day)
    if print_result:
        print(f"check_one_cluster {cluster_domain} result:")
        for row in rows:
            # print all fields of row
            for key, value in vars(row).items():
                print(f"{key}: {value}")
            print("-" * 100)
    return rows


class CheckRedisUpMetricTask:
    """检查redis_exporter的up指标, 每个节点的redis_exporter的up指标值为1, 否则认为异常"""

    check_type: str

    def __init__(self):
        self.check_type = RedisCheckSubType.Exporter.value

    def _log_delete_progress(self, report_day: int, deleted_count: int) -> None:
        logger.info(
            "CheckRedisUpMetricTask report_day: %s sub_type: %s deleted_count: %s",
            report_day,
            self.check_type,
            deleted_count,
        )

    def start(
        self,
        report_day: int = None,
        batch_size: int = 20,
        cluster_domain: str | None = None,
        bk_biz_id: int | None = None,
    ) -> tuple[int, int, int, int]:
        """
        redis cluster：
        1, list all cluster (or scoped by cluster_domain / bk_biz_id)
        2, filter failed, write to db
        """
        if cluster_domain and bk_biz_id is not None:
            raise ValueError("cluster_domain and bk_biz_id are mutually exclusive")
        scoped = bool(cluster_domain) or bk_biz_id is not None

        if report_day is None:
            report_day = get_report_day_from_time(timezone.now())
        record_batch_ops = RedisCheckReportBatchOps(self.check_type, report_day)

        redis_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Redis.value)
        # 构建查询条件: 集群创建时间大于1小时
        query = Q(cluster_type__in=redis_cluster_types) & Q(create_at__lt=timezone.now() - timedelta(hours=1))
        if cluster_domain:
            query &= Q(immute_domain=cluster_domain)
        if bk_biz_id is not None:
            query &= Q(bk_biz_id=bk_biz_id)

        cluster_list = list(Cluster.objects.filter(query).prefetch_related("tags"))
        cluster_id_list = [c.id for c in cluster_list]
        logger.info(
            "CheckRedisUpMetricTask clusters=%s cluster_domain=%s bk_biz_id=%s",
            len(cluster_id_list),
            cluster_domain or "-",
            bk_biz_id if bk_biz_id is not None else "-",
        )

        if scoped:
            deleted_count = record_batch_ops.delete_today_record_for_clusters(cluster_id_list)
            self._log_delete_progress(report_day, deleted_count)
        else:
            deleted_count = record_batch_ops.delete_old_record(360)
            self._log_delete_progress(report_day, deleted_count)
            deleted_count = record_batch_ops.delete_today_record()
            self._log_delete_progress(report_day, deleted_count)

        # app_total 统计每个状态的集群数量
        cluster_state_total = {
            ReportStateType.NORMAL.value: 0,
            ReportStateType.WARNING.value: 0,
            ReportStateType.ABNORMAL.value: 0,
        }

        total_num = 0
        for i in range(0, len(cluster_list), batch_size):
            for cluster in cluster_list[i : i + batch_size]:
                total_num += 1
                rows = self.check_cluster(cluster, report_day)
                if rows:
                    cluster_state_total[rows[0].state] += 1
                    ingest_abnormal_cluster_rows(
                        rows,
                        dimension=RedisPortraitDimensionCode.CONFIG_HEALTH,
                        prefix="[exporter]",
                    )
                for record in rows:
                    record_batch_ops.append(record)
            record_batch_ops.bulk_create()
        logger.info(
            f"CheckRedisUpMetricTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"cluster_state_total: {cluster_state_total}"
        )
        success_num = cluster_state_total[ReportStateType.NORMAL.value]
        warning_num = cluster_state_total[ReportStateType.WARNING.value]
        abnormal_num = cluster_state_total[ReportStateType.ABNORMAL.value]
        return (total_num, success_num, warning_num, abnormal_num)

    def is_skip_check(self, cluster: Cluster) -> tuple[bool, str]:
        """
        检查集群 tag `temporary` 是否为真（true/yes/1 等）
        若为真，则返回 True 与跳过原因；否则返回 False 与空字符串
        """
        tags = {tag.key: tag.value for tag in cluster.tags.all()} if cluster.tags else {}
        v = tags.get("temporary", "")
        if str(v).strip().lower() in ("true", "yes", "1"):
            return True, f"skipped by temporary:{v}"
        return False, ""

    def check_cluster(self, cluster: Cluster, report_day: int) -> list:
        """
        检查集群, 返回检查结果
        如果有异常，则返回异常记录
        """
        last_error = None
        for i in range(3):
            try:
                cluster_report = RedisClusterReport(cluster, report_day, self.check_type)
                records = self.check_cluster_inner(cluster_report, cluster)
                if records is not None:
                    return records
            except Exception as e:
                logger.error(f"check_cluster error: {e}, retry {i + 1} times, sleep {i * 3 + 1} seconds")
                last_error = e
                time.sleep(i * 3 + 1)
        final_cluster_report = RedisClusterReport(cluster, report_day, self.check_type)
        return final_cluster_report.make_error_record(f"system error after 3 times retry: {last_error}")

    def check_cluster_inner(self, cluster_report: RedisClusterReport, cluster: Cluster) -> list:
        """
        集群巡检主流程：
        1. 前置跳过（temporary / 无 storage / 无 running）
        2. 检查 storage（down / duplicate / redundant / redundant2）
        3. 有 proxy 时再检查 proxy；proxy 跳过仅记 WARNING，不影响 storage 结果
        """
        skipped, reason = self.is_skip_check(cluster)
        if skipped:
            return cluster_report.make_skip_record(reason)

        storage_nodes = get_all_storage_nodes(cluster)
        storage_skip_reason = self._get_storage_skip_reason(storage_nodes)
        if storage_skip_reason:
            return cluster_report.make_skip_record(storage_skip_reason)

        self.check_storage(cluster, storage_nodes, cluster_report)
        self._maybe_check_proxy(cluster, cluster_report)
        return cluster_report.make_records()

    @staticmethod
    def _has_running_node(node_list: list) -> bool:
        return any(node.get("status") == InstanceStatus.RUNNING.value for node in node_list)

    def _get_storage_skip_reason(self, storage_nodes: list) -> str | None:
        # meta 无 storage 属于异常，但不在本报告范围内，直接跳过
        if not storage_nodes:
            return "skipped by no storage node"
        if not self._has_running_node(storage_nodes):
            return "skipped by no running node"
        return None

    def _maybe_check_proxy(self, cluster: Cluster, cluster_report: RedisClusterReport) -> None:
        """有 proxy 类型才检查；无节点或节点全异常时只记 WARNING，storage 结果仍保留。"""
        proxy_type = get_proxy_type(cluster)
        if not proxy_type:
            return

        proxy_nodes = get_all_proxy_nodes(cluster)
        if not proxy_nodes:
            cluster_report.append(
                ReportStateType.WARNING.value,
                proxy_type,
                "-",
                "skipped by no proxy node",
            )
            return
        if not self._has_running_node(proxy_nodes):
            cluster_report.append(
                ReportStateType.WARNING.value,
                proxy_type,
                "-",
                "skipped by all proxy nodes are abnormal",
            )
            return

        self.check_proxy(cluster, proxy_nodes, proxy_type, cluster_report)

    def check_storage(self, cluster: Cluster, all_node: list, cluster_report: RedisClusterReport):
        """storage：比对 meta 节点与 redis_up，再补 redundant / redundant2。"""
        metric_val = fetch_metric_by_cluster(cluster.immute_domain)
        msg_list = self._check_nodes_metric(all_node, metric_val, "")
        self._append_storage_redundant_msgs(msg_list, cluster, all_node, metric_val)
        self._generate_report_records(msg_list, cluster_report, "storage")

    def check_proxy(
        self, cluster: Cluster, proxy_node_list: list, proxy_type: str, cluster_report: RedisClusterReport
    ):
        """proxy：比对 meta 节点与 proxy_up，再补 redundant / redundant2。"""
        proxy_metric_val = fetch_proxy_metric_by_cluster(cluster)
        proxy_msg_list = self._check_nodes_metric(proxy_node_list, proxy_metric_val, proxy_type)
        self._append_proxy_redundant_msgs(proxy_msg_list, cluster, proxy_node_list, proxy_type, proxy_metric_val)
        self._generate_report_records(proxy_msg_list, cluster_report, proxy_type)

    def _check_nodes_metric(self, node_list: list, metric_val: dict | None, exporter_prefix: str) -> defaultdict:
        """
        按 meta 节点逐个比对 metric：
        - 无数据或 value=0 且 running → *_exporter_down
        - value>1 → *_exporter_duplicate
        - 其余 → ok
        exporter_prefix 为空时，按节点 instance_role 决定前缀。
        """
        msg_list = defaultdict(list)
        metric_val = metric_val or {}
        fixed_prefix = exporter_prefix or None
        for node in node_list:
            addr = _node_to_addr(node)
            item = _aggregate_metric_for_addr(metric_val, addr)
            prefix = fixed_prefix or self._instance_role_to_exporter_prefix(node.get("instance_role", ""))
            if item is None or item["value"] == 0:
                if node.get("status") == InstanceStatus.RUNNING.value:
                    msg = f"{prefix}_exporter_down"
                else:
                    # 非 running 无上报视为正常
                    msg = "ok"
            elif item["value"] > 1:
                msg = f"{prefix}_exporter_duplicate"
            else:
                msg = "ok"
            msg_list[msg].append(node)
            logger.debug(
                "check_nodes_metric msg=%s addr=%s role=%s status=%s value=%s",
                msg,
                addr,
                node.get("instance_role", ""),
                node.get("status", ""),
                None if item is None else item.get("value"),
            )
        return msg_list

    def _instance_role_to_exporter_prefix(self, instance_role: str) -> str:
        """instance_role 与 exporter 前缀一致，直接透传。"""
        return instance_role

    def _generate_report_records(self, msg_list: defaultdict, cluster_report: RedisClusterReport, shard: str):
        """把 msg_list 写入 cluster_report；ok 记 NORMAL，其它记 ABNORMAL。"""
        for msg, node_list in msg_list.items():
            if msg == "ok":
                state = ReportStateType.NORMAL.value
                full_msg = "ok"
            else:
                state = ReportStateType.ABNORMAL.value
                full_msg = f"{msg}: {','.join(_short_addr_list(node_list))}"
            cluster_report.append(state, shard, "-", full_msg)

    def _append_redundant_addrs(
        self,
        msg_list: defaultdict,
        known_addrs: set[str],
        metric_val: dict | None,
        prefix_for_addr,
    ) -> None:
        """cluster metric 中出现、但 meta 不存在的 addr → *_exporter_redundant。"""
        if not metric_val:
            return
        for addr in metric_val:
            if addr in known_addrs:
                continue
            prefix = prefix_for_addr(addr)
            msg_list[f"{prefix}_exporter_redundant"].append(_addr_to_node(addr))

    def _append_storage_redundant_msgs(
        self,
        msg_list: defaultdict,
        cluster: Cluster,
        all_node: list,
        metric_val: dict | None,
    ) -> None:
        """
        storage 多余上报：
        - redundant: 集群外节点上报了本集群指标
        - redundant2: 本集群节点上报了其他集群指标（TendisRedisInstance 跳过）
        """
        known_addrs = {_node_to_addr(node) for node in all_node}
        self._append_redundant_addrs(
            msg_list,
            known_addrs,
            metric_val,
            lambda addr: self._instance_role_to_exporter_prefix(_first_instance_role_for_addr(metric_val, addr)),
        )

        if cluster.cluster_type == ClusterType.TendisRedisInstance.value:
            return

        iplist = {node["ip"] for node in all_node}
        redundant2_metric_val = fetch_metric_by_iplist(list(iplist))
        if not redundant2_metric_val:
            return
        for addr, series_list in redundant2_metric_val.items():
            for series in series_list:
                if series["cluster_domain"] == cluster.immute_domain:
                    continue
                prefix = self._instance_role_to_exporter_prefix(series["instance_role"])
                msg_list[f"{prefix}_exporter_redundant2"].append(_addr_to_node(addr))

    def _append_proxy_redundant_msgs(
        self,
        proxy_msg_list: defaultdict,
        cluster: Cluster,
        proxy_node_list: list,
        proxy_type: str,
        proxy_metric_val: dict | None,
    ) -> None:
        """
        proxy 多余上报：
        - redundant: 集群外 proxy 节点上报了本集群指标
        - redundant2: 本集群 proxy IP 上报了 meta 外地址的指标
        """
        known_addrs = {_node_to_addr(proxy_node) for proxy_node in proxy_node_list}
        prefix = self._instance_role_to_exporter_prefix(proxy_type)
        self._append_redundant_addrs(
            proxy_msg_list,
            known_addrs,
            proxy_metric_val,
            lambda _addr: prefix,
        )

        # proxy：同一 IP 通常只属于一个集群的 proxy；按 IP 查到的非 meta 地址视为 redundant2
        proxy_iplist = {proxy_node["ip"] for proxy_node in proxy_node_list}
        redundant2_proxy_metric_val = fetch_proxy_metric_by_iplist(cluster.cluster_type, list(proxy_iplist))
        if not redundant2_proxy_metric_val:
            return
        for addr in redundant2_proxy_metric_val:
            if addr in known_addrs:
                continue
            proxy_msg_list[f"{prefix}_exporter_redundant2"].append(_addr_to_node(addr))


def _node_to_addr(node: dict) -> str:
    """
    将node字典转换为ip:port
    """
    return f"{node['ip']}:{node['port']}"


def _addr_to_node(addr: str) -> dict:
    """
    将ip:port转换为node
    """
    ip, port_str = addr.split(":")
    return {"ip": ip, "port": int(port_str)}


def _proxy_kind_from_cluster_type(cluster_type: str) -> str:
    """根据 cluster_type 子串识别 proxy 种类：twemproxy / predixy；无则返回空串。"""
    ct = cluster_type.lower()
    if "twemproxy" in ct:
        return "twemproxy"
    if "predixy" in ct:
        return "predixy"
    return ""


def get_proxy_type(cluster: Cluster) -> str:
    """获取 proxy 类型（与 cluster_type 中的关键字一致）。"""
    return _proxy_kind_from_cluster_type(cluster.cluster_type)


_PROXY_UP_METRICS_NAME = {
    "twemproxy": "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_up",
    "predixy": "bkmonitor:exporter_dbm_predixy_exporter:predixy_up",
}


def get_proxy_metrics_name(cluster_type: str) -> str:
    """获取 proxy 的 metrics 名称。"""
    return _PROXY_UP_METRICS_NAME.get(_proxy_kind_from_cluster_type(cluster_type), "")


def _short_addr_list(node_list: list) -> list:
    """
    将ip:port列表转换为ip列表
    1. 只有一个端口时，使用ip:port
    2. 有多个端口时，使用ip:[port1, port2, ...]
    3. 有多个端口且连续时，使用ip:[port1-port2]
    4. 有多个端口且不连续时，使用ip:[port1, port2, ...]
    """
    # sort node_list by ip, port
    node_list.sort(key=lambda x: (x["ip"], int(x["port"])))
    ip_port_map = {}
    for node in node_list:
        ip = node["ip"]
        port = int(node["port"])
        if ip not in ip_port_map:
            ip_port_map[ip] = []
        ip_port_map[ip].append(port)
    short_addr_list = []
    for ip, ports in ip_port_map.items():
        if len(ports) == 1:
            short_addr_list.append(f"{ip}:{ports[0]}")
        else:
            # 将连续端口合并为范围，不连续的单独列出
            ranges = []
            start = ports[0]
            end = start
            for port in ports[1:]:
                if port == end + 1:
                    end = port
                else:
                    if start == end:
                        ranges.append(f"{ip}:{start}")
                    else:
                        ranges.append(f"{ip}:{start}-{end}")
                    start = port
                    end = port
            # 处理最后一个范围
            if start == end:
                ranges.append(f"{ip}:{start}")
            else:
                ranges.append(f"{ip}:{start}-{end}")
            short_addr_list.extend(ranges)
    return short_addr_list


def get_all_storage_nodes(cluster: Cluster) -> list:
    """
        获取所有节点的ip和端口信息
        {
        "bk_cloud_id": instance.machine.bk_cloud_id if instance.machine else None,
        "machine_type": instance.machine.machine_type if instance.machine else None,
        "id": instance.id,
        "bk_biz_id": instance.bk_biz_id,
        "bk_host_id": instance.machine.bk_host_id if instance.machine else None,
        "ip": instance.machine.ip if instance.machine else None,
        "port": instance.port,
        "instance_role": instance.instance_role,
        "seg_range": seg_range,  # shardName
    }
    """
    return DbmClusterRepository.fetch_storage_list(cluster_id=cluster.id)


def get_all_proxy_nodes(cluster: Cluster) -> list:
    """
    获取所有proxy节点的ip和端口信息
    """
    return DbmClusterRepository.fetch_proxy_list(bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id)


def fetch_metric_by_iplist(iplist: list) -> dict | None:
    """
    查询ip列表的redis_up metric
    成功: dict[ip:port, list[单条 series 字段]]；查询失败: None
    """
    start_time, end_time = _metric_query_window()
    promql = _promql_redis_up_by_iplist(iplist)
    return _instant_query_metric(start_time, end_time, promql)


def fetch_metric_by_cluster(cluster_domain) -> dict | None:
    """
    查询集群的redis_up metric
    成功: dict[ip:port, list[单条 series 字段]]；查询失败: None
    """
    logger.info("fetch_metric_by_cluster cluster : {} ".format(cluster_domain))
    start_time, end_time = _metric_query_window()
    promql = _promql_redis_up_by_cluster(cluster_domain)
    return _instant_query_metric(start_time, end_time, promql)


def fetch_proxy_metric_by_cluster(cluster: Cluster) -> dict | None:
    """
    查询集群的proxy_up metric
    成功: dict[ip:port, list[单条 series 字段]]；无 proxy 指标名时: {}；查询失败: None
    """
    metrics_name = get_proxy_metrics_name(cluster.cluster_type)
    if not metrics_name:
        return {}
    logger.info("fetch_proxy_metric_by_cluster cluster : {} ".format(cluster.immute_domain))
    start_time, end_time = _metric_query_window()
    promql = """count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)
        ({metrics_name}{{cluster_domain="{cluster_domain}"}})""".format(
        metrics_name=metrics_name, cluster_domain=cluster.immute_domain
    )
    return _instant_query_metric(start_time, end_time, promql)


def fetch_proxy_metric_by_iplist(cluster_type: str, iplist: list) -> dict | None:
    """
    查询ip列表的proxy_up metric
    成功: dict[ip:port, list[单条 series 字段]]；无 proxy 指标名时: {}；查询失败: None
    """
    metrics_name = get_proxy_metrics_name(cluster_type)
    if not metrics_name:
        return {}
    start_time, end_time = _metric_query_window()
    promql = """count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)
        ({metrics_name}{{bk_target_ip=~"{iplist_str}"}}) """.format(
        metrics_name=metrics_name, iplist_str=build_promql_regex_pattern(iplist)
    )
    return _instant_query_metric(start_time, end_time, promql)


# 封装查询metric的函数, 同一 ip:port 可能对应多条 series
def _instant_query_metric(start_time: datetime.datetime, end_time: datetime.datetime, promql: str) -> dict | None:
    """
    查询 metric
    成功: defaultdict[str, list[dict]]，key 为 bk_target_ip:instance_port，value 为该地址下多条 series 记录
    失败: None
    """
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    params["query_configs"][0]["promql"] = promql
    metric_result = defaultdict(list)
    try:
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
    except Exception as e:
        logger.error("query metric error: {}".format(e))
        return None
    for item in series:
        ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
        metric_result[ip_port].append(
            {
                "instance": ip_port,
                "instance_role": item["dimensions"]["instance_role"],
                "instance_port": item["dimensions"]["instance_port"],
                "bk_target_ip": item["dimensions"]["bk_target_ip"],
                "cluster_domain": item["dimensions"]["cluster_domain"],
                "value": item["datapoints"][0][0],
            }
        )
    return metric_result


def build_promql_regex_pattern(value_list: list) -> str:
    """
    构建promql regex的pattern，用于promql查询的=~操作
    value_list: list[str]
    return: str
    example:
    value_list: ["aa", "bb", "cc"]
    return: "^(aa|bb|cc)$"
    注意，正常prometheus不需要前缀^和后缀$，但蓝鲸监控需要，否则它会匹配到更多的数据
    """
    return "^(" + "|".join(value_list) + ")$"
