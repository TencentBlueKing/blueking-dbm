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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.models.mysql_dts import MysqlDtsStatus
from backend.flow.plugins.components.collections.mysql.dts.reinstall.precheck import MysqlDtsReinstallPrecheckService


class MysqlDtsReinstallPrecheckServiceTest(SimpleTestCase):
    """重装前置检查组件测试。"""

    def _make_service_data(self, dts_cluster_id: int, force_reinstall: bool = False):
        """构造 Service 的 data 输入。"""
        data = MagicMock()
        data.get_one_of_inputs.return_value = {
            "dts_cluster_id": dts_cluster_id,
            "force_reinstall": force_reinstall,
        }
        return data

    def _make_queryset(self, count: int):
        """构造模拟的 QuerySet。"""
        qs = MagicMock()
        qs.count.return_value = count
        return qs

    @patch("backend.flow.plugins.components.collections.mysql.dts.reinstall.precheck.MysqlDtsInfo.objects.filter")
    def test_no_active_migrate_passes(self, mock_filter):
        """无活跃迁移时通过检查。"""
        mock_filter.return_value = self._make_queryset(0)

        service = MysqlDtsReinstallPrecheckService()
        service.log_info = MagicMock()
        data = self._make_service_data(dts_cluster_id=1)

        result = service._execute(data, None)

        self.assertTrue(result)
        service.log_info.assert_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.reinstall.precheck.MysqlDtsInfo.objects.filter")
    def test_active_migrate_without_force_fails(self, mock_filter):
        """有活跃迁移 + force_reinstall=False 时拒绝。"""
        mock_filter.return_value = self._make_queryset(3)

        service = MysqlDtsReinstallPrecheckService()
        service.log_error = MagicMock()
        data = self._make_service_data(dts_cluster_id=1, force_reinstall=False)

        result = service._execute(data, None)

        self.assertFalse(result)
        service.log_error.assert_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.reinstall.precheck.MysqlDtsInfo.objects.filter")
    def test_active_migrate_with_force_passes(self, mock_filter):
        """有活跃迁移 + force_reinstall=True 时警告但通过。"""
        mock_filter.return_value = self._make_queryset(2)

        service = MysqlDtsReinstallPrecheckService()
        service.log_warning = MagicMock()
        data = self._make_service_data(dts_cluster_id=1, force_reinstall=True)

        result = service._execute(data, None)

        self.assertTrue(result)
        service.log_warning.assert_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.reinstall.precheck.MysqlDtsInfo.objects.filter")
    def test_filter_uses_correct_statuses(self, mock_filter):
        """检查使用正确的活跃状态过滤。"""
        mock_filter.return_value = self._make_queryset(0)

        service = MysqlDtsReinstallPrecheckService()
        service.log_info = MagicMock()
        data = self._make_service_data(dts_cluster_id=99)

        service._execute(data, None)

        mock_filter.assert_called_once()
        call_kwargs = mock_filter.call_args.kwargs
        self.assertEqual(call_kwargs["dts_cluster_id"], 99)
        self.assertIn(MysqlDtsStatus.ToDo.value, call_kwargs["status__in"])
        self.assertIn(MysqlDtsStatus.FullOnline.value, call_kwargs["status__in"])
