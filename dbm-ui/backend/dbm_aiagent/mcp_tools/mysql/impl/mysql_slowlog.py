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
import json
from typing import Dict

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str


def query_slow_logs(
    cluster_type: ClusterType,
    cluster_domain: str,
    instance_role: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    try:
        query_params = {
            "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.mysql_slowlog",
            "start_time": datetime2str(start_time),
            "end_time": datetime2str(end_time),
            # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
            # "query_string": f"cluster_domain: \"{cluster_domain}\" AND instance_role: \"{instance_role}\"",
            "query_string": f'__ext.cluster_domain: "{cluster_domain}" __ext.instance_role: "{instance_role}"',
            "start": 0,
            "size": 1000,
            "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
        }
        resp = BKLogApi.esquery_search(
            query_params,
            use_admin=True,
        )
        print(json.dumps(resp))
        slog_logs = []
        for hit in resp["hits"]["hits"]:
            log_source = hit.get("_source", None)
            if log_source is None:
                continue
            slow_query = log_source.get("slow_query", None)
            if slow_query is None:
                continue
            query_string = slow_query.get("query_string", "")
            slog_logs.append(query_string)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query slow logs failed: {e}")

    return {
        "cluster_domain": cluster_domain,
        "cluster_type": cluster_type,
        "slog_logs": slog_logs,
    }
