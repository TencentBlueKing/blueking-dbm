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
from mock.mock import patch

from backend.db_meta import api
from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import DbModuleExistException
from backend.db_meta.models import BKModule, DBModule
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.cc import CCApiMock

pytestmark = pytest.mark.django_db


class TestCreateDBModule:
    def test_create_success(self):
        """创建成功"""
        db_module_name = "hello"
        api.db_module.create(
            **{"bk_biz_id": constant.BK_BIZ_ID, "name": db_module_name, "cluster_type": ClusterType.TenDBHA.value}
        )
        assert DBModule.objects.filter(bk_biz_id=constant.BK_BIZ_ID, db_module_name=db_module_name).exists()

    def test_create_with_exception(self):
        """重复创建异常"""
        self.test_create_success()
        with pytest.raises(DbModuleExistException):
            self.test_create_success()
