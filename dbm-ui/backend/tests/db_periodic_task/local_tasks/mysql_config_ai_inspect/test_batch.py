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
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_report.models.mysql_config_ai_inspect import MysqlConfigAiInspectStatus

pytestmark = pytest.mark.django_db


def _fake_clusters():
    return [
        SimpleNamespace(id=1, bk_biz_id=1001, immute_domain="a.db", cluster_type=ClusterType.TenDBHA.value),
        SimpleNamespace(id=2, bk_biz_id=1001, immute_domain="b.db", cluster_type=ClusterType.TenDBSingle.value),
        SimpleNamespace(id=3, bk_biz_id=1002, immute_domain="c.db", cluster_type=ClusterType.TenDBCluster.value),
    ]


def _mock_cluster_qs(clusters):
    qs = MagicMock()
    qs.only.return_value = clusters
    return qs


def _patch_batch_cache(batch_mod):
    mock_cache = MagicMock()
    mock_cache.add.return_value = True
    return patch.object(batch_mod, "cache", mock_cache)


def test_ensure_open_batch_creates_pending_rows(ai_inspect_table, batch_mod):
    Model = ai_inspect_table
    with _patch_batch_cache(batch_mod), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        return_value=_mock_cluster_qs(_fake_clusters()),
    ):
        batch_id = batch_mod.ensure_open_batch()
    assert batch_id
    rows = list(Model.objects.filter(batch_id=batch_id).order_by("cluster_id"))
    assert len(rows) == 3
    assert all(r.status == MysqlConfigAiInspectStatus.PENDING.value for r in rows)
    assert {r.cluster_domain for r in rows} == {"a.db", "b.db", "c.db"}


def test_ensure_open_batch_reuses_open_batch(ai_inspect_table, batch_mod):
    Model = ai_inspect_table
    with _patch_batch_cache(batch_mod), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        return_value=_mock_cluster_qs(_fake_clusters()),
    ):
        first = batch_mod.ensure_open_batch()
        second = batch_mod.ensure_open_batch()
    assert first == second
    assert Model.objects.filter(batch_id=first).count() == 3


def test_ensure_open_batch_opens_new_after_finished(ai_inspect_table, batch_mod):
    Model = ai_inspect_table
    with _patch_batch_cache(batch_mod), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        return_value=_mock_cluster_qs(_fake_clusters()),
    ):
        batch1 = batch_mod.ensure_open_batch()
    Model.objects.filter(batch_id=batch1).update(status=MysqlConfigAiInspectStatus.SUCCESS.value)
    assert batch_mod.is_batch_finished(batch1)

    next_clusters = _fake_clusters() + [
        SimpleNamespace(id=99, bk_biz_id=1001, immute_domain="new.db", cluster_type=ClusterType.TenDBHA.value)
    ]
    with _patch_batch_cache(batch_mod), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        return_value=_mock_cluster_qs(next_clusters),
    ):
        batch2 = batch_mod.ensure_open_batch()
    assert batch2 != batch1
    assert Model.objects.filter(batch_id=batch1, cluster_id=99).count() == 0
    assert Model.objects.filter(batch_id=batch2, cluster_domain="new.db").exists()


def test_ensure_open_batch_waits_on_lock(ai_inspect_table, batch_mod):
    Model = ai_inspect_table
    Model.objects.create(
        batch_id="open-1",
        bk_biz_id=1001,
        cluster_id=1,
        cluster_domain="a.db",
        cluster_type=ClusterType.TenDBHA.value,
        status=MysqlConfigAiInspectStatus.PENDING.value,
        creator="system",
        updater="system",
    )
    mock_cache = MagicMock()
    mock_cache.add.return_value = False
    filter_mock = MagicMock()
    with patch.object(batch_mod, "cache", mock_cache), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        filter_mock,
    ):
        batch_id = batch_mod.ensure_open_batch()
    assert batch_id == "open-1"
    filter_mock.assert_not_called()
    assert Model.objects.count() == 1


def test_ensure_open_batch_fail_closed_on_cache_error(ai_inspect_table, batch_mod):
    Model = ai_inspect_table
    mock_cache = MagicMock()
    mock_cache.add.side_effect = RuntimeError("cache down")
    filter_mock = MagicMock()
    with patch.object(batch_mod, "cache", mock_cache), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        filter_mock,
    ):
        batch_id = batch_mod.ensure_open_batch()
    assert batch_id is None
    filter_mock.assert_not_called()
    assert Model.objects.count() == 0


def test_find_open_batch_prefers_oldest(ai_inspect_table, batch_mod):
    Model = ai_inspect_table
    older = Model.objects.create(
        batch_id="old-batch",
        bk_biz_id=1001,
        cluster_id=1,
        cluster_domain="old.db",
        cluster_type=ClusterType.TenDBHA.value,
        status=MysqlConfigAiInspectStatus.PENDING.value,
        creator="system",
        updater="system",
    )
    newer = Model.objects.create(
        batch_id="new-batch",
        bk_biz_id=1001,
        cluster_id=2,
        cluster_domain="new.db",
        cluster_type=ClusterType.TenDBHA.value,
        status=MysqlConfigAiInspectStatus.PENDING.value,
        creator="system",
        updater="system",
    )
    Model.objects.filter(id=older.id).update(create_at=timezone.now() - timedelta(hours=2))
    Model.objects.filter(id=newer.id).update(create_at=timezone.now() - timedelta(hours=1))
    assert batch_mod._find_open_batch_id() == "old-batch"
