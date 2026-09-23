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
from django.contrib.auth import get_user_model
from django.urls import resolve
from rest_framework.test import APIClient

from backend.db_meta.enums import ClusterType, DestroyedStatus
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.rollback.views import BackupBatchViewSet, RollbackViewSet

BIZ_ID = 3
ROLLBACK_ROOT = "/apis/redis/bizs/{}/rollback/".format(BIZ_ID)


@pytest.mark.parametrize(
    "path, method, view_cls, action",
    [
        (ROLLBACK_ROOT, "get", RollbackViewSet, "list"),
        (ROLLBACK_ROOT + "12/", "get", RollbackViewSet, "retrieve"),
        (ROLLBACK_ROOT + "check_time/", "post", RollbackViewSet, "check_time"),
        (ROLLBACK_ROOT + "batches/list_batches/", "post", BackupBatchViewSet, "list_batches"),
        (ROLLBACK_ROOT + "batches/batch_details/", "post", BackupBatchViewSet, "batch_details"),
        (ROLLBACK_ROOT + "batches/precheck/", "post", BackupBatchViewSet, "precheck"),
    ],
)
def test_rollback_routes_resolve_to_expected_views(path, method, view_cls, action):
    func = resolve(path).func
    assert getattr(func, "cls", None) is view_cls
    assert func.actions.get(method) == action


@pytest.mark.django_db
def test_rollback_list_returns_results():
    task = TbTendisRollbackTasks.objects.create(
        creator="admin",
        related_rollback_bill_id=1,
        bk_biz_id=BIZ_ID,
        bk_cloud_id=0,
        prod_cluster_type=ClusterType.TendisRedisInstance.value,
        prod_cluster="ins.test.db",
        prod_cluster_id=1,
        prod_instance_range=["1.1.1.1:30000"],
        temp_cluster_type=ClusterType.TendisRedisInstance.value,
        temp_instance_range=["2.2.2.2:30000"],
        temp_cluster_proxy="2.2.2.2:30000",
        prod_temp_instance_pairs=[["1.1.1.1:30000", "2.2.2.2:30000"]],
        host_count=1,
        recovery_time_point="2026-01-01T00:00:00+08:00",
        status=2,
        destroyed_status=DestroyedStatus.NOT_DESTROYED,
    )
    user, _ = get_user_model().objects.get_or_create(username="admin")
    client = APIClient()
    client.force_authenticate(user=user)

    with patch.object(settings, "MIDDLEWARE", []):
        response = client.get(ROLLBACK_ROOT, {"limit": 20, "offset": 0})

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["id"] for item in data["results"]] == [task.id]
    assert data["count"] == 1
