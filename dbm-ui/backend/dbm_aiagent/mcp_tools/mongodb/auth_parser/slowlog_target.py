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
from django.http import HttpRequest

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    FakeRequest,
    auth_parse_clusters,
    auth_parse_hosts,
    auth_parse_instances,
)
from backend.dbm_aiagent.mcp_tools.typing import ClusterIdList


def auth_parse_slowlog_target(request: HttpRequest, *args, **kwargs) -> ClusterIdList:
    """
    解析 MongoDB slowlog 入参为集群 ID 列表，优先级：
    1. cluster_domain
    2. instance（ip:port）
    3. instance_host（主机 IP）
    """
    data = request.query_params if request.method == "GET" else request.data
    cluster_domain = (data.get("cluster_domain") or "").strip()
    instance = (data.get("instance") or "").strip()
    instance_host = (data.get("instance_host") or "").strip()

    if cluster_domain:
        return auth_parse_clusters(FakeRequest(request.method, {"cluster_domain": cluster_domain}))
    if instance:
        return auth_parse_instances(FakeRequest(request.method, {"instance": instance}))
    if instance_host:
        return auth_parse_hosts(FakeRequest(request.method, {"ip": instance_host}))

    raise ValueError("cluster_domain, instance or instance_host is required")
