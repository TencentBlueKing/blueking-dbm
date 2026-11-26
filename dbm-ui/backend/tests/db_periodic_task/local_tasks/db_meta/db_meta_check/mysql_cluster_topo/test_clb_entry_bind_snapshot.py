import importlib
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    ClusterPhase,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceStatus,
    TenDBClusterSpiderRole,
)
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_periodic_task.clb_snapshot.snapshot import CLBEntrySnapshot, ClusterCLBSnapshot
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.models import MetaCheckReport
from backend.db_report.views.mysql.mysql_dbmeta_check_view import MySQLMetaCheckReportViewSet
from backend.db_report.views.mysql.mysql_entry_check_view import ENTRY_CHECK_REPORT_TITLE, MySQLEntryCheckReportViewSet
from backend.db_report.views.tendbcluster.tendbcluster_dbmeta_check_view import TendbClusterMetaCheckReportViewSet

ENTRY_MODULE = "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.entry_consistency"


@pytest.fixture(scope="module", autouse=True)
def entry_consistency(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(ENTRY_MODULE)


class _All(list):
    def all(self):
        return self


def _proxy(ip, port, role=None, status=InstanceStatus.RUNNING, phase=InstancePhase.ONLINE):
    proxy = SimpleNamespace(status=status, phase=phase, port=port, machine=SimpleNamespace(ip=ip))
    if role is not None:
        proxy.tendbclusterspiderext = SimpleNamespace(spider_role=role)
    return proxy


def _storage(
    ip,
    role=InstanceInnerRole.SLAVE,
    stand_by=True,
    status=InstanceStatus.RUNNING,
    phase=InstancePhase.ONLINE,
):
    return SimpleNamespace(
        status=status,
        phase=phase,
        instance_inner_role=role,
        is_stand_by=stand_by,
        machine=SimpleNamespace(ip=ip),
    )


def _entry(entry_id, entry, entry_type, proxies=None, storages=None, role="master_entry", forward_to=None):
    return SimpleNamespace(
        id=entry_id,
        entry=entry,
        cluster_entry_type=entry_type,
        role=role,
        forward_to=forward_to,
        proxyinstance_set=_All(proxies or []),
        storageinstance_set=_All(storages or []),
    )


def _cluster(cluster_id, cluster_type, entries, proxies, storages=None):
    return SimpleNamespace(
        id=cluster_id,
        immute_domain="db.example.db",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster_type=cluster_type,
        clusterentry_set=_All(entries),
        proxyinstance_set=_All(proxies),
        storageinstance_set=_All(storages or []),
    )


def _snapshot(cluster_id, entry_id, listener_rs, **kwargs):
    checked_at = kwargs.pop("checked_at", time.time())
    return ClusterCLBSnapshot(
        cluster_id=cluster_id,
        checked_at=checked_at,
        entries=[
            CLBEntrySnapshot(
                cluster_entry_id=entry_id,
                entry=kwargs.pop("entry", "127.0.0.10"),
                clb_id=kwargs.pop("clb_id", "lb-1"),
                listener_id=kwargs.pop("listener_id", "lbl-1"),
                region=kwargs.pop("region", "ap-test"),
                listener_rs=listener_rs,
                listener_rs_error=kwargs.pop("listener_rs_error", None),
                unhealthy_rs=kwargs.pop("unhealthy_rs", []),
                meta_error=kwargs.pop("meta_error", None),
                health_error=kwargs.pop("health_error", None),
            )
        ],
    )


def _ha_cluster(entries, proxies, storages=None):
    return _cluster(7, ClusterType.TenDBHA.value, entries, proxies, storages)


def test_fresh_matching_clb_is_normal(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    state, msg = entry_consistency.build_mysql_entry_check(
        _ha_cluster([entry], [proxy]), _snapshot(7, 1, ["127.0.0.2:20000"])
    )
    assert state == ReportStateType.NORMAL.value
    assert msg == "全部入口一致"


def test_thirty_hour_snapshot_with_matching_rs_is_warning(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, ["127.0.0.2:20000"], checked_at=time.time() - 30 * 3600)
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.WARNING.value
    assert "快照偏旧（30 小时）" in msg
    assert "127.0.0.10" in msg


def test_rs_mismatch_keeps_port_and_is_abnormal(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    state, msg = entry_consistency.build_mysql_entry_check(
        _ha_cluster([entry], [proxy]), _snapshot(7, 1, ["127.0.0.3:20000"])
    )
    assert state == ReportStateType.ABNORMAL.value
    assert "缺少: 127.0.0.2:20000" in msg
    assert "多出: 127.0.0.3:20000" in msg


def test_missing_snapshot_is_abnormal_without_nameservice(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    with patch("backend.components.NameServiceApi.clb_get_target_private_ips") as nameservice:
        state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), None)
    assert state == ReportStateType.ABNORMAL.value
    assert msg == "clb  (127.0.0.10): 快照缺失"
    assert not nameservice.called


def test_outdated_snapshot_is_abnormal(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, ["127.0.0.2:20000"], checked_at=time.time() - 50 * 3600)
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.ABNORMAL.value
    assert "快照过旧（50 小时）" in msg


def test_blank_listener_id_is_metadata_incomplete(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, ["127.0.0.2:20000"], listener_id="")
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.ABNORMAL.value
    assert "元数据不完整：监听器 ID 为空" in msg
    assert "缺少" not in msg


def test_meta_error_takes_precedence_over_blank_listener_id(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, None, listener_id="", meta_error="CLB entry detail not found")
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.ABNORMAL.value
    assert "元数据不完整：CLB entry detail not found" in msg
    assert "监听器 ID 为空" not in msg


def test_listener_rs_error_is_included_when_listener_rs_is_none(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, None, listener_rs_error="nameservice timeout")
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.ABNORMAL.value
    assert "无法查询后端：nameservice timeout" in msg


def test_diff_omits_empty_missing_or_extra_section(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, ["127.0.0.2:20000", "127.0.0.3:20000"])
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.ABNORMAL.value
    assert "多出: 127.0.0.3:20000" in msg
    assert "缺少:" not in msg


def test_unhealthy_rs_is_abnormal(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    entry = _entry(1, "127.0.0.10", "clb", [proxy])
    snapshot = _snapshot(7, 1, ["127.0.0.2:20000"], unhealthy_rs=["127.0.0.2:20000"])
    state, msg = entry_consistency.build_mysql_entry_check(_ha_cluster([entry], [proxy]), snapshot)
    assert state == ReportStateType.ABNORMAL.value
    assert "不健康: 127.0.0.2:20000" in msg


def test_dns_and_clb_share_one_message(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    clb = _entry(1, "127.0.0.10", "clb", [proxy])
    dns = _entry(2, "db.example.db", "dns", role="master_entry")
    cluster = _ha_cluster([clb, dns], [proxy])

    def dns_get(unused_cluster, entry):
        assert entry.entry == "db.example.db"
        return {"127.0.0.4"}

    state, msg = entry_consistency.build_mysql_entry_check(cluster, _snapshot(7, 1, ["127.0.0.3:20000"]), dns_get)
    assert state == ReportStateType.ABNORMAL.value
    assert msg.index("clb  (127.0.0.10)") < msg.index("dns  (db.example.db)")
    assert "缺少: 127.0.0.2" in msg
    assert "多出: 127.0.0.4" in msg


def test_forward_to_and_clbdns_are_skipped(entry_consistency):
    proxy = _proxy("127.0.0.2", 20000)
    forwarded = _entry(1, "db.example.db", "dns", forward_to=SimpleNamespace(id=99, entry="127.0.0.10"))
    clbdns = _entry(2, "clb.example.db", "clbDns")
    cluster = _ha_cluster([forwarded, clbdns], [proxy])

    def dns_get(unused_cluster, entry):
        raise AssertionError(entry.entry)

    state, msg = entry_consistency.build_mysql_entry_check(cluster, None, dns_get)
    assert state == ReportStateType.NORMAL.value
    assert msg == "全部入口一致"


def test_dns_query_failure_is_abnormal(entry_consistency):
    dns = _entry(1, "db.example.db", "dns", role="master_entry")
    cluster = _ha_cluster([dns], [_proxy("127.0.0.2", 20000)])

    def dns_get(unused_cluster, entry):
        raise RuntimeError("dns down")

    state, msg = entry_consistency.build_mysql_entry_check(cluster, None, dns_get)
    assert state == ReportStateType.ABNORMAL.value
    assert "解析失败：dns down" in msg


def test_tendbha_slave_dns_uses_entry_storage_set(entry_consistency):
    standby = _storage("127.0.0.5", stand_by=True)
    ro_slave = _storage("127.0.0.6", stand_by=False)
    offline_slave = _storage("127.0.0.7", stand_by=False, phase=InstancePhase.OFFLINE)
    default_slave_dns = _entry(
        1, "db-slave.example.db", "dns", storages=[standby, ro_slave, offline_slave], role="slave_entry"
    )
    ro_only_dns = _entry(2, "db-ro.example.db", "dns", storages=[ro_slave], role="slave_entry")
    cluster = _ha_cluster([default_slave_dns, ro_only_dns], [], [standby, ro_slave, offline_slave])

    def dns_get(unused_cluster, entry):
        if entry.entry == "db-slave.example.db":
            return {"127.0.0.5", "127.0.0.6"}
        return {"127.0.0.6"}

    state, msg = entry_consistency.build_mysql_entry_check(cluster, None, dns_get)
    assert state == ReportStateType.NORMAL.value
    assert msg == "全部入口一致"


def test_tendbcluster_dns_uses_spider_role(entry_consistency):
    master = _proxy("127.0.0.2", 25000, role=TenDBClusterSpiderRole.SPIDER_MASTER)
    slave = _proxy("127.0.0.3", 25000, role=TenDBClusterSpiderRole.SPIDER_SLAVE)
    master_dns = _entry(1, "db.example.db", "dns", role="master_entry")
    slave_dns = _entry(2, "db-slave.example.db", "dns", role="slave_entry")
    cluster = _cluster(8, ClusterType.TenDBCluster.value, [master_dns, slave_dns], [master, slave])

    def dns_get(unused_cluster, entry):
        if entry.role == "master_entry":
            return {"127.0.0.2"}
        return {"127.0.0.9"}

    state, msg = entry_consistency.build_mysql_entry_check(cluster, None, dns_get)
    assert state == ReportStateType.ABNORMAL.value
    assert "dns  (db.example.db)" not in msg
    assert "缺少: 127.0.0.3" in msg
    assert "多出: 127.0.0.9" in msg


def test_entry_report_columns_have_failed_days_and_no_cluster_type():
    names = [column["name"] for column in ENTRY_CHECK_REPORT_TITLE]
    assert names == ["bk_biz_id", "cluster", "state", "msg", "create_at", "failed_days"]


@pytest.mark.django_db
def test_written_row_stays_out_of_meta_check():
    from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.entry_consistency import (
        write_mysql_entry_report,
    )

    cluster = Cluster.objects.create(
        bk_biz_id=3,
        name="entry-ha",
        cluster_type=ClusterType.TenDBHA.value,
        immute_domain="entry-ha.db",
        phase=ClusterPhase.ONLINE.value,
    )
    with patch(
        "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.entry_consistency.clb_snapshot.get_many",
        return_value={cluster.id: None},
    ), patch("backend.components.NameServiceApi.clb_get_target_private_ips") as nameservice:
        report = write_mysql_entry_report(cluster.id)

    assert report.state == ReportStateType.NORMAL.value
    assert report.failed_days == 0
    assert report.ip is None
    assert not nameservice.called
    assert report.id not in set(MySQLMetaCheckReportViewSet.queryset.values_list("id", flat=True))
    assert report.id in set(MySQLEntryCheckReportViewSet.queryset.values_list("id", flat=True))
    assert report.id not in set(TendbClusterMetaCheckReportViewSet.queryset.values_list("id", flat=True))


@pytest.mark.django_db
def test_orm_forward_to_foreign_key_entry_is_skipped():
    from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo import entry_consistency

    cluster = Cluster.objects.create(
        bk_biz_id=3,
        name="entry-fwd",
        cluster_type=ClusterType.TenDBHA.value,
        immute_domain="entry-fwd.db",
        phase=ClusterPhase.ONLINE.value,
    )
    clb_entry = ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.CLB.value,
        entry="127.0.0.10",
        role=ClusterEntryRole.MASTER_ENTRY.value,
    )
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry="entry-fwd.db",
        role=ClusterEntryRole.MASTER_ENTRY.value,
        forward_to=clb_entry,
    )
    snapshot = _snapshot(cluster.id, clb_entry.id, [])
    with patch.object(entry_consistency, "_default_dns_ips", side_effect=AssertionError("should skip forwarded dns")):
        report = entry_consistency.write_mysql_entry_report(cluster.id, snapshot=snapshot)

    assert report.state == ReportStateType.NORMAL.value
    assert report.msg == "全部入口一致"


@pytest.mark.django_db
def test_failed_days_follow_yesterdays_row():
    from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo import entry_consistency

    cluster = Cluster.objects.create(
        bk_biz_id=3,
        name="entry-days",
        cluster_type=ClusterType.TenDBHA.value,
        immute_domain="entry-days.db",
        phase=ClusterPhase.ONLINE.value,
    )
    yesterday = MetaCheckReport.objects.create(
        bk_biz_id=3,
        cluster=cluster.immute_domain,
        cluster_type=ClusterType.TenDBHA.value,
        subtype=MetaCheckSubType.MysqlEntryInconsistent.value,
        state=ReportStateType.ABNORMAL.value,
        msg="old",
        failed_days=2,
        creator="system",
        updater="system",
    )
    MetaCheckReport.objects.filter(id=yesterday.id).update(create_at=timezone.now() - timedelta(hours=24))
    missing = ("abnormal", "clb  (127.0.0.10): 快照缺失")
    with patch.object(entry_consistency, "build_mysql_entry_check", return_value=missing), patch.object(
        entry_consistency.clb_snapshot, "get_many", return_value={cluster.id: None}
    ):
        report = entry_consistency.write_mysql_entry_report(cluster.id)
    assert report.failed_days == 3
