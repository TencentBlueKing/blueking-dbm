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

from backend.db_dirty.constants import PoolType
from backend.db_dirty.models import DirtyMachine

pytestmark = pytest.mark.django_db

TASK_MODULE = "backend.db_periodic_task.local_tasks.update_host_property"


def test_update_host_property_syncs_dirty_machine_cloud_fields():
    from backend.db_periodic_task.local_tasks.update_host_property import update_host_property

    DirtyMachine.objects.create(bk_host_id=10001, bk_cloud_id=0, ip="1.1.1.1", pool=PoolType.Resource)
    events = {
        "bk_watched": True,
        "bk_events": [
            {
                "bk_cursor": "cursor-1",
                "bk_detail": {
                    "bk_host_id": 10001,
                    "bk_os_name": "tlinux",
                    "bk_cloud_region": "ap-shanghai",
                    "bk_cloud_zone": "ap-shanghai-2",
                },
            }
        ],
    }

    with patch(f"{TASK_MODULE}.cache") as mock_cache, patch(
        f"{TASK_MODULE}.CCApi.check_host_event", return_value=events
    ) as mock_check_host_event:
        mock_cache.get.return_value = None
        update_host_property()

    bk_fields = mock_check_host_event.call_args.args[0]["bk_fields"]
    assert "bk_cloud_region" in bk_fields
    assert "bk_cloud_zone" in bk_fields
    dirty = DirtyMachine.objects.get(bk_host_id=10001)
    assert dirty.os_name == "tlinux"
    assert dirty.bk_cloud_region == "ap-shanghai"
    assert dirty.bk_cloud_zone == "ap-shanghai-2"
