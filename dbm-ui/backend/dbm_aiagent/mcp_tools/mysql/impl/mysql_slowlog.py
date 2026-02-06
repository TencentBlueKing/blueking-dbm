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
from typing import Dict

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str, timezone2timestamp

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
            "order_by": ["time"],
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
            item["values"] = row["values"][-1]  # row["values"]
            item[metric_param["field_name"]] = row["values"][-1]

            # query one sample detail
            item["sample"] = query_slow_log_detail(
                item.get("cluster_domain"), item.get("query_digest_md5"), start_time, end_time
            )
            slog_logs.append(item)

    except Exception as e:
        raise DBMMcpBaseException(msg=f"query slow logs failed: {e}")

    return {
        "cluster_domain": cluster_domain,
        "slog_logs": slog_logs,
    }


def query_slow_log_detail(
    cluster_domain: str,
    query_digest_md5: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    query_params = {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.mysql_slowlog",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
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
