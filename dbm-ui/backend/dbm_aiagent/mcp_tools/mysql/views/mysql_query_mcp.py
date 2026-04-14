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

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, Machine
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    auth_parse_bizs,
    auth_parse_clusters,
    auth_parse_instances,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportMachineTypeException
from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_topo import mysql_cluster_topo
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql import explain_sql
from backend.dbm_aiagent.mcp_tools.mysql.impl.query_trx import query_long_running_trx
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_create_table import show_create_table
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_engine_status import show_engine_status
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_priv_template import show_biz_mysql_privilege_template
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_processlist import show_mysql_processlist, show_proxy_processlist
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_status import mysql_show_slave_status, show_instance_status
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_variables import show_instance_variables
from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_topo import (
    MySQLClusterTopoInputSerializer,
    MySQLClusterTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.explain_sql import (
    ExplainSQLInputSerializer,
    ExplainSQLOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.query_trx import QueryLongRunningTrxOutputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.show_create_table import (
    ShowCreateTableInputSerializer,
    ShowCreateTableOutputSerializer,
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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
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
        description=str(_("""查询实例运行时参数, 执行 show global variables，返回所有变量""")),
        request_slz=ShowInstanceVariablesInputSerializer,
        response_slz=ShowInstanceVariablesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_runtime_variables(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_runtime_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_slave_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_bizs,
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

    @mcp_tools_api_decorator(
        description=str(_("查询 MySQL 实例进程列表，返回原始 processlist 信息.")),
        request_slz=ShowInstanceProcessListInputSerializer,
        response_slz=ShowMySQLInstanceProcessListOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY, DBMMcpTools.MYSQL_METRICS],
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_mysql_processlist(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_proxy_processlist(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

        return Response(
            {
                "processlist": show_proxy_processlist(
                    bk_cloud_id=machine_obj.bk_cloud_id,
                    address=address,
                ),
            }
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 mysql 长事务，事务未关闭，当前可能正在执行 SQL，也可能 Sleep 未提交")),
        request_slz=ShowInstanceProcessListInputSerializer,
        response_slz=QueryLongRunningTrxOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_QUERY],
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def trx_long_running(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_global_variables_with_names(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        names = self.get_param("variable_names")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_global_status_with_names(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        names = self.get_param("status_names")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)

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
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_instances,
        name_prefix="mysql_query",
    )
    def show_instance_engine_status(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        address = self.get_param("address")
        engine = self.get_param("engine")

        machine_obj = _validate_and_get_machine(bk_cloud_id, address)
        return Response(show_engine_status(bk_cloud_id, address, engine, machine_obj.machine_type))


def _validate_and_get_machine(bk_cloud_id: int | None, address: str) -> Machine:
    """验证并获取机器对象"""
    ip, port = address.split(":")
    machine_q = Machine.objects.filter(ip=ip)

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
