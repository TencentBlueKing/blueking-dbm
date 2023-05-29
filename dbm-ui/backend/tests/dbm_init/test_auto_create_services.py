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

from backend.dbm_init.services import Services
from backend.tests.mock_data.components.bklog import BKLogApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock


class TestAutoCreateServices(TestCase):
    @patch("backend.dbm_init.services.ItsmApi", ItsmApiMock)
    def test_auto_create_itsm_service(self):
        service_id = Services.auto_create_itsm_service()
        self.assertEqual(service_id, 94)

    @patch("backend.dbm_init.services.BKLogApi", BKLogApiMock)
    def test_auto_create_bklog_service(self):
        is_success = Services.auto_create_bklog_service()
        self.assertEqual(is_success, True)
