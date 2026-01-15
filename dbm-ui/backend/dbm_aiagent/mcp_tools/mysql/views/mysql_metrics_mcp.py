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

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_metrics import query_mysql_metrics
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_metrics import (
    MysqlMetricsInputSerializer,
    MysqlMetricsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


class MySQLMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    def _query_metrics_by_type(self, request, metric_name, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        metric_name = metric_name

        datapoints_result = query_mysql_metrics(
            cluster_type=cluster_type,
            cluster_domain=cluster_domain,
            start_time=start_time,
            end_time=end_time,
            metric_type=metric_name,
        )

        return Response(
            {
                metric_name: datapoints_result,
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("获取一段时间内某个 tendbha/tendbcluster 集群的 cpu负载 指标信息")),
        request_slz=MysqlMetricsInputSerializer,
        response_slz=MysqlMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_metrics",
    )
    def query_cpu_summary(self, request, *args, **kwargs):
        return self._query_metrics_by_type(request, "cpu_summary", *args, **kwargs)

    @mcp_tools_api_decorator(
        description=str(_("获取一段时间内某个 tendbha/tendbcluster 集群的 qps 请求量 指标信息")),
        request_slz=MysqlMetricsInputSerializer,
        response_slz=MysqlMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_metrics",
    )
    def query_qps_summary(self, request, *args, **kwargs):
        return self._query_metrics_by_type(request, "qps_summary", *args, **kwargs)

    @mcp_tools_api_decorator(
        description=str(_("获取一段时间内某个 tendbha/tendbcluster 集群的 slow_query 数量 指标信息")),
        request_slz=MysqlMetricsInputSerializer,
        response_slz=MysqlMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_metrics",
    )
    def query_slow_count(self, request, *args, **kwargs):
        return self._query_metrics_by_type(request, "slow_count", *args, **kwargs)

    @mcp_tools_api_decorator(
        description=str(_("获取一段时间内某个 tendbha/tendbcluster 集群的 connections 连接数 指标信息")),
        request_slz=MysqlMetricsInputSerializer,
        response_slz=MysqlMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_metrics",
    )
    def query_connections(self, request, *args, **kwargs):
        return self._query_metrics_by_type(request, "connections", *args, **kwargs)

    @mcp_tools_api_decorator(
        description=str(_("获取一段时间内某个 tendbha/tendbcluster 集群的 threads_running 线程数 指标信息")),
        request_slz=MysqlMetricsInputSerializer,
        response_slz=MysqlMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_metrics",
    )
    def query_threads_running(self, request, *args, **kwargs):
        return self._query_metrics_by_type(request, "threads_running", *args, **kwargs)
