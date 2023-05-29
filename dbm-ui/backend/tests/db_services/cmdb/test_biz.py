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

from unittest.mock import patch

from django.test import TestCase
from django.utils.crypto import get_random_string

from backend.db_services.cmdb.biz import list_bizs
from backend.iam_app.dataclass.actions import ActionEnum
from backend.tests.conftest import mock_bk_user
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock


class TestBiz(TestCase):
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    def test_list_bizs(self):
        biz_list = list_bizs(user=mock_bk_user(get_random_string(10)))
        self.assertEqual(biz_list[0].permission[ActionEnum.DB_MANAGE.id], True)
