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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.models.mysql_config_ai_inspect import MysqlConfigAiInspectStatus
from backend.db_report.portrait import MysqlPortraitDimensionCode
from backend.db_report.portrait.exceptions import PortraitSDKBaseException

pytestmark = pytest.mark.django_db

_RID = "11111111-2222-3333-4444-555555555555"
_URL = f"https://dbm.example.com/ai-chat/share/{_RID}/"


def _seed_row(Model, **kwargs):
    defaults = dict(
        batch_id="batch-t",
        bk_biz_id=1001,
        cluster_id=10,
        cluster_domain="t.db",
        cluster_type=ClusterType.TenDBHA.value,
        status=MysqlConfigAiInspectStatus.RUNNING.value,
        creator="system",
        updater="system",
    )
    defaults.update(kwargs)
    return Model.objects.create(**defaults)


def test_worker_success_persists_fields(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model)
    lock_key = f"mysql_config_ai_inspect:{row.batch_id}:{row.cluster_id}"
    agent_json = f'{{"report_id": "{_RID}", "share_url": "{_URL}", "summary": "s"}}'
    with patch.object(inspect_tasks.cache, "delete") as delete_mock, patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value=agent_json
    ), patch.object(inspect_tasks, "ingest_summary") as ingest_mock:
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.SUCCESS.value
    assert row.report_id == _RID
    assert row.share_url == _URL
    assert row.summary == "s"
    assert row.agent_cost_ms >= 0
    delete_mock.assert_called_with(lock_key)
    ingest_mock.assert_called_once()
    kwargs = ingest_mock.call_args.kwargs
    assert kwargs["db_type"] == DBType.MySQL
    assert kwargs["dimension"] == MysqlPortraitDimensionCode.CONFIG_CHECK
    assert kwargs["bk_biz_id"] == row.bk_biz_id
    assert kwargs["cluster_domain"] == row.cluster_domain
    assert kwargs["summary"] == "s"
    assert kwargs["detail_url"] == _URL


def test_worker_success_tendbcluster_portrait_db_type(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, cluster_type=ClusterType.TenDBCluster.value, cluster_domain="spider.t.db")
    lock_key = "k-spider"
    agent_json = f'{{"report_id": "{_RID}", "share_url": "{_URL}", "summary": "ok"}}'
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value=agent_json
    ), patch.object(inspect_tasks, "ingest_summary") as ingest_mock:
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    assert ingest_mock.call_args.kwargs["db_type"] == DBType.TenDBCluster


def test_worker_retries_then_fails(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, retry_count=0)
    lock_key = "k1"
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value="not-json"
    ), patch.object(inspect_tasks, "ingest_summary") as ingest_mock:
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.PENDING.value
    assert row.retry_count == 1
    ingest_mock.assert_not_called()

    row.status = MysqlConfigAiInspectStatus.RUNNING.value
    row.save(update_fields=["status"])
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value="not-json"
    ), patch.object(inspect_tasks, "ingest_summary") as ingest_mock:
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.retry_count == 2
    assert row.status == MysqlConfigAiInspectStatus.PENDING.value
    ingest_mock.assert_not_called()

    row.status = MysqlConfigAiInspectStatus.RUNNING.value
    row.save(update_fields=["status"])
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value="not-json"
    ), patch.object(inspect_tasks, "ingest_summary") as ingest_mock:
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.retry_count == 3
    assert row.status == MysqlConfigAiInspectStatus.FAILED.value
    ingest_mock.assert_not_called()


def test_worker_success_after_retry(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, retry_count=1, status=MysqlConfigAiInspectStatus.RUNNING.value)
    lock_key = "k2"
    agent_json = f'{{"report_id": "{_RID}", "share_url": "{_URL}"}}'
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value=agent_json
    ), patch.object(inspect_tasks, "ingest_summary") as ingest_mock:
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.SUCCESS.value
    assert row.summary == ""
    assert row.report_id == _RID
    assert ingest_mock.call_args.kwargs["summary"] == ""
    assert ingest_mock.call_args.kwargs["detail_url"] == _URL


def test_worker_success_keeps_status_when_portrait_fails(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model)
    lock_key = "k-portrait-fail"
    agent_json = f'{{"report_id": "{_RID}", "share_url": "{_URL}", "summary": "s"}}'
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", return_value=agent_json
    ), patch.object(inspect_tasks, "ingest_summary", side_effect=PortraitSDKBaseException("portrait boom")):
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.SUCCESS.value
    assert row.report_id == _RID
    assert row.share_url == _URL


