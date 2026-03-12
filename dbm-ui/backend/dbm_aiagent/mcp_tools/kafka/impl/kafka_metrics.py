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
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.components import BKMonitorV3Api
from backend.db_meta.models import Cluster
from backend.utils.time import timezone2timestamp

logger = logging.getLogger("root")

# 查询模板
UNIFY_QUERY_PARAMS = {
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    "start_time": 0,
    "end_time": 0,
    "slimit": 500,
    "down_sample_range": "5m",
    "type": "range",
}


# Kafka 监控指标 PromQL 模板
KAFKA_METRICS_PROMQL = {
    # 1. 生产消费流量指标
    "producer_traffic": {
        "desc": "生产流量(字节/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_bytesin_total{cluster_domain="%s"}[5m])
        )""",
    },
    "consumer_traffic": {
        "desc": "消费流量(字节/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_bytesout_total{cluster_domain="%s"}[5m])
        )""",
    },
    "producer_msg_rate": {
        "desc": "生产消息速率(条/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_messagesin_total{cluster_domain="%s"}[5m])
        )""",
    },
    # 2. CPU 指标
    "cpu_usage_avg": {
        "desc": "Broker平均CPU利用率(%)",
        "promql": """avg by (cluster_domain) (
            avg_over_time(bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    "cpu_usage_max": {
        "desc": "Broker峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    # 3. 内存指标
    "memory_usage_avg": {
        "desc": "Broker平均内存利用率(%)",
        "promql": """avg by (cluster_domain) (
            avg_over_time(bkmonitor:dbm_system:mem:pct_used{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    "memory_usage_max": {
        "desc": "Broker峰值内存利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(bkmonitor:dbm_system:mem:pct_used{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    "jvm_heap_usage": {
        "desc": "JVM堆内存使用率(%)",
        "promql": """avg by (cluster_domain) (
            (kafka_server_kafkaserver_heapmemoryused{cluster_domain="%s"}
            / kafka_server_kafkaserver_heapmemorymax{cluster_domain="%s"}) * 100
        )""",
    },
    # 4. 磁盘指标
    "disk_usage": {
        "desc": "磁盘使用率(%)",
        "promql": """max by (cluster_domain, instance, mount_point) (
            max_over_time(bkmonitor:dbm_system:disk:in_use{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    "disk_io_read": {
        "desc": "磁盘读取速率(字节/秒)",
        "promql": """sum by (cluster_domain) (
            rate(bkmonitor:dbm_system:io:read_bytes{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    "disk_io_write": {
        "desc": "磁盘写入速率(字节/秒)",
        "promql": """sum by (cluster_domain) (
            rate(bkmonitor:dbm_system:io:write_bytes{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    # 5. 网络指标
    "network_in": {
        "desc": "网络流入速率(字节/秒)",
        "promql": """sum by (cluster_domain) (
            rate(bkmonitor:dbm_system:net:bytes_recv{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    "network_out": {
        "desc": "网络流出速率(字节/秒)",
        "promql": """sum by (cluster_domain) (
            rate(bkmonitor:dbm_system:net:bytes_sent{cluster_domain="%s",instance_role="broker"}[5m])
        )""",
    },
    # 6. Kafka 性能指标
    "request_queue_size": {
        "desc": "请求队列大小",
        "promql": """max by (cluster_domain) (
            kafka_network_requestchannel_requestqueuesize{cluster_domain="%s"}
        )""",
    },
    "response_queue_size": {
        "desc": "响应队列大小",
        "promql": """max by (cluster_domain) (
            kafka_network_requestchannel_responsequeuesize{cluster_domain="%s"}
        )""",
    },
    "active_controllers": {
        "desc": "活跃Controller数量",
        "promql": """sum by (cluster_domain) (
            kafka_controller_kafkacontroller_activecontrollercount{cluster_domain="%s"}
        )""",
    },
    "under_replicated_partitions": {
        "desc": "副本不足的分区数",
        "promql": """sum by (cluster_domain) (
            kafka_server_replicamanager_underreplicatedpartitions{cluster_domain="%s"}
        )""",
    },
    "offline_partitions": {
        "desc": "离线分区数",
        "promql": """sum by (cluster_domain) (
            kafka_controller_kafkacontroller_offlinepartitionscount{cluster_domain="%s"}
        )""",
    },
    "isr_shrinks": {
        "desc": "ISR收缩速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_replicamanager_isrshrinks_total{cluster_domain="%s"}[5m])
        )""",
    },
    "isr_expands": {
        "desc": "ISR扩展速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_replicamanager_isrexpands_total{cluster_domain="%s"}[5m])
        )""",
    },
    # 7. 延迟指标
    "produce_request_time": {
        "desc": "生产请求平均延迟(ms)",
        "promql": """avg by (cluster_domain) (
            kafka_network_requestmetrics_totaltimems{cluster_domain="%s",request="Produce",quantile="0.95"}
        )""",
    },
    "fetch_request_time": {
        "desc": "消费请求平均延迟(ms)",
        "promql": """avg by (cluster_domain) (
            kafka_network_requestmetrics_totaltimems{cluster_domain="%s",request="FetchConsumer",quantile="0.95"}
        )""",
    },
    # 8. ZooKeeper 指标
    "zk_connections": {
        "desc": "ZooKeeper连接数",
        "promql": """sum by (cluster_domain) (
            kafka_server_sessionexpirelistener_zkconnectionspersec{cluster_domain="%s"}
        )""",
    },
    # 9. 日志指标
    "log_flush_rate": {
        "desc": "日志刷盘速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_log_log_logflushrateandsizems_count{cluster_domain="%s"}[5m])
        )""",
    },
    "log_size": {
        "desc": "日志总大小(字节)",
        "promql": """sum by (cluster_domain) (
            kafka_log_log_size{cluster_domain="%s"}
        )""",
    },
    # 10. 请求速率指标
    "produce_request_rate": {
        "desc": "生产请求速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_totalproducerequests_total{cluster_domain="%s"}[5m])
        )""",
    },
    "fetch_request_rate": {
        "desc": "消费请求速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_totalfetchrequests_total{cluster_domain="%s"}[5m])
        )""",
    },
    "failed_produce_request_rate": {
        "desc": "生产请求失败速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_failedproducerequests_total{cluster_domain="%s"}[5m])
        )""",
    },
    "failed_fetch_request_rate": {
        "desc": "消费请求失败速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            rate(kafka_server_brokertopicmetrics_failedfetchrequests_total{cluster_domain="%s"}[5m])
        )""",
    },
    # 11. 连接与负载指标
    "tcp_established": {
        "desc": "TCP已建立连接数",
        "promql": """sum by (cluster_domain) (
            bkmonitor:dbm_system:netstat:cur_tcp_estab{cluster_domain="%s",instance_role="broker"}
        )""",
    },
    "system_load1": {
        "desc": "系统1分钟负载",
        "promql": """avg by (cluster_domain) (
            bkmonitor:dbm_system:load:load1{cluster_domain="%s",instance_role="broker"}
        )""",
    },
}


# Kafka 维度明细指标 PromQL 模板（TopN 查询）
KAFKA_DETAIL_METRICS_PROMQL = {
    # Topic 维度
    "topic_traffic_in": {
        "desc": "Topic生产流量TopN(字节/秒)",
        "dimension": "topic",
        "label_key": "topic",
        "promql": """topk({top_n},
            sum by (topic) (
                rate(kafka_server_brokertopicmetrics_bytesin_total{{cluster_domain="{cluster_domain}",topic!=""}}[5m])
            )
        )""",
    },
    "topic_traffic_out": {
        "desc": "Topic消费流量TopN(字节/秒)",
        "dimension": "topic",
        "label_key": "topic",
        "promql": """topk({top_n},
            sum by (topic) (
                rate(kafka_server_brokertopicmetrics_bytesout_total{{cluster_domain="{cluster_domain}",topic!=""}}[5m])
            )
        )""",
    },
    "topic_message_rate": {
        "desc": "Topic消息速率TopN(条/秒)",
        "dimension": "topic",
        "label_key": "topic",
        "promql": """topk({top_n},
            sum by (topic) (
                rate(kafka_server_brokertopicmetrics_messagesin_total{{cluster_domain="{cluster_domain}",topic!=""}}[5m])
            )
        )""",
    },
    "topic_log_size": {
        "desc": "Topic数据量TopN(字节)",
        "dimension": "topic",
        "label_key": "topic",
        "promql": """topk({top_n},
            sum by (topic) (
                kafka_log_log_size{{cluster_domain="{cluster_domain}",topic!=""}}
            )
        )""",
    },
    # Consumer Group 维度
    "consumer_group_lag": {
        "desc": "消费组积压TopN(条)",
        "dimension": "consumer_group",
        "label_key": "consumergroup",
        "promql": """topk({top_n},
            sum by (consumergroup) (
                kafka_consumergroup_lag{{cluster_domain="{cluster_domain}",consumergroup!=""}}
            )
        )""",
    },
    # Broker 维度
    "broker_traffic_in": {
        "desc": "Broker生产流量(字节/秒)",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """sum by (instance) (
            rate(kafka_server_brokertopicmetrics_bytesin_total{{cluster_domain="{cluster_domain}"}}[5m])
        )""",
    },
    "broker_traffic_out": {
        "desc": "Broker消费流量(字节/秒)",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """sum by (instance) (
            rate(kafka_server_brokertopicmetrics_bytesout_total{{cluster_domain="{cluster_domain}"}}[5m])
        )""",
    },
    "broker_produce_request_rate": {
        "desc": "Broker生产请求速率(次/秒)",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """sum by (instance) (
            rate(kafka_server_brokertopicmetrics_totalproducerequests_total{{cluster_domain="{cluster_domain}"}}[5m])
        )""",
    },
    "broker_fetch_request_rate": {
        "desc": "Broker消费请求速率(次/秒)",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """sum by (instance) (
            rate(kafka_server_brokertopicmetrics_totalfetchrequests_total{{cluster_domain="{cluster_domain}"}}[5m])
        )""",
    },
    "broker_cpu_usage": {
        "desc": "Broker CPU使用率(%)",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{cluster_domain="{cluster_domain}",instance_role="broker"}}[5m]
        )""",
    },
    "broker_tcp_established": {
        "desc": "Broker TCP连接数",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """bkmonitor:dbm_system:netstat:cur_tcp_estab{{cluster_domain="{cluster_domain}",instance_role="broker"}}""",
    },
    # Disk 维度
    "disk_usage_detail": {
        "desc": "磁盘使用率按挂载点(%)",
        "dimension": "disk",
        "label_key": "mount_point",
        "promql": """max_over_time(
            bkmonitor:dbm_system:disk:in_use{{cluster_domain="{cluster_domain}",instance_role="broker"}}[5m]
        )""",
    },
}


def query_kafka_detail_metrics(
    bk_biz_id: int,
    cluster_domain: str,
    metric_name: str,
    top_n: int = 10,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict:
    """
    查询 Kafka 维度明细指标（TopN）

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        metric_name: 指标名称，参见 KAFKA_DETAIL_METRICS_PROMQL
        top_n: 返回 TopN 条目，默认10
        start_time: 开始时间，默认1小时前
        end_time: 结束时间，默认当前时间

    Returns:
        包含维度明细数据的字典
    """
    # 验证集群是否存在
    try:
        Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        return {"error": f"集群不存在: {cluster_domain}"}

    # 验证指标名称
    if metric_name not in KAFKA_DETAIL_METRICS_PROMQL:
        valid_names = ", ".join(KAFKA_DETAIL_METRICS_PROMQL.keys())
        return {"error": f"无效的指标名称: {metric_name}，可选值: {valid_names}"}

    metric_config = KAFKA_DETAIL_METRICS_PROMQL[metric_name]

    # 设置默认时间范围（最近1小时）
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=1)

    start_timestamp = int(timezone2timestamp(start_time))
    end_timestamp = int(timezone2timestamp(end_time))

    # 构建 PromQL
    promql = metric_config["promql"].format(cluster_domain=cluster_domain, top_n=top_n)

    # 构建查询参数
    query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    query_params["bk_biz_id"] = bk_biz_id
    query_params["start_time"] = start_timestamp
    query_params["end_time"] = end_timestamp
    query_params["query_configs"][0]["promql"] = promql

    result = {
        "cluster_domain": cluster_domain,
        "dimension": metric_config["dimension"],
        "metric_name": metric_name,
        "metric_desc": metric_config["desc"],
        "items": [],
        "total_series_count": 0,
    }

    try:
        response = BKMonitorV3Api.unify_query(query_params)

        if response and "series" in response:
            series_list = response["series"]
            result["total_series_count"] = len(series_list)
            label_key = metric_config["label_key"]

            for series in series_list:
                # 提取维度标签
                dimensions = series.get("dimensions", {})
                label = dimensions.get(label_key, "unknown")

                # 提取数据点并计算统计信息
                datapoints = series.get("datapoints", [])
                values = [point[0] for point in datapoints if point[0] is not None]

                item = {"label": label, "latest_value": 0, "statistics": {}}
                if values:
                    item["latest_value"] = values[-1]
                    item["statistics"] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "latest": values[-1],
                    }

                result["items"].append(item)

            # 按 latest_value 降序排序
            result["items"].sort(key=lambda x: x["latest_value"], reverse=True)

    except Exception as e:
        logger.error(f"查询维度明细指标 {metric_name} 失败: {str(e)}")
        result["error"] = str(e)

    return result


def query_kafka_metrics(
    bk_biz_id: int,
    cluster_domain: str,
    metric_types: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict:
    """
    查询 Kafka 集群监控指标

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        metric_types: 指标类型列表，不传则查询所有指标
        start_time: 开始时间，默认7天前
        end_time: 结束时间，默认当前时间

    Returns:
        包含监控指标数据的字典
    """
    # 验证集群是否存在
    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        return {"error": f"集群不存在: {cluster_domain}"}

    # 设置默认时间范围（最近7天）
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(days=7)

    start_timestamp = int(timezone2timestamp(start_time))
    end_timestamp = int(timezone2timestamp(end_time))

    # 如果未指定指标类型，查询所有指标
    if not metric_types:
        metric_types = list(KAFKA_METRICS_PROMQL.keys())

    # 验证指标类型
    invalid_metrics = [m for m in metric_types if m not in KAFKA_METRICS_PROMQL]
    if invalid_metrics:
        return {"error": f"无效的指标类型: {', '.join(invalid_metrics)}"}

    result = {
        "cluster_domain": cluster_domain,
        "bk_biz_id": bk_biz_id,
        "cluster_id": cluster.id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "time_range_days": (end_time - start_time).days,
        "metrics": {},
    }

    # 查询每个指标
    for metric_type in metric_types:
        metric_config = KAFKA_METRICS_PROMQL[metric_type]
        promql = metric_config["promql"].replace("%s", cluster_domain)

        # 构建查询参数
        query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        query_params["bk_biz_id"] = bk_biz_id
        query_params["start_time"] = start_timestamp
        query_params["end_time"] = end_timestamp
        query_params["query_configs"][0]["promql"] = promql

        try:
            # 调用监控接口
            response = BKMonitorV3Api.unify_query(query_params)

            # 解析数据
            metric_data = {
                "description": metric_config["desc"],
                "data_points": [],
                "statistics": {},
            }

            if response and "series" in response:
                series_list = response["series"]
                if series_list:
                    # 按 series 分别统计，避免多 series 合并导致统计失真
                    all_values = []
                    for series in series_list:
                        if "datapoints" in series:
                            datapoints = series["datapoints"]
                            metric_data["data_points"].extend(datapoints)
                            series_values = [p[0] for p in datapoints if p[0] is not None]
                            all_values.extend(series_values)

                    # 统计信息：对于 sum/avg by (cluster_domain) 的 PromQL 通常只有一个 series
                    # 多 series 场景下取所有数据点的统计，语义由 PromQL 聚合保证
                    if all_values:
                        metric_data["statistics"] = {
                            "min": min(all_values),
                            "max": max(all_values),
                            "avg": sum(all_values) / len(all_values),
                            "latest": all_values[-1],
                            "count": len(all_values),
                            "series_count": len(series_list),
                        }

            result["metrics"][metric_type] = metric_data

        except Exception as e:
            logger.error(f"查询指标 {metric_type} 失败: {str(e)}")
            result["metrics"][metric_type] = {
                "description": metric_config["desc"],
                "error": str(e),
            }

    return result


def get_kafka_performance_summary(
    bk_biz_id: int,
    cluster_domain: str,
    days: int = 7,
) -> Dict:
    """
    获取 Kafka 集群性能摘要（最近N天）

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        days: 查询天数，默认7天

    Returns:
        包含性能摘要的字典
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # 查询关键指标
    key_metrics = [
        "producer_traffic",
        "consumer_traffic",
        "cpu_usage_avg",
        "cpu_usage_max",
        "memory_usage_max",
        "disk_usage",
        "under_replicated_partitions",
        "offline_partitions",
        "produce_request_rate",
        "fetch_request_rate",
        "failed_produce_request_rate",
        "failed_fetch_request_rate",
    ]

    metrics_data = query_kafka_metrics(
        bk_biz_id=bk_biz_id,
        cluster_domain=cluster_domain,
        metric_types=key_metrics,
        start_time=start_time,
        end_time=end_time,
    )

    if "error" in metrics_data:
        return metrics_data

    # 构建性能摘要
    summary = {
        "cluster_domain": cluster_domain,
        "time_range": f"最近{days}天",
        "traffic_summary": {},
        "resource_summary": {},
        "health_summary": {},
        "request_summary": {},
    }

    # 流量摘要
    metrics = metrics_data.get("metrics", {})
    if "producer_traffic" in metrics and metrics["producer_traffic"].get("statistics"):
        stats = metrics["producer_traffic"]["statistics"]
        summary["traffic_summary"]["producer_peak_bytes_per_sec"] = stats.get("max", 0)
        summary["traffic_summary"]["producer_avg_bytes_per_sec"] = stats.get("avg", 0)

    if "consumer_traffic" in metrics and metrics["consumer_traffic"].get("statistics"):
        stats = metrics["consumer_traffic"]["statistics"]
        summary["traffic_summary"]["consumer_peak_bytes_per_sec"] = stats.get("max", 0)
        summary["traffic_summary"]["consumer_avg_bytes_per_sec"] = stats.get("avg", 0)

    # 资源摘要
    if "cpu_usage_avg" in metrics and metrics["cpu_usage_avg"].get("statistics"):
        summary["resource_summary"]["cpu_avg_percent"] = metrics["cpu_usage_avg"]["statistics"].get("avg", 0)

    if "cpu_usage_max" in metrics and metrics["cpu_usage_max"].get("statistics"):
        summary["resource_summary"]["cpu_peak_percent"] = metrics["cpu_usage_max"]["statistics"].get("max", 0)

    if "memory_usage_max" in metrics and metrics["memory_usage_max"].get("statistics"):
        summary["resource_summary"]["memory_peak_percent"] = metrics["memory_usage_max"]["statistics"].get("max", 0)

    if "disk_usage" in metrics and metrics["disk_usage"].get("statistics"):
        summary["resource_summary"]["disk_peak_percent"] = metrics["disk_usage"]["statistics"].get("max", 0)

    # 健康摘要
    if "under_replicated_partitions" in metrics and metrics["under_replicated_partitions"].get("statistics"):
        summary["health_summary"]["max_under_replicated_partitions"] = int(
            metrics["under_replicated_partitions"]["statistics"].get("max", 0)
        )

    if "offline_partitions" in metrics and metrics["offline_partitions"].get("statistics"):
        summary["health_summary"]["max_offline_partitions"] = int(
            metrics["offline_partitions"]["statistics"].get("max", 0)
        )

    # 请求速率摘要
    if "produce_request_rate" in metrics and metrics["produce_request_rate"].get("statistics"):
        summary["request_summary"]["produce_request_avg_per_sec"] = metrics["produce_request_rate"]["statistics"].get(
            "avg", 0
        )

    if "fetch_request_rate" in metrics and metrics["fetch_request_rate"].get("statistics"):
        summary["request_summary"]["fetch_request_avg_per_sec"] = metrics["fetch_request_rate"]["statistics"].get(
            "avg", 0
        )

    if "failed_produce_request_rate" in metrics and metrics["failed_produce_request_rate"].get("statistics"):
        summary["request_summary"]["failed_produce_request_avg_per_sec"] = metrics["failed_produce_request_rate"][
            "statistics"
        ].get("avg", 0)

    if "failed_fetch_request_rate" in metrics and metrics["failed_fetch_request_rate"].get("statistics"):
        summary["request_summary"]["failed_fetch_request_avg_per_sec"] = metrics["failed_fetch_request_rate"][
            "statistics"
        ].get("avg", 0)

    return summary
