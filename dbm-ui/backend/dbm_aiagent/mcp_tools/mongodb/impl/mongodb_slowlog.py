"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict, Optional

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.exceptions import ApiResultError
from backend.utils.time import datetime2str

# cluster_domain 与 instance_host 不能同时为空
SLOWLOG_CLUSTER_OR_HOST_REQUIRED = "cluster_domain and instance_host cannot both be empty"


def _require_cluster_or_host(cluster_domain: str, instance_host: str) -> None:
    if not (cluster_domain or instance_host):
        raise DBMMcpBaseException(msg=SLOWLOG_CLUSTER_OR_HOST_REQUIRED)


def get_mongodb_slowlog_overview(
    cluster_domain: Optional[str] = None,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
) -> Dict:
    # 将get_mongodb_slowlog_aggr_by_ns和get_mongodb_slowlog_aggr_by_instance的结果合并
    result1 = get_mongodb_slowlog_aggr_by_ns(cluster_domain, instance_host, instance, start_time, end_time)
    result2 = get_mongodb_slowlog_aggr_by_instance(cluster_domain, instance_host, instance, start_time, end_time)
    return {
        "aggr_by_ns_and_queryHash": result1,
        "aggr_by_shard_and_instance": result2,
    }


def get_mongodb_slowlog_aggr_by_ns(
    cluster_domain: Optional[str] = None,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
) -> Dict:
    """查询 MongoDB 集群慢查询按 ns 与 queryHash 聚合的统计，适用于 MongoShardedCluster 或 MongoReplicaSetCluster。"""
    _require_cluster_or_host(cluster_domain or "", instance_host or "")
    if start_time is None or end_time is None:
        raise DBMMcpBaseException(msg="start_time and end_time are required")
    query_params = get_query_params(
        cluster_domain=cluster_domain,
        instance_host=instance_host,
        instance=instance,
        start_time=start_time,
        end_time=end_time,
        size=0,  # 返回0条数据，只要aggs 的结果
        aggs={
            "by_ns": {
                "terms": {
                    "field": "attr.ns",
                    "size": 100,
                },
                "aggs": {
                    "by_queryHash": {
                        "terms": {
                            "field": "attr.queryHash",
                            "size": 10,
                        }
                    }
                },
            }
        },
    )
    result = _get_mongo_slowlog(query_params)
    return result


def get_mongodb_slowlog_aggr_by_instance(
    cluster_domain: Optional[str] = None,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
) -> Dict:
    """查询 MongoDB 集群慢查询按 ns 与 queryHash 聚合的统计，适用于 MongoShardedCluster 或 MongoReplicaSetCluster。"""
    _require_cluster_or_host(cluster_domain or "", instance_host or "")
    if start_time is None or end_time is None:
        raise DBMMcpBaseException(msg="start_time and end_time are required")
    query_params = get_query_params(
        cluster_domain=cluster_domain,
        instance_host=instance_host,
        instance=instance,
        start_time=start_time,
        end_time=end_time,
        size=0,  # 返回0条数据，只要aggs 的结果
        aggs={
            "by_shard": {
                "terms": {
                    "field": "meta.instance_set_name",
                    "size": 100,
                },
                "aggs": {
                    "by_instance": {
                        "terms": {
                            "field": "meta.instance",
                            "size": 40,
                        }
                    }
                },
            },
        },
    )
    result = _get_mongo_slowlog(query_params)
    return result


def get_mongodb_slowlog_list(
    cluster_domain: Optional[str] = None,
    instance: Optional[str] = None,
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
    ns: Optional[str] = None,
    query_hash: Optional[str] = None,
) -> Dict:
    """查询 MongoDB 集群的慢查询日志，支持按 ns、queryHash 过滤。"""
    _require_cluster_or_host(cluster_domain or "", instance or "")
    if start_time is None or end_time is None:
        raise DBMMcpBaseException(msg="start_time and end_time are required")
    query_params = get_query_params(
        cluster_domain=cluster_domain,
        instance=instance,
        start_time=start_time,
        end_time=end_time,
        ns=ns,
        query_hash=query_hash,
        size=10,
    )
    entries = _get_mongo_slowlog(query_params)
    return {"slowlog_entries": entries, "total_count": len(entries)}


def _get_mongo_slowlog(query_params: Dict) -> Dict:
    """从日志平台查询 MongoDB 慢日志。需配置 DBM_MONGODB 相关 index。"""
    try:
        resp = BKLogApi.esquery_search(query_params, use_admin=True)
        # 打印resp的内容
        return resp
    except DBMMcpBaseException:
        raise
    except ApiResultError as e:
        err_msg = str(e)
        if "从meta获取连接信息失败" in err_msg or "meta" in err_msg.lower():
            raise DBMMcpBaseException(
                msg=(
                    f"蓝鲸日志平台查询失败: {err_msg}。"
                    f"请确认业务 ID {getattr(env, 'DBA_APP_BK_BIZ_ID', '')} 下已配置 MongoDB 慢日志采集项与索引集 mongodb_slowlog，且日志平台 meta 服务可用。"
                )
            )
        raise DBMMcpBaseException(msg=f"query mongodb slow logs failed: {e}")
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query mongodb slow logs failed: {e}")


def get_query_params(
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
    cluster_domain: Optional[str] = None,
    instance_host: Optional[str] = None,
    instance_role: Optional[str] = None,
    instance: Optional[str] = None,
    ns: Optional[str] = None,
    query_hash: Optional[str] = None,
    size: int = 100,
    aggs: Optional[Dict] = None,
) -> Dict:
    """MongoDB 慢日志查询参数。indices 需按实际 MongoDB 慢日志 index 配置。"""
    MONGO_SLOWLOG_INITIAL_QUERY_STRING = '(NOT meta.instance_role:"backup") AND id:51803 AND (NOT attr.ns:*.$cmd)'

    if start_time is None or end_time is None:
        raise DBMMcpBaseException(msg="start_time and end_time are required")
    domain = cluster_domain or ""
    query_parts = []
    if domain:
        query_parts.append(f'meta.cluster_domain:"{domain}"')
    if instance_host:
        query_parts.append(f'meta.instance_host:"{instance_host}"')
    if instance_role:
        query_parts.append(f'meta.instance_role:"{instance_role}"')
    if instance:
        query_parts.append(f'meta.instance:"{instance}"')
    if ns:
        query_parts.append(f'attr.ns:"{ns}"')
    if query_hash:
        query_parts.append(f'attr.queryHash:"{query_hash}"')
    query_params = {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.mongodb_log",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": MONGO_SLOWLOG_INITIAL_QUERY_STRING + " AND " + " AND ".join(query_parts)
        if query_parts
        else "*",
        "start": 0,
        "size": size,
        "sort_list": [["durationMillis", "desc"]],
    }
    if aggs:
        query_params["aggs"] = aggs
    return query_params
