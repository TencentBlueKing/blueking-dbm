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
import logging
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ

logger = logging.getLogger("root")

DEFAULT_LIMIT = 100
DEFAULT_TIME_RANGE_DAYS = 7


def query_proxy_conn_log(
    cluster_domain: str,
    proxy_ips: List[str],
    username: Optional[str] = None,
    thread_ids: Optional[List[int]] = None,
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
    limit: Optional[int] = None,
) -> Dict:
    """查询 mysql-proxy 连接记录（infodba_schema.proxy_conn_log）

    通过 cluster_domain 找到所有后端节点，在每个后端节点上执行查询，合并结果。
    仅支持 TenDBHA 类型集群。
    """
    # 校验集群类型
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain=cluster_domain).first()
    if not cluster_obj:
        raise DBMMcpBaseException(msg=_("集群 {} 不存在").format(cluster_domain))

    if cluster_obj.cluster_type != ClusterType.TenDBHA:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_obj.cluster_type)

    # 获取所有后端存储节点地址
    backend_addresses = [inst.ip_port for inst in cluster_obj.storageinstance_set.all()]
    if not backend_addresses:
        raise DBMMcpBaseException(msg=_("集群 {} 无后端存储节点").format(cluster_domain))

    # 计算时间范围
    if not end_time:
        end_time = timezone.now()
    if not start_time:
        start_time = end_time - timedelta(days=DEFAULT_TIME_RANGE_DAYS)

    eff_limit = limit if limit is not None else DEFAULT_LIMIT

    # 构建 SQL
    sql = _build_query_sql(
        proxy_ips=proxy_ips,
        username=username,
        thread_ids=thread_ids,
        start_time=start_time,
        end_time=end_time,
        limit=eff_limit,
    )

    logger.info("query_proxy_conn_log sql: %s, addresses: %s", sql, backend_addresses)

    # 在所有后端节点上执行查询
    bk_cloud_id = cluster_obj.bk_cloud_id
    all_records: List[Dict] = []

    try:
        drs_raw_res = DRSApi.rpc(
            {
                "addresses": backend_addresses,
                "cmds": [sql],
                "bk_cloud_id": bk_cloud_id,
            }
        )
    except Exception as e:
        raise DBMMcpBaseException(msg=_("DRS 调用失败: {}").format(str(e)))

    for addr_res in drs_raw_res:
        if addr_res["error_msg"]:
            logger.warning(
                "query_proxy_conn_log address error: %s, msg: %s", addr_res.get("address"), addr_res["error_msg"]
            )
            continue

        cmd_res = addr_res["cmd_results"][0]
        if cmd_res["error_msg"]:
            logger.warning("query_proxy_conn_log cmd error: %s", cmd_res["error_msg"])
            continue

        table_data = cmd_res.get("table_data") or []
        for row in table_data:
            all_records.append(
                {
                    "proxy_ip": row.get("proxy_ip", ""),
                    "conn_time": row.get("conn_time", ""),
                    "username": row.get("username", ""),
                    "client_host": row.get("client_host", ""),
                    "thread_id": int(row["thread_id"]) if row.get("thread_id") else 0,
                }
            )

    # 按 proxy_ip 分组
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for record in all_records:
        grouped[record["proxy_ip"]].append(record)

    # 构建返回结果，保持 proxy_ips 的输入顺序
    instances = []
    for ip in proxy_ips:
        records = grouped.get(ip, [])
        # 按 conn_time 降序排列，截取 limit 条
        records.sort(key=lambda x: x["conn_time"], reverse=True)
        instances.append(
            {
                "proxy_ip": ip,
                "records": records[:eff_limit],
                "total": len(records),
            }
        )

    return {
        "cluster_domain": cluster_domain,
        "instances": instances,
    }


def _build_query_sql(
    proxy_ips: List[str],
    username: Optional[str],
    thread_ids: Optional[List[int]],
    start_time,
    end_time,
    limit: int,
) -> str:
    """构建查询 infodba_schema.proxy_conn_log 的 SQL"""
    # proxy_ip IN 条件
    proxy_ip_in = ", ".join(f"'{ip}'" for ip in proxy_ips)
    conditions = [
        f"proxy_ip IN ({proxy_ip_in})",
        f"conn_time >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'",
        f"conn_time <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'",
    ]

    if username:
        conditions.append(f"username = '{username}'")

    if thread_ids:
        thread_id_in = ", ".join(str(tid) for tid in thread_ids)
        conditions.append(f"thread_id IN ({thread_id_in})")

    where_clause = " AND ".join(conditions)

    sql = (
        f"SELECT proxy_ip, conn_time, username, client_host, thread_id "
        f"FROM infodba_schema.proxy_conn_log "
        f"WHERE {where_clause} "
        f"ORDER BY conn_time DESC "
        f"LIMIT {limit}"
    )
    return sql
