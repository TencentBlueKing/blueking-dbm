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
from typing import Dict, List

from django.db.models import Aggregate, CharField, Count, IntegerField, Max, Min, Q, Sum
from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.db_report.models import MysqlProxyConnlog, MysqlSlowlogDetail
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import timezone2timestamp

from . import config

SLOW_LOG_QUERY_PARAM = {
    "reference_name": "a",
    "data_source": "bklog",
    "table_id": "bklog_index_set_%d",
    "field_name": "query_time",
    "is_regexp": False,
    "time_field": "time",
    "function": [
        {
            "method": "max",
            "dimensions": [
                "slow_query.query_digest_md5",
                # "__ext.cluster_domain",
                # "__ext.instance_role",
                # "user",
                # "db_name",
                # "slow_query.db_name",
                # "slow_query.table_name",
                # "slow_query.query_digest_text"
            ],
        }
    ],
    # "time_aggregation": {"window": "5m", "function": "max_over_time"},
    "conditions": {"field_list": [], "condition_list": []},
    "limit": 5,
}


def query_slow_logs_by_metric(
    cluster_domain: str,
    instance_role: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    metric_name: str,
    limit: int,
) -> Dict:
    if not config.MYSQL_SLOW_LOG_INDEX_SET_ID:
        config.init_collectors_index_set_id()
        if not config.MYSQL_SLOW_LOG_INDEX_SET_ID:
            raise DBMMcpBaseException(msg="MYSQL_SLOW_LOG_INDEX_SET_ID is not set")

    query_param = copy.deepcopy(SLOW_LOG_QUERY_PARAM)
    query_param["table_id"] = SLOW_LOG_QUERY_PARAM["table_id"] % config.MYSQL_SLOW_LOG_INDEX_SET_ID
    query_param["limit"] = limit if limit else 5
    # query_param["conditions"]["field_list"][0]["value"] = [cluster_domain]
    # query_param["conditions"]["field_list"][1]["value"] = [instance_role]
    cluster_cond = {
        "field_name": "__ext.cluster_domain",
        "op": "eq",
        "value": [cluster_domain],
    }
    role_cond = {"field_name": "__ext.instance_role", "op": "eq", "value": [instance_role]}
    query_param["conditions"]["field_list"].append(cluster_cond)
    query_param["conditions"]["field_list"].append(role_cond)
    # query_param["conditions"]["field_list"].append(common_cond)
    query_param["conditions"]["condition_list"].append("and")

    if metric_name == "query_time" or metric_name == "":
        query_param["reference_name"] = "a"
        query_param["field_name"] = "query_time"
        query_param["function"][0]["method"] = "max"

    if metric_name == "slow_count":
        query_param["reference_name"] = "a"
        query_param["field_name"] = "query_digest_md5"
        query_param["function"][0]["method"] = "count"

    if metric_name == "rows_scan" or metric_name == "rows_examined":
        query_param["reference_name"] = "a"
        query_param["field_name"] = "rows_examined"
        query_param["function"][0]["method"] = "sum"

    if not query_param["field_name"]:
        raise DBMMcpBaseException(msg="metric_name is not supported")

    query_result = query_slow_logs(cluster_domain, query_param, start_time, end_time)
    query_result["metric_aggregate_type"] = "%s by %s" % (
        query_param["function"][0]["method"],
        query_param["field_name"],
    )
    return query_result


