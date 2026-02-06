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
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, Machine
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpNotSupportClusterTypeException,
    DBMMcpNotSupportMachineTypeException,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_topo import mysql_cluster_topo
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql import explain_sql
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_create_table import show_create_table
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_priv_template import show_biz_mysql_privilege_template
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_processlist import show_cluster_processlist_summary
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_status import mysql_show_slave_status, show_instance_status
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_variables import show_mysql_variables
from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_topo import (
    MySQLClusterTopoInputSerializer,
    MySQLClusterTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.explain_sql import (
    ExplainSQLInputSerializer,
    ExplainSQLOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_create_table import (
    ShowCreateTableInputSerializer,
    ShowCreateTableOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_priv_template import (
    ShowBizMySQLPrivilegeTemplateInputSerializer,
    ShowBizMySQLPrivilegeTemplateOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_processlist import (
    ShowClusterProcessListSummaryInputSerializer,
    ShowClusterProcessListSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_status import (
    ShowInstanceSlaveStatusInputSerializer,
    ShowInstanceStatuesOutputSerializer,
    ShowInstanceStatusesInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_variables import (
    ShowMySQLVariablesInputSerializer,
    ShowMySQLVariablesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import MySQLProcessListInstanceGroupType
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission

logger = logging.getLogger("root")


class MySQLQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的表结构")),
        request_slz=ShowCreateTableInputSerializer,
        response_slz=ShowCreateTableOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_query",
    )
    def show_create_table(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        db_name = self.get_param("db_name")
        table_name = self.get_param("table_name")

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        return Response(
            show_create_table(
                cluster_type=cluster_obj.cluster_type,
                cluster_domain=cluster_domain,
                dbname=db_name,
                tablename=table_name,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 SQL 执行计划")),
        request_slz=ExplainSQLInputSerializer,
        response_slz=ExplainSQLOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_query",
    )
    def explain_sql(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        db_name = self.get_param("db_name")
        query_sql = self.get_param("query_sql")

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

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
        name_prefix="mysql_query",
    )
    def mysql_cluster_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

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
                """查询集群连接摘要
不要隐藏聚合结果, 按下面的格式展示
# 接入层摘要 (如果不为空)
二级标题是各项统计项
# 存储摘要
二级标题是各项统计项"""
            )
        ),
        request_slz=ShowClusterProcessListSummaryInputSerializer,
        response_slz=ShowClusterProcessListSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_cluster_processlist_summary(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        instance_group = MySQLProcessListInstanceGroupType.MasterGroup.value

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        if cluster_obj.cluster_type not in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_obj.cluster_type)

        if (
            cluster_obj.cluster_type == ClusterType.TenDBSingle
            and instance_group == MySQLProcessListInstanceGroupType.SlaveGroup
        ):
            return Response({"msg": "TenDBSingle 集群没有从库，无法查询从库连接摘要"})

        summary = show_cluster_processlist_summary(cluster_obj, instance_group)

        return Response(summary)

    @mcp_tools_api_decorator(
        description=str(_("""查询 MySQL 常见运行时参数, 执行 show global variables""")),
        request_slz=ShowMySQLVariablesInputSerializer,
        response_slz=ShowMySQLVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_mysql_popular_runtime_variables(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        variable_hints = self.get_param("variable_hints")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

        return Response(
            {
                **show_mysql_variables(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    machine_type=machine_obj.machine_type,
                    variable_hints=variable_hints,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询实例常见运行时状态, 执行 show global status""")),
        request_slz=ShowInstanceStatusesInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_instance_popular_runtime_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        status_hints = self.get_param("status_hints")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

        return Response(
            {
                **show_instance_status(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                    machine_type=machine_obj.machine_type,
                    status_hints=status_hints,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询实例主从同步状态, 执行 show slave status""")),
        request_slz=ShowInstanceSlaveStatusInputSerializer,
        response_slz=ShowInstanceStatuesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_instance_slave_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

        return Response(
            {
                "runtime_status": mysql_show_slave_status(bk_cloud_id=machine_obj.bk_cloud_id, address=address),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询业务 TenDBSingle, TenDBHA ,TenDBCluster 类型的权限模版""")),
        request_slz=ShowBizMySQLPrivilegeTemplateInputSerializer,
        response_slz=ShowBizMySQLPrivilegeTemplateOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        name_prefix="mysql_query",
    )
    def show_biz_mysql_privilege_template(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_type = self.get_param("cluster_type")

        return Response(
            {
                "privilege_templates": show_biz_mysql_privilege_template(
                    bk_biz_id=bk_biz_id, cluster_type=cluster_type
                ),
            }
        )


def _validate_and_get_machine(bk_cloud_id: int | None, address: str) -> Machine:
    """验证并获取机器对象"""
    ip, port = address.split(":")
    machine_q = Machine.objects.filter(ip=ip)

    if not machine_q.exists():
        raise ObjectDoesNotExist(f"机器{ip}不存在")

    if machine_q.count() > 1:
        if not bk_cloud_id:
            raise ValueError("机器IP不唯一, 请指定 bk_cloud_id")
        machine_q = machine_q.filter(bk_cloud_id=bk_cloud_id)

    machine_obj = machine_q.get()

    if machine_obj.machine_type not in [
        MachineType.SINGLE,
        MachineType.BACKEND,
        MachineType.REMOTE,
        MachineType.SPIDER,
    ]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_obj.machine_type)

    return machine_obj
