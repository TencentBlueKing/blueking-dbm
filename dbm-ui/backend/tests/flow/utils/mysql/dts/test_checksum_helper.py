# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, TenDBClusterSpiderRole
from backend.flow.utils.mysql.dts.checksum_helper import build_dts_checksum_ticket_info
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskSpec, SourceSpec, SyncScope
from backend.ticket.builders.common.constants import MySQLChecksumTicketMode
from backend.ticket.builders.mysql.mysql_checksum import MySQLChecksumFlowBuilder
from backend.ticket.constants import TicketType


def _role_value(role):
    return getattr(role, "value", role)


def _make_storage_instance(*, inst_id, ip, port, role=None):
    machine = SimpleNamespace(ip=ip, id=inst_id)
    ins = SimpleNamespace(
        id=inst_id,
        machine=machine,
        machine_id=inst_id,
        port=port,
        instance_role=role,
        instance_inner_role=InstanceInnerRole.MASTER.value,
    )
    return ins


def _make_proxy_instance(*, inst_id, ip, port, spider_role=None):
    machine = SimpleNamespace(ip=ip, id=inst_id)
    return SimpleNamespace(
        id=inst_id,
        machine=machine,
        machine_id=inst_id,
        port=port,
        spider_role=_role_value(spider_role) if spider_role is not None else None,
    )


class _StorageQS:
    def __init__(self, storages):
        self._storages = list(storages)

    def filter(self, **kwargs):
        items = self._storages
        if "instance_role" in kwargs:
            items = [s for s in items if s.instance_role == kwargs["instance_role"]]
        if "instance_inner_role" in kwargs:
            items = [s for s in items if s.instance_inner_role == kwargs["instance_inner_role"]]
        if "machine__ip" in kwargs:
            items = [s for s in items if s.machine.ip == kwargs["machine__ip"]]
        if "port" in kwargs:
            items = [s for s in items if s.port == kwargs["port"]]
        return _StorageQS(items)

    def first(self):
        return self._storages[0] if self._storages else None

    def get(self, **kwargs):
        for s in self._storages:
            if all(getattr(s, k) == v for k, v in kwargs.items()):
                return s
        raise LookupError(kwargs)


class _ProxyQS:
    def __init__(self, proxies):
        self._proxies = list(proxies)

    def filter(self, **kwargs):
        items = self._proxies
        role = kwargs.get("tendbclusterspiderext__spider_role")
        if role is not None:
            role_val = _role_value(role)
            items = [p for p in items if p.spider_role == role_val]
        if "machine__ip" in kwargs:
            items = [p for p in items if p.machine.ip == kwargs["machine__ip"]]
        if "port" in kwargs:
            items = [p for p in items if p.port == kwargs["port"]]
        return _ProxyQS(items)

    def first(self):
        return self._proxies[0] if self._proxies else None


def _cluster(*, cluster_id, cluster_type, storages=None, proxies=None, bk_biz_id=21, bk_cloud_id=0):
    cluster = MagicMock()
    cluster.id = cluster_id
    cluster.cluster_type = cluster_type
    cluster.bk_biz_id = bk_biz_id
    cluster.bk_cloud_id = bk_cloud_id
    cluster.storageinstance_set = _StorageQS(storages or [])
    cluster.proxyinstance_set = _ProxyQS(proxies or [])
    return cluster


class BuildDtsChecksumTicketInfoTest(SimpleTestCase):
    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_uses_mysql_dts_checksum_type(self, mock_cluster_cls):
        src_cluster = SimpleNamespace(
            id=100,
            bk_biz_id=21,
            bk_cloud_id=0,
            cluster_type=ClusterType.TenDBHA.value,
            storageinstance_set=MagicMock(),
        )
        dst_cluster = SimpleNamespace(
            id=200,
            bk_biz_id=21,
            bk_cloud_id=0,
            cluster_type=ClusterType.TenDBHA.value,
            storageinstance_set=MagicMock(),
        )
        master_ins = _make_storage_instance(inst_id=1, ip="127.0.0.1", port=3306)
        slave_ins = _make_storage_instance(inst_id=2, ip="127.0.0.2", port=3306)
        src_cluster.storageinstance_set.filter.return_value.first.return_value = master_ins
        dst_cluster.storageinstance_set.filter.return_value.first.return_value = slave_ins
        mock_cluster_cls.objects.get.side_effect = [src_cluster, dst_cluster]

        task_spec = DtsTaskSpec(
            task_name="mysql-dts-21-100-200",
            target_cluster_id=200,
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="source-100-abc",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                    source_host="127.0.0.1:3306",
                )
            ],
        )
        info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)

        self.assertEqual(info["ticket_type"], TicketType.MYSQL_DTS_CHECKSUM)
        details = info["details"]
        self.assertTrue(details["dts_mode"])
        self.assertFalse(details["is_sync_non_innodb"])
        self.assertFalse(details["need_manual_confirm"])
        self.assertEqual(details["data_repair"], {"is_repair": False, "mode": MySQLChecksumTicketMode.MANUAL})
        info0 = details["infos"][0]
        self.assertEqual(info0["cluster_id"], 100)
        self.assertEqual(info0["master"]["ip"], "127.0.0.1")
        self.assertEqual(info0["slaves"][0]["ip"], "127.0.0.2")
        self.assertEqual(info0["db_patterns"], ["db_a"])


