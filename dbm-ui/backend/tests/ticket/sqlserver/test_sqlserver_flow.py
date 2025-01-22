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
from unittest.mock import patch

import pytest

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, Machine, StorageInstance, StorageInstanceTuple
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
    SQLSERVER_HA_MANUAL_DATA,
    SQLSERVER_IMPORT_SQLFILE_TICKET_DATA,
    SQLSERVER_MACHINE_DATA,
    SQLSERVER_MASTER_FAIL_OVER_TICKET_DATA,
    SQLSERVER_MASTER_SLAVE_SWITCH_TICKET_DATA,
    SQLSERVER_RESET_TICKET_DATA,
    SQLSERVER_RESTORE_LOCAL_SLAVE_TICKET_DATA,
    SQLSERVER_RESTORE_SLAVE_SOURCE_TICKET_DATA,
    SQLSERVER_RESTORE_SLAVE_TICKET_DATA,
    SQLSERVER_ROLLBACK_TICKET_DATA,
    SQLSERVER_SINGLE_APPLY_TICKET_DATA,
    SQLSERVER_SINGLE_MANUAL_DATA,
    SQLSERVER_STORAGE_INSTANCE_DATA,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_sqlserver_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 创建外部用户和内外部用户映射
        DBModule.objects.bulk_create([DBModule(**data) for data in DB_MODULE_DATA])
        Machine.objects.bulk_create([Machine(**data) for data in SQLSERVER_MACHINE_DATA])
        Cluster.objects.bulk_create([Cluster(**data) for data in SQLSERVER_CLUSTER_DATA])
        StorageInstance.objects.bulk_create([StorageInstance(**data) for data in SQLSERVER_STORAGE_INSTANCE_DATA])
        cluster_single = Cluster.objects.get(cluster_type=ClusterType.SqlserverSingle.value)
        cluster_ha = Cluster.objects.get(cluster_type=ClusterType.SqlserverHA.value)
        storage_instance_single = StorageInstance.objects.get(cluster_type=ClusterType.SqlserverSingle.value)
        storage_instances = StorageInstance.objects.filter(cluster_type=ClusterType.SqlserverHA.value)
        StorageInstanceTuple.objects.create(ejector=storage_instances[0], receiver=storage_instances[1])
        storage_instance_single.cluster.add(cluster_single)
        for storageinstance in storage_instances:
            storageinstance.cluster.add(cluster_ha)
        yield
        DBModule.objects.all().delete()
        Cluster.objects.all().delete()
        StorageInstance.objects.all().delete()
        Machine.objects.all().delete()


