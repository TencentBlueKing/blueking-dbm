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

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_proxy_connlog import query_proxy_connlog
from backend.dbm_aiagent.mcp_tools.mysql.impl.query_proxy_conn_log import query_proxy_conn_log
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_proxy_connlog import (
    ProxyConnlogInputSerializer,
    ProxyConnlogOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.query_proxy_conn_log import QueryProxyConnLogOutputSerializer
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class MySQLProxyConnlogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 MySQL Proxy 连接日志。"
                "cluster_domain 和 instance_hosts 为必填参数，instance_hosts 传入 proxy 实例 IP 列表（格式如 '1.1.1.1'）。"
                "可选条件：conn_user 连接用户、session_ids 会话ID列表。"
                "时间范围默认最近 7 天，可通过 start_time/end_time 自定义。"
                "返回结果按 instance_host 分组，每组返回符合条件的连接记录。"
            )
        ),
        request_slz=ProxyConnlogInputSerializer,
        response_slz=ProxyConnlogOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_LOG],
        name_prefix="mysql",
    )
    def query_proxy_connlog(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        proxy_ips = self.get_param("proxy_ips")
        conn_user = self.get_param("conn_user")
        session_ids = self.get_param("session_ids")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")

        return Response(
            query_proxy_connlog(
                proxy_ips=proxy_ips,
                cluster_domain=cluster_domain,
                conn_user=conn_user,
                session_ids=session_ids,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 MySQL Proxy 连接记录（从后端 MySQL 实例的 infodba_schema.proxy_conn_log 表查询）。"
                "仅支持 TenDBHA 类型集群。"
                "cluster_domain 和 proxy_ips 为必填参数，proxy_ips 传入 proxy IP 列表。"
                "可选条件：username 连接用户、thread_ids 线程ID列表。"
                "时间范围默认最近 7 天，可通过 start_time/end_time 自定义。"
                "返回结果按 proxy_ip 分组，每组返回符合条件的连接记录。"
            )
        ),
        request_slz=ProxyConnlogInputSerializer,
        response_slz=QueryProxyConnLogOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_LOG],
        name_prefix="mysql",
    )
    def query_proxy_connlog_from_backend(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        proxy_ips = self.get_param("proxy_ips")
        conn_user = self.get_param("conn_user")
        session_ids = self.get_param("session_ids")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")

        return Response(
            query_proxy_conn_log(
                cluster_domain=cluster_domain,
                proxy_ips=proxy_ips,
                username=conn_user,
                thread_ids=session_ids,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        )
