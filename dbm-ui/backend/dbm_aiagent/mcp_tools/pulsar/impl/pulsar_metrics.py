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

# Pulsar 监控指标 PromQL 模板
#
# 数据来源说明：
# 1. 主机层指标走 bkmonitor:dbm_system:*，由 db_monitor/tpls/alarm/pulsar/ 下的告警模板证实
#    该套 label（db_type=pulsar / instance_role=pulsar_broker）可用
# 2. Pulsar 自身指标由 dbm_pulsarbroker_bkpull 等采集插件上报，仅 pulsar_msg_backlog
#    在仓库内有明确出处（Pulsar 延迟告警.json）
#
# 注意：新增 Pulsar 自身指标前，务必先在监控平台指标检索里确认该指标已被采集，
# 不要照抄 Pulsar 官方文档的指标名，否则查询会静默返回空数据。
PULSAR_METRICS_PROMQL = {
    # 1. 消息积压指标（运维最关心，来源：Pulsar 延迟告警模板）
    "msg_backlog": {
        "desc": "消息积压总量(条)",
        "promql": """sum by (cluster_domain) (
            pulsar_msg_backlog{cluster_domain="%s"}
        )""",
    },
    # 2. Broker CPU 指标
    "broker_cpu_usage_avg": {
        "desc": "Broker平均CPU利用率(%)",
        "promql": """avg by (cluster_domain) (
            avg_over_time(bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="pulsar_broker"}[5m])
        )""",
    },
    "broker_cpu_usage_max": {
        "desc": "Broker峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="pulsar_broker"}[5m])
        )""",
    },
    # 3. BookKeeper CPU 指标（存储层，写入压力大时先看这里）
    "bookkeeper_cpu_usage_avg": {
        "desc": "BookKeeper平均CPU利用率(%)",
        "promql": """avg by (cluster_domain) (
            avg_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="pulsar_bookkeeper"}[5m]
            )
        )""",
    },
    "bookkeeper_cpu_usage_max": {
        "desc": "BookKeeper峰值CPU利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(
                bkmonitor:dbm_system:cpu_summary:usage{cluster_domain="%s",instance_role="pulsar_bookkeeper"}[5m]
            )
        )""",
    },
    # 4. 内存指标
    "broker_memory_usage_max": {
        "desc": "Broker峰值内存利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(bkmonitor:dbm_system:mem:pct_used{cluster_domain="%s",instance_role="pulsar_broker"}[5m])
        )""",
    },
    "bookkeeper_memory_usage_max": {
        "desc": "BookKeeper峰值内存利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(bkmonitor:dbm_system:mem:pct_used{cluster_domain="%s",instance_role="pulsar_bookkeeper"}[5m])
        )""",
    },
    # 5. 磁盘指标（BookKeeper 承载数据存储，磁盘水位是关键容量指标）
    "bookkeeper_disk_usage_max": {
        "desc": "BookKeeper峰值磁盘利用率(%)",
        "promql": """max by (cluster_domain, instance, mount_point) (
            max_over_time(bkmonitor:dbm_system:disk:in_use{cluster_domain="%s",instance_role="pulsar_bookkeeper"}[5m])
        )""",
    },
    "broker_disk_usage_max": {
        "desc": "Broker峰值磁盘利用率(%)",
        "promql": """max by (cluster_domain, instance, mount_point) (
            max_over_time(bkmonitor:dbm_system:disk:in_use{cluster_domain="%s",instance_role="pulsar_broker"}[5m])
        )""",
    },
    # 6. 磁盘 IO 指标（BookKeeper 写入瓶颈排查）
    "bookkeeper_disk_io_util_max": {
        "desc": "BookKeeper峰值磁盘IO利用率(%)",
        "promql": """max by (cluster_domain, instance) (
            max_over_time(bkmonitor:dbm_system:io:util{cluster_domain="%s",instance_role="pulsar_bookkeeper"}[5m])
        )""",
    },
    # 7. 网络流量指标
    "broker_net_recv": {
        "desc": "Broker网络入流量(字节/秒)",
        "promql": """sum by (cluster_domain) (
            bkmonitor:dbm_system:net:speed_recv{cluster_domain="%s",instance_role="pulsar_broker"}
        )""",
    },
    "broker_net_sent": {
        "desc": "Broker网络出流量(字节/秒)",
        "promql": """sum by (cluster_domain) (
            bkmonitor:dbm_system:net:speed_sent{cluster_domain="%s",instance_role="pulsar_broker"}
        )""",
    },
}

