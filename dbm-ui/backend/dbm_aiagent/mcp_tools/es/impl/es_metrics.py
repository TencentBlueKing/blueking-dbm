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


# ES 监控指标 PromQL 模板
#
# 数据来源说明：
# 1. 主机层指标走 bkmonitor:dbm_system:*，instance_role 使用 es_master/es_datanode_hot/es_datanode_cold/es_client
#    参考 db_monitor/constants.py 中 ClusterType.Es 的容量表达式与 bk_dataview/dashboards/json/es.json
# 2. ES 自身指标由 dbm_elasticsearch_exporter 采集，数据源前缀
#    bkmonitor:exporter_dbm_elasticsearch_exporter:*，可用指标包含：
#      - elasticsearch_cluster_health_status: 集群健康状态(0=green,1=yellow,2=red)
#      - elasticsearch_indices_shards_docs: shard 文档数
#      - elasticsearch_indices_docs_primary: 主分片文档数
#      - elasticsearch_indices_store_size_bytes: 存储大小
#      - elasticsearch_indices_indexing_index_total: 索引写入次数
#      - elasticsearch_indices_indexing_index_time_seconds_total: 索引写入耗时
#      - elasticsearch_indices_search_query_total: 检索次数
#      - elasticsearch_indices_search_query_time_seconds: 检索耗时
#      - elasticsearch_jvm_memory_used_bytes / elasticsearch_jvm_memory_max_bytes: JVM 堆内存
#      - elasticsearch_thread_pool_queue_count: 线程池队列
#      - elasticsearch_thread_pool_rejected_count: 线程池拒绝
#
# 注意：新增 ES 自身指标前，务必先在监控平台指标检索里确认该指标已被采集，
# 不要照抄 ES 官方文档的指标名，否则查询会静默返回空数据。
ES_METRICS_PROMQL = {
    # 1. 集群健康状态（最核心的健康信号）
    "cluster_health_status": {
        "desc": "集群健康状态(0=green,1=yellow,2=red)",
        "promql": """max by (cluster_domain) (
            bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_cluster_health_status{cluster_domain="%s"}
        )""",
    },
    # 2. 索引数据规模
    "indices_docs_primary": {
        "desc": "主分片文档总数(条)",
        "promql": """sum by (cluster_domain) (
            bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_docs_primary{cluster_domain="%s"}
        )""",
    },
    "indices_store_size": {
        "desc": "索引存储总大小(字节)",
        "promql": """sum by (cluster_domain) (
            bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_store_size_bytes{cluster_domain="%s"}
        )""",
    },
    # 3. 索引写入/检索速率
    "indexing_rate": {
        "desc": "索引写入速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            irate(
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_indexing_index_total{
                    cluster_domain="%s"
                }[5m]
            )
        )""",
    },
    "search_rate": {
        "desc": "检索速率(次/秒)",
        "promql": """sum by (cluster_domain) (
            irate(
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_search_query_total{
                    cluster_domain="%s"
                }[5m]
            )
        )""",
    },
    "indexing_latency": {
        "desc": "单次索引写入平均耗时(秒)",
        "promql": """(
            sum by (cluster_domain) (
                irate(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_indexing_index_time_seconds_total{
                        cluster_domain="%s"
                    }[5m]
                )
            )
            /
            sum by (cluster_domain) (
                irate(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_indexing_index_total{
                        cluster_domain="%s"
                    }[5m]
                ) > 0
            )
        )""",
    },
    "search_latency": {
        "desc": "单次检索平均耗时(秒)",
        "promql": """(
            sum by (cluster_domain) (
                irate(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_search_query_time_seconds{
                        cluster_domain="%s"
                    }[5m]
                )
            )
            /
            sum by (cluster_domain) (
                irate(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_search_query_total{
                        cluster_domain="%s"
                    }[5m]
                ) > 0
            )
        )""",
    },
    # 4. 线程池队列/拒绝（写入/搜索排队与拒绝，问题时最先关注）
    "thread_pool_queue_max": {
        "desc": "线程池队列峰值",
        "promql": """max by (cluster_domain) (
            bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_thread_pool_queue_count{cluster_domain="%s"}
        )""",
    },
    "thread_pool_rejected_max": {
        "desc": "线程池5分钟窗口拒绝增量峰值",
        "promql": """sum by (cluster_domain) (
            increase(
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_thread_pool_rejected_count{
                    cluster_domain="%s"
                }[5m]
            )
        )""",
    },
    # 5. JVM 堆内存（ES 集群 OOM 与 GC 压力主要指标）
    "jvm_heap_usage_max": {
        "desc": "JVM堆内存峰值使用率(%)",
        "promql": """(
            max by (cluster_domain, name) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_jvm_memory_used_bytes{
                    cluster_domain="%s"
                }
            )
            /
            max by (cluster_domain, name) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_jvm_memory_max_bytes{
                    cluster_domain="%s"
                }
            )
            * 100
        )""",
    },
    # 6. 数据节点 CPU 指标（hot/cold 拆分，便于定位热点）
    "hot_cpu_usage_avg": {
        "desc": "热节点平均CPU利用率(%)",
        "promql": """avg by (cluster_domain) (
            avg_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="es_datanode_hot"}[5m]
            )
        )""",
    },
    "hot_cpu_usage_max": {
        "desc": "热节点峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="es_datanode_hot"}[5m]
            )
        )""",
    },
    "cold_cpu_usage_avg": {
        "desc": "冷节点平均CPU利用率(%)",
        "promql": """avg by (cluster_domain) (
            avg_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="es_datanode_cold"}[5m]
            )
        )""",
    },
    "cold_cpu_usage_max": {
        "desc": "冷节点峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="es_datanode_cold"}[5m]
            )
        )""",
    },
    "master_cpu_usage_max": {
        "desc": "Master节点峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="es_master"}[5m]
            )
        )""",
    },
    "client_cpu_usage_max": {
        "desc": "Client节点峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="es_client"}[5m]
            )
        )""",
    },
    # 7. 内存指标（主机层内存使用率）
    "hot_memory_usage_max": {
        "desc": "热节点峰值内存利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:mem:pct_used{cluster_domain="%s",instance_role="es_datanode_hot"}[5m]
            )
        )""",
    },
    "cold_memory_usage_max": {
        "desc": "冷节点峰值内存利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:mem:pct_used{cluster_domain="%s",instance_role="es_datanode_cold"}[5m]
            )
        )""",
    },
    # 8. 磁盘指标（DataNode 承载数据存储，磁盘水位是关键容量指标）
    "hot_disk_usage_max": {
        "desc": "热节点峰值磁盘利用率(%)",
        "promql": """max by (cluster_domain, instance, mount_point) (
            max_over_time(
                bkmonitor:dbm_system:disk:in_use{cluster_domain="%s",instance_role="es_datanode_hot"}[5m]
            )
        )""",
    },
    "cold_disk_usage_max": {
        "desc": "冷节点峰值磁盘利用率(%)",
        "promql": """max by (cluster_domain, instance, mount_point) (
            max_over_time(
                bkmonitor:dbm_system:disk:in_use{cluster_domain="%s",instance_role="es_datanode_cold"}[5m]
            )
        )""",
    },
    # 9. 磁盘 IO 指标（写入瓶颈排查）
    "hot_disk_io_util_max": {
        "desc": "热节点峰值磁盘IO利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:io:util{cluster_domain="%s",instance_role="es_datanode_hot"}[5m]
            )
        )""",
    },
    # 10. 网络流量指标
    "client_net_recv": {
        "desc": "Client节点网络入流量(字节/秒)",
        "promql": """sum by (cluster_domain) (
            bkmonitor:dbm_system:net:speed_recv{cluster_domain="%s",instance_role="es_client"}
        )""",
    },
    "client_net_sent": {
        "desc": "Client节点网络出流量(字节/秒)",
        "promql": """sum by (cluster_domain) (
            bkmonitor:dbm_system:net:speed_sent{cluster_domain="%s",instance_role="es_client"}
        )""",
    },
}


