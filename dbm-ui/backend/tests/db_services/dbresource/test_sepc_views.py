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

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_meta.enums.spec import SpecClusterType, SpecMachineType
from backend.db_meta.models import Spec
from backend.db_services.dbresource.views.sepc import DBSpecViewSet
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """禁用中间件以简化测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(autouse=True)
def setup_permissions():
    """设置权限 - 禁用权限验证"""
    patch.object(DBSpecViewSet, "permission_classes", [AllowAny]).start()
    patch.object(DBSpecViewSet, "get_permissions", lambda x: []).start()
    patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
    yield


class TestDBSpecViewSet:
    """测试 DBSpecViewSet 类 - 规格管理视图核心功能"""

    @pytest.fixture
    def test_spec(self):
        """创建测试规格"""
        spec = Spec.objects.create(
            spec_id=7000,
            spec_name="test_viewset_spec",
            spec_cluster_type=SpecClusterType.MySQL.value,
            spec_machine_type=SpecMachineType.BACKEND.value,
            cpu={"max": 16, "min": 16},
            mem={"max": 64, "min": 64},
            storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
            device_class=["S5"],
            qps={"min": 1000, "max": 5000},
            enable=True,
            desc="Test spec for viewset",
        )
        yield spec
        spec.delete()

    @pytest.fixture
    def test_multiple_specs(self):
        """创建多个测试规格"""
        specs = []
        for i in range(3):
            spec = Spec.objects.create(
                spec_id=7100 + i,
                spec_name=f"batch_spec_{i}",
                spec_cluster_type=SpecClusterType.MySQL.value,
                spec_machine_type=SpecMachineType.BACKEND.value,
                cpu={"max": 8, "min": 8},
                mem={"max": 32, "min": 32},
                storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
                device_class=["S5"],
                enable=True,
            )
            specs.append(spec)
        yield specs
        for spec in specs:
            spec.delete()

    def test_create_spec(self):
        """测试创建规格"""
        url = "/apis/dbresource/spec/"
        data = {
            "spec_name": "new_test_spec",
            "spec_cluster_type": SpecClusterType.MySQL.value,
            "spec_machine_type": SpecMachineType.BACKEND.value,
            "cpu": {"max": 8, "min": 8},
            "mem": {"max": 32, "min": 32},
            "storage_spec": [{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
            "device_class": ["S5"],
            "enable": True,
            "desc": "Created via test",
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()["data"]
        assert result["spec_name"] == "new_test_spec"

        # 清理
        Spec.objects.filter(spec_name="new_test_spec").delete()

    def test_retrieve_spec(self, test_spec):
        """测试获取规格详情"""
        url = f"/apis/dbresource/spec/{test_spec.spec_id}/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert result["spec_id"] == test_spec.spec_id
        assert result["spec_name"] == test_spec.spec_name

    def test_update_spec(self, test_spec):
        """测试更新规格"""
        url = f"/apis/dbresource/spec/{test_spec.spec_id}/"
        data = {
            "spec_name": "updated_spec_name",
            "spec_cluster_type": test_spec.spec_cluster_type,
            "spec_machine_type": test_spec.spec_machine_type,
            "cpu": {"max": 32, "min": 32},
            "mem": {"max": 128, "min": 128},
            "storage_spec": test_spec.storage_spec,
            "device_class": ["S5", "S6"],
            "enable": True,
            "desc": "Updated description",
        }
        response = client.put(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert result["spec_name"] == "updated_spec_name"

    def test_batch_common_update(self, test_multiple_specs):
        """测试批量修改规格的启用状态"""
        spec_ids = [spec.spec_id for spec in test_multiple_specs]

        url = "/apis/dbresource/spec/batch_common_update/"
        data = {"spec_ids": spec_ids, "enable": False}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK

        # 验证所有规格都已禁用
        for spec_id in spec_ids:
            spec = Spec.objects.get(spec_id=spec_id)
            assert spec.enable is False

    @patch("backend.db_meta.models.Machine.objects.filter")
    def test_list_specs(self, mock_machine_filter, test_spec):
        """测试获取规格列表"""
        mock_machine_filter.return_value.values_list.return_value = []

        url = f"/apis/dbresource/spec/?spec_cluster_type={test_spec.spec_cluster_type}"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "results" in result
        assert result["count"] >= 1

    def test_verify_duplicated_spec_name_not_exists(self):
        """测试校验规格名称 - 不存在重复"""
        url = "/apis/dbresource/spec/verify_duplicated_spec_name/"
        data = {
            "spec_name": "unique_spec_name_12345",
            "spec_cluster_type": SpecClusterType.MySQL.value,
            "spec_machine_type": SpecMachineType.BACKEND.value,
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert result is False

    def test_verify_duplicated_spec_name_exists(self, test_spec):
        """测试校验规格名称 - 存在重复"""
        url = "/apis/dbresource/spec/verify_duplicated_spec_name/"
        data = {
            "spec_name": test_spec.spec_name,
            "spec_cluster_type": test_spec.spec_cluster_type,
            "spec_machine_type": test_spec.spec_machine_type,
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert result is True

    def test_verify_duplicated_spec_name_self_update(self, test_spec):
        """测试校验规格名称 - 自己更新自己"""
        url = "/apis/dbresource/spec/verify_duplicated_spec_name/"
        data = {
            "spec_name": test_spec.spec_name,
            "spec_cluster_type": test_spec.spec_cluster_type,
            "spec_machine_type": test_spec.spec_machine_type,
            "spec_id": test_spec.spec_id,
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert result is False

    def test_query_qps_range(self):
        """测试获取QPS范围"""
        specs = []
        for i in range(2):
            spec = Spec.objects.create(
                spec_id=7300 + i,
                spec_name=f"qps_spec_{i}",
                spec_cluster_type=SpecClusterType.MySQL.value,
                spec_machine_type=SpecMachineType.BACKEND.value,
                cpu={"max": 8, "min": 8},
                mem={"max": 32, "min": 32},
                storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
                device_class=["S5"],
                qps={"min": 1000 * (i + 1), "max": 5000 * (i + 1)},
                enable=True,
            )
            specs.append(spec)

        url = "/apis/dbresource/spec/query_qps_range/"
        params = {
            "spec_machine_type": SpecMachineType.BACKEND.value,
            "spec_cluster_type": SpecClusterType.MySQL.value,
            "capacity": 100,
        }
        response = client.get(url, params)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "min" in result
        assert "max" in result
        assert result["min"] <= result["max"]

        # 清理
        for spec in specs:
            spec.delete()
