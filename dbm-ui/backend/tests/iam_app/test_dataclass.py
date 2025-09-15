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
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings

from backend import env
from backend.db_meta.enums import ClusterType
from backend.iam_app.dataclass import (
    assign_auth_to_dba,
    assign_auth_to_group,
    flush_groups_auth,
    generate_iam_biz_maintain_json,
    generate_iam_migration_json,
    generate_resource_topo_auth,
)
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta, _all_actions
from backend.iam_app.dataclass.resources import ResourceEnum, _all_resources
from backend.iam_app.exceptions import ActionNotExistError, ResourceNotExistError
from backend.tests.mock_data import constant

pytestmark = pytest.mark.django_db


class TestIAMDataclass:
    """IAM Dataclass综合测试"""

    def test_action_meta_init(self):
        """测试ActionMeta初始化"""
        action = ActionMeta(
            id="test_action",
            name="测试动作",
            name_en="Test Action",
            type="view",
            related_resource_types=[],
            related_actions=[],
        )
        assert action.id == "test_action"
        assert action.name == "测试动作"

    def test_action_meta_to_json(self):
        """测试ActionMeta转JSON"""
        action = ActionMeta(
            id="test_action",
            name="测试动作",
            name_en="Test Action",
            type="view",
            related_resource_types=[],
            related_actions=[],
        )
        json_data = action.to_json()
        assert json_data["id"] == "test_action"
        assert json_data["name"] == "测试动作"

    def test_action_meta_eq(self):
        """测试ActionMeta相等性"""
        action1 = ActionMeta(
            id="test_action",
            name="测试动作",
            name_en="Test Action",
            type="view",
            related_resource_types=[],
            related_actions=[],
        )
        action2 = ActionMeta(
            id="test_action",
            name="测试动作2",
            name_en="Test Action 2",
            type="view",
            related_resource_types=[],
            related_actions=[],
        )
        assert action1 == action2  # 只比较id

    def test_action_enum_get_action_by_id(self):
        """测试通过ID获取动作"""
        action = ActionEnum.get_action_by_id("db_manage")
        assert action == ActionEnum.DB_MANAGE

    def test_action_enum_get_action_by_id_not_found(self):
        """测试获取不存在的动作"""
        with pytest.raises(ActionNotExistError):
            ActionEnum.get_action_by_id("not_exist_action")

    def test_action_enum_get_match_actions(self):
        """测试获取匹配的动作"""
        actions = ActionEnum.get_match_actions("mysql")
        assert len(actions) > 0

    def test_all_actions_not_empty(self):
        """测试所有动作字典不为空"""
        assert len(_all_actions) > 0
        assert "db_manage" in _all_actions

    def test_resource_meta_create_instance(self):
        """测试创建资源实例"""
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))
        assert resource.type == "biz"
        assert resource.id == str(constant.BK_BIZ_ID)

    def test_resource_enum_get_resource_by_id(self):
        """测试通过ID获取资源"""
        resource = ResourceEnum.get_resource_by_id("mysql")
        assert resource == ResourceEnum.MYSQL

    def test_resource_enum_get_resource_by_id_not_found(self):
        """测试获取不存在的资源"""
        with pytest.raises(ResourceNotExistError):
            ResourceEnum.get_resource_by_id("not_exist_resource")

    def test_resource_enum_cluster_type_to_resource_meta(self):
        """测试集群类型到资源的映射"""
        resource_meta = ResourceEnum.cluster_type_to_resource_meta(ClusterType.TenDBHA)
        assert resource_meta == ResourceEnum.MYSQL

    def test_all_resources_not_empty(self):
        """测试所有资源字典不为空"""
        assert len(_all_resources) > 0
        assert "mysql" in _all_resources

    def test_generate_iam_migration_json(self):
        """测试生成IAM迁移JSON"""
        json_name = "test_migration.json"
        json_path = os.path.join(settings.BASE_DIR, f"backend/iam_app/migration_json_files/{json_name}")

        if os.path.exists(json_path):
            os.remove(json_path)

        generate_iam_migration_json(json_name=json_name)

        assert os.path.exists(json_path)

        with open(json_path, "r") as f:
            content = json.load(f)
            assert "system_id" in content
            assert content["system_id"] == env.BK_IAM_SYSTEM_ID

        os.remove(json_path)

    def test_generate_resource_topo_auth(self):
        """测试生成资源拓扑授权"""
        res_actions = [ActionEnum.MYSQL_VIEW, ActionEnum.MYSQL_EDIT]
        result = generate_resource_topo_auth(res_actions, bk_biz_id=constant.BK_BIZ_ID, bk_biz_name="测试业务")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_generate_iam_biz_maintain_json(self):
        """测试生成业务运维迁移JSON"""
        json_name = "test_biz_maintain.json"
        json_path = os.path.join(settings.BASE_DIR, f"backend/iam_app/migration_json_files/{json_name}")

        if os.path.exists(json_path):
            os.remove(json_path)

        generate_iam_biz_maintain_json(json_name=json_name)

        assert os.path.exists(json_path)

        with open(json_path, "r") as f:
            content = json.load(f)
            assert isinstance(content, list)

        os.remove(json_path)

    @patch("backend.iam_app.dataclass.Permission.get_iam_client")
    def test_assign_auth_to_group_success(self, mock_get_iam_client, test_app_cache):
        """测试分配权限到用户组成功"""
        mock_iam = MagicMock()
        mock_iam._client.grant_user_group_actions.return_value = (True, "", {})
        mock_get_iam_client.return_value = mock_iam

        # assign_auth_to_group参数是: iam, biz, group_id
        assign_auth_to_group(mock_iam, test_app_cache, 1)

        assert mock_iam._client.grant_user_group_actions.called

    @patch("backend.iam_app.dataclass.Permission.get_iam_client")
    def test_assign_auth_to_group_failure(self, mock_get_iam_client, test_app_cache):
        """测试分配权限到用户组失败"""
        from backend.iam_app.exceptions import BaseIAMError

        mock_iam = MagicMock()
        mock_iam._client.grant_user_group_actions.return_value = (False, "error", {})
        mock_get_iam_client.return_value = mock_iam

        with pytest.raises(BaseIAMError):
            assign_auth_to_group(mock_iam, test_app_cache, 1)

    @patch("backend.iam_app.dataclass.assign_auth_to_group")
    @patch("backend.iam_app.dataclass.Permission.get_iam_client")
    def test_assign_auth_to_dba_success(self, mock_get_iam_client, mock_assign, test_app_cache):
        """测试分配DBA权限成功"""
        mock_iam = MagicMock()
        mock_iam._client.create_user_groups.return_value = (True, "", [1])
        mock_iam._client.add_user_group_members.return_value = (True, "", {})
        mock_get_iam_client.return_value = mock_iam

        # assign_auth_to_dba参数是: bk_biz_id, group_name, members
        assign_auth_to_dba(bk_biz_id=constant.BK_BIZ_ID, group_name="test_group", members=["admin"])

        assert mock_iam._client.create_user_groups.called
        assert mock_assign.called

    @patch("backend.iam_app.dataclass.Permission.get_iam_client")
    def test_assign_auth_to_dba_create_failure(self, mock_get_iam_client, test_app_cache):
        """测试分配DBA权限-创建用户组失败"""
        from backend.iam_app.exceptions import BaseIAMError

        mock_iam = MagicMock()
        mock_iam._client.create_user_groups.return_value = (False, "error", [])
        mock_get_iam_client.return_value = mock_iam

        with pytest.raises(BaseIAMError):
            assign_auth_to_dba(bk_biz_id=constant.BK_BIZ_ID, group_name="test_group", members=["admin"])

    @patch("backend.iam_app.dataclass.assign_auth_to_group")
    @patch("backend.iam_app.dataclass.Permission.get_iam_client")
    def test_flush_groups_auth_success(self, mock_get_iam_client, mock_assign):
        """测试刷新用户组权限"""
        mock_iam = MagicMock()
        mock_iam._client.query_user_groups.return_value = (True, "", {"results": []})
        mock_get_iam_client.return_value = mock_iam

        flush_groups_auth()

        assert mock_iam._client.query_user_groups.called