# ES 维度明细指标 PromQL 模板（TopN 查询）
ES_DETAIL_METRICS_PROMQL = {
    # 索引维度：写入/检索/大小 TopN
    "index_docs_topn": {
        "desc": "索引文档数TopN(条)",
        "dimension": "index",
        "label_key": "index",
        "promql": """topk({top_n},
            sum by (index) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_docs_primary{{
                    cluster_domain="{cluster_domain}",index!=""
                }}
            )
        )""",
    },
    "index_store_size_topn": {
        "desc": "索引存储大小TopN(字节)",
        "dimension": "index",
        "label_key": "index",
        "promql": """topk({top_n},
            sum by (index) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_store_size_bytes{{
                    cluster_domain="{cluster_domain}",index!=""
                }}
            )
        )""",
    },
    "index_indexing_rate_topn": {
        "desc": "索引写入速率TopN(次/秒)",
        "dimension": "index",
        "label_key": "index",
        "promql": """topk({top_n},
            sum by (index) (
                irate(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_indexing_index_total{{
                        cluster_domain="{cluster_domain}",index!=""
                    }}[5m]
                )
            )
        )""",
    },
    "index_search_rate_topn": {
        "desc": "索引检索速率TopN(次/秒)",
        "dimension": "index",
        "label_key": "index",
        "promql": """topk({top_n},
            sum by (index) (
                irate(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_indices_search_query_total{{
                        cluster_domain="{cluster_domain}",index!=""
                    }}[5m]
                )
            )
        )""",
    },
    # 节点维度：CPU/内存/磁盘/JVM 明细
    "hot_node_cpu_usage": {
        "desc": "热节点CPU使用率明细(%)",
        "dimension": "hot_node",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{
                cluster_domain="{cluster_domain}",instance_role="es_datanode_hot"
            }}[5m]
        )""",
    },
    "cold_node_cpu_usage": {
        "desc": "冷节点CPU使用率明细(%)",
        "dimension": "cold_node",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{
                cluster_domain="{cluster_domain}",instance_role="es_datanode_cold"
            }}[5m]
        )""",
    },
    "master_node_cpu_usage": {
        "desc": "Master节点CPU使用率明细(%)",
        "dimension": "master_node",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{
                cluster_domain="{cluster_domain}",instance_role="es_master"
            }}[5m]
        )""",
    },
    "client_node_cpu_usage": {
        "desc": "Client节点CPU使用率明细(%)",
        "dimension": "client_node",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{
                cluster_domain="{cluster_domain}",instance_role="es_client"
            }}[5m]
        )""",
    },
    "node_jvm_heap_usage": {
        "desc": "节点JVM堆内存使用率明细(%)",
        "dimension": "node",
        "label_key": "name",
        "promql": """(
            max by (cluster_domain, name) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_jvm_memory_used_bytes{{
                    cluster_domain="{cluster_domain}"
                }}
            )
            /
            max by (cluster_domain, name) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_jvm_memory_max_bytes{{
                    cluster_domain="{cluster_domain}"
                }}
            )
            * 100
        )""",
    },
    "hot_disk_usage_detail": {
        "desc": "热节点磁盘使用率按挂载点(%)",
        "dimension": "disk",
        "label_key": "mount_point",
        "promql": """max_over_time(
            bkmonitor:dbm_system:disk:in_use{{
                cluster_domain="{cluster_domain}",instance_role="es_datanode_hot"
            }}[5m]
        )""",
    },
    "cold_disk_usage_detail": {
        "desc": "冷节点磁盘使用率按挂载点(%)",
        "dimension": "disk",
        "label_key": "mount_point",
        "promql": """max_over_time(
            bkmonitor:dbm_system:disk:in_use{{
                cluster_domain="{cluster_domain}",instance_role="es_datanode_cold"
            }}[5m]
        )""",
    },
    # 线程池维度：区分 write/search/get 等 thread_pool
    "thread_pool_rejected_topn": {
        "desc": "线程池5分钟窗口拒绝增量TopN(按pool类型)",
        "dimension": "thread_pool",
        "label_key": "type",
        "promql": """topk({top_n},
            sum by (type) (
                increase(
                    bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_thread_pool_rejected_count{{
                        cluster_domain="{cluster_domain}"
                    }}[5m]
                )
            )
        )""",
    },
    "thread_pool_queue_topn": {
        "desc": "线程池队列长度TopN(按pool类型)",
        "dimension": "thread_pool",
        "label_key": "type",
        "promql": """topk({top_n},
            max by (type) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_thread_pool_queue_count{{
                    cluster_domain="{cluster_domain}"
                }}
            )
        )""",
    },
}


