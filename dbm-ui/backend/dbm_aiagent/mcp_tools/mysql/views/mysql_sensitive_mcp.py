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
from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, Spec
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_instances
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.serializers.kill_connection import KillConnectionInputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.modify_cluster_spec import (
    ModifyMySQLClusterSpecOutputSerializer,
    ModifyTenDBClusterSpecInputSerializer,
    ModifyTenDBHASpecInputSerializer,
    ModifyTenDBSingleSpecInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission, McpIsDbaPermission


class MySQLSensitiveMcpViewSet(McpToolsViewSet):
    """
    MySQL敏感操作
    """

    @mcp_tools_api_decorator(
        description=str(_("""杀死 MySQL 实例上的指定连接""")),
        request_slz=KillConnectionInputSerializer,
        response_slz=KillConnectionInputSerializer,
        permission_classes=[McpClusterDetailPermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_SENSITIVE],
        name_prefix="mysql_sensitive",
        enable_callee_plan=True,
    )
    def kill_connection(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        connection_id = self.get_param("connection_id")
        address = self.get_param("address")

        drs_raw_res = DRSApi.v2_mysql_rpc(
            params={
                "bk_cloud_id": bk_cloud_id,
                "addresses": [address],
                "cmds": [f"KILL {connection_id}"],
                "query_timeout": 10,
            }
        )

        address_res = drs_raw_res[0]
        if address_res["error_msg"]:
            raise DBMMcpBaseException(msg=address_res["error_msg"])

        cmd_res = address_res["cmd_results"][0]
        if cmd_res["error_msg"]:
            raise DBMMcpBaseException(msg=cmd_res["error_msg"])

        return Response({"bk_cloud_id": bk_cloud_id, "address": address, "connection_id": connection_id})

    @mcp_tools_api_decorator(
        description=str(_("""修改 TenDBHA 集群规格, 只能修改 proxy 和 standby backend""")),
        request_slz=ModifyTenDBHASpecInputSerializer,
        response_slz=ModifyMySQLClusterSpecOutputSerializer,
        permission_classes=[McpClusterDetailPermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_SENSITIVE],
        name_prefix="mysql_sensitive",
        enable_callee_plan=True,
    )
    def modify_tendbha_spec(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        # 对于 TenDBHA, 这个 role 其实是 machine_type [proxy, backend]
        role = self.get_param("role")
        spec_id = self.get_param("spec_id")

        new_spec = Spec.objects.get(spec_id=spec_id)

        cluster_obj = Cluster.objects.get(cluster_type=ClusterType.TenDBHA, immute_domain=cluster_domain)

        if role == MachineType.PROXY:
            for ins in cluster_obj.proxyinstance_set.all():
                ins.machine.spec_id = new_spec.spec_id
                ins.machine.spec_config = new_spec.get_spec_info()
                ins.machine.save()
        elif role == MachineType.BACKEND:
            if cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_REPEATER).exists():
                raise DBMMcpBaseException(msg="can't modify backend spec during migration")

            for ins in cluster_obj.storageinstance_set.filter(
                is_stand_by=True, instance_role__in=[InstanceRole.BACKEND_MASTER, InstanceRole.BACKEND_SLAVE]
            ):
                ins.machine.spec_id = new_spec.spec_id
                ins.machine.spec_config = new_spec.get_spec_info()
                ins.machine.save()
        else:
            raise DBMMcpBaseException(msg=f"{role} is not valid machine type for tendbha cluster")

        return Response({"spec_id": new_spec.spec_id, "spec_config": new_spec.get_spec_info()})

    @mcp_tools_api_decorator(
        description=str(_("""修改 TenDBCluster 集群规格, 只能修改 spider_master, spider_slave, remote""")),
        request_slz=ModifyTenDBClusterSpecInputSerializer,
        response_slz=ModifyMySQLClusterSpecOutputSerializer,
        permission_classes=[McpClusterDetailPermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_SENSITIVE],
        name_prefix="mysql_sensitive",
        enable_callee_plan=True,
    )
    def modify_tendbcluster_spec(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        # 对于 TenDBCluster, 这个 role 是 [spider_master, spider_slave, remote]
        role = self.get_param("role")
        spec_id = self.get_param("spec_id")

        new_spec = Spec.objects.get(spec_id=spec_id)

        cluster_obj = Cluster.objects.get(cluster_type=ClusterType.TenDBCluster, immute_domain=cluster_domain)

        if role in [TenDBClusterSpiderRole.SPIDER_MASTER, TenDBClusterSpiderRole.SPIDER_SLAVE]:
            for ins in cluster_obj.proxyinstance_set.filter(tendbclusterspiderext__spider_role=role):
                ins.machine.spec_id = new_spec.spec_id
                ins.machine.spec_config = new_spec.get_spec_info()
                ins.machine.save()
        elif role == MachineType.REMOTE:
            if cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REMOTE_REPEATER).exists():
                raise DBMMcpBaseException(msg="can't modify remote spec during migration")

            for ins in cluster_obj.storageinstance_set.filter(
                is_stand_by=True, instance_role__in=[InstanceRole.REMOTE_MASTER, InstanceRole.REDIS_SLAVE]
            ):
                ins.machine.spec_id = new_spec.spec_id
                ins.machine.spec_config = new_spec.get_spec_info()
                ins.machine.save()
        else:
            raise DBMMcpBaseException(msg=f"not support modify tendbcluster {role} spec")

        return Response({"spec_id": new_spec.spec_id, "spec_config": new_spec.get_spec_info()})

    @mcp_tools_api_decorator(
        description=str(_("""修改 TenDBSingle 集群规格""")),
        request_slz=ModifyTenDBSingleSpecInputSerializer,
        response_slz=ModifyMySQLClusterSpecOutputSerializer,
        permission_classes=[McpClusterDetailPermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_SENSITIVE],
        name_prefix="mysql_sensitive",
        enable_callee_plan=True,
    )
    def modify_tendbsingle_spec(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        spec_id = self.get_param("spec_id")

        new_spec = Spec.objects.get(spec_id=spec_id)

        cluster_obj = Cluster.objects.get(cluster_type=ClusterType.TenDBSingle, immute_domain=cluster_domain)

        for ins in cluster_obj.storageinstance_set.all():
            ins.machine.spec_id = new_spec.spec_id
            ins.machine.spec_config = new_spec.get_spec_info()
            ins.machine.save()

        return Response({"spec_id": new_spec.spec_id, "spec_config": new_spec.get_spec_info()})
