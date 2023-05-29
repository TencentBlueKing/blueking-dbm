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

from backend.db_meta import api, models
from backend.db_meta.enums import AccessLayer, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import StorageInstance
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db

TEST_STORAGE_INSTANCE_PORT = 20000


@pytest.fixture
def init_normal_storage_instance(create_city):
    bk_city = models.BKCity.objects.first()
    machine1 = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP)),
    )
    machine2 = models.Machine.objects.create(
        ip=cc.NORMAL_IP2,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP2)),
    )

    StorageInstance.objects.create(
        machine=machine1,
        port=TEST_STORAGE_INSTANCE_PORT,
        instance_role=InstanceRole.BACKEND_MASTER,
        instance_inner_role=InstanceInnerRole.MASTER,
    )
    StorageInstance.objects.create(
        machine=machine2,
        port=TEST_STORAGE_INSTANCE_PORT,
        instance_role=InstanceRole.BACKEND_SLAVE,
        instance_inner_role=InstanceInnerRole.SLAVE,
    )


@pytest.fixture
def init_remote_storage_instance(create_city):
    bk_city = models.BKCity.objects.first()
    machine = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.REMOTE.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP)),
    )
    StorageInstance.objects.create(
        machine=machine,
        port=TEST_STORAGE_INSTANCE_PORT,
        instance_role=InstanceRole.REMOTE_MASTER.value,
        instance_inner_role=InstanceInnerRole.REPEATER.value,
    )


class TestCreateStorageInstanceTuple:
    def test_create_success(self, init_normal_storage_instance):
        api.storage_instance_tuple.create(
            [
                {
                    "ejector": {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_INSTANCE_PORT},
                    "receiver": {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_INSTANCE_PORT},
                }
            ]
        )
        assert models.StorageInstanceTuple.objects.exists()

    def test_create_master_as_receiver(self, init_normal_storage_instance):
        with pytest.raises(Exception):
            api.storage_instance_tuple.create(
                [
                    {
                        "ejector": {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_INSTANCE_PORT},
                        "receiver": {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_INSTANCE_PORT},
                    }
                ]
            )

    def test_create_slave_as_ejector(self, init_normal_storage_instance):
        with pytest.raises(Exception):
            api.storage_instance_tuple.create(
                [
                    {
                        "ejector": {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_INSTANCE_PORT},
                        "receiver": {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_INSTANCE_PORT},
                    }
                ]
            )

    def test_create_to_self(self, init_remote_storage_instance):
        with pytest.raises(Exception):
            api.storage_instance_tuple.create(
                [
                    {
                        "ejector": {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_INSTANCE_PORT},
                        "receiver": {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_INSTANCE_PORT},
                    }
                ]
            )