class DtsChecksumTargetSpiderAlignTest(SimpleTestCase):
    """AE1–AE4：TenDBCluster 目标对齐 DTS Spider；HA 目标与源端行为不变。"""

    def _ha_src_cluster(self):
        master = _make_storage_instance(inst_id=9, ip="127.0.0.10", port=20000, role=InstanceRole.BACKEND_MASTER.value)
        master.is_stand_by = False
        master.instance_inner_role = InstanceInnerRole.MASTER.value
        standby = _make_storage_instance(
            inst_id=11, ip="127.0.0.12", port=20000, role=InstanceRole.BACKEND_SLAVE.value
        )
        standby.is_stand_by = True
        standby.instance_inner_role = InstanceInnerRole.SLAVE.value
        other = _make_storage_instance(inst_id=10, ip="127.0.0.11", port=20000, role=InstanceRole.BACKEND_SLAVE.value)
        other.is_stand_by = False
        other.instance_inner_role = InstanceInnerRole.SLAVE.value
        return _cluster(
            cluster_id=100,
            cluster_type=ClusterType.TenDBHA.value,
            storages=[other, standby, master],
        )

    def _cluster_dst(self):
        remote = _make_storage_instance(inst_id=40, ip="127.0.0.40", port=20000, role=InstanceRole.REMOTE_MASTER.value)
        primary = _make_proxy_instance(
            inst_id=50,
            ip="127.0.0.8",
            port=26000,
            spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
        )
        secondary = _make_proxy_instance(
            inst_id=51,
            ip="127.0.0.5",
            port=25000,
            spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
        )
        return (
            _cluster(
                cluster_id=200,
                cluster_type=ClusterType.TenDBCluster.value,
                storages=[remote],
                proxies=[primary, secondary],
            ),
            remote,
            primary,
            secondary,
        )

    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_ae1_explicit_target_spider_not_remote_master(self, mock_cluster_cls):
        src = self._ha_src_cluster()
        dst, remote, unused_primary, secondary = self._cluster_dst()
        mock_cluster_cls.objects.get.side_effect = [src, dst]

        task_spec = DtsTaskSpec(
            task_name="ha-to-cluster-ae1",
            target_cluster_id=200,
            target_spider="127.0.0.5:25000",
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="src-100",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                    source_host="127.0.0.12:20000",
                )
            ],
        )
        info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)
        slave = info["details"]["infos"][0]["slaves"][0]
        self.assertEqual((slave["ip"], slave["port"]), (secondary.machine.ip, secondary.port))
        self.assertNotEqual((slave["ip"], slave["port"]), (remote.machine.ip, remote.port))
        self.assertEqual(slave["instance_inner_role"], InstanceInnerRole.SLAVE.value)
        self.assertEqual(slave["id"], secondary.id)
        self.assertEqual(slave["bk_host_id"], secondary.machine_id)

    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_ae3_default_spider_master_when_target_spider_none(self, mock_cluster_cls):
        src = self._ha_src_cluster()
        dst, remote, primary, unused_secondary = self._cluster_dst()
        mock_cluster_cls.objects.get.side_effect = [src, dst]

        task_spec = DtsTaskSpec(
            task_name="ha-to-cluster-ae3",
            target_cluster_id=200,
            target_spider=None,
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="src-100",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                    source_host="127.0.0.12:20000",
                )
            ],
        )
        info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)
        slave = info["details"]["infos"][0]["slaves"][0]
        self.assertEqual((slave["ip"], slave["port"]), (primary.machine.ip, primary.port))
        self.assertNotEqual((slave["ip"], slave["port"]), (remote.machine.ip, remote.port))

    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_ae2_unspecified_source_is_master(self, mock_cluster_cls):
        src = self._ha_src_cluster()
        dst, unused_remote, unused_primary, unused_secondary = self._cluster_dst()
        mock_cluster_cls.objects.get.side_effect = [src, dst]

        task_spec = DtsTaskSpec(
            task_name="ha-to-cluster-ae2",
            target_cluster_id=200,
            target_spider="127.0.0.5:25000",
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="src-100",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                )
            ],
        )
        info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)
        master = info["details"]["infos"][0]["master"]
        self.assertEqual((master["ip"], master["port"]), ("127.0.0.10", 20000))

    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_checksum_follows_backend_slave_role(self, mock_cluster_cls):
        src = self._ha_src_cluster()
        dst, unused_remote, unused_primary, unused_secondary = self._cluster_dst()
        mock_cluster_cls.objects.get.side_effect = [src, dst]

        task_spec = DtsTaskSpec(
            task_name="ha-to-cluster-slave-role",
            target_cluster_id=200,
            target_spider="127.0.0.5:25000",
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="src-100",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                    source_instance_role=InstanceRole.BACKEND_SLAVE.value,
                )
            ],
        )
        info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)
        master = info["details"]["infos"][0]["master"]
        self.assertEqual((master["ip"], master["port"]), ("127.0.0.11", 20000))

    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_ae4_ha_to_ha_still_uses_backend_master(self, mock_cluster_cls):
        src = self._ha_src_cluster()
        backend_master = _make_storage_instance(
            inst_id=20, ip="127.0.0.22", port=20000, role=InstanceRole.BACKEND_MASTER.value
        )
        dst = _cluster(
            cluster_id=200,
            cluster_type=ClusterType.TenDBHA.value,
            storages=[backend_master],
        )
        mock_cluster_cls.objects.get.side_effect = [src, dst]

        task_spec = DtsTaskSpec(
            task_name="ha-to-ha-ae4",
            target_cluster_id=200,
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="src-100",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                    source_host="127.0.0.12:20000",
                )
            ],
        )
        info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)
        slave = info["details"]["infos"][0]["slaves"][0]
        self.assertEqual((slave["ip"], slave["port"]), (backend_master.machine.ip, backend_master.port))
        self.assertEqual(slave["instance_inner_role"], InstanceInnerRole.SLAVE.value)

    @patch("backend.flow.utils.mysql.dts.checksum_helper.Cluster")
    def test_invalid_spider_endpoint_raises(self, mock_cluster_cls):
        src = self._ha_src_cluster()
        dst, unused_remote, unused_primary, unused_secondary = self._cluster_dst()
        mock_cluster_cls.objects.get.side_effect = [src, dst]

        task_spec = DtsTaskSpec(
            task_name="ha-to-cluster-bad-spider",
            target_cluster_id=200,
            target_spider="127.0.0.99:25000",
            sources=[
                SourceSpec(
                    cluster_id=100,
                    source_name="src-100",
                    sync_scope=SyncScope(do_dbs=["db_a"]),
                    source_host="127.0.0.12:20000",
                )
            ],
        )
        with self.assertRaises(ValueError):
            build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=21)


