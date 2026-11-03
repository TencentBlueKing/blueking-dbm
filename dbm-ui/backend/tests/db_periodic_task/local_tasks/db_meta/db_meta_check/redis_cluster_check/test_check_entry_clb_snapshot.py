import importlib
from unittest.mock import patch

import pytest

_PKG = "backend.db_periodic_task.local_tasks.db_meta.db_meta_check"


@pytest.fixture(scope="module")
def modules(django_db_setup, django_db_blocker):
    # Importing local_tasks registers periodic tasks, which writes beat rows.
    with django_db_blocker.unblock():
        check_entry = importlib.import_module(f"{_PKG}.redis_cluster_check.check_entry")
        task = importlib.import_module(f"{_PKG}.task")
    return check_entry, task


def test_disabled_entry_check_submits_nothing(modules):
    check_entry, _ = modules
    config = check_entry.RedisEntryCheckConfig(enabled=False)
    with patch.object(check_entry, "_get_config", return_value=config), patch.object(
        check_entry, "_get_candidate_clusters"
    ) as candidates, patch.object(check_entry.clb_snapshot, "submit") as submit:
        check_entry.submit_redis_clb_snapshot()
    assert not candidates.called
    assert not submit.called


def test_enabled_entry_check_submits_its_candidates(modules):
    check_entry, _ = modules
    config = check_entry.RedisEntryCheckConfig(enabled=True)
    with patch.object(check_entry, "_get_config", return_value=config), patch.object(
        check_entry, "_get_candidate_clusters", return_value=[3, 1, 2]
    ) as candidates, patch.object(check_entry.clb_snapshot, "submit") as submit:
        check_entry.submit_redis_clb_snapshot()
    candidates.assert_called_once_with(config)
    submit.assert_called_once_with([3, 1, 2])


def test_snapshot_periodic_task_calls_submission(modules):
    _, task = modules
    with patch.object(task, "submit_redis_clb_snapshot") as submit:
        task.redis_clb_snapshot_task()
    submit.assert_called_once_with()
