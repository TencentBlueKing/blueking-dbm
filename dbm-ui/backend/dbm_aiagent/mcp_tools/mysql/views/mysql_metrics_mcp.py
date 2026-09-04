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
from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import parse_step_to_seconds
from backend.dbm_aiagent.mcp_tools.common.views.promql_query import query_promql_metrics_with_roles
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_metrics import METRIC_TYPES, query_mysql_metrics
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_metrics import (
    MysqlMetricsInputSerializer,
    MysqlMetricsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class MySQLMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "获取一段时间内某个 tendbha/tendbcluster 监控指标，"
                "支持的指标类型有：disk_used、disk_usage、cpu_summary、qps_summary、memory_usage、"
                "slow_count、connections、threads_running"
            )
        ),
        request_slz=MysqlMetricsInputSerializer,
        response_slz=MysqlMetricsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="mysql_metrics",
    )
    def query_by_metric_name(self, request, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        metric_name = self.get_param("metric_name")

        promql_tmpl = METRIC_TYPES.get(metric_name, None)
        if not promql_tmpl:
            # 不支持查询 metric_name 类型的指标数据
            raise DBMMcpNotSupportClusterTypeException()
        query_builder = promql_tmpl.get(cluster_type, None)
        if not query_builder:
            query_builder = promql_tmpl.get("default", None)
            if not query_builder:
                # 集群类型 cluster_type 不支持查询 metric_name 类型的指标数据
                raise DBMMcpNotSupportClusterTypeException()

        query_builder.start_time = self.get_param("start_time")
        query_builder.end_time = self.get_param("end_time")
        # 仅当用户显式传入 step 时才覆盖预定义指标中的 step
        step = self.get_param("step")
        if step and parse_step_to_seconds(step) > parse_step_to_seconds(query_builder.step):
            query_builder.step = step

        # instance_role 条件在 promql_tmpl filter 中已定义
        result = query_promql_metrics_with_roles(cluster_domain, "", query_builder)
        result["aggregation"] = query_builder.get_aggregation()
        if query_builder.metric_name:
            result["metric_name"] = query_builder.metric_name
        else:
            result["metric_name"] = metric_name
        return Response(result)

    def _query_metrics_by_type(self, request, metric_name, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        metric_name = metric_name

        # 该路径无预定义 step，用户未传时默认 1m
        step = self.get_param("step") or "1m"

        datapoints_result = query_mysql_metrics(
            cluster_type=cluster_type,
            cluster_domain=cluster_domain,
            start_time=start_time,
            end_time=end_time,
            metric_type=metric_name,
            step=step,
        )

        return Response(
            {
                metric_name: datapoints_result,
            }
        )
