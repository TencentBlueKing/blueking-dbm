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
from rest_framework.exceptions import ValidationError

from backend.db_meta import api, models
from backend.db_meta.enums import AccessLayer, InstanceRole, InstanceStatus, MachineType
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db

TEST_STORAGE_PORT1 = 10000
TEST_STORAGE_PORT2 = 10001
TEST_INVALID_STORAGE_PORT = 99999


@pytest.fixture
def init_storage_machine(create_city):
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


class TestStorageInstance:
    def test_create_success(self, init_storage_machine):
        """创建成功"""
        api.storage_instance.create(
            [
                {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_PORT1, "instance_role": InstanceRole.BACKEND_MASTER.value},
                {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_PORT2, "instance_role": InstanceRole.BACKEND_SLAVE.value},
            ]
        )
        assert (
            models.StorageInstance.objects.filter(bk_biz_id=constant.BK_BIZ_ID, machine__ip=cc.NORMAL_IP).count() == 2
        )

    def test_create_storage_err_with_not_exist_machine(self):
        """机器不存在异常"""
        with pytest.raises(models.Machine.DoesNotExist):
            api.storage_instance.create(
                [
                    {
                        "ip": cc.NORMAL_IP,
                        "port": TEST_STORAGE_PORT1,
                        "instance_role": InstanceRole.BACKEND_MASTER.value,
                    },
                ]
            )

    def test_create_storage_err_with_not_exist_role(self, init_storage_machine):
        """角色不存在"""
        with pytest.raises(ValidationError):
            api.storage_instance.create(
                [
                    {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_PORT1, "instance_role": "not_exists"},
                ]
            )

    def test_create_storage_err_with_invalid_port(self):
        """异常的端口输入"""
        with pytest.raises(ValidationError):
            api.storage_instance.create(
                [
                    {
                        "ip": cc.NORMAL_IP,
                        "port": TEST_INVALID_STORAGE_PORT,
                        "instance_role": InstanceRole.BACKEND_MASTER.value,
                    },
                ]
            )

    def test_create_storage_err_with_invalid_access_layer(self, create_city):
        """接入层类型错误"""
        bk_city = models.BKCity.objects.first()
        models.Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.PROXY,
        )
        with pytest.raises(Exception):
            api.storage_instance.create(
                [
                    {
                        "ip": cc.NORMAL_IP,
                        "port": TEST_STORAGE_PORT1,
                        "instance_role": InstanceRole.BACKEND_MASTER.value,
                    },
                ]
            )

    def test_update_success(self, init_storage_machine):
        """更新成功"""
        self.test_create_success(init_storage_machine)
        api.storage_instance.update(
            [
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_STORAGE_PORT1,
                    "instance_role": InstanceRole.BACKEND_MASTER.value,
                    "status": InstanceStatus.UNAVAILABLE.value,
                },
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_STORAGE_PORT2,
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                    "status": InstanceStatus.RUNNING.value,
                },
            ]
        )
        assert models.StorageInstance.objects.filter(
            **{
                "machine__ip": cc.NORMAL_IP,
                "port": TEST_STORAGE_PORT1,
                "instance_role": InstanceRole.BACKEND_MASTER.value,
                "status": InstanceStatus.UNAVAILABLE.value,
            }
        ).exists()
        assert models.StorageInstance.objects.filter(
            **{
                "machine__ip": cc.NORMAL_IP,
                "port": TEST_STORAGE_PORT2,
                "instance_role": InstanceRole.BACKEND_SLAVE.value,
                "status": InstanceStatus.RUNNING.value,
            }
        ).exists()
