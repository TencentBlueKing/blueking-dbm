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
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_db_table_size import query_database_size, query_table_size
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_db_table_size import (
    DatabaseSizeInputSerializer,
    DatabaseSizeOutputSerializer,
    TableSizeInputSerializer,
    TableSizeOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class MySQLTableCapacityMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 tendbsingle, tendbha, tendbcluster 集群中指定数据库的大小。"
                "database_names 传 ['*'] 则查询所有数据库大小。"
                "tendbcluster 集群会自动将各分片数据汇总，返回的是逻辑库的总大小。"
                "返回的 database_size 单位是字节(bytes)。"
                "limit 按库名字典序截取（默认 20）；top_n 按库大小降序截取，与 limit 互斥；"
                "min_size_bytes 可过滤掉小于该字节数的库。"
            )
        ),
        request_slz=DatabaseSizeInputSerializer,
        response_slz=DatabaseSizeOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_CAPACITY],
        name_prefix="mysql",
    )
    def query_db_size(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        instance_role = self.get_param("instance_role")
        database_names = self.get_param("database_names")
        base_time = self.get_param("base_time")
        limit = self.get_param("limit")
        top_n = self.get_param("top_n")
        min_size_bytes = self.get_param("min_size_bytes")

        return Response(
            query_database_size(
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                database_names=database_names,
                base_time=base_time,
                limit=limit,
                top_n=top_n,
                min_size_bytes=min_size_bytes,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 tendbsingle, tendbha, tendbcluster 集群中表的大小。"
                "database_name 可选，传则查询指定库下的表，不传则跨集群下所有库查询符合 table_names 的表。"
                "table_names 传 ['*'] 则查询所有表大小。"
                "tendbcluster 集群会自动将各分片数据汇总，返回的是逻辑表的总大小。"
                "返回的 table_size 单位是字节(bytes)。"
                "limit 按表名字典序截取（默认 50)；top_n 按表大小降序截取，与 limit 互斥；"
                "min_size_bytes 可过滤掉小于该字节数的表。"
            )
        ),
        request_slz=TableSizeInputSerializer,
        response_slz=TableSizeOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_CAPACITY],
        name_prefix="mysql",
    )
    def query_table_size(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        instance_role = self.get_param("instance_role")
        database_name = self.get_param("database_name")
        table_names = self.get_param("table_names")
        base_time = self.get_param("base_time")
        limit = self.get_param("limit")
        top_n = self.get_param("top_n")
        min_size_bytes = self.get_param("min_size_bytes")

        return Response(
            query_table_size(
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                database_name=database_name,
                table_names=table_names,
                base_time=base_time,
                limit=limit,
                top_n=top_n,
                min_size_bytes=min_size_bytes,
            )
        )
