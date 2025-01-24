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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster, Machine, StorageInstance
from backend.tests.mock_data import constant
from backend.tests.mock_data.ticket.doris_flow import (
    DORIS_APPLY_TICKET_DATA,
    DORIS_CLUSTER_DATA,
    DORIS_DESTROY_TICKET_DATA,
    DORIS_DISABLE_TICKET_DATA,
    DORIS_ENABLE_TICKET_DATA,
    DORIS_MACHINE_DATA,
    DORIS_REBOOT_TICKET_DATA,
    DORIS_REPLACE_TICKET_DATA,
    DORIS_SHRINK_TICKET_DATA,
    DORIS_STORAGE_INSTANCE_DATA,
    SCALEUP_INPUT_TICKET_DATA,
    SCALEUP_POOL_TICKET_DATA,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_doris_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 创建外部用户和内外部用户映射
        AppCache.objects.get_or_create(bk_biz_id=constant.BK_BIZ_ID, db_app_abbr="DBA", bk_biz_name="dba")
        Cluster.objects.bulk_create([Cluster(**data) for data in DORIS_CLUSTER_DATA])
        Machine.objects.bulk_create([Machine(**data) for data in DORIS_MACHINE_DATA])
        StorageInstance.objects.bulk_create([StorageInstance(**data) for data in DORIS_STORAGE_INSTANCE_DATA])
        cluster = Cluster.objects.first()
        storage_instance = StorageInstance.objects.filter(cluster_type=ClusterType.Doris.value)
        cluster.storageinstance_set.set(storage_instance, clear=True)
        yield
        Cluster.objects.filter(cluster_type=ClusterType.Doris.value).delete()
        StorageInstance.objects.filter(cluster_type=ClusterType.Doris.value).delete()
        Machine.objects.filter(cluster_type=ClusterType.Doris.value).delete()


class TestDorisApplyFlow(BaseTicketTest):
    """
    DORIS APPLY测试类。
    """

    # DORIS apply: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
    def test_doris_single_apply_flow(self):
        self.flow_test(DORIS_APPLY_TICKET_DATA)

    # DORIS disable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_disable_flow(self):
        self.flow_test(DORIS_DISABLE_TICKET_DATA)

    # DORIS enable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_enable_flow(self):
        self.flow_test(DORIS_ENABLE_TICKET_DATA)

    # DORIS destroy: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_destroy_flow(self):
        self.flow_test(DORIS_DESTROY_TICKET_DATA)

    # DORIS scale_up_pool: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_scaleup_pool_flow(self):
        self.flow_test(SCALEUP_POOL_TICKET_DATA)

    # DORIS scale_up_input: start --> itsm --> INNER_FLOW --> end
    def test_scaleup_input_flow(self):
        self.flow_test(SCALEUP_INPUT_TICKET_DATA)

    # DORIS shrink: start --> itsm --> INNER_FLOW --> end
    def test_doris_shrink_flow(self):
        self.flow_test(DORIS_SHRINK_TICKET_DATA)

    # DORIS reboot: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_reboot_flow(self):
        self.flow_test(DORIS_REBOOT_TICKET_DATA)

    # DORIS replace: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_replace_flow(self):
        self.flow_test(DORIS_REPLACE_TICKET_DATA)

    @classmethod
    def apply_patches(cls):
        # 定义并启动新的patch
        mock_idle_pool_patch = patch(
            "backend.ticket.builders.common.bigdata.BigDataDetailsSerializer.validate_hosts_from_idle_pool"
        )
        mock_db_meta_patch = patch(
            "backend.ticket.builders.common.bigdata.BigDataDetailsSerializer.validate_hosts_not_in_db_meta"
        )
        cls.patches.extend([mock_idle_pool_patch, mock_db_meta_patch])
        super().apply_patches()
