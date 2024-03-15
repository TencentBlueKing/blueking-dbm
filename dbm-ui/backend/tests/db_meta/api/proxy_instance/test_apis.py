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
from rest_framework.exceptions import ValidationError

from backend.db_meta import api, models
from backend.db_meta.enums import AccessLayer, InstanceStatus, MachineType
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db

TEST_PROXY_PORT1 = 10000
TEST_PROXY_PORT2 = 10001
TEST_INVALID_PROXY_PORT = 99999


class TestProxyInstance:
    def test_create_success(self, init_proxy_machine):
        """创建成功"""
        api.proxy_instance.create(
            [
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_PROXY_PORT1,
                },
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_PROXY_PORT2,
                },
            ]
        )
        assert models.ProxyInstance.objects.filter(bk_biz_id=constant.BK_BIZ_ID, machine__ip=cc.NORMAL_IP).count() == 2

    def test_create_proxy_err_with_not_exist_machine(self):
        """机器不存在异常"""
        with pytest.raises(models.Machine.DoesNotExist):
            api.proxy_instance.create(
                [
                    {
                        "ip": cc.NORMAL_IP,
                        "port": TEST_PROXY_PORT1,
                    },
                ]
            )

    def test_create_proxy_err_with_invalid_port(self):
        """异常的端口输入"""
        with pytest.raises(ValidationError):
            api.proxy_instance.create(
                [
                    {
                        "ip": cc.NORMAL_IP,
                        "port": TEST_INVALID_PROXY_PORT,
                    },
                ]
            )

    def test_create_proxy_err_with_invalid_access_layer(self, create_city):
        """接入层类型错误"""
        bk_city = models.BKCity.objects.first()
        models.Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
        )
        with pytest.raises(Exception):
            api.proxy_instance.create(
                [
                    {
                        "ip": cc.NORMAL_IP,
                        "port": TEST_PROXY_PORT1,
                    },
                ]
            )

    def test_update_success(self, init_proxy_machine):
        """更新成功"""
        api.proxy_instance.create(
            [
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_PROXY_PORT1,
                },
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_PROXY_PORT2,
                },
            ]
        )
        api.proxy_instance.update(
            [
                {"ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT1, "status": InstanceStatus.RUNNING.value},
                {"ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT2, "status": InstanceStatus.UNAVAILABLE.value},
            ]
        )
        assert models.ProxyInstance.objects.filter(
            **{"machine__ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT1, "status": InstanceStatus.RUNNING.value}
        ).exists()
        assert models.ProxyInstance.objects.filter(
            **{"machine__ip": cc.NORMAL_IP, "port": TEST_PROXY_PORT2, "status": InstanceStatus.UNAVAILABLE.value}
        ).exists()