# 维度明细指标（TopN 排行）
PULSAR_DETAIL_METRICS_PROMQL = {
    # Topic 维度
    "topic_msg_backlog": {
        "desc": "Topic消息积压量(条)",
        "dimension": "topic",
        "label_key": "topic",
        "promql": """topk({top_n},
            sum by (topic) (
                pulsar_msg_backlog{{cluster_domain="{cluster_domain}",topic!=""}}
            )
        )""",
    },
    # Namespace 维度
    "namespace_msg_backlog": {
        "desc": "Namespace消息积压量(条)",
        "dimension": "namespace",
        "label_key": "namespace",
        "promql": """topk({top_n},
            sum by (namespace) (
                pulsar_msg_backlog{{cluster_domain="{cluster_domain}",namespace!=""}}
            )
        )""",
    },
    # Broker 维度
    "broker_cpu_usage": {
        "desc": "Broker CPU使用率(%)",
        "dimension": "broker",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{cluster_domain="{cluster_domain}",instance_role="pulsar_broker"}}[5m]
        )""",
    },
    # BookKeeper 维度
    "bookkeeper_cpu_usage": {
        "desc": "BookKeeper CPU使用率(%)",
        "dimension": "bookkeeper",
        "label_key": "instance",
        "promql": """avg_over_time(
            bkmonitor:dbm_system:cpu_summary:usage{{
                cluster_domain="{cluster_domain}",instance_role="pulsar_bookkeeper"
            }}[5m]
        )""",
    },
    # Disk 维度：BookKeeper 是数据存储层，磁盘明细优先看它
    "bookkeeper_disk_usage_detail": {
        "desc": "BookKeeper磁盘使用率按挂载点(%)",
        "dimension": "disk",
        "label_key": "mount_point",
        "promql": """max_over_time(
            bkmonitor:dbm_system:disk:in_use{{
                cluster_domain="{cluster_domain}",instance_role="pulsar_bookkeeper"
            }}[5m]
        )""",
    },
    "broker_disk_usage_detail": {
        "desc": "Broker磁盘使用率按挂载点(%)",
        "dimension": "disk",
        "label_key": "mount_point",
        "promql": """max_over_time(
            bkmonitor:dbm_system:disk:in_use{{cluster_domain="{cluster_domain}",instance_role="pulsar_broker"}}[5m]
        )""",
    },
}


def query_pulsar_detail_metrics(
    bk_biz_id: int,
    cluster_domain: str,
    metric_name: str,
    top_n: int = 10,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict:
    """
    查询 Pulsar 维度明细指标（TopN）

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        metric_name: 指标名称，参见 PULSAR_DETAIL_METRICS_PROMQL
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

    if metric_name not in PULSAR_DETAIL_METRICS_PROMQL:
        valid_names = ", ".join(PULSAR_DETAIL_METRICS_PROMQL.keys())
        return {"error": f"无效的指标名称: {metric_name}，可选值: {valid_names}"}

    metric_config = PULSAR_DETAIL_METRICS_PROMQL[metric_name]

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
            result["total_series_count"] = len(series_list)
            label_key = metric_config["label_key"]

            for series in series_list:
                label = series.get("dimensions", {}).get(label_key, "unknown")
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
        logger.error(f"查询 Pulsar 维度明细指标 {metric_name} 失败: {str(e)}")
        result["error"] = str(e)

    return result


