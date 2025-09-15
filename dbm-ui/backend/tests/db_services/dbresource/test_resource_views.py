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

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend import env
from backend.db_dirty.constants import MachineEventType
from backend.db_meta.enums.spec import SpecClusterType, SpecMachineType
from backend.db_meta.models import Spec
from backend.db_meta.models.machine import DeviceClass
from backend.db_services.dbresource.views.resource import DBResourceViewSet
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.tests.mock_data import constant
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """禁用中间件以简化测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(scope="class", autouse=True)
def setup_class(django_db_setup, django_db_blocker):
    """设置测试类 - 禁用权限验证"""
    with django_db_blocker.unblock():
        # 禁用权限验证
        patch.object(DBResourceViewSet, "permission_classes", [AllowAny]).start()
        patch.object(DBResourceViewSet, "get_permissions", lambda x: []).start()
        # Mock IAM权限
        patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
        yield


class TestDBResourceViewSet:
    """测试 DBResourceViewSet 类"""

    @patch("backend.db_services.dbresource.handlers.ResourceHandler.resource_list")
    def test_resource_list(self, mock_resource_list):
        """测试资源池资源列表"""
        mock_resource_list.return_value = {
            "count": 1,
            "results": [{"ip": "1.1.1.1", "bk_host_id": 1, "bk_cloud_id": 0}],
        }

        url = "/apis/dbresource/resource/list/"
        response = client.post(url, data={"limit": 10, "offset": 0}, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["count"] == 1
        assert mock_resource_list.called

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_hosts")
    @patch("backend.db_services.ipchooser.handlers.topo_handler.TopoHandler.trees")
    @patch("backend.db_services.ipchooser.handlers.topo_handler.TopoHandler.query_hosts")
    @patch("backend.components.dbresource.client.DBResourceApi.resource_list_all")
    def test_list_dba_hosts(self, mock_resource_list, mock_query_hosts, mock_trees, mock_search_hosts):
        """测试获取DBA业务下的主机信息"""
        mock_trees.return_value = [
            {"instance_id": 1, "meta": {"bk_biz_id": env.DBA_APP_BK_BIZ_ID}, "object_id": "module"}
        ]
        mock_resource_list.return_value = {"details": [{"bk_host_id": 10001}]}
        mock_query_hosts.return_value = {
            "total": 2,
            "data": [{"host_id": 10001, "ip": "1.1.1.1"}, {"host_id": 10002, "ip": "1.1.1.2"}],
        }

        url = f"/apis/dbresource/resource/list_dba_hosts/?bk_biz_id={env.DBA_APP_BK_BIZ_ID}"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "data" in result
        # 验证占用标记
        assert result["data"][0]["occupancy"] is True
        assert result["data"][1]["occupancy"] is False

    @patch("backend.db_services.ipchooser.handlers.host_handler.HostHandler.details")
    def test_query_dba_hosts(self, mock_details):
        """测试查询DBA业务下的主机信息"""
        mock_details.return_value = [{"host_id": 10001, "ip": "1.1.1.1", "bk_cloud_id": 0}]

        url = "/apis/dbresource/resource/query_dba_hosts/?bk_host_ids=10001,10002"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert mock_details.called

    @patch("backend.ticket.models.Ticket.create_ticket")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_hosts")
    def test_resource_import(self, mock_search_hosts, mock_create_ticket):
        """测试资源导入"""
        mock_search_hosts.return_value = [
            {
                "bk_host_id": 10001,
                "bk_host_innerip": "1.1.1.1",
                "bk_os_type": "linux",
                "idc_city_name": "shanghai",
                "bk_cloud_id": 0,
            }
        ]
        mock_ticket = MagicMock()
        mock_ticket.id = 12345
        mock_create_ticket.return_value = mock_ticket

        url = "/apis/dbresource/resource/import/"
        data = {
            "for_biz": constant.BK_BIZ_ID,
            "resource_type": "mysql",
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "hosts": [{"ip": "1.1.1.1", "host_id": 10001, "bk_cloud_id": 0}],
            "labels": ["test"],
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "ticket_ids" in result
        assert len(result["ticket_ids"]) > 0

    @patch("backend.utils.redis.RedisConn.zrange")
    @patch("backend.flow.models.FlowTree.objects.filter")
    def test_query_resource_import_tasks(self, mock_filter, mock_zrange):
        """测试查询资源导入任务"""
        mock_zrange.return_value = ["root_id_1", "root_id_2"]
        # 创建模拟的FlowTree对象
        done_tree = MagicMock()
        done_tree.root_id = "root_id_1"
        done_tree.status = StateType.FINISHED
        processing_tree = MagicMock()
        processing_tree.root_id = "root_id_2"
        processing_tree.status = StateType.RUNNING
        mock_filter.return_value = [done_tree, processing_tree]

        url = "/apis/dbresource/resource/query_import_tasks/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "task_ids" in result
        assert len(result["task_ids"]) == 1
        assert "root_id_2" in result["task_ids"]

    @patch("backend.components.dbresource.client.DBResourceApi.resource_apply")
    def test_resource_apply(self, mock_apply):
        """测试资源申请"""
        mock_apply.return_value = {"request_id": "req_123", "details": []}

        url = "/apis/dbresource/resource/apply/"
        data = {
            "bk_cloud_id": 0,
            "resource_type": "mysql",
            "for_biz_id": constant.BK_BIZ_ID,
            "details": [{"group_mark": "backend", "count": 2, "spec": {"cpu": 8, "mem": 32}}],
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_apply.called

    @patch("backend.components.dbresource.client.DBResourceApi.get_mountpoints")
    def test_get_mountpoints(self, mock_get_mountpoints):
        """测试获取挂载点"""
        mock_get_mountpoints.return_value = ["/data", "/data1"]

        url = "/apis/dbresource/resource/get_mountpoints/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert mock_get_mountpoints.called

    @patch("backend.components.dbresource.client.DBResourceApi.get_disktypes")
    def test_get_disktypes(self, mock_get_disktypes):
        """测试获取磁盘类型"""
        mock_get_disktypes.return_value = ["SSD", "SATA"]

        url = "/apis/dbresource/resource/get_disktypes/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert mock_get_disktypes.called

    def test_get_os_types(self):
        """测试获取操作系统类型"""
        url = "/apis/dbresource/resource/get_os_types/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert isinstance(result, list)
        assert len(result) > 0

    @patch("backend.components.dbresource.client.DBResourceApi.get_subzones")
    def test_get_subzones(self, mock_get_subzones):
        """测试根据逻辑城市查询园区"""
        mock_get_subzones.return_value = [{"sub_zone_id": "zone1", "sub_zone": "Zone 1"}]

        url = "/apis/dbresource/resource/get_subzones/?citys=shanghai"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert mock_get_subzones.called

    def test_get_device_class(self):
        """测试获取机型列表"""
        # 创建测试数据
        device = DeviceClass.objects.create(device_type="S5", cpu=8, mem=32, disk=500)

        url = "/apis/dbresource/resource/get_device_class/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "results" in result
        # 清理
        device.delete()

    @patch("backend.components.dbresource.client.DBResourceApi.resource_pre_apply")
    def test_resource_pre_apply(self, mock_pre_apply):
        """测试资源预申请"""
        mock_pre_apply.return_value = {"request_id": "req_456", "details": []}

        url = "/apis/dbresource/resource/pre_apply/"
        data = {
            "bk_cloud_id": 0,
            "resource_type": "mysql",
            "for_biz_id": constant.BK_BIZ_ID,
            "details": [{"group_mark": "backend", "count": 2, "spec": {"cpu": 8, "mem": 32}}],
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "resource_request_id" in result

    @patch("backend.components.dbresource.client.DBResourceApi.resource_confirm")
    def test_resource_confirm(self, mock_confirm):
        """测试资源确认"""
        mock_confirm.return_value = {"result": True}

        url = "/apis/dbresource/resource/confirm/"
        data = {"request_id": "req_123", "host_ids": [10001, 10002]}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_confirm.called

    @patch("backend.components.dbresource.client.DBResourceApi.resource_delete")
    @patch("backend.db_dirty.models.MachineEvent.host_event_trigger")
    def test_resource_delete_fault(self, mock_trigger, mock_delete):
        """测试资源删除 - 转移故障池"""
        mock_delete.return_value = {"result": True}

        url = "/apis/dbresource/resource/delete/"
        data = {
            "hosts": [{"bk_host_id": 10001, "bk_biz_id": constant.BK_BIZ_ID, "ip": "1.1.1.1", "bk_cloud_id": 0}],
            "event": MachineEventType.ToFault,
            "remark": "test delete",
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_trigger.called
        assert mock_delete.called

    @patch("backend.components.dbresource.client.DBResourceApi.resource_delete")
    @patch("backend.db_dirty.models.MachineEvent.hosts_can_return")
    @patch("backend.db_dirty.models.MachineEvent.host_event_trigger")
    @patch("backend.flow.utils.cc_manage.CcManage.transfer_host_to_idlemodule_across_biz")
    def test_resource_delete_undo_import(self, mock_transfer, mock_trigger, mock_can_return, mock_delete):
        """测试资源删除 - 撤销导入"""
        mock_can_return.return_value = (True, "")
        mock_delete.return_value = {"result": True}

        url = "/apis/dbresource/resource/delete/"
        data = {
            "hosts": [{"bk_host_id": 10001, "bk_biz_id": constant.BK_BIZ_ID, "ip": "1.1.1.1", "bk_cloud_id": 0}],
            "event": MachineEventType.UndoImport,
            "remark": "undo import",
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_can_return.called
        assert mock_trigger.called
        assert mock_transfer.called

    @patch("backend.components.dbresource.client.DBResourceApi.resource_batch_update")
    def test_resource_update(self, mock_update):
        """测试资源更新"""
        mock_update.return_value = {"result": True}

        url = "/apis/dbresource/resource/update/"
        data = {"bk_host_ids": [10001], "labels": ["updated"], "for_biz": constant.BK_BIZ_ID}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_update.called

    @patch("backend.components.dbresource.client.DBResourceApi.resource_group_count")
    def test_resource_group_count(self, mock_group_count):
        """测试按照组件统计资源数量"""
        mock_group_count.return_value = {"mysql": 10, "redis": 5}

        url = "/apis/dbresource/resource/resource_group_count/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert mock_group_count.called

    @patch("backend.components.dbresource.client.DBResourceApi.resource_summary")
    @patch("backend.db_meta.models.AppCache.batch_get_app_attr")
    def test_resource_summary(self, mock_batch_get, mock_summary):
        """测试按照条件聚合资源统计"""
        mock_summary.return_value = {
            "no_spec_ip_list": [],
            "summary_data": [{"dedicated_biz": constant.BK_BIZ_ID, "count": 10}],
        }
        mock_batch_get.return_value = {constant.BK_BIZ_ID: "test_biz"}

        url = "/apis/dbresource/resource/resource_summary/?db_type=mysql&group_by=device_class"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "summary_data" in result
        assert "for_biz_name" in result["summary_data"][0]

    def test_resource_import_urls(self):
        """测试获取资源导入相关链接"""
        url = "/apis/dbresource/resource/resource_import_urls/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "bk_cmdb_url" in result
        assert "bk_nodeman_url" in result
        assert "bk_scr_url" in result

    @patch("backend.components.dbresource.client.DBResourceApi.operation_list")
    def test_query_operation_list(self, mock_operation_list):
        """测试查询资源操作记录"""
        # 创建模拟FlowTree
        tree = FlowTree.objects.create(
            root_id="task_123",
            bk_biz_id=constant.BK_BIZ_ID,
            tree={},
            status=StateType.FINISHED,
        )

        mock_operation_list.return_value = {
            "details": [
                {
                    "task_id": "task_123",
                    "bill_id": "12345",
                    "bill_type": TicketType.RESOURCE_IMPORT,
                    "operator": "admin",
                }
            ]
        }

        url = "/apis/dbresource/resource/query_operation_list/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "results" in result
        if result["results"]:
            assert "ticket_id" in result["results"][0]
            assert "ticket_type_display" in result["results"][0]

        # 清理
        tree.delete()

    @patch("backend.db_services.dbresource.handlers.ResourceHandler.spec_resource_count")
    def test_spec_resource_count(self, mock_spec_count):
        """测试规格数量的预计"""
        # 创建测试规格
        spec = Spec.objects.create(
            spec_id=6000,
            spec_name="test_spec",
            spec_cluster_type=SpecClusterType.MySQL.value,
            spec_machine_type=SpecMachineType.BACKEND.value,
            cpu={"max": 8, "min": 8},
            mem={"max": 32, "min": 32},
            storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
            device_class=["S5"],
            enable=True,
        )

        mock_spec_count.return_value = {"6000": 10}

        url = "/apis/dbresource/resource/spec_resource_count/"
        data = {
            "bk_biz_id": constant.BK_BIZ_ID,
            "bk_cloud_id": 0,
            "spec_ids": [6000],
            "city": "shanghai",
            "sub_zone_ids": [1],
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_spec_count.called

        # 清理
        spec.delete()

    @patch("backend.db_services.dbresource.handlers.ResourceHandler.spec_cost_estimate")
    def test_spec_cost_estimate(self, mock_cost_estimate):
        """测试规格成本预估"""
        # 创建测试规格
        spec = Spec.objects.create(
            spec_id=6001,
            spec_name="cost_spec",
            spec_cluster_type=SpecClusterType.MySQL.value,
            spec_machine_type=SpecMachineType.BACKEND.value,
            cpu={"max": 16, "min": 16},
            mem={"max": 64, "min": 64},
            storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
            device_class=["S5"],
            enable=True,
        )

        mock_cost_estimate.return_value = 5000

        url = "/apis/dbresource/resource/spec_cost_estimate/"
        data = {
            "cluster_type": SpecClusterType.MySQL.value,
            "resource_spec": {"backend_group": {"spec_id": 6001, "count": 2}},
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        # 清理
        spec.delete()

    @patch("backend.components.hcm.client.HCMApi.check_host_has_uwork")
    @patch("backend.components.xwork.client.XworkApi.check_xwork_list")
    def test_check_fault_hosts(self, mock_xwork, mock_uwork):
        """测试查询故障主机信息"""
        mock_uwork.return_value = {10001: {"order_id": "U123", "status": "running"}}
        mock_xwork.return_value = {10001: {"order_id": "X456", "status": "pending"}}

        url = "/apis/dbresource/resource/check_fault_hosts/"
        data = {"hosts": [{"ip": "1.1.1.1", "bk_host_id": 10001}]}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "10001" in result
        assert "uwork" in result["10001"]
        assert "xwork" in result["10001"]

    @patch("backend.components.dbresource.client.DBResourceApi.resource_append_labels")
    def test_append_labels(self, mock_append):
        """测试追加主机标签"""
        mock_append.return_value = {"result": True}

        url = "/apis/dbresource/resource/append_labels/"
        data = {"bk_host_ids": [10001], "labels": ["new_label"]}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_append.called
