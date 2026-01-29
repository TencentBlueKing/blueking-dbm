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
from django.db.models import Q
from django.http import HttpRequest

from backend.dbm_aiagent.mcp_tools.typing import BizIdList, ClusterIdList


def auth_default(request: HttpRequest, *args, **kwargs) -> list:
    """默认鉴权"""
    return []


def auth_parse_bizs(request: HttpRequest, *args, **kwargs) -> BizIdList:
    """
    解析业务列表 - 获取业务列表鉴权
    request 接收params:
    - bk_biz_id: 业务ID
    """
    data = request.query_params if request.method == "GET" else request.data
    if "bk_biz_id" not in data:
        raise ValueError("bk_biz_id is required")
    return [data["bk_biz_id"]]


def auth_parse_clusters(request: HttpRequest, *args, **kwargs) -> ClusterIdList:
    """
    解析集群列表 - 获取集群列表鉴权
    request 接收params:
    - cluster_domain: 集群域名
    - cluster_domains: 集群域名列表
    """
    from backend.db_meta.models import Cluster

    data = request.query_params if request.method == "GET" else request.data
    if "cluster_domain" not in data and "cluster_domains" not in data:
        raise ValueError("cluster_domain is required")

    data = data.get("cluster_domain") or data.get("cluster_domains")
    data = data if isinstance(data, list) else [data]
    cluster_ids = list(Cluster.objects.filter(immute_domain__in=data).values_list("id", flat=True))

    if not cluster_ids:
        raise ValueError("parse error, no clusters found for the given params")

    return cluster_ids


def auth_parse_hosts(request: HttpRequest, *args, **kwargs) -> ClusterIdList:
    """
    解析主机列表 - 获取集群列表鉴权
    request 接收params:
    - ip: 主机IP
    - ips: 主机IP列表
    - bk_host_id: 主机ID
    - bk_host_ids: 主机ID列表
    """
    from backend.db_meta.models import Cluster

    data = request.query_params if request.method == "GET" else request.data
    if "ip" in data:
        filters = Q(storageinstance__machine__ip=data["ip"]) | Q(proxyinstance__machine__ip=data["ip"])
        cluster_ids = list(Cluster.objects.filter(filters).values_list("id", flat=True))
    elif "ips" in data:
        filters = Q(storageinstance__machine__ip__in=data["ips"]) | Q(proxyinstance__machine__ip__in=data["ips"])
        cluster_ids = list(Cluster.objects.filter(filters).values_list("id", flat=True))
    elif "bk_host_id" in data:
        filters = Q(storageinstance__machine__bk_host_id=data["bk_host_id"]) | Q(
            proxyinstance__machine__bk_host_id=data["bk_host_id"]
        )
        cluster_ids = list(Cluster.objects.filter(filters).values_list("id", flat=True))
    elif "bk_host_ids" in data:
        filters = Q(storageinstance__machine__bk_host_id__in=data["bk_host_ids"]) | Q(
            proxyinstance__machine__bk_host_id__in=data["bk_host_ids"]
        )
        cluster_ids = list(Cluster.objects.filter(filters).values_list("id", flat=True))
    else:
        raise ValueError("ip or bk_host_id is required")

    if not cluster_ids:
        raise ValueError("parse error, no clusters found for the given params")

    return cluster_ids
