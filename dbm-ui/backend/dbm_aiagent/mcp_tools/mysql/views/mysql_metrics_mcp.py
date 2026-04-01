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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters, auth_parse_instances
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_metrics import (
    aggregate_processlist_by_type,
    query_mysql_metrics,
    show_instance_processlist,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_metrics import (
    MysqlMetricsInputSerializer,
    MysqlMetricsOutputSerializer,
    ShowInstanceProcessListAggregatedInputSerializer,
    ShowInstanceProcessListAggregatedOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_metrics",
    )
    def query_threads_running(self, request, *args, **kwargs):
        return self._query_metrics_by_type(request, "threads_running", *args, **kwargs)

    @mcp_tools_api_decorator(
        description=str(_("""查询 mysql 某个实例连接情况, 返回是按照 aggregate_type 聚合 processlist 的结果，不是 processlist 原始信息""")),
        request_slz=ShowInstanceProcessListAggregatedInputSerializer,
        response_slz=ShowInstanceProcessListAggregatedOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_query",
    )
    def show_instance_processlist_aggregated(self, request, *args, **kwargs):
        instance = self.get_param("instance")
        aggregate_types = self.get_param("aggregate_type")
        # 根据 instance(ip:port) 反查集群，instance 可能是存储层实例，也可能是接入层实例
        ip, port = instance.split(":")

        machine = Machine.objects.filter(ip=ip).first()
        instance_obj = ProxyInstance.objects.filter(machine__ip=ip, port=int(port)).first()
        if not instance_obj:
            instance_obj = StorageInstance.objects.filter(machine__ip=ip, port=int(port)).first()

        if not instance_obj:
            raise ValueError(f"No cluster found for instance {instance}")
        if instance_obj.cluster_type not in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=instance_obj.cluster_type)

        processlist_detail = show_instance_processlist(
            instance, machine.bk_cloud_id, instance_obj.cluster_type, instance_obj.instance_role
        )
        aggregated = []
        for aggregate_type in aggregate_types:
            processlist_aggregated = aggregate_processlist_by_type(processlist_detail, aggregate_type)
            aggregated.append(
                {
                    "processlist_aggregated": processlist_aggregated,
                    "aggregate_type": aggregate_type,
                }
            )

        return Response(
            {
                "processlist_summary": aggregated,
                "instance_role": instance_obj.instance_role,
                "total_count": len(processlist_detail),
            }
        )
