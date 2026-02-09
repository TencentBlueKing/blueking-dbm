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

from backend.dbm_aiagent.agent.commands import MysqlSlowSqlTunerCommand
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_slowlog import query_slow_log_detail, query_slow_logs_by_metric
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_slowlog import (
    MysqlOneSlowlogInputSerializer,
    MysqlSlowlogInputSerializer,
    MysqlSlowlogOutputSerializer,
    MysqlSlowTunerInputSerializer,
    MysqlSlowTunerOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission

logger = logging.getLogger("root")


class MySQLSlowlogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "获取 tendbsingle, tendbha, tendbcluster 集群的慢查询统计信息。返回的 slow_logs 结果里面字段解读如下：\n"
                "query_digest_md5: 是慢日志摘要字段的 MD5 值，也叫 digest 或者 query_digest;\n"
                "metric_aggregate_type: 是慢查询的聚合统计方法，比如按查执行耗时排序(max by query_time), "
                "按执行次数取总和排序(count by query_digest_md5)，按扫描行数总和排序(sum by rows_examined)\n"
                "values: 聚合的结果，具体含义根据 metric_aggregate_type 来定\n"
                "sample: 对应的一个慢 sql 样例，里面有详细信息，比如 sql指纹，sql 原文，扫描行数等"
            )
        ),
        request_slz=MysqlSlowlogInputSerializer,
        response_slz=MysqlSlowlogOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_slowlog",
    )
    def query_slow_logs_aggregated(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
        # cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        instance_role = self.get_param("instance_role")
        metric_name = self.get_param("metric_name")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")

        return Response(
            query_slow_logs_by_metric(
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                start_time=start_time,
                end_time=end_time,
                metric_name=metric_name,
                limit=limit,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "根据 query_digest 获取 mysql 某一条慢查询详情。返回的 slow_logs 结果里面字段解读如下：\n"
                "query_digest_text: 是慢日志摘要文本，也叫 digest_text 或者 fingerprint;\n"
                "query_digest_md5: 是慢日志摘要字段的 MD5 值，也叫 digest 或者 query_digest;\n"
                "sql_text: 是慢日志的原始 SQL 文本，如果提到 sql 详情，或者 sql原文，指的就是这个字段;\n"
                "db_name: 是慢日志涉及的数据库名;\n"
                "table_name: 是慢日志涉及的表名;\n"
                "rows_examined: 是慢日志扫描的行数，也叫 rows_scan;\n"
            )
        ),
        request_slz=MysqlOneSlowlogInputSerializer,
        response_slz=MysqlSlowlogOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_slowlog",
    )
    def query_one_slow_log_detail(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        query_digest_md5 = self.get_param("query_digest_md5")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")

        return Response(
            query_slow_log_detail(
                cluster_domain=cluster_domain,
                query_digest_md5=query_digest_md5,
                start_time=start_time,
                end_time=end_time,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "分析某一条慢查询，返回优化建议。慢查询可以传入 sql_text 或者 query_digest_md5"
                "会自动从 db 集群上获取表结构和查询计划，进行什么分析，并给出表结构或者 sql 的优化改造建议"
            )
        ),
        request_slz=MysqlSlowTunerInputSerializer,
        response_slz=MysqlSlowTunerOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_slowlog",
    )
    def sql_tune(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        db_name = self.get_param("db_name")
        sql_text = self.get_param("sql_text")
        query_digest_md5 = self.get_param("query_digest_md5")

        try:
            result = AgentHandler.ask_agent_with_command(
                command=MysqlSlowSqlTunerCommand.command,
                username="admin",
                command_params={
                    "sql_text": sql_text,
                    "query_digest_md5": query_digest_md5,
                    "cluster_domain": cluster_domain,
                    "db_name": db_name,
                },
            )
        except Exception as e:
            logger.error(f"sql_tune error: {e}")
            return Response({"error": str(e)})

        return Response(result)
