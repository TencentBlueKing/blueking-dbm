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
import ipaddress

import pytest

from backend.db_meta import models
from backend.db_meta.enums import AccessLayer, MachineType
from backend.db_meta.models import BKCity, Machine
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc


@pytest.fixture
def machine_fixture():
    bk_city = BKCity.objects.first()
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP2,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        bk_cloud_id=1,
        bk_host_id=1002,
    )
    yield machine


@pytest.fixture
def init_proxy_machine():
    bk_city = models.BKCity.objects.first()
    machine = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.PROXY,
    )
    return machine


@pytest.fixture
def init_storage_machine():
    bk_city = models.BKCity.objects.first()
    machine = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP)),
    )
    return machine
