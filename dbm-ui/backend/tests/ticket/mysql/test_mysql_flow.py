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
import copy
import logging
import os
import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, Spec, StorageInstance
from backend.flow.models import FlowNode, FlowTree
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.drs import DRSApiMock
from backend.tests.mock_data.components.mysql_priv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.components.sql_import import SQLSimulationApiMock
from backend.tests.mock_data.flow.engine.bamboo.engine import BambooEngineMock
from backend.tests.mock_data.ticket.mysql_flow import (
    MYSQL_ADD_SLAVE_DATA,
    MYSQL_AUTHORIZE_TICKET_DATA,
    MYSQL_CHECKSUM_DATA,
    MYSQL_CLUSTER_DATA,
    MYSQL_DATA_MIGRATE_DATA,
    MYSQL_DELETE_CLEAR_DB_DATA,
    MYSQL_DUMP_DATA,
    MYSQL_FLASHBACK_DATA,
    MYSQL_HA_DB_TABLE_BACKUP_DATA,
    MYSQL_HA_FULL_BACKUP_DATA,
    MYSQL_ITSM_AUTHORIZE_TICKET_DATA,
    MYSQL_MACHINE_DATA,
    MYSQL_MASTER_SLAVE_SWITCH_DATA,
    MYSQL_PROXY_ADD_DATA,
    MYSQL_PROXY_SWITCH_DATA,
    MYSQL_PROXYINSTANCE_DATA,
    MYSQL_ROLLBACK_CLUSTER_DATA,
    MYSQL_SINGLE_APPLY_TICKET_DATA,
    MYSQL_SPEC_DATA,
    MYSQL_STORAGE_INSTANCE,
    MYSQL_TENDBHA_TICKET_DATA,
    SQL_IMPORT_FLOW_NODE_DATA,
    SQL_IMPORT_TICKET_DATA,
)
from backend.tests.mock_data.ticket.ticket_flow import FLOW_TREE_DATA
from backend.tests.ticket.server_base import BaseTicketTest
from backend.ticket.constants import EXCLUSIVE_TICKET_EXCEL_PATH, TicketType
from backend.utils.excel import ExcelHandler

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_mysql_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        clusters = Cluster.objects.bulk_create([Cluster(**data) for data in MYSQL_CLUSTER_DATA])
        Machine.objects.bulk_create([Machine(**data) for data in MYSQL_MACHINE_DATA])
        storage_instances = StorageInstance.objects.bulk_create(
            [StorageInstance(**data) for data in MYSQL_STORAGE_INSTANCE]
        )
        storage_instances[0].cluster.add(clusters[0])
        storage_instances[1].cluster.add(clusters[0])
        storage_instances[2].cluster.add(clusters[1])
        proxy_instances = ProxyInstance.objects.bulk_create(
            [ProxyInstance(**data) for data in MYSQL_PROXYINSTANCE_DATA]
        )
        proxy_instances[0].cluster.add(clusters[0])
        proxy_instances[0].storageinstance.add(storage_instances[0])
        proxy_instances[0].storageinstance.add(storage_instances[1])
        Spec.objects.bulk_create([Spec(**data) for data in MYSQL_SPEC_DATA])
        FlowTree.objects.create(**FLOW_TREE_DATA)
        FlowNode.objects.create(**SQL_IMPORT_FLOW_NODE_DATA)
        yield
        mysql_cluster_types = ClusterType.db_type_to_cluster_types(DBType.MySQL)
        Cluster.objects.filter(cluster_type__in=mysql_cluster_types).delete()
        ProxyInstance.objects.filter(cluster_type__in=mysql_cluster_types).delete()
        StorageInstance.objects.filter(cluster_type__in=mysql_cluster_types).delete()
        Machine.objects.filter(cluster_type__in=mysql_cluster_types).delete()
        Spec.objects.filter(spec_cluster_type=DBType.Redis).delete()
        FlowTree.objects.all().delete()
        FlowNode.objects.all().delete()


