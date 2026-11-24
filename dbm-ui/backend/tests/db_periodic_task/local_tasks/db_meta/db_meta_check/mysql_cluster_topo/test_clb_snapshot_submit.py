import importlib
from unittest.mock import patch

import pytest

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster

SUBMIT_MODULE = "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.clb_snapshot_submit"


@pytest.fixture(scope="module")
def submit_mod(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(SUBMIT_MODULE)


def _create_cluster(name, cluster_type, phase, domain):
    return Cluster.objects.create(
        bk_biz_id=3,
        name=name,
        cluster_type=cluster_type,
        immute_domain=domain,
        phase=phase,
    )


@pytest.mark.django_db
def test_snapshot_candidates_skip_offline_and_tmp_domain(submit_mod):
    ha = _create_cluster("ha-online", ClusterType.TenDBHA.value, ClusterPhase.ONLINE.value, "submit-ha-online.db")
    offline = _create_cluster(
        "ha-offline", ClusterType.TenDBHA.value, ClusterPhase.OFFLINE.value, "submit-ha-offline.db"
    )
    plain = _create_cluster(
        "tc-online", ClusterType.TenDBCluster.value, ClusterPhase.ONLINE.value, "submit-tc-online.db"
    )
    tmp = _create_cluster(
        "tc-tmp",
        ClusterType.TenDBCluster.value,
        ClusterPhase.ONLINE.value,
        "submit-tc-tmp20260101-1234567.db",
    )
    no_clb = _create_cluster("ha-noclb", ClusterType.TenDBHA.value, ClusterPhase.ONLINE.value, "submit-ha-noclb.db")

    with patch.object(submit_mod.clb_snapshot, "submit") as submit:
        submit_mod.submit_mysql_clb_snapshot()

    submitted = submit.call_args.args[0]
    assert ha.id in submitted
    assert plain.id in submitted
    assert no_clb.id in submitted
    assert offline.id not in submitted
    assert tmp.id not in submitted


@pytest.fixture(scope="module")
def check_task(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.db_meta.db_meta_check.task")


def test_mysql_snapshot_task_calls_submission(check_task):
    with patch.object(check_task, "submit_mysql_clb_snapshot") as submit:
        check_task.mysql_clb_snapshot_task()
    submit.assert_called_once_with()


@pytest.mark.django_db
def test_tendbha_daily_check_skips_offline_batches_snapshots_and_isolates_errors(check_task):
    c1 = _create_cluster("daily-ha-1", ClusterType.TenDBHA.value, ClusterPhase.ONLINE.value, "daily-ha-1.db")
    c2 = _create_cluster("daily-ha-2", ClusterType.TenDBHA.value, ClusterPhase.ONLINE.value, "daily-ha-2.db")
    offline = _create_cluster("daily-ha-off", ClusterType.TenDBHA.value, ClusterPhase.OFFLINE.value, "daily-ha-off.db")

    written = []

    def fake_write(cluster_id, snapshot=None):
        written.append((cluster_id, snapshot))
        if cluster_id == c1.id:
            raise RuntimeError("boom")

    with patch.object(check_task.tendbha, "health_check", return_value=[]) as health_check, patch.object(
        check_task, "load_clb_snapshots", return_value={c1.id: "snap-1", c2.id: "snap-2"}
    ) as load_snaps, patch.object(check_task, "write_mysql_entry_report", side_effect=fake_write):
        check_task.tendbha_topo_daily_check()

    checked_ids = [call.args[0] for call in health_check.call_args_list]
    assert c1.id in checked_ids
    assert c2.id in checked_ids
    assert offline.id not in checked_ids
    load_snaps.assert_called_once()
    assert (c1.id, "snap-1") in written
    assert (c2.id, "snap-2") in written


@pytest.mark.django_db
def test_tendbcluster_daily_check_skips_offline_and_tmp_domain(check_task):
    online = _create_cluster(
        "daily-tc-on", ClusterType.TenDBCluster.value, ClusterPhase.ONLINE.value, "daily-tc-on.db"
    )
    offline = _create_cluster(
        "daily-tc-off", ClusterType.TenDBCluster.value, ClusterPhase.OFFLINE.value, "daily-tc-off.db"
    )
    tmp = _create_cluster(
        "daily-tc-tmp",
        ClusterType.TenDBCluster.value,
        ClusterPhase.ONLINE.value,
        "daily-tc-tmp20260101-1234567.db",
    )

    with patch.object(check_task.tendbcluster, "health_check", return_value=[]) as health_check, patch.object(
        check_task, "load_clb_snapshots", return_value={}
    ) as load_snaps, patch.object(check_task, "write_mysql_entry_report") as write_report:
        check_task.tendbcluster_topo_daily_check()

    checked_ids = [call.args[0] for call in health_check.call_args_list]
    assert online.id in checked_ids
    assert offline.id not in checked_ids
    assert tmp.id not in checked_ids
    load_snaps.assert_called_once()
    reported_ids = [call.args[0] for call in write_report.call_args_list]
    assert online.id in reported_ids
    assert offline.id not in reported_ids
    assert tmp.id not in reported_ids
