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
from unittest.mock import MagicMock, patch

import pytest

from backend.dbm_aiagent.mcp_tools.mongodb.auth_parser import permissions as mongo_permissions
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mcp import (
    META_ACTION_CLUSTER_OVERVIEW,
    META_ACTION_LIST_CLUSTERS,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum


def _request(**data):
    request = MagicMock()
    request.method = "POST"
    request.data = data
    return request


class TestMcpMongoMetaPermission:
    """query_meta 按 action 分派鉴权，未知 action 默认拒绝"""

    @pytest.mark.parametrize("action", ["", None, "drop_everything", "list_my_bizs", "list_by_hosts"])
    def test_unknown_action_denied(self, action):
        """未知 action（含已下线的 list_my_bizs / 已拆出的 list_by_hosts）返回 False，避免 500"""
        perm = mongo_permissions.McpMongoMetaPermission()
        assert perm.has_permission(_request(action=action), MagicMock()) is False

    def test_list_clusters_delegates_to_biz_permission(self):
        with patch.object(mongo_permissions, "McpDBManagePermission") as mocked:
            mocked.return_value.has_permission.return_value = False
            perm = mongo_permissions.McpMongoMetaPermission()
            assert perm.has_permission(_request(action=META_ACTION_LIST_CLUSTERS, bk_biz_id=1), MagicMock()) is False
            assert mocked.return_value.mcp_auth_parser is mongo_permissions.auth_parse_bizs

    def test_cluster_overview_delegates_to_cluster_permission(self):
        with patch.object(mongo_permissions, "McpClusterDetailPermission") as mocked:
            mocked.return_value.has_permission.return_value = True
            perm = mongo_permissions.McpMongoMetaPermission()
            request = _request(action=META_ACTION_CLUSTER_OVERVIEW, cluster_domain="m1.rs0.dba.db")
            assert perm.has_permission(request, MagicMock()) is True
            assert mocked.return_value.mcp_auth_parser is mongo_permissions.auth_parse_clusters


class TestMcpMongoApplyPermission:
    """创单鉴权必须使用 mongodb_apply，与页面创单的 IAM 动作一致"""

    def test_action_and_resource(self):
        perm = mongo_permissions.McpMongoApplyPermission()
        assert perm.actions == [ActionEnum.MONGODB_APPLY]
        assert perm.resource_meta == ResourceEnum.BUSINESS

    def test_bill_views_use_apply_permission(self):
        """读源码断言，避免 ENABLE_DBM_AI=false 时 import views 拉起未安装 app。"""
        from pathlib import Path

        view_path = Path(mongo_permissions.__file__).resolve().parents[1] / "views" / "mongodb_bill_mcp.py"
        text = view_path.read_text(encoding="utf-8")
        assert "McpMongoApplyPermission" in text
        assert '"permission_classes": [McpMongoApplyPermission]' in text
