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
from django.db import IntegrityError
from mock.mock import patch

from backend.db_meta import api
from backend.db_meta.enums import MachineType
from backend.db_meta.models import BKCity, Machine
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db


@pytest.fixture
def machine_fixture(create_city):
    bk_city = BKCity.objects.first()
    Machine.objects.create(
        ip=cc.NORMAL_IP2,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        bk_cloud_id=1,
        bk_host_id=2,
    )


class TestCreateMachine:
    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_success(self, create_city):
        """创建成功"""
        api.machine.create(
            machines=[
                {"ip": cc.NORMAL_IP, "bk_biz_id": constant.BK_BIZ_ID, "machine_type": MachineType.BACKEND.value}
            ],
            bk_cloud_id=1,
        )
        assert Machine.objects.filter(
            ip=cc.NORMAL_IP, bk_biz_id=constant.BK_BIZ_ID, machine_type=MachineType.BACKEND.value
        ).exists()

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_ip_not_in_cc(self):
        # TODO 细化异常
        with pytest.raises(Exception):
            api.machine.create(
                machines=[
                    {
                        "ip": cc.IP_NOT_IN_BKCC,
                        "bk_biz_id": constant.BK_BIZ_ID,
                        "machine_type": MachineType.BACKEND.value,
                    }
                ],
                bk_cloud_id=1,
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_city_not_registered(self):
        with pytest.raises(Exception):
            api.machine.create(
                machines=[
                    {
                        "ip": cc.IP_WITH_NOT_REGISTERED_CITY,
                        "bk_biz_id": constant.BK_BIZ_ID,
                        "machine_type": MachineType.BACKEND.value,
                    }
                ],
                bk_cloud_id=1,
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_dup_ip(self, machine_fixture):
        with pytest.raises(IntegrityError):
            api.machine.create(
                machines=[
                    {"ip": cc.NORMAL_IP2, "bk_biz_id": constant.BK_BIZ_ID, "machine_type": MachineType.BACKEND.value}
                ],
                bk_cloud_id=1,
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_invalid_ip(self):
        with pytest.raises(Exception):
            api.machine.create(
                machines=[
                    {"ip": "abc.123", "bk_biz_id": constant.BK_BIZ_ID, "machine_type": MachineType.BACKEND.value}
                ],
                bk_cloud_id=1,
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_invalid_meta_type(self, machine_fixture):
        with pytest.raises(Exception):
            api.machine.create(
                machines=[{"ip": cc.NORMAL_IP, "bk_biz_id": constant.BK_BIZ_ID, "machine_type": "err_type"}],
                bk_cloud_id=1,
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_missing_meta_type(self, machine_fixture):
        with pytest.raises(Exception):
            api.machine.create(
                machines=[{"ip": cc.NORMAL_IP, "bk_biz_id": constant.BK_BIZ_ID}],
                bk_cloud_id=1,
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_empty_input(self, machine_fixture):
        with pytest.raises(Exception):
            api.machine.create([])

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_not_list_input(self, machine_fixture):
        with pytest.raises(Exception):
            api.machine.create({})
