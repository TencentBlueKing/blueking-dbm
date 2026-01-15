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
from typing import Dict, List

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Cluster, Machine
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str


def get_cluster_slowlog(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> List[Dict]:
    cluster_slows = []
    proxies_slowlogs = _get_slowlog(
        get_query_params(immute_domain=immute_domain, role="proxy", start_time=start_time, end_time=end_time)
    )
    master_slowlogs = _get_slowlog(
        get_query_params(immute_domain=immute_domain, role="redis_master", start_time=start_time, end_time=end_time)
    )
    cluster_slows.append(proxies_slowlogs)
    cluster_slows.append(master_slowlogs)
    return {"slowlog_entries": cluster_slows, "total_count": len(cluster_slows)}


def get_host_slowlog(
    host: str,
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> List[Dict]:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
    machine_obj = Machine.objects.get(bk_cloud_id=cluster_obj.bk_cloud_id, ip=host)

    host_slows = []
    if machine_obj.access_layer == AccessLayer.PROXY.value:
        host_slows = _get_slowlog(
            get_query_params(
                immute_domain=immute_domain, role="proxy", start_time=start_time, end_time=end_time, host=host
            )
        )
    else:
        host_slows = _get_slowlog(
            get_query_params(
                immute_domain=immute_domain, role="redis_master", start_time=start_time, end_time=end_time, host=host
            )
        )

    return {"slowlog_entries": host_slows, "total_count": len(host_slows)}


def _get_slowlog(
    query_params: Dict,
) -> Dict:
    try:
        resp = BKLogApi.esquery_search(
            query_params,
            use_admin=True,
        )

        slog_logs = []
        for hit in resp["hits"]["hits"]:
            log_src = hit.get("_source", None)
            if log_src is None:
                continue
            slow_query = log_src.get("redis", None)
            if slow_query is None:
                continue
            slowlog_d = slow_query.get("slowlog", "")
            slowlog_d["instance_addr"] = "{}:{}".format(
                log_src["__ext"]["instance_host"], log_src["__ext"]["instance_port"]
            )
            slowlog_d["instance_role"] = log_src["__ext"]["instance_role"]
            slowlog_d["create_time"] = log_src["event"]["created"]
            slowlog_d["duration_us"] = slowlog_d["duration"]["us"]
            slog_logs.append(slowlog_d)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query slow logs failed: {e}")

    return slog_logs


def get_query_params(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    role=None,
    host=None,
) -> Dict:

    query_parts = [f'__ext.cluster_domain:"{immute_domain}"']
    if role:
        query_parts.append(f'__ext.instance_role:"{role}"')
    if host:
        query_parts.append(f'__ext.instance_host:"{host}"')

    query_params = {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.redis_slowlog",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": " AND ".join(query_parts),
        "start": 0,
        "size": 1000,
        "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }

    return query_params
