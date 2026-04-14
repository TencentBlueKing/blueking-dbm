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
from datetime import timedelta
from typing import Dict, List, Optional

from django.db.models import Max, Sum
from django.utils import timezone

from backend.db_report.models import MysqlDbTableSize
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

logger = logging.getLogger("root")


def query_database_size(
    cluster_domain: str,
    instance_role: str,
    database_names: List[str],
    base_time: Optional[timezone.datetime] = None,
) -> Dict:
    """查询某些 databases 的大小

    tendbcluster 有分片概念，database_name 是逻辑库名（如 dbtest），original_database_name 是真实库名（如 dbtest_1, dbtest_2）。
    统计大小时需要把同一个小时里各分片数据 sum 起来，但不能跨小时 sum。
    所以先按 (database_name, dteventtimehour) 分组 sum(table_size) 得到每个库每小时的大小，
    然后取每个库最新一个小时的数据作为结果。

    实现方式：
    1. 先按 (database_name, dteventtimehour) 分组，sum(table_size) 得到每个库每小时的大小
    2. 用 ORM 取最新的 dteventtimehour 对应的数据
    """
    # 计算时间范围：[base_time - 48h, base_time]
    if not base_time:
        base_time = timezone.now()
    start_time = base_time - timedelta(hours=48)

    try:
        # 构建基础过滤条件
        qs = MysqlDbTableSize.objects.filter(
            cluster_domain=cluster_domain,
            instance_role=instance_role,
            dteventtimehour__gte=start_time,
            dteventtimehour__lte=base_time,
        )

        # 如果不是查询所有库，则过滤指定库名
        if database_names and "*" not in database_names:
            qs = qs.filter(database_name__in=database_names)

        # 按 (database_name, dteventtimehour) 分组，sum(table_size) 得到每个库每小时的大小
        qs = (
            qs.values("database_name", "dteventtimehour")
            .annotate(
                database_size=Sum("table_size"),
                latest_report_time=Max("report_time"),
            )
            .order_by("database_name", "-dteventtimehour")
        )
        logger.info("query_mysql_capacity sql: %s", qs.query)
        all_rows = list(qs)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query database size failed: {e}")

    # 对每个 database_name 只保留最新一个小时的数据
    seen_databases = set()
    result: List[Dict] = []
    for item in all_rows:
        db_name = item["database_name"]
        if db_name in seen_databases:
            continue
        seen_databases.add(db_name)

        # 将时间字段转为字符串
        if item.get("dteventtimehour") and hasattr(item["dteventtimehour"], "strftime"):
            item["dteventtimehour"] = item["dteventtimehour"].strftime("%Y-%m-%d %H:%M:%S")
        elif item.get("dteventtimehour"):
            item["dteventtimehour"] = str(item["dteventtimehour"])

        result.append(item)

    return {
        "cluster_domain": cluster_domain,
        "instance_role": instance_role,
        "databases": result,
    }


def query_table_size(
    cluster_domain: str,
    instance_role: str,
    database_name: str,
    table_names: List[str],
    base_time: Optional[timezone.datetime] = None,
    limit=50,
) -> Dict:
    """查询某些表的大小

    tendbcluster 有分片概念，需要把同一个小时里各分片的同名表数据 sum 起来。
    按 (database_name, table_name, dteventtimehour) 分组 sum(table_size)，
    然后取每个表最新一个小时的数据作为结果。
    """
    # 计算时间范围：[base_time - 48h, base_time]
    if not base_time:
        base_time = timezone.now()
    start_time = base_time - timedelta(hours=48)

    try:
        qs = MysqlDbTableSize.objects.filter(
            cluster_domain=cluster_domain,
            instance_role=instance_role,
            database_name=database_name,
            dteventtimehour__gte=start_time,
            dteventtimehour__lte=base_time,
        )

        # 如果指定了表名，则过滤
        if table_names and table_names != ["*"]:
            qs = qs.filter(table_name__in=table_names)

        # 按 (database_name, table_name, dteventtimehour) 分组
        qs = (
            qs.values("database_name", "table_name", "dteventtimehour")
            .annotate(
                table_size=Sum("table_size"),
                latest_report_time=Max("report_time"),
            )
            .order_by("table_name", "-dteventtimehour")
        )
        all_rows = list(qs)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query table size failed: {e}")

    # 对每个 table_name 只保留最新一个小时的数据
    seen_tables = set()
    result: List[Dict] = []
    for item in all_rows:
        tbl_name = item["table_name"]
        if tbl_name in seen_tables:
            continue
        seen_tables.add(tbl_name)

        # 将时间字段转为字符串
        if item.get("dteventtimehour") and hasattr(item["dteventtimehour"], "strftime"):
            item["dteventtimehour"] = item["dteventtimehour"].strftime("%Y-%m-%d %H:%M:%S")
        elif item.get("dteventtimehour"):
            item["dteventtimehour"] = str(item["dteventtimehour"])

        result.append(item)
        if len(result) >= limit:
            break

    return {
        "cluster_domain": cluster_domain,
        "instance_role": instance_role,
        "database_name": database_name,
        "tables": result,
    }
