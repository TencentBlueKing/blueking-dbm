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
from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import PromQLQueryBuilder, execute_promql
from backend.dbm_aiagent.mcp_tools.common.serializers.promql_query import (
    PromQLQueryOutputSerializer,
    QueryMetricByInstanceInputSerializer,
    QueryMetricByRoleInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


def query_promql_metrics_with_roles(cluster_domain, instance_role, p: PromQLQueryBuilder):
    p.filters.append({"label_name": "cluster_domain", "op": "equal", "value": cluster_domain})
    if "cluster_domain" not in p.group_by:
        p.group_by.append("cluster_domain")

    if instance_role:
        p.filters.append({"label_name": "instance_role", "op": "match", "value": "|".join(instance_role)})
        if "instance_role" not in p.group_by:
            p.group_by.append("instance_role")

    promql_dict = p.prepare_promql()
    expr = promql_dict.pop("expression", None)
    return execute_promql(
        prom_queries=promql_dict, expr=expr, start_time=p.start_time, end_time=p.end_time, step=p.step
    )


def query_promql_metrics_with_instances(cluster_domain, instance, p: PromQLQueryBuilder):
    p.filters.append({"label_name": "cluster_domain", "op": "equal", "value": cluster_domain})
    if "cluster_domain" not in p.group_by:
        p.group_by.append("cluster_domain")

    if "dbm_system" in p.metric_name:
        # dbm_system 是操作系统级别的指标，提取 instances 里面的 host 来过滤
        instance_hosts = list(set([instance.split(":")[0] for instance in instance]))
        p.filters.append({"label_name": "instance_host", "op": "match", "value": "|".join(instance_hosts)})
        if "instance_host" not in p.group_by:
            p.group_by.append("instance_host")
    else:
        # dbm 指标 instance 格式是 ip-port，需要转换
        instance = [instance.replace(":", "-") for instance in instance]
        p.filters.append({"label_name": "instance", "op": "match", "value": "|".join(instance)})
        if "instance" not in p.group_by:
            p.group_by.append("instance")

    promql_dict = p.prepare_promql()
    expr = promql_dict.pop("expression", None)
    return execute_promql(
        prom_queries=promql_dict, expr=expr, start_time=p.start_time, end_time=p.end_time, step=p.step
    )


class PromQLQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "按 cluster 来查询集群级别监控指标。根据指标名称、标签过滤条件、聚合方式等参数自动构建 PromQL 并查询监控数据。"
                "支持 range_function（Gauge 指标用 max/min/sum/avg/count 对应 *_over_time，Counter 指标用 rate/increase）"
                "和外层聚合（如 max/sum/avg 等），以及 group_by 分组。返回时序数据和实际执行的 PromQL 语句。"
            )
        ),
        request_slz=QueryMetricByRoleInputSerializer,
        response_slz=PromQLQueryOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="promql",
    )
    def query_metrics_with_roles(self, request, *args, **kwargs):
        cluster_domain = (self.get_param("cluster_domain"),)
        instance_role = (self.get_param("instance_role"),)
        p = PromQLQueryBuilder(
            alias="A",
            metric_name=self.get_param("metric_name"),
            filters=self.get_param("filters", []),
            group_by=self.get_param("group_by", []),
            aggregation=self.get_param("aggregation"),
            range_function=self.get_param("range_function"),
            start_time=self.get_param("start_time"),
            end_time=self.get_param("end_time"),
            step=self.get_param("step", "1m"),
        )
        result = query_promql_metrics_with_roles(cluster_domain, instance_role, p)

        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "按 cluster instance(ip:port) 来查询实例级别监控指标。根据指标名称、标签过滤条件、聚合方式等参数自动构建 PromQL 并查询监控数据。"
                "支持 range_function（Gauge 指标用 max/min/sum/avg/count 对应 *_over_time，Counter 指标用 rate/increase）"
                "和外层聚合（如 max/sum/avg 等），以及 group_by 分组。返回时序数据和实际执行的 PromQL 语句。"
            )
        ),
        request_slz=QueryMetricByInstanceInputSerializer,
        response_slz=PromQLQueryOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="promql",
    )
    def query_metrics_with_instances(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        instance = self.get_param("instance")

        p = PromQLQueryBuilder(
            alias="A",
            metric_name=self.get_param("metric_name"),
            filters=self.get_param("filters", []),
            group_by=self.get_param("group_by", []),
            aggregation=self.get_param("aggregation"),
            range_function=self.get_param("range_function"),
            start_time=self.get_param("start_time"),
            end_time=self.get_param("end_time"),
            step=self.get_param("step", "1m"),
        )

        result = query_promql_metrics_with_instances(cluster_domain, instance, p)
        return Response(result)
