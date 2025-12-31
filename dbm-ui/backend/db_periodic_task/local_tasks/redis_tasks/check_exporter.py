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
from backend.db_report.enums.redis_sub_type import RedisExporterCheckSubType
from backend.db_report.repo.task_record_repo import get_report_day_from_time

logger = logging.getLogger("root")


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
        self.check_type = RedisExporterCheckSubType.Exporter.value

    def start(self, report_day: int = None, batch_size: int = 20) -> tuple[int, int, int, int]:
        """
        redis cluster：
        1, list all cluster
        2, filter failed, write to db
        """
        if report_day is None:
            report_day = get_report_day_from_time(timezone.now())
        record_batch_ops = RedisCheckReportBatchOps(self.check_type, report_day)
        deleted_count = record_batch_ops.delete_old_record(360)
        logger.info(
            f"CheckRedisUpMetricTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )
        deleted_count = record_batch_ops.delete_today_record()
        logger.info(
            f"CheckRedisUpMetricTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )
        redis_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Redis.value)
        # 构建查询条件: 集群创建时间大于1小时
        query = Q(cluster_type__in=redis_cluster_types) & Q(create_at__lt=timezone.now() - timedelta(hours=1))
        cluster_list = Cluster.objects.filter(query).prefetch_related("tags")

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
                cluster_state_total[rows[0].state] += 1
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
        检查集群的tags是否为skip_check=true
        如果为true，则返回True, "skipped by skip_check:true"
        如果为false，则返回False, ""
        """
        tags = {tag.key: tag.value for tag in cluster.tags.all()} if cluster.tags else {}
        v = tags.get("temporary", "")
        if v in ["true", "yes", "True", "Yes", "1"]:
            return True, "skipped by temporary:{}".format(v)
        return False, ""

    def check_cluster(self, cluster: Cluster, report_day: int) -> list:
        """
        检查集群, 返回检查结果
        如果有异常，则返回异常记录
        """
        cluster_report = RedisClusterReport(cluster, report_day, self.check_type)
        last_error = None
        for i in range(3):
            try:
                records = self.check_cluster_inner(cluster_report, cluster)
                if records is not None:
                    return records
            except Exception as e:
                logger.error(f"check_cluster error: {e}, retry {i + 1} times, sleep {i * 3} seconds")
                last_error = e
                time.sleep(i * 3) + 1
        return cluster_report.make_error_record(f"system error after 3 times retry: {last_error}")

    def check_cluster_inner(self, cluster_report: RedisClusterReport, cluster: Cluster) -> list:
        """
        1. 获得所有的redis_up metric.
        2. 对比bk_target_ip, instance_port 是否一致
        3. 异常情况:
        - down               # exporter down. should not happen.
        - duplicate          # 重复的节点. 本集群的节点上报了相同的指标
        - redundant          # 多余的节点. 存在集群外的节点上报本集群的指标
        - redundant2         # 多余的metric. 本集群的节点上报了其他集群的指标
        """
        # 检查是否跳过检查
        skipped, reason = self.is_skip_check(cluster)
        if skipped:
            return cluster_report.make_skip_record(reason)

        # meta里没有storage节点，跳过检查，这种情况也属于异常，但不在这个报告的范围内，所以直接跳过
        all_node = get_all_storage_nodes(cluster)
        if len(all_node) == 0:
            return cluster_report.make_skip_record("skipped by no storage node")

        # 如果所有的node都为异常，则认为集群异常, 跳过检查
        all_node_status = [node.get("status") for node in all_node]
        if not any(node_status == InstanceStatus.RUNNING.value for node_status in all_node_status):
            return cluster_report.make_skip_record("skipped by no running node")

        self.check_storage(cluster, all_node, cluster_report)

        # 检查proxy. 如果proxy节点不存在或都为异常，可以跳过此步骤
        proxy_type = get_proxy_type(cluster)
        if proxy_type != "":
            proxy_node_list = get_all_proxy_nodes(cluster)
            if len(proxy_node_list) == 0:
                return cluster_report.make_skip_record("skipped by no proxy node")
            if not any(proxy_node.get("status") == InstanceStatus.RUNNING.value for proxy_node in proxy_node_list):
                return cluster_report.make_skip_record("skipped by all proxy nodes are abnormal")
            self.check_proxy(cluster, proxy_node_list, proxy_type, cluster_report)

        return cluster_report.make_records()

    def _check_nodes_metric(self, node_list: list, metric_val: dict, exporter_prefix: str) -> defaultdict:
        """
        检查节点metric的通用方法
        :param node_list: 节点列表
        :param metric_val: metric值字典
        :param exporter_prefix: exporter前缀，如 "master" 或 "slave" 或 "twemproxy" 或 "predixy"
        :return: msg_list defaultdict
        """
        original_exporter_prefix = exporter_prefix
        msg_list = defaultdict(list)
        for node in node_list:
            addr = _node_to_addr(node)
            item = metric_val.get(addr)
            if original_exporter_prefix == "" or original_exporter_prefix is None:
                exporter_prefix = self._instance_role_to_exporter_prefix(node.get("instance_role", ""))
            else:
                exporter_prefix = original_exporter_prefix
            # redis_master -> master, redis_slave -> slave, twemproxy -> twemproxy, predixy -> predixy
            if item is None or item["value"] == 0:  # metric not found or exporter down
                if node.get("status") == InstanceStatus.RUNNING.value:
                    msg = f"{exporter_prefix}_exporter_down"
                else:
                    # 其它状态下，没有上报是正常的，不处理
                    msg = "ok"
            elif item["value"] > 1:  # duplicate
                msg = f"{exporter_prefix}_exporter_duplicate"
            else:
                msg = "ok"
            msg_list[msg].append(node)
        return msg_list

    def _instance_role_to_exporter_prefix(self, instance_role: str) -> str:
        """
        将instance_role转换为exporter_prefix
        """
        if instance_role == "redis_master":
            return "redis_master"
        elif instance_role == "redis_slave":
            return "redis_slave"
        elif instance_role == "twemproxy":
            return "twemproxy"
        elif instance_role == "predixy":
            return "predixy"
        else:
            return instance_role

    def _generate_report_records(self, msg_list: defaultdict, cluster_report: RedisClusterReport, shard: str):
        """
        生成报告记录的通用方法
        :param msg_list: 消息列表字典
        :param cluster_report: 集群报告对象
        :param shard: 分片名称，如 "storage" 或 "twemproxy"
        """
        for msg, node_list in msg_list.items():
            if msg == "ok":
                state = ReportStateType.NORMAL.value
                full_msg = "ok"
            else:
                state = ReportStateType.ABNORMAL.value
                full_msg = f"{msg}: {','.join(_short_addr_list(node_list))}"
            cluster_report.append(state, shard, "-", full_msg)

    def check_storage(self, cluster: Cluster, all_node: list, cluster_report: RedisClusterReport):
        """
        检查storage
        """
        metric_val = fetch_metric_by_cluster(cluster.immute_domain)
        msg_list = self._check_nodes_metric(all_node, metric_val, "")

        # 检查是否存在多余的节点. 存在集群外的节点上报本集群的指标
        addr_list = {_node_to_addr(node) for node in all_node}  # 去重
        # cluster_domain 中返回的addr, 但不在all_node中.
        if metric_val is not None:
            for addr in metric_val:
                if addr not in addr_list:
                    exporter_prefix = self._instance_role_to_exporter_prefix(
                        metric_val[addr].get("instance_role", "redis")
                    )
                    msg_list[f"{exporter_prefix}_exporter_redundant"].append(_addr_to_node(addr))

        # 如果集群类型不是TendisRedisInstance，则检查是否存在多余的metric
        # 检查是否存在多余的metric. 本集群的节点上报了其他集群的指标
        if cluster.cluster_type != ClusterType.TendisRedisInstance.value:
            node_addr_map = {_node_to_addr(node): node for node in all_node}
            iplist = {node["ip"] for node in all_node}
            redundant2_metric_val = fetch_metric_by_iplist(list(iplist))
            if redundant2_metric_val is not None:
                for addr in redundant2_metric_val:
                    if addr not in node_addr_map:
                        exporter_prefix = self._instance_role_to_exporter_prefix(
                            redundant2_metric_val[addr].get("instance_role", "redis")
                        )
                        msg_list[f"{exporter_prefix}_exporter_redundant2"].append(_addr_to_node(addr))

        # 生成报告记录
        self._generate_report_records(msg_list, cluster_report, "storage")

    def check_proxy(
        self, cluster: Cluster, proxy_node_list: list, proxy_type: str, cluster_report: RedisClusterReport
    ):
        """
        检查proxy
        1. 获得所有的proxy_up metric.
        2. 对比bk_target_ip, instance_port 是否一致
        3. 异常情况:
        - down               # exporter down. should not happen.
        - duplicate          # 重复的proxy节点. 本集群的proxy节点上报了相同的指标
        - redundant          # 多余的proxy节点. 存在集群外的proxy节点上报本集群的指标
        - redundant2         # 多余的metric. 本集群的proxy节点上报了其他集群的指标
        """
        # check for proxy node
        proxy_metric_val = fetch_proxy_metric_by_cluster(cluster)
        proxy_msg_list = self._check_nodes_metric(proxy_node_list, proxy_metric_val, proxy_type)

        # 多余的proxy节点. 存在集群外的proxy节点上报本集群的指标
        all_proxy_node_addr_list = {_node_to_addr(proxy_node) for proxy_node in proxy_node_list}  # 去重
        for addr in proxy_metric_val:
            if addr not in all_proxy_node_addr_list:
                exporter_prefix = self._instance_role_to_exporter_prefix(proxy_type)
                proxy_msg_list[f"{exporter_prefix}_exporter_redundant"].append(_addr_to_node(addr))

        # 多余的metric. 本集群的proxy节点上报了其他集群的指标
        # proxy节点：同一个ip只会属于同一个集群的proxy
        proxy_node_addr_map = {_node_to_addr(proxy_node): proxy_node for proxy_node in proxy_node_list}
        proxy_iplist = {proxy_node["ip"] for proxy_node in proxy_node_list}
        redundant2_proxy_metric_val = fetch_proxy_metric_by_iplist(cluster.cluster_type, list(proxy_iplist))
        # 多余的metric. 本集群的proxy节点上报了其他集群的指标
        for addr in redundant2_proxy_metric_val:
            if addr not in proxy_node_addr_map:
                exporter_prefix = self._instance_role_to_exporter_prefix(proxy_type)
                proxy_msg_list[f"{exporter_prefix}_exporter_redundant2"].append(_addr_to_node(addr))

        # 生成报告记录
        self._generate_report_records(proxy_msg_list, cluster_report, proxy_type)
        return


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


def get_proxy_type(cluster: Cluster) -> str:
    """
    获取proxy类型
    """
    if "twemproxy" in cluster.cluster_type.lower():
        return "twemproxy"
    elif "predixy" in cluster.cluster_type.lower():
        return "predixy"
    else:
        return ""


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


def fetch_metric_by_iplist(iplist: list) -> dict:
    """
    查询ip列表的redis_up metric
    return [] or None(error)
    """
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    metrics_name = "bkmonitor:exporter_dbm_redis_exporter:redis_up"
    promql = """count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)
        ({metrics_name}{{bk_target_ip=~"{iplist_str}"}}
        ) """.format(
        metrics_name=metrics_name, iplist_str=build_promql_regex_pattern(iplist)
    )
    return _instant_query_metric(start_time, end_time, promql)


def fetch_metric_by_cluster(cluster_domain) -> dict:
    """
    查询集群的redis_up metric
    return [] or None(error)
    """
    logger.info("fetch_metric_by_cluster cluster : {} ".format(cluster_domain))
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    metrics_name = "bkmonitor:exporter_dbm_redis_exporter:redis_up"
    promql = """count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)
        ({metrics_name}{{cluster_domain="{cluster_domain}"}}
        ) """.format(
        metrics_name=metrics_name, cluster_domain=cluster_domain
    )
    return _instant_query_metric(start_time, end_time, promql)


def get_proxy_metrics_name(cluster_type: str) -> str:
    """
    获取proxy的metrics名称
    """
    if "twemproxy" in cluster_type.lower():
        return "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_up"
    elif "predixy" in cluster_type.lower():
        return "bkmonitor:exporter_dbm_predixy_exporter:predixy_up"
    else:
        return ""


def fetch_proxy_metric_by_cluster(cluster: Cluster) -> dict:
    """
    查询集群的proxy_up metric
    return [] or None(error)
    """
    metrics_name = get_proxy_metrics_name(cluster.cluster_type)
    if metrics_name == "":
        return {}
    logger.info("fetch_proxy_metric_by_cluster cluster : {} ".format(cluster.immute_domain))
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    promql = """count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)
        ({metrics_name}{{cluster_domain="{cluster_domain}"}})""".format(
        metrics_name=metrics_name, cluster_domain=cluster.immute_domain
    )
    return _instant_query_metric(start_time, end_time, promql)


def fetch_proxy_metric_by_iplist(cluster_type: str, iplist: list) -> dict:
    """
    查询ip列表的proxy_up metric
    return [] or None(error)
    """
    metrics_name = get_proxy_metrics_name(cluster_type)
    if metrics_name == "":
        return {}
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    promql = """count by (cluster_domain,instance,instance_role,instance_port,bk_target_ip)
        ({metrics_name}{{bk_target_ip=~"{iplist_str}"}}) """.format(
        metrics_name=metrics_name, iplist_str=build_promql_regex_pattern(iplist)
    )
    return _instant_query_metric(start_time, end_time, promql)


# 封装查询metric的函数, return value by ip_port
def _instant_query_metric(start_time: datetime.datetime, end_time: datetime.datetime, promql: str) -> dict:
    """
    查询metric
    return value by ip_port or None(error)
    """
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    params["query_configs"][0]["promql"] = promql
    metric_result = {}
    try:
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
    except Exception as e:
        logger.error("query metric error: {}".format(e))
        return None
    for item in series:
        ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
        metric_result[ip_port] = {
            "instance": ip_port,
            "instance_role": item["dimensions"]["instance_role"],
            "instance_port": item["dimensions"]["instance_port"],
            "bk_target_ip": item["dimensions"]["bk_target_ip"],
            "cluster_domain": item["dimensions"]["cluster_domain"],
            "value": item["datapoints"][0][0],
        }
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
