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

from blueapps.account.models import User
from django.test import TestCase

from backend.dbm_init.services import Services
from backend.tests.mock_data.components.bklog import BKLogApiMock
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock


class TestAutoCreateServices(TestCase):
    @patch("backend.dbm_init.services.ItsmApi", ItsmApiMock)
    def test_auto_create_itsm_service(self):
        service_id = Services.auto_create_itsm_service()
        self.assertEqual(service_id, 94)

    @patch("backend.db_monitor.utils.BKLogApi", BKLogApiMock)
    @patch("backend.db_monitor.format.CCApi", CCApiMock)
    def test_auto_create_bklog_service(self):
        is_success = Services.auto_create_bklog_service()
        self.assertEqual(is_success, True)

    @patch("backend.dbm_init.services.CCApi.create_biz_custom_field")
    @patch("backend.dbm_init.services.CCApi.search_object_attribute")
    def test_init_cc_dbm_meta_create_attr(self, mock_search_attr, mock_create_attr):
        """当主机模型缺少 dbm 字段时应创建自定义字段"""
        mock_search_attr.return_value = []
        mock_create_attr.return_value = {"result": True}

        Services.init_cc_dbm_meta(bk_biz_id=1)

        mock_create_attr.assert_called_once()

    @patch("backend.dbm_init.services.CCApi.create_biz_custom_field")
    @patch("backend.dbm_init.services.CCApi.search_object_attribute")
    def test_init_cc_dbm_meta_attr_exists(self, mock_search_attr, mock_create_attr):
        """已存在自定义字段时直接返回"""
        mock_search_attr.return_value = [{"bk_property_id": "dbm_meta"}]

        result = Services.init_cc_dbm_meta(bk_biz_id=1)

        self.assertTrue(result)
        mock_create_attr.assert_not_called()

    @patch("backend.dbm_init.services.CCApi.create_object_attribute")
    @patch("backend.dbm_init.services.CCApi.search_object_attribute")
    @patch("backend.dbm_init.services.Services.init_cc_dbm_meta")
    @patch("backend.dbm_init.services.get_or_create_pending_module")
    @patch("backend.dbm_init.services.get_or_create_resource_module")
    @patch("backend.dbm_init.services.AppMonitorTopo.init_topo")
    def test_auto_create_bkcc_service(
        self,
        mock_init_topo,
        mock_resource_module,
        mock_pending_module,
        mock_init_cc_meta,
        mock_search_attr,
        mock_create_attr,
    ):
        """初始化 BKCC 服务时应依次调用拓扑与模块初始化"""
        mock_search_attr.return_value = [{"bk_property_id": "db_app_abbr"}]

        self.assertTrue(Services.auto_create_bkcc_service())
        mock_init_topo.assert_called_once()
        mock_resource_module.assert_called_once()
        mock_pending_module.assert_called_once()
        mock_init_cc_meta.assert_called_once()
        mock_create_attr.assert_not_called()

    @patch.object(Services, "init_custom_metric_and_event")
    def test_auto_create_bkmonitor_channel(self, mock_init_metric):
        """自定义上报通道初始化只需要转调 init_custom_metric_and_event"""
        self.assertTrue(Services.auto_create_bkmonitor_channel())
        mock_init_metric.assert_called_once()

    @patch("backend.dbm_init.services.BkJobFileSourceManager.get_or_create_file_source")
    def test_auto_create_bkjob_service(self, mock_file_source):
        """初始化 BKJob 文件源"""
        Services.auto_create_bkjob_service()
        mock_file_source.assert_called_once()

    @patch("backend.dbm_init.services.api_call")
    def test_auto_register_application(self, mock_api_call):
        """注册通知中心调用成功"""
        mock_api_call.return_value = {"result": True}
        Services.auto_register_application()
        mock_api_call.assert_called_once()

    @patch("backend.dbm_init.services.call_command")
    @patch("backend.dbm_init.services.generate_iam_migration_json")
    def test_auto_create_iam_migrations(self, mock_generate_json, mock_call_command):
        """自动注册 IAM 只需调用脚本与命令"""
        mock_generate_json.side_effect = [None]

        Services.auto_create_iam_migrations()

        mock_generate_json.assert_called_once_with(json_name="initial.json")
        mock_call_command.assert_called_once_with("iam_makemigrations", "initial.json")

    @patch("backend.dbm_init.services.SwitchOrgView.initial")
    def test_auto_init_grafana_success(self, mock_initial):
        user, __ = User.objects.get_or_create(username="admin", is_superuser=True, is_staff=True)

        result = Services.auto_init_grafana()

        self.assertTrue(result)
        mock_initial.assert_called_once()
        request_arg = mock_initial.call_args[0][0]
        self.assertEqual(request_arg.user, user)
        self.assertEqual(getattr(request_arg, "org_name"), "dbm")

    @patch("backend.dbm_init.services.SystemSettings.objects")
    def test_auto_create_ssl_service_skip_when_exists(self, mock_system_objects):
        mock_system_objects.filter.return_value.exists.return_value = True

        result = Services.auto_create_ssl_service()

        self.assertTrue(result)
        mock_system_objects.filter.return_value.exists.assert_called_once()
