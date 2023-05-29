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

import pytest
from mock import patch
from rest_framework.test import APIRequestFactory

from backend.db_meta.enums import ClusterType
from backend.db_services.cmdb.biz import list_bizs, list_modules_by_biz
from backend.tests.conftest import mark_global_skip
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


@mark_global_skip
class TestCMDBViewSet:
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    def test_list_bizs(self):
        assert len(list_bizs(user="admin")) >= 1

    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    def test_list_modules(self, init_db_module):
        modules = list_modules_by_biz(bk_biz_id=constant.BK_BIZ_ID, cluster_type=ClusterType.TenDBHA.value)
        assert len(modules) == 1
