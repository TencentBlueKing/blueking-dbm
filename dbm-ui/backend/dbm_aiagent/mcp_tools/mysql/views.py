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
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_topo import mysql_cluster_topo
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql import explain_sql
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_create_table import show_create_table
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_processlist import show_cluster_processlist
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_status import show_instance_status
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_variables import show_mysql_variables
from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_topo import (
    ClusterTopoInputSerializer,
    TenDBClusterTopoOutputSerializer,
    TenDBHATopoOutputSerializer,
    TenDBSingleTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.explain_sql import (
    ExplainSQLInputSerializer,
    ExplainSQLOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_create_table import (
    ShowCreateTableInputSerializer,
    ShowCreateTableOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_processlist import (
    ShowProcessListInputSerializer,
    ShowProcessListOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_status import (
    ShowInstanceStatuesOutputSerializer,
    ShowInstanceStatusesInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_variables import (
    ShowMySQLVariablesInputSerializer,
    ShowMySQLVariablesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission


class MySQLMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的表结构")),
        request_slz=ShowCreateTableInputSerializer,
        response_slz=ShowCreateTableOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_create_table(self, request, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tablename = self.get_param("tablename")

        return Response(
            show_create_table(
                cluster_type=cluster_type, cluster_domain=cluster_domain, dbname=dbname, tablename=tablename
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 SQL 执行计划")),
        request_slz=ExplainSQLInputSerializer,
        response_slz=ExplainSQLOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def explain_sql(self, request, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        query_sql = self.get_param("query_sql")

        return Response(
            explain_sql(cluster_type=cluster_type, cluster_domain=cluster_domain, dbname=dbname, query_sql=query_sql)
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 TenDBSingle 集群拓扑结构")),
        request_slz=ClusterTopoInputSerializer,
        response_slz=TenDBSingleTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def tendbsingle_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        return Response(mysql_cluster_topo(cluster_type=ClusterType.TenDBSingle, cluster_domain=cluster_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 TenDBHA 集群拓扑结构")),
        request_slz=ClusterTopoInputSerializer,
        response_slz=TenDBHATopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def tendbha_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        return Response(mysql_cluster_topo(cluster_type=ClusterType.TenDBHA, cluster_domain=cluster_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 TenDBCluster 集群拓扑结构")),
        request_slz=ClusterTopoInputSerializer,
        response_slz=TenDBClusterTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def tendbcluster_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        return Response(mysql_cluster_topo(cluster_type=ClusterType.TenDBCluster, cluster_domain=cluster_domain))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询集群连接列表
            1. 连接信息的原始详情可用于人工阅读分析
            2. 按 host 或者 user 或者 db 或者 state 的聚合结果可以分析连接概况
            3. 详情列表的 count 数量就是对应实例或者集群的总连接数. 可以结合最大连接数(max_connections)运行时参数来评估实例的连接够不够用
            4. addresses 参数默认为 None, 按不同的集群类型有不同的含义
              * 当集群类型为 TenDBSingle 时, 获取所有存储层的连接信息
              * 当集群类型为 TenDBHA 时, 获取所有接入层(proxy)的连接信息
              * 当集群类型为 TenDBCluster 时, 获取所有主接入层(spider master)的连接信息
            5. addresses 不为空时, 获取指定实例的连接信息
            6. addresses 要么为 None, 要么只能是 ip:port 形式的实例列表
            """
            )
        ),
        request_slz=ShowProcessListInputSerializer,
        response_slz=ShowProcessListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_cluster_processlist(self, request, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        addresses = self.get_param("addresses")

        return Response(show_cluster_processlist(cluster_type, cluster_domain, addresses))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询 MySQL 运行时参数
限制只能查询机器类型(machine_type) 是 single, backend, remote, spider 实例的状态"""
            )
        ),
        request_slz=ShowMySQLVariablesInputSerializer,
        response_slz=ShowMySQLVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_mysql_variables(self, request, *args, **kwargs):
        address = self.get_param("address")
        machine_type = self.get_param("machine_type")
        variable_hints = self.get_param("variable_hints")

        return Response(show_mysql_variables(address, machine_type, variable_hints))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询实例运行时状态
        限制只能查询机器类型(machine_type) 是 single, proxy, backend, remote, spider 实例的状态
        """
            )
        ),
        request_slz=ShowInstanceStatusesInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_instance_status(self, request, *args, **kwargs):
        address = self.get_param("address")
        machine_type = self.get_param("machine_type")

        return Response(show_instance_status(address, machine_type))
