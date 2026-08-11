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

from backend.db_report.models import MysqlProxyConnlog
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

logger = logging.getLogger("root")

DEFAULT_CONNLOG_LIMIT = 500
DEFAULT_TIME_RANGE_DAYS = 7


def query_proxy_connlog(
    proxy_ips: List[str],
    cluster_domain: Optional[str] = None,
    conn_user: Optional[str] = None,
    session_ids: Optional[List[int]] = None,
    start_time: Optional[timezone.datetime] = None,
    end_time: Optional[timezone.datetime] = None,
    limit: Optional[int] = None,
) -> Dict:
    """查询 mysql-proxy 连接日志

    按 instance_host 分组返回符合条件的连接记录。
    时间范围默认为 [now - 7天, now]。
    """
    # 计算时间范围
    if not end_time:
        end_time = timezone.now()
    if not start_time:
        start_time = end_time - timedelta(days=DEFAULT_TIME_RANGE_DAYS)

    eff_limit = limit if limit is not None else DEFAULT_CONNLOG_LIMIT

    try:
        # 构建基础过滤条件
        qs = MysqlProxyConnlog.objects.filter(
            proxy_ip__in=proxy_ips,
            conn_time__gte=start_time,
            conn_time__lte=end_time,
        )

        # 可选条件拼接
        if conn_user:
            qs = qs.filter(conn_user=conn_user)
        if session_ids:
            qs = qs.filter(session_id__in=session_ids)

        # 按连接时间降序排列
        qs = qs.order_by("-conn_time")

        logger.info("query_proxy_connlog sql: %s", qs.query)
        all_rows = list(qs.values("instance_host", "conn_time", "client_ip", "conn_user", "session_id"))
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query proxy connlog failed: {e}")

    # 按 instance_host 分组，每组截取 limit 条
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    group_total: Dict[str, int] = defaultdict(int)

    for row in all_rows:
        host = row["instance_host"]
        group_total[host] += 1
        if len(grouped[host]) < eff_limit:
            # 将时间字段转为字符串
            if row.get("conn_time") and hasattr(row["conn_time"], "strftime"):
                row["conn_time"] = row["conn_time"].strftime("%Y-%m-%d %H:%M:%S")
            elif row.get("conn_time"):
                row["conn_time"] = str(row["conn_time"])
            grouped[host].append(row)

    # 构建返回结果，保持 instance_hosts 的输入顺序
    instances = []
    for host in proxy_ips:
        instances.append(
            {
                "instance_host": host,
                "records": [
                    {
                        "conn_time": r["conn_time"],
                        "client_ip": r.get("client_ip"),
                        "conn_user": r.get("conn_user"),
                        "session_id": r.get("session_id"),
                    }
                    for r in grouped.get(host, [])
                ],
                "total": group_total.get(host, 0),
            }
        )

    return {
        "cluster_domain": cluster_domain,
        "instances": instances,
    }
