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
from mock.mock import patch

from backend.constants import IP_PORT_DIVIDER
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.gse import GseApiMock

pytestmark = pytest.mark.django_db


class TestInstanceHandler:
    @patch("backend.db_services.ipchooser.handlers.host_handler.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.handlers.base.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.GseApi", GseApiMock())
    def test_find_related_clusters_by_cluster_id(self, bk_biz_id, dbha_cluster):
        assert (
            len(
                InstanceHandler(bk_biz_id).check_instances(
                    [inst.machine.ip for inst in dbha_cluster.storageinstance_set.all()]
                )
            )
            == 2
        )
        assert (
            len(
                InstanceHandler(bk_biz_id).check_instances(
                    [inst.machine.ip for inst in dbha_cluster.proxyinstance_set.all()]
                )
            )
            == 2
        )
        proxy = dbha_cluster.proxyinstance_set.first()
        assert (
            len(InstanceHandler(bk_biz_id).check_instances([f"{proxy.machine.ip}{IP_PORT_DIVIDER}{proxy.port}"])) == 1
        )
