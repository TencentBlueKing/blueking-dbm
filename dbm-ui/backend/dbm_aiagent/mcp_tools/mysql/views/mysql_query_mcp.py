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
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


class MySQLQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的表结构")),
        request_slz=ShowCreateTableInputSerializer,
        response_slz=ShowCreateTableOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_create_table(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
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
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
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
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
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
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
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
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
        cluster_domain = self.get_param("cluster_domain")

        return Response(mysql_cluster_topo(cluster_type=ClusterType.TenDBCluster, cluster_domain=cluster_domain))

    @mcp_tools_api_decorator(
        description=str(_("""查询集群连接列表, 默认合并接入层和存储连接""")),
        request_slz=ShowProcessListInputSerializer,
        response_slz=ShowProcessListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_cluster_processlist(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")

        res = show_cluster_processlist(cluster_type, cluster_domain)
        logger.info(res)
        return Response({"cluster_process_lists": res})

    @mcp_tools_api_decorator(
        description=str(_("""查询 MySQL 运行时参数""")),
        request_slz=ShowMySQLVariablesInputSerializer,
        response_slz=ShowMySQLVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_mysql_variables(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
        address = self.get_param("address")
        machine_type = self.get_param("machine_type")
        variable_hints = self.get_param("variable_hints")

        return Response(show_mysql_variables(address, machine_type, variable_hints))

    @mcp_tools_api_decorator(
        description=str(_("""查询实例运行时状态""")),
        request_slz=ShowInstanceStatusesInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_instance_status(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
        address = self.get_param("address")
        machine_type = self.get_param("machine_type")

        return Response(show_instance_status(address, machine_type))