def query_pulsar_metrics(
    bk_biz_id: int,
    cluster_domain: str,
    metric_types: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict:
    """
    查询 Pulsar 集群监控指标

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
        metric_types = list(PULSAR_METRICS_PROMQL.keys())

    invalid_metrics = [m for m in metric_types if m not in PULSAR_METRICS_PROMQL]
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
        metric_config = PULSAR_METRICS_PROMQL[metric_type]
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
                "data_points": [],
                "statistics": {},
            }

            if response and "series" in response:
                series_list = response["series"]
                if series_list:
                    # 按 series 分别收集，统计语义由 PromQL 聚合保证
                    all_values = []
                    for series in series_list:
                        if "datapoints" in series:
                            datapoints = series["datapoints"]
                            metric_data["data_points"].extend(datapoints)
                            all_values.extend([p[0] for p in datapoints if p[0] is not None])

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
            logger.error(f"查询 Pulsar 指标 {metric_type} 失败: {str(e)}")
            result["metrics"][metric_type] = {
                "description": metric_config["desc"],
                "error": str(e),
            }

    return result


def get_pulsar_performance_summary(
    bk_biz_id: int,
    cluster_domain: str,
    days: int = 7,
) -> Dict:
    """
    获取 Pulsar 集群性能摘要（最近N天）

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
        "msg_backlog",
        "broker_cpu_usage_avg",
        "broker_cpu_usage_max",
        "bookkeeper_cpu_usage_avg",
        "bookkeeper_cpu_usage_max",
        "broker_memory_usage_max",
        "bookkeeper_memory_usage_max",
        "bookkeeper_disk_usage_max",
        "broker_disk_usage_max",
        "bookkeeper_disk_io_util_max",
    ]

    metrics_data = query_pulsar_metrics(
        bk_biz_id=bk_biz_id,
        cluster_domain=cluster_domain,
        metric_types=key_metrics,
        start_time=start_time,
        end_time=end_time,
    )

    if "error" in metrics_data:
        return metrics_data

    metrics = metrics_data.get("metrics", {})

    def stat_of(metric_type: str, key: str, default=0):
        """从指标结果里取某个统计值，指标缺失或查询失败时返回默认值"""
        stats = metrics.get(metric_type, {}).get("statistics") or {}
        return stats.get(key, default)

    return {
        "cluster_domain": cluster_domain,
        "time_range": f"最近{days}天",
        # 积压摘要：Pulsar 运维最核心的健康信号
        "backlog_summary": {
            "msg_backlog_peak": stat_of("msg_backlog", "max"),
            "msg_backlog_avg": stat_of("msg_backlog", "avg"),
            "msg_backlog_latest": stat_of("msg_backlog", "latest"),
        },
        # Broker 层资源
        "broker_resource_summary": {
            "cpu_avg_percent": stat_of("broker_cpu_usage_avg", "avg"),
            "cpu_peak_percent": stat_of("broker_cpu_usage_max", "max"),
            "memory_peak_percent": stat_of("broker_memory_usage_max", "max"),
            "disk_peak_percent": stat_of("broker_disk_usage_max", "max"),
        },
        # BookKeeper 层资源（存储层，容量与写入瓶颈看这里）
        "bookkeeper_resource_summary": {
            "cpu_avg_percent": stat_of("bookkeeper_cpu_usage_avg", "avg"),
            "cpu_peak_percent": stat_of("bookkeeper_cpu_usage_max", "max"),
            "memory_peak_percent": stat_of("bookkeeper_memory_usage_max", "max"),
            "disk_peak_percent": stat_of("bookkeeper_disk_usage_max", "max"),
            "disk_io_util_peak_percent": stat_of("bookkeeper_disk_io_util_max", "max"),
        },
    }