def test_periodic_dispatches_one_pending(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    _seed_row(Model, cluster_id=1, cluster_domain="a.db", status=MysqlConfigAiInspectStatus.PENDING.value)
    _seed_row(Model, cluster_id=2, cluster_domain="b.db", status=MysqlConfigAiInspectStatus.PENDING.value)

    apply_mock = MagicMock()
    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", True), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.ensure_open_batch",
        return_value="batch-t",
    ), patch.object(inspect_tasks, "start_new_span", side_effect=lambda f: MagicMock()), patch.object(
        inspect_tasks.run_mysql_config_ai_inspect, "apply_async", apply_mock
    ), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache.add",
        return_value=True,
    ):
        inspect_tasks.periodic_mysql_config_ai_inspect()

    assert apply_mock.call_count == 1
    running = Model.objects.filter(status=MysqlConfigAiInspectStatus.RUNNING.value)
    assert running.count() == 1
    assert Model.objects.filter(status=MysqlConfigAiInspectStatus.PENDING.value).count() == 1


def test_periodic_skips_when_ai_disabled(ai_inspect_table, inspect_tasks):
    ensure_mock = MagicMock()
    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", False), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.ensure_open_batch",
        ensure_mock,
    ):
        inspect_tasks.periodic_mysql_config_ai_inspect()
    ensure_mock.assert_not_called()


def test_periodic_skips_when_running_exists(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    _seed_row(Model, cluster_id=1, status=MysqlConfigAiInspectStatus.RUNNING.value)
    _seed_row(Model, cluster_id=2, cluster_domain="b.db", status=MysqlConfigAiInspectStatus.PENDING.value)
    apply_mock = MagicMock()
    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", True), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.ensure_open_batch",
        return_value="batch-t",
    ), patch.object(inspect_tasks.run_mysql_config_ai_inspect, "apply_async", apply_mock):
        inspect_tasks.periodic_mysql_config_ai_inspect()
    apply_mock.assert_not_called()
    assert Model.objects.filter(status=MysqlConfigAiInspectStatus.PENDING.value).count() == 1


def test_reclaim_stale_running(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, status=MysqlConfigAiInspectStatus.RUNNING.value)
    # 直接把 update_at 打到过期窗口
    Model.objects.filter(id=row.id).update(
        update_at=timezone.now() - timedelta(seconds=inspect_tasks.STALE_RUNNING_SEC + 10)
    )
    row.refresh_from_db()
    with patch.object(inspect_tasks.cache, "delete") as delete_mock:
        count = inspect_tasks.reclaim_stale_running(row.batch_id)
    assert count == 1
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.PENDING.value
    assert row.retry_count == 1
    delete_mock.assert_called_with(f"mysql_config_ai_inspect:{row.batch_id}:{row.cluster_id}")


def test_reclaim_stale_marks_failed_at_max_retry(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, status=MysqlConfigAiInspectStatus.RUNNING.value, retry_count=2)
    Model.objects.filter(id=row.id).update(
        update_at=timezone.now() - timedelta(seconds=inspect_tasks.STALE_RUNNING_SEC + 10)
    )
    with patch.object(inspect_tasks.cache, "delete"):
        count = inspect_tasks.reclaim_stale_running(row.batch_id)
    assert count == 1
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.FAILED.value
    assert row.retry_count == 3


def test_mark_failed_cas_skips_success(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, status=MysqlConfigAiInspectStatus.RUNNING.value)
    Model.objects.filter(id=row.id).update(status=MysqlConfigAiInspectStatus.SUCCESS.value)
    # 内存仍按 RUNNING 尝试失败落库，CAS 应拒绝覆盖 SUCCESS
    row.status = MysqlConfigAiInspectStatus.RUNNING.value
    ok = inspect_tasks._mark_attempt_failed(row, "stale race", 0)
    assert ok is False
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.SUCCESS.value
    assert row.retry_count == 0


def test_claim_bumps_update_at_avoids_false_reclaim(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, cluster_id=1, status=MysqlConfigAiInspectStatus.PENDING.value)
    Model.objects.filter(id=row.id).update(
        update_at=timezone.now() - timedelta(seconds=inspect_tasks.STALE_RUNNING_SEC + 3600)
    )
    apply_mock = MagicMock()
    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", True), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.ensure_open_batch",
        return_value="batch-t",
    ), patch.object(inspect_tasks, "start_new_span", side_effect=lambda f: MagicMock()), patch.object(
        inspect_tasks.run_mysql_config_ai_inspect, "apply_async", apply_mock
    ), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache.add",
        return_value=True,
    ):
        inspect_tasks.periodic_mysql_config_ai_inspect()
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.RUNNING.value
    assert row.update_at >= timezone.now() - timedelta(seconds=30)
    assert inspect_tasks.reclaim_stale_running(row.batch_id) == 0
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.RUNNING.value


