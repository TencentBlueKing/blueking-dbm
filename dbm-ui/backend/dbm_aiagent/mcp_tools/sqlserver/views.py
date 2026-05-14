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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.blocking_sessions import sqlserver_blocking_sessions
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.cluster_topo import sqlserver_cluster_topo
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.explain_sql import sqlserver_explain_sql
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis import (
    sqlserver_get_index_fragmentation,
    sqlserver_get_index_usage_stats,
    sqlserver_get_table_indexes,
    sqlserver_get_table_schema,
    sqlserver_get_table_stats,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.instance_summary import sqlserver_instance_summary
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.list_databases import sqlserver_list_databases
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.list_table_status import sqlserver_list_table_status
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.server_config_summary import sqlserver_server_config_summary
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.slow_log_query import sqlserver_slow_log_query
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.top_requests import sqlserver_top_requests
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.wait_stats_snapshot import sqlserver_wait_stats_snapshot
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.blocking_sessions import (
    SQLServerBlockingSessionsInputSerializer,
    SQLServerBlockingSessionsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.cluster_topo import (
    SQLServerTopoInputSerializer,
    SQLServerTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.explain_sql import (
    SQLServerExplainSQLInputSerializer,
    SQLServerExplainSQLOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis import (
    SQLServerIndexFragmentationInputSerializer,
    SQLServerIndexFragmentationOutputSerializer,
    SQLServerIndexUsageStatsInputSerializer,
    SQLServerIndexUsageStatsOutputSerializer,
    SQLServerTableIndexesInputSerializer,
    SQLServerTableIndexesOutputSerializer,
    SQLServerTableSchemaInputSerializer,
    SQLServerTableSchemaOutputSerializer,
    SQLServerTableStatsInputSerializer,
    SQLServerTableStatsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.instance_summary import (
    SQLServerInstanceSummaryInputSerializer,
    SQLServerInstanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.list_databases import (
    SQLServerListDatabasesInputSerializer,
    SQLServerListDatabasesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.list_table_status import (
    SQLServerListTableStatusInputSerializer,
    SQLServerListTableStatusOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.server_config_summary import (
    SQLServerServerConfigSummaryInputSerializer,
    SQLServerServerConfigSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.slow_log_query import (
    SQLServerSlowLogQueryInputSerializer,
    SQLServerSlowLogQueryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.top_requests import (
    SQLServerTopRequestsInputSerializer,
    SQLServerTopRequestsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.wait_stats_snapshot import (
    SQLServerWaitStatsSnapshotInputSerializer,
    SQLServerWaitStatsSnapshotOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission


class SqlserverMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 集群拓扑结构")),
        request_slz=SQLServerTopoInputSerializer,
        response_slz=SQLServerTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def cluster_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        return Response(sqlserver_cluster_topo(cluster_domain=cluster_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 实例基础信息（版本、Edition、CPU、内存、启动时间等）；" "address 不传时返回集群内所有实例的信息")),
        request_slz=SQLServerInstanceSummaryInputSerializer,
        response_slz=SQLServerInstanceSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def instance_summary(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        return Response(sqlserver_instance_summary(cluster_domain=cluster_domain, address=address))

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 实例上的数据库清单（含状态、恢复模式、兼容级别、大小）；" "address 不传时返回集群内所有实例的清单")),
        request_slz=SQLServerListDatabasesInputSerializer,
        response_slz=SQLServerListDatabasesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def list_databases(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        order_by = self.get_param("order_by")
        order = self.get_param("order")
        return Response(
            sqlserver_list_databases(
                cluster_domain=cluster_domain,
                address=address,
                order_by=order_by,
                order=order,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出 SQLServer 业务库下用户表的状态信息（行数、占用大小、最近活跃、统计过期度）；"
                "用于在精细分析（get_table_schema / get_table_indexes 等）之前先定位值得分析的表；"
                "默认按总占用大小倒序返回前 200 条；address 不传时缺省走 master；"
                "verbose 三态枚举（互斥）：summary（默认）只返回 4 个核心字段（schema_name/"
                "table_name/row_count/total_size_mb），token 友好；detail 返回全部 20 个字段；"
                "count_only 仅统计当前库（叠加过滤后）的用户表总数，不返回明细；"
                "支持 order_by（total_size_mb/row_count/index_size_mb/stats_outdated_count/"
                "last_user_update）+ order（desc/asc）自定义排序，verbose=count_only 时排序参数被忽略；"
                "兼容 SQL Server 2008 ~ 2022"
            )
        ),
        request_slz=SQLServerListTableStatusInputSerializer,
        response_slz=SQLServerListTableStatusOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def list_table_status(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        schema = self.get_param("schema")
        table_name = self.get_param("table_name")
        address = self.get_param("address")
        limit = self.get_param("limit")
        verbose = self.get_param("verbose")
        order_by = self.get_param("order_by")
        order = self.get_param("order")
        return Response(
            sqlserver_list_table_status(
                cluster_domain=cluster_domain,
                dbname=dbname,
                schema=schema,
                table_name=table_name,
                address=address,
                limit=limit,
                verbose=verbose,
                order_by=order_by,
                order=order,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 实例关键配置摘要（白名单内的 sp_configure 选项）；" "address 不传时返回集群内所有实例的配置")),
        request_slz=SQLServerServerConfigSummaryInputSerializer,
        response_slz=SQLServerServerConfigSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def server_config_summary(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        return Response(sqlserver_server_config_summary(cluster_domain=cluster_domain, address=address))

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 当前阻塞会话快照（被阻塞请求 + 阻塞源信息）；" "address 不传时缺省查询 master")),
        request_slz=SQLServerBlockingSessionsInputSerializer,
        response_slz=SQLServerBlockingSessionsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def blocking_sessions(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        top = self.get_param("top")
        return Response(
            sqlserver_blocking_sessions(
                cluster_domain=cluster_domain,
                address=address,
                top=top,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 累计等待统计 TOP N（dm_os_wait_stats，已剔除良性等待）；" "address 不传时缺省查询 master")),
        request_slz=SQLServerWaitStatsSnapshotInputSerializer,
        response_slz=SQLServerWaitStatsSnapshotOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def wait_stats_snapshot(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        top = self.get_param("top")
        return Response(
            sqlserver_wait_stats_snapshot(
                cluster_domain=cluster_domain,
                address=address,
                top=top,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 当前活跃请求 TOP N（按 cpu/duration/reads/writes 排序）；" "address 不传时缺省查询 master")),
        request_slz=SQLServerTopRequestsInputSerializer,
        response_slz=SQLServerTopRequestsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def top_requests(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        top = self.get_param("top")
        order_by = self.get_param("order_by")
        return Response(
            sqlserver_top_requests(
                cluster_domain=cluster_domain,
                address=address,
                top=top,
                order_by=order_by,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 SQLServer 估算执行计划（SHOWPLAN_XML，仅编译不执行）；"
                "仅允许 SELECT / WITH(CTE) 语句的计划分析，"
                "不允许多语句、写操作、DDL、xp_/sp_ 调用、WAITFOR、USE/GO 等；"
                "address 不传时缺省走 master"
            )
        ),
        request_slz=SQLServerExplainSQLInputSerializer,
        response_slz=SQLServerExplainSQLOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def explain_sql(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        query_sql = self.get_param("query_sql")
        address = self.get_param("address")
        return Response(
            sqlserver_explain_sql(
                cluster_domain=cluster_domain,
                dbname=dbname,
                query_sql=query_sql,
                address=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _("查询 SQLServer 慢日志（来源 [Monitor].[dbo].[TRACE_TSQL]）；" "支持按时间范围、库名、最小耗时过滤，address 不传时缺省查询 master")
        ),
        request_slz=SQLServerSlowLogQueryInputSerializer,
        response_slz=SQLServerSlowLogQueryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def slow_log_query(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        address = self.get_param("address")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        database_name = self.get_param("database_name")
        min_duration_ms = self.get_param("min_duration_ms")
        top = self.get_param("top")
        order_by = self.get_param("order_by")
        return Response(
            sqlserver_slow_log_query(
                cluster_domain=cluster_domain,
                address=address,
                start_time=start_time,
                end_time=end_time,
                database_name=database_name,
                min_duration_ms=min_duration_ms,
                top=top,
                order_by=order_by,
            )
        )

    # ============================================================
    # 索引分析功能域（index_analysis）
    #   P0：get_table_schema / get_table_indexes / get_table_stats
    #   P1：get_index_usage_stats / get_index_fragmentation
    # ============================================================

    @mcp_tools_api_decorator(
        description=str(
            _(
                "批量查询 SQLServer 表结构（列、类型、可空、计算列、默认/检查约束、主键、外键）；"
                "tables 一次传 1~20 张表，整批共用同一个 schema；每张表独立返回 status，"
                "单表不存在不会让整批失败；address 不传时缺省走 master"
            )
        ),
        request_slz=SQLServerTableSchemaInputSerializer,
        response_slz=SQLServerTableSchemaOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def get_table_schema(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tables = self.get_param("tables")
        schema = self.get_param("schema")
        address = self.get_param("address")
        return Response(
            sqlserver_get_table_schema(
                cluster_domain=cluster_domain,
                dbname=dbname,
                tables=tables,
                schema=schema,
                address=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "批量查询 SQLServer 表上现有索引清单（含键列、INCLUDE 列、唯一性、是否禁用、"
                "近似行数、压缩状态）；tables 一次传 1~20 张表，整批共用同一个 schema；"
                "每张表独立返回 status；address 不传时缺省走 master"
            )
        ),
        request_slz=SQLServerTableIndexesInputSerializer,
        response_slz=SQLServerTableIndexesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def get_table_indexes(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tables = self.get_param("tables")
        schema = self.get_param("schema")
        address = self.get_param("address")
        return Response(
            sqlserver_get_table_indexes(
                cluster_domain=cluster_domain,
                dbname=dbname,
                tables=tables,
                schema=schema,
                address=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "批量查询 SQLServer 表的统计对象状态（最近更新时间、采样行数、修改行数、是否过期）；"
                "用于诊断执行计划行数估算偏差是否由统计过期引起；"
                "tables 一次传 1~20 张表，整批共用同一个 schema；每张表独立返回 status；"
                "address 不传时缺省走 master"
            )
        ),
        request_slz=SQLServerTableStatsInputSerializer,
        response_slz=SQLServerTableStatsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def get_table_stats(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tables = self.get_param("tables")
        schema = self.get_param("schema")
        address = self.get_param("address")
        return Response(
            sqlserver_get_table_stats(
                cluster_domain=cluster_domain,
                dbname=dbname,
                tables=tables,
                schema=schema,
                address=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "批量查询 SQLServer 表上每个索引的使用画像（user_seek/scan/lookup/update 累计计数）；"
                "用于识别冗余索引或从未使用的索引。计数为实例启动以来累计，"
                "故同时返回 sqlserver_start_time 作为样本起点；"
                "tables 一次传 1~20 张表，整批共用同一个 schema；"
                "每张表独立返回 status；address 不传时缺省走 master"
            )
        ),
        request_slz=SQLServerIndexUsageStatsInputSerializer,
        response_slz=SQLServerIndexUsageStatsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def get_index_usage_stats(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tables = self.get_param("tables")
        schema = self.get_param("schema")
        address = self.get_param("address")
        return Response(
            sqlserver_get_index_usage_stats(
                cluster_domain=cluster_domain,
                dbname=dbname,
                tables=tables,
                schema=schema,
                address=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "批量查询 SQLServer 表上各索引的碎片状态（dm_db_index_physical_stats，LIMITED 模式扫描）；"
                "默认仅返回 page_count >= 1000 的索引（小索引碎片对性能基本无影响）；"
                "用于辅助决策 REORGANIZE / REBUILD；"
                "tables 一次传 1~20 张表，整批共用同一个 schema；每张表独立返回 status；"
                "address 不传时缺省走 master"
            )
        ),
        request_slz=SQLServerIndexFragmentationInputSerializer,
        response_slz=SQLServerIndexFragmentationOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="sqlserver_query",
    )
    def get_index_fragmentation(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tables = self.get_param("tables")
        schema = self.get_param("schema")
        address = self.get_param("address")
        min_page_count = self.get_param("min_page_count")
        return Response(
            sqlserver_get_index_fragmentation(
                cluster_domain=cluster_domain,
                dbname=dbname,
                tables=tables,
                schema=schema,
                address=address,
                min_page_count=min_page_count,
            )
        )
