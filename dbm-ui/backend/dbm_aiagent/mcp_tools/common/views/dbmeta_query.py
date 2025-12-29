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

from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS, DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.list_biz_dbmodules import list_biz_dbmodules
from backend.dbm_aiagent.mcp_tools.common.serializers.empty import EmptyInputSerializer
from backend.dbm_aiagent.mcp_tools.common.serializers.list_bizs import ListPlatformBizsOutputSerializer
from backend.dbm_aiagent.mcp_tools.common.serializers.list_cluster import (
    ListBizClustersInputSerializer,
    ListBizClustersOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.list_dbmodule import (
    ListDBModulesInputSerializer,
    ListDBModulesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.list_enums import ListPlatformClusterTypeOutputSerializer
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
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
        mcp=[DBMAMcpTools.DBMETA_QUERY],
        name_prefix="dbmeta_query",
    )
    def list_platform_cluster_type(self, request, *args, **kwargs):
        res = {
            "cluster_types": [
                {"cluster_type_value": ct[0], "cluster_type_name": ct[1]} for ct in ClusterType.get_choices()
            ]
        }
        logger.info(res)
        return Response(res)

    @mcp_tools_api_decorator(
        description=str(_("获取业务特定集群类型的模块信息, dbmodule")),
        request_slz=ListDBModulesInputSerializer,
        response_slz=ListDBModulesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.DBMETA_QUERY],
        name_prefix="dbmeta_query",
    )
    def list_biz_dbmodules(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_type = self.get_param("cluster_type")

        return Response({"dbmodules": list_biz_dbmodules(bk_biz_id, cluster_type)})

    @mcp_tools_api_decorator(
        description=str(_("获取业务特定集群类型的集群")),
        request_slz=ListBizClustersInputSerializer,
        response_slz=ListBizClustersOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.DBMETA_QUERY],
        name_prefix="dbmeta_query",
    )
    def list_biz_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_type = self.get_param("cluster_type")

        res = [
            {
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "bk_biz_id": bk_biz_id,
                "cluster_type": cluster_obj.cluster_type,
                "cluster_domain": cluster_obj.immute_domain,
                "region": cluster_obj.region,
                "affinity": cluster_obj.disaster_tolerance_level,
                "status": cluster_obj.status,
            }
            for cluster_obj in Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type)
        ]

        return Response({"clusters": res})

    @mcp_tools_api_decorator(
        description=str(_("获取平台所有业务的中文名, 英文名和组件负责人")),
        request_slz=EmptyInputSerializer,
        response_slz=ListPlatformBizsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.DBMETA_QUERY],
        name_prefix="dbmeta_query",
    )
    def list_platform_bizs_base_info(self, request, *args, **kwargs):
        res = []
        for app in AppCache.objects.all():
            bk_biz_id = app.bk_biz_id
            abbr = app.db_app_abbr

            comp_infos = []
            for biz_admin in DBAdministrator.objects.filter(bk_biz_id=bk_biz_id):
                db_type = biz_admin.db_type
                admins = biz_admin.users
                if not admins:
                    admins = DEFAULT_DB_ADMINISTRATORS

                if db_type == DBType.MySQL:
                    comp_infos.append(
                        {"db_type": DBType.MySQL, "cluster_type": ClusterType.TenDBSingle, "dbas": admins[0:2]}
                    )
                    comp_infos.append(
                        {"db_type": DBType.MySQL, "cluster_type": ClusterType.TenDBHA, "dbas": admins[0:2]}
                    )
                else:
                    comp_infos.append({"db_type": db_type, "cluster_type": db_type, "dbas": admins[0:2]})

            res.append({"bk_biz_id": bk_biz_id, "abbr": abbr, "db_components": comp_infos})

        return Response({"bizs": res})