class TestMySQLTicket(BaseTicketTest):
    """
    测试mysql授权流程正确性
    """

    @classmethod
    def apply_patches(cls):
        mock_list_account_rules_patch = patch(
            "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi", DBPrivManagerApiMock
        )
        mock_dbconfig_api_patch = patch(
            "backend.ticket.builders.mysql.mysql_single_apply.DBConfigApi", DBConfigApiMock
        )
        mock_simulation_api_patch = patch(
            "backend.ticket.builders.mysql.mysql_import_sqlfile.SQLSimulationApi", SQLSimulationApiMock
        )
        mock_bamboo_api_patch = patch(
            "backend.ticket.builders.mysql.mysql_import_sqlfile.BambooEngine", BambooEngineMock
        )
        mock_cc_api_patch = patch("backend.db_meta.models.app.CCApi", CCApiMock())
        mock_drs_api_patch = patch(
            "backend.db_services.mysql.remote_service.handlers.DRSApi", new_callable=lambda: DRSApiMock()
        )
        cls.patches.extend(
            [
                mock_list_account_rules_patch,
                mock_dbconfig_api_patch,
                mock_simulation_api_patch,
                mock_bamboo_api_patch,
                mock_cc_api_patch,
                mock_drs_api_patch,
            ]
        )
        super().apply_patches()

    def test_mysql_authorize_ticket_flow(self):
        authorize_uid = uuid.uuid1().hex
        cache.set(authorize_uid, MYSQL_ITSM_AUTHORIZE_TICKET_DATA)
        authorize_data = copy.deepcopy(MYSQL_AUTHORIZE_TICKET_DATA)
        authorize_data["details"]["authorize_uid"] = authorize_uid
        self.flow_test(authorize_data)
        cache.delete(authorize_uid)

    def test_mysql_master_slave_switch_flow(self):
        self.flow_test(MYSQL_MASTER_SLAVE_SWITCH_DATA)

    def test_mysql_proxy_add_flow(self):
        self.flow_test(MYSQL_PROXY_ADD_DATA)

    def test_mysql_proxy_switch_flow(self):
        self.flow_test(MYSQL_PROXY_SWITCH_DATA)

    def test_mysql_ha_db_table_backup_flow(self):
        self.flow_test(MYSQL_HA_DB_TABLE_BACKUP_DATA)

    def test_mysql_delete_clear_db_flow(self):
        self.flow_test(MYSQL_DELETE_CLEAR_DB_DATA)

    def test_mysql_rollback_cluster_data_flow(self):
        self.flow_test(MYSQL_ROLLBACK_CLUSTER_DATA)

    def test_mysql_flashback_data_flow(self):
        self.flow_test(MYSQL_FLASHBACK_DATA)

    def test_mysql_add_slave_flow(self):
        self.flow_test(MYSQL_ADD_SLAVE_DATA)

    def test_mysql_checksum_flow(self):
        self.flow_test(MYSQL_CHECKSUM_DATA)

    def test_mysql_full_backup_flow(self):
        self.flow_test(MYSQL_HA_FULL_BACKUP_DATA)

    def test_mysql_data_migrate_flow(self):
        self.flow_test(MYSQL_DATA_MIGRATE_DATA)

    def test_mysql_single_apply_flow(self):
        self.flow_test(MYSQL_SINGLE_APPLY_TICKET_DATA)

    def test_mysql_sql_import_flow(self):
        self.flow_test(SQL_IMPORT_TICKET_DATA)

    def test_mysql_ha_apply_flow(self):
        self.flow_test(MYSQL_TENDBHA_TICKET_DATA)

    def test_mysql_dump_data_flow(self, init_mysql_cluster):
        cluster = Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).first()
        MYSQL_DUMP_DATA["details"]["cluster_id"] = cluster.id
        self.flow_test(MYSQL_DUMP_DATA)

    def test_exclusive_ticket_map(self):
        # 测试互斥表互斥逻辑正常
        path = os.path.join(settings.BASE_DIR, EXCLUSIVE_TICKET_EXCEL_PATH)
        exclusive_matrix = ExcelHandler.paser_matrix(path)
        invalid_labels = set(exclusive_matrix.keys()) - set(TicketType.get_labels())
        logger.warning("invalid_labels is %s", invalid_labels)
        assert len(invalid_labels) == 0
