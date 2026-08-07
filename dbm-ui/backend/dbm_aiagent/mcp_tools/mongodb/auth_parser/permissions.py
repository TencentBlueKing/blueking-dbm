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
from typing import List

from pydantic import TypeAdapter
from rest_framework import permissions

from backend.dbm_aiagent.mcp_tools import typing
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs, auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mcp import (
    META_ACTION_CLUSTER_OVERVIEW,
    META_ACTION_LIST_CLUSTERS,
    META_ACTION_LIST_MONGOS,
    META_ACTION_LIST_SHARDS,
)
from backend.iam_app.dataclass import ResourceEnum, ResourceMeta
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.handlers.drf_perm.mcp import (
    BaseMcpDetailPermission,
    McpClusterDetailPermission,
    McpDBManagePermission,
)


def _request_data(request):
    return request.query_params if request.method == "GET" else request.data


class McpMongoApplyPermission(BaseMcpDetailPermission):
    """
    MongoDB 部署创单鉴权，与正式单据 MONGODB_REPLICASET_APPLY / MONGODB_SHARD_APPLY 的 IAM 动作一致
    鉴权字段：业务列表 List[int]
    """

    resource_checker = TypeAdapter(typing.BizIdList)

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions=[ActionEnum.MONGODB_APPLY], resource_meta=ResourceEnum.BUSINESS)


class McpMongoMetaPermission(permissions.BasePermission):
    """按 query_meta.action 分派业务/集群鉴权（仅 DBM ORM 动作）。"""

    def has_permission(self, request, view):
        action = _request_data(request).get("action")

        if action == META_ACTION_LIST_CLUSTERS:
            perm = McpDBManagePermission()
            perm.mcp_auth_parser = auth_parse_bizs
            return perm.has_permission(request, view)

        if action in (META_ACTION_CLUSTER_OVERVIEW, META_ACTION_LIST_MONGOS, META_ACTION_LIST_SHARDS):
            perm = McpClusterDetailPermission()
            perm.mcp_auth_parser = auth_parse_clusters
            return perm.has_permission(request, view)

        # 未知 action 默认拒绝（fail-closed）。serializer ChoiceField 已限制合法值；
        # 新增 META_ACTION 时务必同步更新本 permission 分派分支。
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class McpMongoAlarmPermission(permissions.BasePermission):
    """有 cluster_domain 走集群 VIEW，否则走业务 DB_MANAGE。"""

    def has_permission(self, request, view):
        data = _request_data(request)
        if (data.get("cluster_domain") or "").strip():
            perm = McpClusterDetailPermission()
            perm.mcp_auth_parser = auth_parse_clusters
            return perm.has_permission(request, view)

        perm = McpDBManagePermission()
        perm.mcp_auth_parser = auth_parse_bizs
        return perm.has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