def _build_series_statistics(datapoints: List[List]) -> Optional[Dict]:
    latest_value = datapoints[-1][0] if datapoints else None
    values = [point[0] for point in datapoints if point[0] is not None]
    if not values:
        return None

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "latest": latest_value,
        "count": len(values),
    }


def _build_aggregate_statistics(series_list: List[Dict]) -> Optional[Dict]:
    latest_value = None
    if len(series_list) == 1:
        datapoints = series_list[0].get("datapoints", [])
        latest_value = datapoints[-1][0] if datapoints else None

    all_values = []
    for series in series_list:
        datapoints = series.get("datapoints", [])
        all_values.extend([point[0] for point in datapoints if point[0] is not None])

    if not all_values:
        return None

    max_value = max(all_values)
    if len(series_list) > 1:
        return {
            "max": max_value,
            "series_count": len(series_list),
        }

    return {
        "min": min(all_values),
        "max": max_value,
        "avg": sum(all_values) / len(all_values),
        "latest": latest_value,
        "count": len(all_values),
        "series_count": 1,
    }


def _query_aggregate_statistics(
    bk_biz_id: int,
    promql: str,
    start_time: datetime,
    end_time: datetime,
    metric_desc: str,
) -> Optional[Dict]:
    query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    query_params["bk_biz_id"] = bk_biz_id
    query_params["start_time"] = int(timezone2timestamp(start_time))
    query_params["end_time"] = int(timezone2timestamp(end_time))
    query_params["query_configs"][0]["promql"] = promql

    try:
        response = BKMonitorV3Api.unify_query(query_params)
        if response and "series" in response and response["series"]:
            return _build_aggregate_statistics(response["series"])
    except Exception as e:
        logger.error(f"查询 ES 聚合指标 {metric_desc} 失败: {str(e)}")

    return None