def test_periodic_skips_when_dispatch_lock_held(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    _seed_row(Model, cluster_id=1, status=MysqlConfigAiInspectStatus.PENDING.value)
    apply_mock = MagicMock()

    def _add(key, *_args, **_kwargs):
        # 批次 lease 放行，集群锁占用
        if "batch_lease" in key:
            return True
        return False

    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", True), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.ensure_open_batch",
        return_value="batch-t",
    ), patch.object(inspect_tasks.run_mysql_config_ai_inspect, "apply_async", apply_mock), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache.add",
        side_effect=_add,
    ), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache.delete",
    ):
        inspect_tasks.periodic_mysql_config_ai_inspect()
    apply_mock.assert_not_called()
    assert Model.objects.filter(status=MysqlConfigAiInspectStatus.PENDING.value).count() == 1


def test_periodic_reverts_pending_on_apply_error(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, cluster_id=1, status=MysqlConfigAiInspectStatus.PENDING.value)
    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", True), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.ensure_open_batch",
        return_value="batch-t",
    ), patch.object(inspect_tasks, "start_new_span", side_effect=lambda f: MagicMock()), patch.object(
        inspect_tasks.run_mysql_config_ai_inspect,
        "apply_async",
        side_effect=RuntimeError("broker down"),
    ), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache.add",
        return_value=True,
    ), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache.delete",
    ) as delete_mock:
        inspect_tasks.periodic_mysql_config_ai_inspect()
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.PENDING.value
    assert delete_mock.called


def test_worker_agent_exception_retries(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, retry_count=0)
    lock_key = "k-agent-exc"
    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler,
        "ask_agent_with_content",
        side_effect=TimeoutError("agent down"),
    ):
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    row.refresh_from_db()
    assert row.status == MysqlConfigAiInspectStatus.PENDING.value
    assert row.retry_count == 1
    assert "agent down" in row.error_msg
    assert row.agent_cost_ms >= 0


def test_worker_prompt_includes_domain_and_json(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    row = _seed_row(Model, cluster_domain="prompt.db")
    lock_key = "k-prompt"
    captured = {}

    def _ask(**kwargs):
        captured["content"] = kwargs["content"]
        return f'{{"report_id": "{_RID}", "share_url": "{_URL}", "summary": "s"}}'

    with patch.object(inspect_tasks.cache, "delete"), patch.object(
        inspect_tasks.AgentHandler, "ask_agent_with_content", side_effect=_ask
    ), patch.object(inspect_tasks, "ingest_summary"):
        inspect_tasks.run_mysql_config_ai_inspect(row.id, lock_key)
    assert "cluster_domain: prompt.db" in captured["content"]
    assert '"report_id"' in captured["content"]
    assert "ai-chat/share" in captured["content"]


def test_periodic_opens_next_batch_when_finished(ai_inspect_table, inspect_tasks):
    Model = ai_inspect_table
    _seed_row(Model, status=MysqlConfigAiInspectStatus.SUCCESS.value, cluster_id=1)
    next_clusters = [
        SimpleNamespace(id=99, bk_biz_id=1001, immute_domain="new.db", cluster_type=ClusterType.TenDBHA.value)
    ]
    qs = MagicMock()
    qs.only.return_value = next_clusters
    mock_batch_cache = MagicMock()
    mock_batch_cache.add.return_value = True
    mock_tasks_cache = MagicMock()
    mock_tasks_cache.add.return_value = True
    with patch.object(inspect_tasks.env, "ENABLE_DBM_AI", True), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.Cluster.objects.filter",
        return_value=qs,
    ), patch("backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch.cache", mock_batch_cache,), patch(
        "backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks.cache",
        mock_tasks_cache,
    ), patch.object(
        inspect_tasks, "start_new_span", side_effect=lambda f: MagicMock()
    ), patch.object(
        inspect_tasks.run_mysql_config_ai_inspect, "apply_async"
    ):
        inspect_tasks.periodic_mysql_config_ai_inspect()

    assert Model.objects.filter(cluster_domain="new.db").exists()
    new_batch = Model.objects.get(cluster_domain="new.db").batch_id
    assert new_batch != "batch-t"