def query_slow_logs(
    cluster_domain: str,
    metric_param: Dict,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    try:
        query_params = {
            "start_time": str(timezone2timestamp(start_time)),  # "1754893191"
            "end_time": str(timezone2timestamp(end_time)),
            # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
            # "query_string": f"cluster_domain: \"{cluster_domain}\" AND instance_role: \"{instance_role}\"",
            "query_list": [
                metric_param,
            ],
            "metric_merge": "a",
            "order_by": ["-_value"],
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "bk_app_code": env.APP_CODE,
            "bk_app_secret": env.SECRET_KEY,
            "bk_username": env.DEFAULT_USERNAME,
        }
        resp = BKLogApi.query_ts_reference(
            query_params,
            use_admin=True,
        )
        # {"result": true, "data": {"series": []}, "code": 0, "message": "", "request_id": null}
        # response_result = {'result': True, 'data': {'series': []}, 'code': 0, 'message': ''}
        slog_logs = []
        for row in resp["series"]:
            item = {}
            for i, value in enumerate(row["group_values"]):
                log_label = row["group_keys"][i].replace("__ext.", "").replace("slow_query.", "")
                if log_label in ["cluster_domain", "instance_role"]:
                    # 不重复了
                    continue
                if log_label == "db_name":
                    if item.get("db_name", None) is None or value != "":
                        # db_name 来自 db_name 和 slow_query.db_name
                        item[log_label] = value
                    continue
                item[log_label] = value
            if not item.get("query_digest_md5"):
                continue
            item["values"] = row["values"][-1]  # row["values"]
            item[metric_param["field_name"]] = row["values"][-1][1]  # [ts, value]

            # query one sample detail
            item["sample"] = query_slow_log_detail(cluster_domain, item.get("query_digest_md5"), start_time, end_time)
            slog_logs.append(item)

    except Exception as e:
        raise DBMMcpBaseException(msg=f"query slow logs failed: {e}")

    return {
        "cluster_domain": cluster_domain,
        "slow_logs": slog_logs,
    }


def query_slow_log_detail(
    cluster_domain: str,
    query_digest_md5: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    query_params = {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.mysql_slowlog",
        "start_time": str(timezone2timestamp(start_time)),
        "end_time": str(timezone2timestamp(end_time)),
        # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
        "query_string": f'slow_query.query_digest_md5:"{query_digest_md5}" AND __ext.cluster_domain: "{cluster_domain}"',
        "start": 0,
        "size": 1,
        "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }
    resp = BKLogApi.esquery_search(
        query_params,
        use_admin=True,
    )

    for hit in resp["hits"]["hits"]:
        one_slow_log = {}
        source_log = hit["_source"]
        if source_log.get("slow_query", None) or not source_log.get("__parse_failure", True):
            one_slow_log["query_digest_md5"] = source_log["slow_query"].pop("query_digest_md5")
            # 这里是为了优化 markdown 的展示，去除反引号
            one_slow_log["query_digest_text"] = source_log["slow_query"].pop("query_digest_text").replace("`", "")
            one_slow_log["sql_text"] = source_log["slow_query"].pop("query_string").replace("`", "")
            if source_log.get("db_name", ""):
                one_slow_log["db_name"] = source_log["db_name"]
            else:
                source_log["slow_query"].pop("db_name")
            one_slow_log["table_name"] = source_log["slow_query"].pop("table_name")
            one_slow_log["cluster_domain"] = source_log["__ext"].pop("cluster_domain")
            one_slow_log["instance_role"] = source_log["__ext"].pop("instance_role")
            one_slow_log["instance_host"] = source_log["__ext"].pop("instance_host")
            one_slow_log["instance_port"] = source_log["__ext"].pop("instance_port")
            one_slow_log["cluster_type"] = source_log["__ext"].pop("cluster_type")
            one_slow_log["bk_biz_id"] = source_log["__ext"].pop("app_id")

            one_slow_log["client_host"] = source_log["client_host"]
            one_slow_log["user"] = source_log["user"]
            one_slow_log["query_time"] = source_log["query_time"]
            one_slow_log["rows_sent"] = source_log["rows_sent"]
            one_slow_log["rows_examined"] = source_log["rows_examined"]
            one_slow_log["lock_time"] = source_log["lock_time"]
            one_slow_log["sql_timestamp"] = source_log["sql_timestamp"]
        # 这里只返回一个
        return one_slow_log


def _resolve_tendbha_client_host(item: Dict) -> None:
    """对于 tendbha 集群，client_host 字段实际是 mysql-proxy ip。
    通过 MysqlProxyConnlog 表根据 conn_user、proxy_ip、session_id 查询真正的来源客户端 IP，
    查到则替换 client_host，查不到则保持不变。
    """
    if item.get("cluster_type") != "tendbha" or not item.get("client_host") or not item.get("session_ids"):
        return

    try:
        proxy_ips = [ip.strip() for ip in item["client_host"].split(",") if ip.strip()]
        session_id_list = [int(sid.strip()) for sid in item["session_ids"].split(",") if sid.strip()]
        conn_user = item.get("username", "")
        if not (proxy_ips and session_id_list and conn_user):
            return

        real_client_ips = list(
            MysqlProxyConnlog.objects.filter(
                conn_user=conn_user,
                proxy_ip__in=proxy_ips,
                session_id__in=session_id_list,
            )
            .values_list("client_ip", flat=True)
            .distinct()
        )
        if real_client_ips:
            item["client_host"] = ",".join(real_client_ips)
    except Exception:  # noqa: E722
        pass


def query_slowlog_aggregated(
    cluster_domain: str,
    instance_role: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    order_by="query_time_max",
    limit=10,
    query_sample=True,
    exclude_system=True,
):
    """使用 Django ORM 实现慢日志聚合查询
        SELECT cluster_domain, instance_role, query_digest_md5,
        MIN(dteventtimestamp) AS time_window_min,
        MAX(dteventtimestamp) AS time_window_max,
        COUNT(*) AS count_star,
        MAX(query_time) AS query_time_max,
        SUM(query_time) AS query_time_sum,
        MAX(rows_examined) AS rows_examined_max,
        SUM(rows_examined) AS rows_examined_sum,
        MAX(rows_sent) AS rows_sent_max,
        SUM(rows_sent) AS rows_sent_sum,
        ANY_VALUE(query_digest_text) AS query_digest_text,
        ANY_VALUE(query_command) AS query_command,
        ANY_VALUE(query_db_name) AS query_db_name,
        ANY_VALUE(table_names) AS table_names,
        ANY_VALUE(username) AS username,
        ANY_VALUE(client_host) client_host
    FROM {MysqlSlowlogDetail._meta.db_table}
    WHERE cluster_domain = %s
        AND instance_role = %s
        AND dteventtimestamp > %s
        AND dteventtimestamp <= %s
    GROUP BY cluster_domain, instance_role, query_digest_md5
    ORDER BY {order_by} DESC
    LIMIT %s
    """
    # 自定义 ANY_VALUE 聚合函数，继承 Aggregate 使 Django 不会将其加入 GROUP BY
    class AnyValue(Aggregate):
        function = "ANY_VALUE"
        name = "AnyValue"

    # 自定义 GROUP_CONCAT 聚合函数，兼容 Doris（不支持 DISTINCT）
    class GroupConcat(Aggregate):
        function = "GROUP_CONCAT"
        name = "GroupConcat"
        template = "%(function)s(%(expressions)s%(separator)s)"

        def __init__(self, expression, separator=",", **extra):
            super().__init__(expression, separator=f" SEPARATOR '{separator}'", **extra)

    # 允许排序的字段白名单
    allowed_order_by = {
        "count_star",
        "query_time_max",
        "query_time_sum",
        "rows_examined_max",
        "rows_examined_sum",
        "rows_sent_max",
        "rows_sent_sum",
    }
    if order_by not in allowed_order_by:
        raise DBMMcpBaseException(msg=f"order_by field '{order_by}' is not allowed")

    try:
        base_filter = Q(
            cluster_domain=cluster_domain,
            instance_role=instance_role,
            log_time__gt=start_time,
            log_time__lte=end_time,
        )
        # 排除系统 SQL：username 为系统用户，或 query_digest_text 包含系统 schema
        if exclude_system:
            system_user_q = Q(username__in=["MONITOR", "yw", "dba_bak_all_sel"])
            system_schema_q = (
                Q(query_digest_text__contains="infodba_schema")
                | Q(query_digest_text__contains="information_schema")
                | Q(query_digest_text__contains="performance_schema")
            )
            base_filter &= ~(system_user_q | system_schema_q)

        qs = (
            MysqlSlowlogDetail.objects.filter(base_filter)
            .values("cluster_domain", "instance_role", "query_digest_md5")
            .annotate(
                time_window_min=Min("dteventtimestamp"),
                time_window_max=Max("dteventtimestamp"),
                count_star=Count("*"),
                query_time_max=Max("query_time"),
                query_time_sum=Sum("query_time"),
                rows_examined_max=Max("rows_examined"),
                rows_examined_sum=Sum("rows_examined"),
                rows_examined_min=Min("rows_examined"),
                rows_sent_max=Max("rows_sent"),
                rows_sent_sum=Sum("rows_sent"),
                query_digest_text=AnyValue("query_digest_text", output_field=CharField()),
                query_string=AnyValue("query_string", output_field=CharField()),
                query_command=AnyValue("query_command", output_field=CharField()),
                query_db_name=AnyValue("query_db_name", output_field=CharField()),
                table_names=AnyValue("table_names", output_field=CharField()),
                username=AnyValue("username", output_field=CharField()),
                client_host=GroupConcat("client_host", output_field=CharField()),
                session_ids=GroupConcat("session_id", output_field=CharField()),
                instance_host=AnyValue("instance_host", output_field=CharField()),
                instance_port=AnyValue("instance_port", output_field=IntegerField()),
                cluster_type=AnyValue("cluster_type", output_field=CharField()),
            )
            .order_by(f"-{order_by}")[:limit]
        )
        rows = list(qs)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query slowlog aggregated data failed: {e}")

    result: List[Dict] = []
    for item in rows:
        # 将时间字段转为字符串，方便序列化
        for time_field in ["time_window_min", "time_window_max"]:
            if item.get(time_field) and hasattr(item[time_field], "strftime"):
                item[time_field] = item[time_field].strftime("%Y-%m-%d %H:%M:%S")
            elif item.get(time_field):
                item[time_field] = str(item[time_field])
        # 去除 query_digest_text 中的反引号，优化 markdown 展示
        if item.get("query_digest_text"):
            item["query_digest_text"] = item["query_digest_text"].replace("`", "")
        # GROUP_CONCAT 无 DISTINCT，在 Python 层对 client_host 去重
        if item.get("client_host"):
            item["client_host"] = ",".join(set(ip.strip() for ip in item["client_host"].split(",") if ip.strip()))
        # 对于 tendbha 集群，client_host 实际是 proxy ip，需要通过 MysqlProxyConnlog 查询真正的来源 IP
        _resolve_tendbha_client_host(item)
        # 删除不必要的返回字段
        item.pop("cluster_domain", None)
        item.pop("instance_role", None)
        item.pop("cluster_type", None)
        if not query_sample:
            # 不查询慢日志样本时，删除 query_string 字段。某些情况 sample 非常大，返回给 mcp 占用大量上下文
            item.pop("query_string", None)
        result.append(item)

    return {
        "cluster_domain": cluster_domain,
        "instance_role": instance_role,
        "metric_name": order_by,
        "slow_logs": result,
    }
