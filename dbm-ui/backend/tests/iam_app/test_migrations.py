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

import importlib
from unittest.mock import patch

import pytest

IAM_V3_MIGRATIONS = [
    "backend.iam_app.migrations.0001_initial",
    "backend.iam_app.migrations.0002_bk_dbm_202310271104",
]


@pytest.mark.parametrize("module_path", IAM_V3_MIGRATIONS)
class TestIAMV3Migrations:
    """V3 权限模型迁移在 V4 模式下需跳过"""

    def test_skip_when_iam_v4(self, module_path):
        module = importlib.import_module(module_path)
        with patch.object(module.env, "ENABLE_IAM_V4", True), patch.object(module, "IAMMigrator") as mock_migrator:
            module.forward_func(None, None)
        mock_migrator.assert_not_called()

    def test_migrate_when_iam_v3(self, module_path):
        module = importlib.import_module(module_path)
        with patch.object(module.env, "ENABLE_IAM_V4", False), patch.object(module, "IAMMigrator") as mock_migrator:
            module.forward_func(None, None)
        mock_migrator.assert_called_once_with(module.Migration.migration_json)
        mock_migrator.return_value.migrate.assert_called_once_with()