class TestSqlServerApplyFlow(BaseTicketTest):
    """
    SQLSERVER APPLY测试类。
    """

    # SQLSERVER single部署: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
    def test_sqlserver_single_apply_flow(self):
        self.flow_test(SQLSERVER_SINGLE_APPLY_TICKET_DATA)

    # SQLSERVER single手动输入部署: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_single_manual_apply_flow(self):
        self.flow_test(SQLSERVER_SINGLE_MANUAL_DATA)

    # SQLSERVER ha部署: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
    def test_sqlserver_ha_apply_flow(self):
        self.flow_test(SQLSERVER_HA_APPLY_TICKET_DATA)

    # SQLSERVER ha手动部署: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_ha_manual_apply_flow(self):
        self.flow_test(SQLSERVER_HA_MANUAL_DATA)

    # SQLSERVER disable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_disable_flow(self):
        self.flow_test(SQLSERVER_DISABLE_TICKET_DATA)

    # SQLSERVER enable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_enable_flow(self):
        self.flow_test(SQLSERVER_ENABLE_TICKET_DATA)

    # SQLSERVER destroy: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_destroy_flow(self):
        self.flow_test(SQLSERVER_DESTROY_TICKET_DATA)

    # SQLSERVER dbrename: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_dbrename_flow(self):
        self.flow_test(SQLSERVER_DBRENAME_TICKET_DATA)

    # SQLSERVER backup: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_backup_flow(self):
        self.flow_test(SQLSERVER_BACKUP_TICKET_DATA)

    # SQLSERVER data_migrate: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_data_migrate_flow(self):
        self.flow_test(SQLSERVER_DATA_MIGRATE_TICKET_DATA)

    # SQLSERVER clear: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_sqlserver_clear_flow(self):
        self.flow_test(SQLSERVER_CLEAR_DBS_TICKET_DATA)

    # SQLSERVER import_sqlfile: start --> itsm --> INNER_FLOW --> end
    def test_sqlserver_import_sqlfile_flow(self):
        self.flow_test(SQLSERVER_IMPORT_SQLFILE_TICKET_DATA)

    # SQLSERVER master_slave_switch: start --> itsm --> INNER_FLOW --> end
    def test_master_slave_switch_flow(self):
        self.flow_test(SQLSERVER_MASTER_SLAVE_SWITCH_TICKET_DATA)

    # SQLSERVER master_fail_over: start --> itsm --> INNER_FLOW --> end
    def test_master_fail_over_flow(self):
        self.flow_test(SQLSERVER_MASTER_FAIL_OVER_TICKET_DATA)

    # SQLSERVER reset: start --> itsm --> INNER_FLOW --> end
    def test_sqlserver_reset_flow(self):
        self.flow_test(SQLSERVER_RESET_TICKET_DATA)

    # SQLSERVER restore_local_slave: start --> itsm --> INNER_FLOW --> end
    def test_restore_local_slave_flow(self):
        self.flow_test(SQLSERVER_RESTORE_LOCAL_SLAVE_TICKET_DATA)

    # SQLSERVER restore_slave: start --> itsm --> INNER_FLOW --> end
    def test_restore_slave_flow(self):
        self.flow_test(SQLSERVER_RESTORE_SLAVE_TICKET_DATA)

    # SQLSERVER restore_slave_source: start --> itsm --> INNER_FLOW --> end
    def test_restore_slave_source_flow(self):
        self.flow_test(SQLSERVER_RESTORE_SLAVE_SOURCE_TICKET_DATA)

    # SQLSERVER restore_rollback: start --> itsm --> INNER_FLOW --> end
    def test_sqlserver_rollback_flow(self):
        self.flow_test(SQLSERVER_ROLLBACK_TICKET_DATA)

    @classmethod
    def apply_patches(cls):
        # 扩展基类的apply_patches方法来包括新的patch
        # 定义并启动新的patch
        mock_get_drs_api_patch = patch(
            "backend.flow.utils.sqlserver.sqlserver_db_function.DRSApi", new_callable=lambda: DRSApiMock()
        )
        mock_clear_drs_api_patch = patch(
            "backend.db_services.sqlserver.handlers.DRSApi", new_callable=lambda: DRSApiMock()
        )
        mock_single_module_infos_patch = patch(
            "backend.ticket.builders.sqlserver.sqlserver_single_apply.get_module_infos",
            return_value=DBCONFIG_DATA,
        )
        mock_restore_slave_module_infos_patch = patch(
            "backend.ticket.builders.sqlserver.sqlserver_restore_slave.get_module_infos",
            return_value=DBCONFIG_DATA,
        )
        mock_validate_sqlserver_table_selector_patch = patch(
            "backend.ticket.builders.common.base.CommonValidate.validate_sqlserver_table_selector",
            lambda *args, **kwargs: (True, ""),
        )
        # 启动新的patch并添加到self.mocks列表中以便随后可以停止它
        cls.patches.extend(
            [
                mock_get_drs_api_patch,
                mock_clear_drs_api_patch,
                mock_single_module_infos_patch,
                mock_restore_slave_module_infos_patch,
                mock_validate_sqlserver_table_selector_patch,
            ]
        )
        super().apply_patches()
