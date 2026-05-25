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

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models.machine import Machine
from backend.db_meta.models.spec import Spec
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs
from backend.dbm_aiagent.mcp_tools.common.impl.list_biz_clusters import list_biz_clusters
from backend.dbm_aiagent.mcp_tools.common.impl.list_biz_dbmodules import list_biz_dbmodules
from backend.dbm_aiagent.mcp_tools.common.impl.list_bizs_base_info import list_bizs_base_info
from backend.dbm_aiagent.mcp_tools.common.serializers.empty import EmptyInputSerializer
from backend.dbm_aiagent.mcp_tools.common.serializers.list_bizs import (
    ListBizsInputSerializer,
    ListBizsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.list_cluster import (
    ListBizClustersInputSerializer,
    ListBizClustersOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.list_cluster_type import ListPlatformClusterTypeOutputSerializer
from backend.dbm_aiagent.mcp_tools.common.serializers.list_dbmodule import (
    ListDBModulesInputSerializer,
    ListDBModulesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.list_machine_info import (
    ListMachineInfoInputSerializer,
    ListMachineInfoOutputSerializer,
    MachineInfoSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpUsernameNotFoundException
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


class DBMetaQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取DBM平台支持的所有集群类型")),
        request_slz=EmptyInputSerializer,
        response_slz=ListPlatformClusterTypeOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBMETA_QUERY],
        name_prefix="dbmeta_query",
        enable=False,
    )
    def list_supported_cluster_type(self, request, *args, **kwargs):
        res = {
            "cluster_types": [
                {"cluster_type_value": ct[0], "cluster_type_name": ct[1]} for ct in ClusterType.get_choices()
            ]
        }
        return Response(res)

    @mcp_tools_api_decorator(
        description=str(
            _(
                """获取业务特定集群类型的模块信息, dbmodule
        * cluster_types 可以用 list_bizs_base_info 获取后作为参数"""
            )
        ),
        request_slz=ListDBModulesInputSerializer,
        response_slz=ListDBModulesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBMETA_QUERY],
        mcp_auth_parser=auth_parse_bizs,
        name_prefix="dbmeta_query",
        enable=False,
    )
    def list_biz_dbmodules(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")

        return Response({"dbmodules": list_biz_dbmodules(bk_biz_id)})

    @mcp_tools_api_decorator(
        description=str(_("""查询域名, 机器, 实例所属集群基本信息""")),
        request_slz=ListBizClustersInputSerializer,
        response_slz=ListBizClustersOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBMETA_QUERY, DBMMcpTools.DBM_PUBLIC_MARKET],
        permission_classes=[],
        mcp_auth_parser=None,
        name_prefix="dbmeta_query",
    )
    def list_clusters_base_info(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domains = self.get_param("cluster_domains")
        ips = self.get_param("ips")
        instances = self.get_param("instances")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        # 非DBA用户必须传入ips, instances, cluster_domains
        if not DBAdministrator.is_dba(username) and not (ips or instances or cluster_domains):
            raise Exception("ips, instances, cluster_domains at least one")

        res = list_biz_clusters(
            ips=ips,
            instances=instances,
            cluster_domains=cluster_domains,
            bk_biz_id=bk_biz_id,
        )

        return Response({"clusters": res})

    @mcp_tools_api_decorator(
        description=str(_("获取平台所有业务的中文名, 英文名和组件负责人")),
        request_slz=ListBizsInputSerializer,
        response_slz=ListBizsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBMETA_QUERY, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="dbmeta_query",
        permission_classes=[],
        mcp_auth_parser=None,
    )
    def list_bizs_base_info(self, request, *args, **kwargs):
        bk_biz_ids = self.get_param("bk_biz_ids")
        app_abbrs = self.get_param("app_abbrs")

        if not (bk_biz_ids or app_abbrs):
            raise Exception("bk_biz_ids, app_abbrs at least one")

        res = list_bizs_base_info(bk_biz_ids=bk_biz_ids, app_abbrs=app_abbrs)

        return Response({"bizs": res})

    @mcp_tools_api_decorator(
        description=str(_("获取机器信息")),
        request_slz=ListMachineInfoInputSerializer,
        response_slz=ListMachineInfoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DBMETA_QUERY, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="dbmeta_query",
        permission_classes=[],
        mcp_auth_parser=None,
    )
    def list_machine_info(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        ips = self.get_param("ips")

        if not ips:
            raise Exception("ips is required")

        if bk_cloud_id is None:
            machines = Machine.objects.filter(ip__in=ips)
        else:
            machines = Machine.objects.filter(bk_cloud_id=bk_cloud_id, ip__in=ips)

        found_ips = set(machines.values_list("ip", flat=True))
        not_found_ips = [ip for ip in ips if ip not in found_ips]

        ip_cloud_map = {}
        for m in machines:
            ip_cloud_map.setdefault(m.ip, set()).add(m.bk_cloud_id)
        ambiguous_ips = [
            {"ip": ip, "bk_cloud_ids": sorted(cloud_ids)}
            for ip, cloud_ids in ip_cloud_map.items()
            if len(cloud_ids) > 1
        ]

        spec_ids = set(machines.values_list("spec_id", flat=True))
        spec_map = {s.spec_id: s.get_spec_info() for s in Spec.objects.filter(spec_id__in=spec_ids)}

        data = MachineInfoSerializer(machines, many=True).data
        for item in data:
            item["spec_config"] = spec_map.get(item["spec_id"], item["spec_config"])

        return Response({"machines": data, "not_found_ips": not_found_ips, "ambiguous_ips": ambiguous_ips})