class DtsModePatchTicketDetailTest(SimpleTestCase):
    @patch("backend.ticket.builders.common.base.BaseTicketFlowBuilderPatchMixin.patch_ticket_detail")
    @patch("backend.ticket.builders.mysql.mysql_checksum.DBInstance")
    @patch("backend.ticket.builders.mysql.mysql_checksum.StorageInstance")
    def test_dts_mode_preserves_preset_master(self, mock_storage_cls, mock_db_instance, mock_super_patch):
        preset_master = {
            "id": 99,
            "ip": "127.0.0.9",
            "port": 3306,
            "instance_inner_role": InstanceInnerRole.MASTER.value,
        }
        cluster_master = MagicMock()
        cluster_master.cluster.first.return_value.id = 100
        cluster_master.id = 1
        cluster_master.instance_inner_role = InstanceInnerRole.MASTER.value
        cluster_master.ip_port = "127.0.0.1:3306"
        mock_storage_cls.objects.select_related.return_value.filter.return_value = [cluster_master]
        mock_db_instance.from_inst_obj.return_value.as_dict.return_value = {
            "ip": "127.0.0.1",
            "port": 3306,
            "bk_cloud_id": 0,
            "bk_host_id": 1,
        }
        mock_super_patch.return_value = None

        ticket = MagicMock()
        ticket.details = {
            "dts_mode": True,
            "timing": "2026-07-24T12:15:00+08:00",
            "infos": [
                {
                    "cluster_id": 100,
                    "master": dict(preset_master),
                    "slaves": [{"ip": "127.0.0.2", "port": 3306}],
                }
            ],
        }
        builder = MySQLChecksumFlowBuilder(ticket)
        builder.patch_ticket_detail()

        self.assertEqual(ticket.details["infos"][0]["master"]["ip"], "127.0.0.9")
        self.assertEqual(ticket.details["infos"][0]["slaves"][0]["ip"], "127.0.0.2")
