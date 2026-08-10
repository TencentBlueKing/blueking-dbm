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

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    auth_parse_bizs,
    auth_parse_clusters,
    auth_parse_instances,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpClusterNotFoundException,
    DBMMcpNotSupportClusterTypeException,
    DBMMcpNotSupportMachineTypeException,
)
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.helpers.assert_clustertype import assert_cluster_type
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import cluster_runtime_variables
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_topo import mysql_cluster_topo
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_variable_diff import (
    tendbcluster_variable_diff as tendbcluster_variable_diff_impl,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_variable_diff import (
    tendbha_master_slave_variable_diff as tendbha_master_slave_variable_diff_impl,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql import explain_sql
from backend.dbm_aiagent.mcp_tools.mysql.impl.get_table_partition_conf import (
    get_table_partition_conf as get_table_partition_conf_impl,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.query_cluster_skew_data import query_cluster_skew_data
from backend.dbm_aiagent.mcp_tools.mysql.impl.query_table_data_free import query_table_data_free
from backend.dbm_aiagent.mcp_tools.mysql.impl.query_trx import query_long_running_trx
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_binlog_events import show_binlog_events as run_show_binlog_events
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_binlog_events import (
    show_relaylog_events as run_show_relaylog_events,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_create_table import show_create_table
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_databases_with_patterns import show_databases_with_patterns
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_engine_status import show_engine_status
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_priv_template import show_biz_mysql_privilege_template
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_processlist import (
    aggregate_processlist_by_type,
    show_instance_processlist,
    show_mysql_processlist,
    show_proxy_processlist,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_status import mysql_show_slave_status, show_instance_status
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_variables import show_instance_variables
from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_runtime_variables import (
    MySQLClusterRuntimeVariablesInputSerializer,
    MySQLClusterRuntimeVariablesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_topo import (
    MySQLClusterTopoInputSerializer,
    MySQLClusterTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_variable_diff import (
    TenDBClusterVariableDiffInputSerializer,
    TenDBClusterVariableDiffOutputSerializer,
    TenDBHAMasterSlaveVariableDiffInputSerializer,
    TenDBHAMasterSlaveVariableDiffOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.explain_sql import (
    ExplainSQLInputSerializer,
    ExplainSQLOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.get_table_partition_conf import (
    GetTablePartitionConfInputSerializer,
    GetTablePartitionConfOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.query_cluster_skew_data import (
    QueryClusterSkewDataInputSerializer,
    QueryClusterSkewDataOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.query_table_data_free import (
    QueryTableDataFreeInputSerializer,
    QueryTableDataFreeOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.query_trx import QueryLongRunningTrxOutputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_binlog_events import (
    ShowBinlogEventsInputSerializer,
    ShowBinlogEventsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_create_table import (
    ShowCreateTableInputSerializer,
    ShowCreateTableOutputSerializer,
    ShowCreateTablesInputSerializer,
    ShowCreateTablesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_databases_with_patterns import (
    ShowDatabasesWithPatternsInputSerializer,
    ShowDatabasesWithPatternsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_engine_status import (
    ShowInstanceEngineStatusInputSerializer,
    ShowInstanceEngineStatusOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_priv_template import (
    ShowBizMySQLPrivilegeTemplateInputSerializer,
    ShowBizMySQLPrivilegeTemplateOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_processlist import (
    ShowInstanceProcessListAggregatedInputSerializer,
    ShowInstanceProcessListAggregatedOutputSerializer,
    ShowInstanceProcessListInputSerializer,
    ShowMySQLInstanceProcessListOutputSerializer,
    ShowProxyProcessListOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_status import (
    ShowInstanceSlaveStatusInputSerializer,
    ShowInstanceStatuesOutputSerializer,
    ShowInstanceStatusesInputSerializer,
    ShowStatusNamesInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_variables import (
    ShowInstanceVariablesInputSerializer,
    ShowInstanceVariablesOutputSerializer,
    ShowVariablesNamesInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission, McpDBManagePermission, McpIsDbaPermission

logger = logging.getLogger("root")


class MySQLQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的表结构")),
        request_slz=ShowCreateTableInputSerializer,
        response_slz=ShowCreateTableOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_query",
    )
    def show_create_table(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        db_name = self.get_param("db_name")
        table_name = self.get_param("table_name")

        cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "create_sql": show_create_table(
                    cluster_type=cluster_obj.cluster_type,
                    cluster_domain=cluster_domain,
                    dbname=db_name,
                    tablename=table_name,
                )
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的表结构，可同时获取多个表的结构")),
        request_slz=ShowCreateTablesInputSerializer,
        response_slz=ShowCreateTablesOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_query",
    )
    def show_create_tables(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        table_names = self.get_param("table_names")

        cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        create_sql_list = []
        for table_name in table_names:
            create_sql_list.append(
                {
                    "table_name": table_name,
                    "create_sql": show_create_table(
                        cluster_type=cluster_obj.cluster_type,
                        cluster_domain=cluster_domain,
                        dbname="",
                        tablename=table_name,
                    ),
                }
            )

        return Response(create_sql_list)

    @mcp_tools_api_decorator(
        description=str(_("查询 SQL 执行计划")),
        request_slz=ExplainSQLInputSerializer,
        response_slz=ExplainSQLOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_query",
    )
    def explain_sql(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        db_name = self.get_param("db_name")
        query_sql = self.get_param("query_sql")

        cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            explain_sql(
                cluster_type=cluster_obj.cluster_type,
                cluster_domain=cluster_domain,
                dbname=db_name,
                query_sql=query_sql,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 TenDBSingle, TenDBHA, TenDBCluster 集群拓扑结构")),
        request_slz=MySQLClusterTopoInputSerializer,
        response_slz=MySQLClusterTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="mysql_query",
    )
    def mysql_cluster_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "bk_biz_id": cluster_obj.bk_biz_id,
                "region": cluster_obj.region,
                "tolerance_level": cluster_obj.disaster_tolerance_level,
                "time_zone": cluster_obj.time_zone,
                **mysql_cluster_topo(cluster_obj=cluster_obj),
            }
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询集群所有角色实例的运行时核心配置, 带版本信息; 各实例另含 datadir、data_dir_mount。"
                "已过滤目录/路径类、ssl_*、report_*、myisam_*、performance_schema_*、InnoDB 低价值项;"
                "Spider 另裁 innodb_/slave_/relay_log/replicate_/rpl_semi_sync;"
                "存储层 default_storage_engine 非 InnoDB 时裁全部 innodb_*。"
            )
        ),
        request_slz=MySQLClusterRuntimeVariablesInputSerializer,
        response_slz=MySQLClusterRuntimeVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="mysql_query",
    )
    def cluster_runtime_variables(self, request, *args, **kwargs):
        cluster_id = self.get_param("cluster_id")
        cluster_domain = self.get_param("cluster_domain")

        try:
            if cluster_id is not None:
                cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(id=cluster_id)
            else:
                cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
        except Cluster.DoesNotExist:
            if cluster_id is not None:
                raise DBMMcpClusterNotFoundException(msg=_("集群 id={} 不存在").format(cluster_id))
            raise DBMMcpClusterNotFoundException(msg=_("集群域名 {} 不存在").format(cluster_domain))
        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "cluster_type": cluster_obj.cluster_type,
                **cluster_runtime_variables(cluster_obj=cluster_obj),
            }
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "对比 TenDBHA 集群 master 与 standby slave 的运行时核心参数差异。"
                "一主多从时仅比较 is_stand_by=True 的从库，普通 slave 不参与对比。"
                "已跳过天然不同参数（如 server_id/read_only 等）及可配置忽略键/前缀；"
                "无差异时 replication_pairs 为空列表。cluster_id 与 cluster_domain 二选一。"
            )
        ),
        request_slz=TenDBHAMasterSlaveVariableDiffInputSerializer,
        response_slz=TenDBHAMasterSlaveVariableDiffOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="mysql_query",
    )
    def tendbha_master_slave_variable_diff(self, request, *args, **kwargs):
        cluster_obj = _resolve_cluster_from_params(self.get_param("cluster_id"), self.get_param("cluster_domain"))
        assert_cluster_type(cluster_obj, [ClusterType.TenDBHA])
        return Response(tendbha_master_slave_variable_diff_impl(cluster_obj=cluster_obj))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "对比 TenDBCluster 集群：仅 spider_master 版本摘要与组内参数差异，"
                "以及分片 remote 主从参数差异；不采集 spider_slave。"
                "返回紧凑结构：spider_version.by_version、spider_groups[].mismatches[].by_value、"
                "shard_pairs mismatches 使用 master_value/slave_value；无差异时列表为空。"
                "cluster_id 与 cluster_domain 二选一。"
            )
        ),
        request_slz=TenDBClusterVariableDiffInputSerializer,
        response_slz=TenDBClusterVariableDiffOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="mysql_query",
    )
    def tendbcluster_variable_diff(self, request, *args, **kwargs):
        cluster_obj = _resolve_cluster_from_params(self.get_param("cluster_id"), self.get_param("cluster_domain"))
        assert_cluster_type(cluster_obj, [ClusterType.TenDBCluster])
        return Response(tendbcluster_variable_diff_impl(cluster_obj=cluster_obj))

    @mcp_tools_api_decorator(
        description=str(_("""查询实例运行时参数, 执行 show global variables，返回所有变量""")),
        request_slz=ShowInstanceVariablesInputSerializer,
        response_slz=ShowInstanceVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_runtime_variables(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                **show_instance_variables(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    machine_type=machine_obj.machine_type,
                    names=[],
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询实例运行时状态, 执行 show global status，返回所有值""")),
        request_slz=ShowInstanceStatusesInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_runtime_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                **show_instance_status(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    machine_type=machine_obj.machine_type,
                    names=[],
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询实例主从同步状态, 执行 show slave status""")),
        request_slz=ShowInstanceSlaveStatusInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_slave_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "runtime_statuses": mysql_show_slave_status(bk_cloud_id=machine_obj.bk_cloud_id, address=address),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询业务 TenDBSingle, TenDBHA ,TenDBCluster 类型的权限模版""")),
        request_slz=ShowBizMySQLPrivilegeTemplateInputSerializer,
        response_slz=ShowBizMySQLPrivilegeTemplateOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        name_prefix="mysql_query",
    )
    def show_biz_mysql_privilege_template(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_type = self.get_param("cluster_type")
        if cluster_type not in [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA]:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)

        return Response(
            {
                "privilege_templates": show_biz_mysql_privilege_template(
                    bk_biz_id=bk_biz_id, cluster_type=cluster_type
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 MySQL 实例进程列表，返回原始 processlist 信息.")),
        request_slz=ShowInstanceProcessListInputSerializer,
        response_slz=ShowMySQLInstanceProcessListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_mysql_processlist(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "processlist": show_mysql_processlist(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    # machine_type=machine_obj.machine_type,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 mysql-proxy 即 Proxy 进程列表，返回原始 processlist 信息")),
        request_slz=ShowInstanceProcessListInputSerializer,
        response_slz=ShowProxyProcessListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_proxy_processlist(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "processlist": show_proxy_processlist(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询 mysql 某个实例连接情况, 返回是按照 aggregate_type 聚合 processlist 的结果，不是 processlist 原始信息""")),
        request_slz=ShowInstanceProcessListAggregatedInputSerializer,
        response_slz=ShowInstanceProcessListAggregatedOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_METRICS],
        name_prefix="mysql_query",
    )
    def show_instance_processlist_aggregated(self, request, *args, **kwargs):
        instance = self.get_param("instance")
        aggregate_types = self.get_param("aggregate_type")
        # 根据 instance(ip:port) 反查集群，instance 可能是存储层实例，也可能是接入层实例
        ip, port = instance.split(":")

        machine: Machine = Machine.objects.using(MYSQL_MCP_DB_READ).filter(ip=ip).first()
        assert_cluster_type(machine, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        instance_obj = ProxyInstance.objects.using(MYSQL_MCP_DB_READ).filter(machine__ip=ip, port=int(port)).first()
        if not instance_obj:
            instance_obj = (
                StorageInstance.objects.using(MYSQL_MCP_DB_READ).filter(machine__ip=ip, port=int(port)).first()
            )

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

    @mcp_tools_api_decorator(
        description=str(_("查询 mysql 长事务，事务未关闭，当前可能正在执行 SQL，也可能 Sleep 未提交")),
        request_slz=ShowInstanceProcessListInputSerializer,
        response_slz=QueryLongRunningTrxOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def trx_long_running(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                "long_running_trx": query_long_running_trx(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询指定的 MySQL 参数,
        执行 show global variables where Variable_name in.
        variable_names 参数值大小写敏感, 不会对 variable_names 存在性校验, 非法值不会返回对应的结果"""
            )
        ),
        request_slz=ShowVariablesNamesInputSerializer,
        response_slz=ShowInstanceVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_global_variables_with_names(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        names = self.get_param("variable_names")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                **show_instance_variables(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    machine_type=machine_obj.machine_type,
                    names=names,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """查询指定名字 mysql 实例状态值,
        执行 show global status where Variable_name in.
        status_names 参数值大小写敏感, 不会对 status_names 存在性校验, 非法值不会返回对应的结果"""
            )
        ),
        request_slz=ShowStatusNamesInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_global_status_with_names(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        names = self.get_param("status_names")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            {
                **show_instance_status(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    machine_type=machine_obj.machine_type,
                    names=names,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询实例特定引擎状态""")),
        request_slz=ShowInstanceEngineStatusInputSerializer,
        response_slz=ShowInstanceEngineStatusOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_engine_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        engine = self.get_param("engine")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(show_engine_status(bk_cloud_id, address, engine, machine_obj.machine_type))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """在实例上执行 SHOW BINLOG EVENTS, 支持可选的 IN 日志名、FROM 位点、LIMIT; """
                """limit 行数最大 100(由 limit_row_count 指定, 与可选的 limit_offset 共同组成 LIMIT)"""
            )
        ),
        request_slz=ShowBinlogEventsInputSerializer,
        response_slz=ShowBinlogEventsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_binlog_events(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        log_name = self.get_param("log_name")
        from_pos = self.get_param("from_pos")
        limit_offset = self.get_param("limit_offset")
        limit_row_count = self.get_param("limit_row_count")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            run_show_binlog_events(
                bk_cloud_id=machine_obj.bk_cloud_id,
                address=address,
                machine_type=machine_obj.machine_type,
                log_name=log_name,
                from_pos=from_pos,
                limit_offset=limit_offset,
                limit_row_count=limit_row_count,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """在实例上执行 SHOW RELAYLOG EVENTS, 支持可选的 IN 日志名、FROM 位点、LIMIT; """
                """limit 行数最大 100(由 limit_row_count 指定, 与可选的 limit_offset 共同组成 LIMIT)。"""
                """仅支持有 relay log 的从库实例。"""
            )
        ),
        request_slz=ShowBinlogEventsInputSerializer,
        response_slz=ShowBinlogEventsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_relaylog_events(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        log_name = self.get_param("log_name")
        from_pos = self.get_param("from_pos")
        limit_offset = self.get_param("limit_offset")
        limit_row_count = self.get_param("limit_row_count")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        assert_cluster_type(machine_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            run_show_relaylog_events(
                bk_cloud_id=machine_obj.bk_cloud_id,
                address=address,
                machine_type=machine_obj.machine_type,
                log_name=log_name,
                from_pos=from_pos,
                limit_offset=limit_offset,
                limit_row_count=limit_row_count,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 MySQL 表空洞碎片（information_schema.tables.data_free）。"
                "仅返回空洞大于 10GB 的表，按 data_free 降序排列。"
                "TenDBCluster 会分别查询各 remote slave 分片后按逻辑库表汇聚。"
                "cluster_id 与 cluster_domain 二选一。"
            )
        ),
        request_slz=QueryTableDataFreeInputSerializer,
        response_slz=QueryTableDataFreeOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="mysql_query",
    )
    def query_table_data_free(self, request, *args, **kwargs):
        cluster_id = self.get_param("cluster_id")
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname") or ""
        table_names = self.get_param("table_names")

        if cluster_id is not None:
            cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(id=cluster_id)
        else:
            cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)

        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBCluster, ClusterType.TenDBHA])

        return Response(
            query_table_data_free(
                cluster_id=cluster_obj.id,
                dbname=dbname,
                table_names=table_names,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("根据库名正则模式查询集群的数据库列表")),
        request_slz=ShowDatabasesWithPatternsInputSerializer,
        response_slz=ShowDatabasesWithPatternsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_databases_with_patterns(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        dbs = self.get_param("dbs")
        ignore_dbs = self.get_param("ignore_dbs")

        return Response(
            show_databases_with_patterns(
                cluster_domain=cluster_domain,
                dbs=dbs,
                ignore_dbs=ignore_dbs,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询集群给定时间段内的倾斜事件段。"
                "返回 has_skew、episodes（metric/role/pattern/start/end/group_mean/hot_nodes/cold_nodes/transitions）。"
                "hot_nodes/cold_nodes 含 value、mean、pct、abs_dev；低绝对值倾斜在查询侧过滤；"
                "pattern 仅看高于均值的节点集合是否随时间切换：fixed 或 migrating。"
            )
        ),
        request_slz=QueryClusterSkewDataInputSerializer,
        response_slz=QueryClusterSkewDataOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def query_cluster_skew_data(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        from_date = self.get_param("from_date").astimezone(timezone.utc)
        to_date = self.get_param("to_date").astimezone(timezone.utc)

        cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(
            immute_domain=cluster_domain, cluster_type__in=[ClusterType.TenDBHA, ClusterType.TenDBCluster]
        )

        return Response(
            query_cluster_skew_data(
                cluster_obj=cluster_obj,
                from_date=from_date,
                to_date=to_date,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询单表分区 v2 配置及实例侧表结构（tendbha / tendbsingle）")),
        request_slz=GetTablePartitionConfInputSerializer,
        response_slz=GetTablePartitionConfOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def get_table_partition_conf(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        db_name = self.get_param("db_name")
        table_name = self.get_param("table_name")

        cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
        assert_cluster_type(cluster_obj, [ClusterType.TenDBSingle, ClusterType.TenDBHA])

        return Response(
            get_table_partition_conf_impl(
                cluster_domain=cluster_domain,
                db_name=db_name,
                table_name=table_name,
            )
        )


def _resolve_cluster_from_params(cluster_id, cluster_domain) -> Cluster:
    """解析 cluster_id / cluster_domain（二选一），不存在时抛 DBMMcpClusterNotFoundException。"""
    try:
        if cluster_id is not None:
            return Cluster.objects.using(MYSQL_MCP_DB_READ).get(id=cluster_id)
        return Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        if cluster_id is not None:
            raise DBMMcpClusterNotFoundException(msg=_("集群 id={} 不存在").format(cluster_id))
        raise DBMMcpClusterNotFoundException(msg=_("集群域名 {} 不存在").format(cluster_domain))


def _validate_and_get_machine(bk_cloud_id: int | None, address: str) -> Machine:
    """验证并获取机器对象"""
    ip, port = address.split(":")
    machine_q = Machine.objects.using(MYSQL_MCP_DB_READ).filter(ip=ip)

    if not machine_q.exists():
        raise ObjectDoesNotExist(f"机器{ip}不存在")

    if machine_q.count() > 1:
        if bk_cloud_id is None:
            raise ValueError("Machine IP is not unique, please specify bk_cloud_id")
        machine_q = machine_q.filter(bk_cloud_id=bk_cloud_id)

    machine_obj = machine_q.get()

    if machine_obj.machine_type not in [
        MachineType.SINGLE,
        MachineType.BACKEND,
        MachineType.REMOTE,
        MachineType.SPIDER,
        MachineType.PROXY,
    ]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_obj.machine_type)

    return machine_obj
