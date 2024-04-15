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
import logging
from unittest import TestCase
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, Machine, Spec, StorageInstance
from backend.db_meta.models.db_module import DBModule
from backend.tests.mock_data.components.drs import DRSApiMock
from backend.tests.mock_data.ticket.sqlserver_flow import (
    DB_MODULE_DATA,
    DBCONFIG_DATA,
    SQLSERVER_BACKUP_TICKET_DATA,
    SQLSERVER_CLEAR_DBS_TICKET_DATA,
    SQLSERVER_CLUSTER_DATA,
    SQLSERVER_DATA_MIGRATE_TICKET_DATA,
    SQLSERVER_DBRENAME_TICKET_DATA,
    SQLSERVER_DESTROY_TICKET_DATA,
    SQLSERVER_DISABLE_TICKET_DATA,
    SQLSERVER_ENABLE_TICKET_DATA,
    SQLSERVER_HA_APPLY_TICKET_DATA,
    SQLSERVER_MACHINE_DATA,
    SQLSERVER_SINGLE_APPLY_TICKET_DATA,
    SQLSERVER_SOURCE_APPLICATION_DATA,
    SQLSERVER_SPEC_DATA,
    SQLSERVER_STORAGE_INSTANCE_DATA,
)
from backend.tests.ticket.server_base import TestFlowBase
from backend.ticket.constants import TicketFlowStatus, TicketStatus

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()

INITIAL_FLOW_FINISHED_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED]
CHANGED_MOCK_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED, TicketFlowStatus.RUNNING]


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestSqlServerApplyFlow(TestFlowBase, TestCase):
    """
    SQLSERVER APPLY测试类。
    """

    # SQLSERVER single部署: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
    def test_sqlserver_single_apply_flow(self):
        self.flow_test(client, SQLSERVER_SINGLE_APPLY_TICKET_DATA)

    # SQLSERVER ha部署: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
    def test_sqlserver_ha_apply_flow(self):
        self.flow_test(client, SQLSERVER_HA_APPLY_TICKET_DATA)

    # SQLSERVER disable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_disable_flow(self):
        self.flow_test(client, SQLSERVER_DISABLE_TICKET_DATA)

    # SQLSERVER enable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_enable_flow(self):
        self.flow_test(client, SQLSERVER_ENABLE_TICKET_DATA)

    # SQLSERVER destroy: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_destroy_flow(self):
        self.flow_test(client, SQLSERVER_DESTROY_TICKET_DATA)

    # SQLSERVER dbrename: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_dbrename_flow(self):
        self.flow_test(client, SQLSERVER_DBRENAME_TICKET_DATA)

    # SQLSERVER backup: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_backup_flow(self):
        self.flow_test(client, SQLSERVER_BACKUP_TICKET_DATA)

    # SQLSERVER data_migrate: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_data_migrate_flow(self):
        self.flow_test(client, SQLSERVER_DATA_MIGRATE_TICKET_DATA)

    # SQLSERVER clear: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_clear_flow(self):
        self.flow_test(client, SQLSERVER_CLEAR_DBS_TICKET_DATA)

    def apply_patches(self):
        # 扩展基类的apply_patches方法来包括新的patch
        super().apply_patches()

        # 定义并启动新的patch
        mock_resource_apply_patch = patch(
            "backend.ticket.flow_manager.resource.ResourceApplyFlow.apply_resource",
            lambda resource_request_id, node_infos: (1, SQLSERVER_SOURCE_APPLICATION_DATA),
        )
        mock_get_drs_api_patch = patch(
            "backend.flow.utils.sqlserver.sqlserver_db_function.DRSApi", new_callable=lambda: DRSApiMock()
        )
        mock_get_module_infos_patch = patch(
            "backend.ticket.builders.sqlserver.sqlserver_single_apply.get_module_infos",
            return_value={"mocked_key": "mocked_value"},
        )
        # 启动新的patch并添加到self.mocks列表中以便随后可以停止它
        self.mocks.extend(
            [mock_resource_apply_patch.start(), mock_get_drs_api_patch.start(), mock_get_module_infos_patch.start()]
        )

    def setup(self):
        """
        测试的初始设置。
        """
        DBModule.objects.bulk_create([DBModule(**data) for data in DB_MODULE_DATA])
        Spec.objects.bulk_create([Spec(**data) for data in SQLSERVER_SPEC_DATA])
        Machine.objects.bulk_create([Machine(**data) for data in SQLSERVER_MACHINE_DATA])
        Cluster.objects.bulk_create([Cluster(**data) for data in SQLSERVER_CLUSTER_DATA])
        StorageInstance.objects.bulk_create([StorageInstance(**data) for data in SQLSERVER_STORAGE_INSTANCE_DATA])
        cluster_single = Cluster.objects.get(cluster_type=ClusterType.SqlserverSingle.value)
        cluster_ha = Cluster.objects.get(cluster_type=ClusterType.SqlserverHA.value)
        storage_instance_single = StorageInstance.objects.get(cluster_type=ClusterType.SqlserverSingle.value)
        storage_instance_ha = StorageInstance.objects.get(cluster_type=ClusterType.SqlserverHA.value, machine_id=2)
        storage_instance_single.cluster.add(cluster_single)
        storage_instance_ha.cluster.add(cluster_ha)

        super().setup()
        self.mocks[-1].return_value = DBCONFIG_DATA

    def teardown(self):
        """
        清理数据环境。
        """
        DBModule.objects.all().delete()
        Spec.objects.all().delete()
        Cluster.objects.all().delete()
        StorageInstance.objects.all().delete()
        Machine.objects.all().delete()

        super().teardown()