def query_es_detail_metrics(
    bk_biz_id: int,
    cluster_domain: str,
    metric_name: str,
    top_n: int = 10,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict:
    """
    查询 ES 维度明细指标（TopN）

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        metric_name: 指标名称，参见 ES_DETAIL_METRICS_PROMQL
        top_n: 返回 TopN 条目，默认10
        start_time: 开始时间，默认1小时前
        end_time: 结束时间，默认当前时间

    Returns:
        包含维度明细数据的字典
    """
    try:
        Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        return {"error": f"集群不存在: {cluster_domain}"}

    if metric_name not in ES_DETAIL_METRICS_PROMQL:
        valid_names = ", ".join(ES_DETAIL_METRICS_PROMQL.keys())
        return {"error": f"无效的指标名称: {metric_name}，可选值: {valid_names}"}

    metric_config = ES_DETAIL_METRICS_PROMQL[metric_name]

    # 设置默认时间范围（最近1小时）
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=1)

    promql = metric_config["promql"].format(cluster_domain=cluster_domain, top_n=top_n)

    query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    query_params["bk_biz_id"] = bk_biz_id
    query_params["start_time"] = int(timezone2timestamp(start_time))
    query_params["end_time"] = int(timezone2timestamp(end_time))
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
            label_key = metric_config["label_key"]

            for series in series_list:
                dimensions = series.get("dimensions", {})
                label = dimensions.get(label_key, "unknown")
                datapoints = series.get("datapoints", [])
                if not datapoints or datapoints[-1][0] is None:
                    continue

                latest_value = datapoints[-1][0]
                values = [point[0] for point in datapoints if point[0] is not None]

                result["items"].append(
                    {
                        "label": label,
                        "instance": dimensions.get("instance"),
                        "latest_value": latest_value,
                        "statistics": {
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values),
                            "latest": latest_value,
                        },
                    }
                )

            result["total_series_count"] = len(result["items"])
            result["items"].sort(key=lambda x: x["latest_value"], reverse=True)
            result["items"] = result["items"][:top_n]

    except Exception as e:
        logger.error(f"查询 ES 维度明细指标 {metric_name} 失败: {str(e)}")
        result["error"] = str(e)

    return result


def query_es_metrics(
    bk_biz_id: int,
    cluster_domain: str,
    metric_types: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict:
    """
    查询 ES 集群监控指标

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        metric_types: 指标类型列表，不传则查询所有指标
        start_time: 开始时间，默认7天前
        end_time: 结束时间，默认当前时间

    Returns:
        包含监控指标数据的字典
    """
    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        return {"error": f"集群不存在: {cluster_domain}"}

    # 设置默认时间范围（最近7天）
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(days=7)

    if not metric_types:
        metric_types = list(ES_METRICS_PROMQL.keys())

    invalid_metrics = [m for m in metric_types if m not in ES_METRICS_PROMQL]
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

    start_timestamp = int(timezone2timestamp(start_time))
    end_timestamp = int(timezone2timestamp(end_time))

    for metric_type in metric_types:
        metric_config = ES_METRICS_PROMQL[metric_type]
        promql = metric_config["promql"].replace("%s", cluster_domain)

        query_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        query_params["bk_biz_id"] = bk_biz_id
        query_params["start_time"] = start_timestamp
        query_params["end_time"] = end_timestamp
        query_params["query_configs"][0]["promql"] = promql

        try:
            response = BKMonitorV3Api.unify_query(query_params)

            metric_data = {
                "description": metric_config["desc"],
                "series": [],
                "aggregate_statistics": None,
            }

            if response and "series" in response:
                series_list = response["series"]
                if series_list:
                    for series in series_list:
                        datapoints = series.get("datapoints", [])
                        metric_data["series"].append(
                            {
                                "dimensions": series.get("dimensions", {}),
                                "data_points": datapoints,
                                "statistics": _build_series_statistics(datapoints),
                            }
                        )

                    metric_data["aggregate_statistics"] = _build_aggregate_statistics(series_list)

            result["metrics"][metric_type] = metric_data

        except Exception as e:
            logger.error(f"查询 ES 指标 {metric_type} 失败: {str(e)}")
            result["metrics"][metric_type] = {
                "description": metric_config["desc"],
                "series": [],
                "aggregate_statistics": None,
                "error": str(e),
            }

    return result


def get_es_performance_summary(
    bk_biz_id: int,
    cluster_domain: str,
    days: int = 7,
) -> Dict:
    """
    获取 ES 集群性能摘要（最近N天）

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        days: 查询天数，默认7天

    Returns:
        包含性能摘要的字典
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    key_metrics = [
        "cluster_health_status",
        "indices_docs_primary",
        "indices_store_size",
        "indexing_rate",
        "search_rate",
        "indexing_latency",
        "search_latency",
        "thread_pool_queue_max",
        "thread_pool_rejected_max",
        "hot_cpu_usage_avg",
        "hot_cpu_usage_max",
        "cold_cpu_usage_avg",
        "cold_cpu_usage_max",
        "master_cpu_usage_max",
        "hot_memory_usage_max",
        "cold_memory_usage_max",
        "hot_disk_usage_max",
        "cold_disk_usage_max",
        "hot_disk_io_util_max",
    ]

    metrics_data = query_es_metrics(
        bk_biz_id=bk_biz_id,
        cluster_domain=cluster_domain,
        metric_types=key_metrics,
        start_time=start_time,
        end_time=end_time,
    )

    if "error" in metrics_data:
        return metrics_data

    metrics = metrics_data.get("metrics", {})
    datanode_jvm_stats = _query_aggregate_statistics(
        bk_biz_id=bk_biz_id,
        promql="""(
            max by (cluster_domain, name) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_jvm_memory_used_bytes{
                    cluster_domain="%s",name=~"(dn|hot|cold)-.*"
                }
            )
            /
            max by (cluster_domain, name) (
                bkmonitor:exporter_dbm_elasticsearch_exporter:elasticsearch_jvm_memory_max_bytes{
                    cluster_domain="%s",name=~"(dn|hot|cold)-.*"
                }
            )
            * 100
        )"""
        % (cluster_domain, cluster_domain),
        start_time=start_time,
        end_time=end_time,
        metric_desc="datanode_jvm_heap_peak_percent",
    )

    def stat_of(metric_type: str, key: str, default=None):
        """从指标结果里取某个统计值，指标缺失或无聚合值时返回默认值"""
        stats = metrics.get(metric_type, {}).get("aggregate_statistics") or {}
        return stats.get(key, default)

    # 集群健康状态解读：0=green,1=yellow,2=red
    health_latest = stat_of("cluster_health_status", "latest")
    health_max = stat_of("cluster_health_status", "max")
    health_status_map = {0: "green", 1: "yellow", 2: "red"}

    def resolve_health_status(status_code):
        if status_code is None:
            return "unknown"

        try:
            return health_status_map.get(int(round(status_code)), "unknown")
        except (TypeError, ValueError):
            return "unknown"

    latest_status = resolve_health_status(health_latest)
    worst_status = resolve_health_status(health_max)

    return {
        "cluster_domain": cluster_domain,
        "time_range": f"最近{days}天",
        # 健康摘要：ES 运维核心信号
        "health_summary": {
            "latest_status": latest_status,
            "worst_status": worst_status,
            "latest_status_code": health_latest,
            "worst_status_code": health_max,
        },
        # 数据规模摘要
        "data_summary": {
            "docs_primary_latest": stat_of("indices_docs_primary", "latest"),
            "store_size_bytes_latest": stat_of("indices_store_size", "latest"),
        },
        # 请求速率与延迟摘要
        "request_summary": {
            "indexing_rate_avg": stat_of("indexing_rate", "avg"),
            "indexing_rate_peak": stat_of("indexing_rate", "max"),
            "search_rate_avg": stat_of("search_rate", "avg"),
            "search_rate_peak": stat_of("search_rate", "max"),
            "indexing_latency_avg_seconds": stat_of("indexing_latency", "avg"),
            "search_latency_avg_seconds": stat_of("search_latency", "avg"),
        },
        # 线程池摘要（rejected_peak 表示 5 分钟窗口拒绝增量峰值）
        "thread_pool_summary": {
            "queue_peak": stat_of("thread_pool_queue_max", "max"),
            "rejected_peak": stat_of("thread_pool_rejected_max", "max"),
        },
        # 数据节点资源摘要（JVM 仅统计 data node，不包含 master/client）
        "datanode_resource_summary": {
            "jvm_heap_peak_percent": (datanode_jvm_stats or {}).get("max"),
            "hot_cpu_avg_percent": stat_of("hot_cpu_usage_avg", "avg"),
            "hot_cpu_peak_percent": stat_of("hot_cpu_usage_max", "max"),
            "cold_cpu_avg_percent": stat_of("cold_cpu_usage_avg", "avg"),
            "cold_cpu_peak_percent": stat_of("cold_cpu_usage_max", "max"),
            "hot_memory_peak_percent": stat_of("hot_memory_usage_max", "max"),
            "cold_memory_peak_percent": stat_of("cold_memory_usage_max", "max"),
            "hot_disk_peak_percent": stat_of("hot_disk_usage_max", "max"),
            "cold_disk_peak_percent": stat_of("cold_disk_usage_max", "max"),
            "hot_disk_io_util_peak_percent": stat_of("hot_disk_io_util_max", "max"),
        },
        # Master 资源摘要
        "master_resource_summary": {
            "master_cpu_peak_percent": stat_of("master_cpu_usage_max", "max"),
        },
    }
