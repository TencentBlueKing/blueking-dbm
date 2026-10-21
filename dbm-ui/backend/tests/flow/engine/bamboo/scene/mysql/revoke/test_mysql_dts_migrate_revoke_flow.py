# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import tempfile
from contextlib import ExitStack, nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError
from django.test import SimpleTestCase

from backend.flow.consts import SUCCESS
from backend.flow.engine.bamboo.scene.mysql.revoke.mysql_dts_migrate_revoke_flow import MysqlDtsMigrateRevokeFlow
from backend.flow.engine.bamboo.scene.mysql.validate.mysql_dts_migrate_validator import MysqlDtsMigrateFlowValidator
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_migrate_revoke import (
    MysqlDtsMigrateRevokeComponent,
    MysqlDtsMigrateRevokeService,
    NodeHost,
    RemoteJobUnknown,
    _delete_script,
    _job_succeeded,
    _monitor_script,
    _mysql_guard_script,
    _stop_script,
    delete_remote_paths,
    run_remote_script,
)

MOD = "backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_migrate_revoke"
FLOW = "backend.flow.engine.bamboo.scene.mysql.revoke.mysql_dts_migrate_revoke_flow"


class _Query:
    """模拟 Django QuerySet 的 filter / exclude / first / get，exc 不为空时任何查询都抛该异常。"""

    def __init__(self, rows, exc=None):
        self._rows = list(rows)
        self._exc = exc

    def _raise(self):
        if self._exc:
            raise self._exc

    def filter(self, **kwargs):
        self._raise()
        return _Query([row for row in self._rows if _match(row, kwargs)], self._exc)

    def exclude(self, **kwargs):
        self._raise()
        return _Query([row for row in self._rows if not _match(row, kwargs)], self._exc)

    def select_for_update(self):
        self._raise()
        return self

    def values_list(self, field, flat=False):
        self._raise()
        return [getattr(row, field) if flat else (getattr(row, field),) for row in self._rows]

    def first(self):
        self._raise()
        return self._rows[0] if self._rows else None

    def exists(self):
        self._raise()
        return bool(self._rows)

    def get(self, **kwargs):
        self._raise()
        matched = [row for row in self._rows if _match(row, kwargs)]
        if not matched:
            raise ObjectDoesNotExist()
        return matched[0]

    def __iter__(self):
        self._raise()
        return iter(self._rows)


class _Objects:
    """模拟 Model.objects 管理器。"""

    def __init__(self, rows, exc=None):
        self._query = _Query(rows, exc)

    def filter(self, **kwargs):
        return self._query.filter(**kwargs)

    def exclude(self, **kwargs):
        return self._query.exclude(**kwargs)

    def get(self, **kwargs):
        return self._query.get(**kwargs)

    def select_for_update(self):
        return self._query.select_for_update()


def _match(row, kwargs):
    """按属性匹配查询条件，支持 __in。"""
    for key, expected in kwargs.items():
        if key.endswith("__in"):
            if getattr(row, key[: -len("__in")]) not in expected:
                return False
        elif getattr(row, key) != expected:
            return False
    return True


class _Data:
    """模拟 pipeline 组件的 data 入参。"""

    def __init__(self, inputs):
        self.inputs = SimpleNamespace(**inputs)

    def get_one_of_inputs(self, key):
        return getattr(self.inputs, key, None)


class _FakeBuilder:
    """记录 add_act 调用的假 Builder，用来断言回收流程的节点。"""

    instances = []

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data
        self.acts = []
        self.__class__.instances.append(self)

    def add_act(self, act_name, act_component_code, kwargs=None, **extra):
        self.acts.append(
            {
                "act_name": act_name,
                "act_component_code": act_component_code,
                "kwargs": kwargs,
                "extra": extra,
            }
        )

    def run_pipeline(self, **kwargs):
        self.run_kwargs = kwargs


def _host(ip, host_id, cloud=0):
    """单据 nodes 里的一台主机。"""
    return {"ip": ip, "bk_cloud_id": cloud, "bk_host_id": host_id}


def _machine(ip, machine_type, host_id, cloud=0):
    """DBM 里登记的 Machine。"""
    return SimpleNamespace(ip=ip, bk_cloud_id=cloud, machine_type=machine_type, bk_host_id=host_id)


def _cluster(cluster_id, name, status="running", masters=(), workers=(), bk_biz_id=1, cloud=0):
    """DBM 里登记的 MysqlDtsCluster。"""
    return SimpleNamespace(
        id=cluster_id,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=cloud,
        name=name,
        status=status,
        master_nodes=list(masters),
        worker_nodes=list(workers),
        save=MagicMock(),
    )


def _deploy_row(name="dts-a", path="", engine="builtin", task_name="job1", myloader_dir=""):
    """一行 deploy 模式的迁移。deploy 里的主机、源、目标、授权、proxy IP 都不应出现在退回名单里。"""
    deploy = {
        "cluster_name": name,
        "bk_cloud_id": 0,
        "master_hosts": [{"ip": "127.0.0.9", "bk_cloud_id": 0}],
        "worker_hosts": [{"ip": "127.0.0.5", "bk_cloud_id": 0}],
    }
    if path:
        deploy["deploy_path"] = path
    full_load = {"engine": engine}
    if myloader_dir:
        full_load["myloader"] = {"myloader_dir": myloader_dir}
    return {
        "dts_resource": {"deploy": deploy},
        "task": {"task_mode": "all", "full_load": full_load},
        "migrate": {
            "topology": "one_to_one",
            "one_to_one": {
                "task_name": task_name,
                "source": {"cluster_id": 100, "source_host": "127.0.0.8"},
                "target": {"cluster_id": 200, "spider": "127.0.0.4"},
            },
        },
        "grant_hosts": ["127.0.0.7"],
        "proxy": [{"ip": "127.0.0.6"}],
    }


def _existing_row(cluster_id=5):
    """一行 use_existing 模式的迁移，复用已有 DTS 集群。"""
    return {
        "dts_resource": {"dts_cluster_id": cluster_id},
        "task": {"task_mode": "all", "full_load": {"engine": "builtin"}},
        "migrate": {
            "topology": "one_to_one",
            "one_to_one": {"source": {"cluster_id": 100}, "target": {"cluster_id": 200}},
        },
    }


def _dts_info(ticket_id, cluster_id, status):
    """一条 MysqlDtsInfo 迁移记录。"""
    return SimpleNamespace(ticket_id=ticket_id, dts_cluster_id=cluster_id, status=status)


def _details(rows, nodes):
    """迁移单 details：多行 infos 加上资源申请写回的 nodes。"""
    return {"bk_biz_id": 1, "infos": rows, "nodes": nodes}


def _inner_flow(root_id="migrate-root"):
    """迁移单的内置流程，flow_obj_id 即流水线 root_id。"""
    return SimpleNamespace(ticket_id=7, flow_type="INNER_FLOW", flow_obj_id=root_id)


def _flow_node(status, started_at=None, root_id="migrate-root"):
    """流水线里的一个节点。建流水线时状态为 created，开始执行后写 started_at。"""
    return SimpleNamespace(root_id=root_id, status=status, started_at=started_at)


_STARTED_NODES = (_flow_node("FINISHED", started_at="2026-10-21 10:00:00"),)
_UNSTARTED_NODES = (_flow_node("CREATED"), _flow_node("READY"))


class MysqlDtsMigrateRevokeFlowTest(SimpleTestCase):
    """组件的判定逻辑：哪些主机退回、哪些留下、何时下线集群。远端三个动作用 mock 代替。"""

    def _run(
        self,
        details,
        *,
        machines=(),
        clusters=(),
        flows=(_inner_flow(),),
        flow_nodes=_STARTED_NODES,
        dts_infos=(),
        machine_exc=None,
        flow_node_exc=None,
        cluster_exc=None,
        stop_return=True,
        stop_side=None,
        delete_return=True,
        delete_side=None,
        monitor_return=True,
        mysql_free=True,
        other_tickets=(),
        download_exc=None,
    ):
        """用给定的单据、Machine、集群跑一次组件，返回执行结果、输出的主机和各 mock。"""
        ticket = SimpleNamespace(id=7, bk_biz_id=1, creator="tester", details=details)
        stop = MagicMock(return_value=stop_return)
        delete = MagicMock(return_value=delete_return)
        monitor = MagicMock(return_value=monitor_return)
        guard = MagicMock(return_value=mysql_free)
        if stop_side is not None:
            stop.side_effect = stop_side
        if delete_side is not None:
            delete.side_effect = delete_side
        handler = MagicMock()
        decommission = MagicMock()
        downloads = MagicMock(side_effect=download_exc)
        patches = {
            f"{MOD}.transaction": SimpleNamespace(atomic=nullcontext),
            f"{MOD}.ensure_backup_downloads_finished": downloads,
            f"{MOD}.Ticket.objects": _Objects([ticket, *other_tickets]),
            f"{MOD}.Machine.objects": _Objects(machines, machine_exc),
            f"{MOD}.MysqlDtsCluster.objects": _Objects(clusters, cluster_exc),
            f"{MOD}.Flow.objects": _Objects(flows),
            f"{MOD}.FlowNode.objects": _Objects(flow_nodes, flow_node_exc),
            f"{MOD}.FlowTree.objects": _Objects([]),
            f"{MOD}.MysqlDtsInfo.objects": _Objects(dts_infos),
            f"{MOD}.decommission": decommission,
            f"{MOD}.stop_processes_and_recheck": stop,
            f"{MOD}.delete_remote_paths": delete,
            f"{MOD}.clean_monitor_and_crontab": monitor,
            f"{MOD}.host_free_of_mysql": guard,
            f"{MOD}.FlowOutputHandler": handler,
        }
        with ExitStack() as stack:
            for target, value in patches.items():
                stack.enter_context(patch(target, value))
            service = MysqlDtsMigrateRevokeService()
            service.log_error = MagicMock()
            data = _Data({"global_data": {"job_root_id": "root-1", "parent_ticket": 7, "bk_biz_id": 1}})
            ok = service._execute(data, None)
        if handler.return_value.insert_data.called:
            root_id, hosts = handler.return_value.insert_data.call_args.args
        else:
            root_id, hosts = None, None
        return SimpleNamespace(
            ok=ok,
            root_id=root_id,
            hosts=hosts,
            stop=stop,
            delete=delete,
            monitor=monitor,
            guard=guard,
            decommission=decommission,
            downloads=downloads,
            log_error=service.log_error,
        )

    def _deploy_world(self, **overrides):
        """一行 deploy：master、worker 各一台，都已登记成本单集群的节点。"""
        details = _details(
            [_deploy_row()],
            {
                "0_master": [_host("127.0.0.2", 102)],
                "0_worker": [_host("127.0.0.3", 103)],
            },
        )
        machines = [
            _machine("127.0.0.2", "mysql_dts_master", 102),
            _machine("127.0.0.3", "mysql_dts_worker", 103),
        ]
        clusters = [
            _cluster(11, "dts-a", masters=[{"ip": "127.0.0.2"}], workers=[{"ip": "127.0.0.3"}]),
        ]
        return self._run(details, machines=machines, clusters=clusters, **overrides)

    def test_deploy_row_outputs_node_hosts_with_bk_host_id(self):
        result = self._deploy_world()

        self.assertTrue(result.ok)
        self.assertEqual(result.root_id, "root-1")
        self.assertEqual(
            result.hosts,
            [
                {"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102},
                {"ip": "127.0.0.3", "bk_cloud_id": 0, "bk_host_id": 103},
            ],
        )
        output_ips = {host["ip"] for host in result.hosts}
        self.assertTrue(
            output_ips.isdisjoint({"127.0.0.9", "127.0.0.5", "127.0.0.8", "127.0.0.7", "127.0.0.6", "127.0.0.4"})
        )
        self.assertEqual(result.delete.call_args_list[0].args[1], ("/data/dts/dts-a",))
        self.assertFalse(result.decommission.call_args.kwargs["recycle_hosts"])
        self.assertEqual(result.decommission.call_args.kwargs["dts_cluster_id"], 11)
        self.assertEqual(
            sorted(host["ip"] for host in result.decommission.call_args.kwargs["target_hosts"]),
            ["127.0.0.2", "127.0.0.3"],
        )

    def test_use_existing_row_outputs_no_hosts_and_does_not_decommission(self):
        details = _details(
            [_existing_row()], {"0_master": [_host("127.0.0.2", 102)], "0_worker": [_host("127.0.0.3", 103)]}
        )
        result = self._run(
            details,
            clusters=[_cluster(5, "shared", masters=[{"ip": "127.0.0.2"}], workers=[{"ip": "127.0.0.3"}])],
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [])
        result.decommission.assert_not_called()
        result.stop.assert_not_called()
        result.delete.assert_not_called()

    def test_mixed_ticket_returns_only_the_deploy_row(self):
        details = _details(
            [_existing_row(), _deploy_row(name="dts-b")],
            {
                "0_master": [_host("127.0.0.1", 101)],
                "0_worker": [_host("127.0.0.4", 104)],
                "1_master": [_host("127.0.0.2", 102)],
                "1_worker": [_host("127.0.0.3", 103)],
            },
        )
        result = self._run(
            details,
            machines=[
                _machine("127.0.0.2", "mysql_dts_master", 102),
                _machine("127.0.0.3", "mysql_dts_worker", 103),
            ],
            clusters=[_cluster(12, "dts-b", masters=[{"ip": "127.0.0.2"}], workers=[{"ip": "127.0.0.3"}])],
        )

        self.assertTrue(result.ok)
        self.assertEqual([host["bk_host_id"] for host in result.hosts], [102, 103])
        self.assertEqual(result.decommission.call_count, 1)
        self.assertEqual(result.decommission.call_args.kwargs["dts_cluster_id"], 12)
        self.assertFalse(result.decommission.call_args.kwargs["recycle_hosts"])

    def test_no_machine_returns_only_when_leftovers_are_clean(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        clusters = [_cluster(11, "dts-a")]
        clean = self._run(details, machines=[], clusters=clusters)
        held = self._run(details, machines=[], clusters=clusters, stop_return=False)

        self.assertTrue(clean.ok)
        self.assertEqual(clean.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])
        clean.stop.assert_called()
        clean.delete.assert_called()
        clean.monitor.assert_called()
        self.assertFalse(held.ok)
        self.assertIsNone(held.hosts)
        held.delete.assert_not_called()
        held.decommission.assert_not_called()

    def test_process_still_present_fails_for_retry(self):
        result = self._deploy_world(stop_return=False)

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        self.assertIn("127.0.0.2", result.log_error.call_args.args[0])
        result.delete.assert_not_called()
        result.decommission.assert_not_called()

    def test_path_delete_failure_fails_for_retry(self):
        result = self._deploy_world(delete_return=False)

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.stop.assert_called()
        result.decommission.assert_not_called()

    def test_one_failed_host_skips_decommission_and_publishes_no_hosts(self):
        result = self._deploy_world(delete_side=lambda host, paths: host.ip != "127.0.0.3")

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        self.assertIn("127.0.0.3", result.log_error.call_args.args[0])
        result.decommission.assert_not_called()

    def test_machine_query_error_fails_without_hosts(self):
        result = self._deploy_world(machine_exc=OperationalError("down"))

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.stop.assert_not_called()
        result.decommission.assert_not_called()

    def test_cluster_query_error_fails_without_hosts(self):
        result = self._deploy_world(cluster_exc=OperationalError("down"))

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.decommission.assert_not_called()

    def test_ip_in_another_live_cluster_is_not_cleaned(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(
            details,
            machines=[_machine("127.0.0.2", "mysql_dts_master", 102)],
            clusters=[
                _cluster(11, "dts-a", masters=[{"ip": "127.0.0.2"}]),
                _cluster(22, "dts-other", masters=[{"ip": "127.0.0.2"}]),
            ],
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [])
        result.stop.assert_not_called()
        result.delete.assert_not_called()
        result.decommission.assert_not_called()

    def test_ip_only_in_destroyed_cluster_can_be_returned(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(
            details,
            machines=[_machine("127.0.0.2", "mysql_dts_master", 102)],
            clusters=[
                _cluster(11, "dts-a", masters=[{"ip": "127.0.0.2"}]),
                _cluster(22, "dts-old", status="destroyed", masters=[{"ip": "127.0.0.2"}]),
            ],
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])
        result.decommission.assert_called_once()

    def test_missing_or_destroyed_row_cluster_is_not_decommissioned(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        missing = self._run(details, machines=[_machine("127.0.0.2", "mysql_dts_master", 102)], clusters=[])
        destroyed = self._run(
            details,
            machines=[_machine("127.0.0.2", "mysql_dts_master", 102)],
            clusters=[_cluster(11, "dts-a", status="destroyed", masters=[{"ip": "127.0.0.2"}])],
        )

        self.assertEqual(missing.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])
        missing.decommission.assert_not_called()
        self.assertEqual(destroyed.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])
        destroyed.decommission.assert_not_called()

    def test_non_dts_machine_is_not_cleaned(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(details, machines=[_machine("127.0.0.2", "backend", 102)], clusters=[_cluster(11, "dts-a")])

        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [])
        result.stop.assert_not_called()
        result.delete.assert_not_called()

    def test_base_deploy_path_is_not_deleted(self):
        details = _details([_deploy_row(path="/data/dts")], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(
            details, machines=[_machine("127.0.0.2", "mysql_dts_master", 102)], clusters=[_cluster(11, "dts-a")]
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.stop.assert_not_called()
        result.delete.assert_not_called()
        result.decommission.assert_not_called()

    def test_custom_deploy_path_also_deletes_default_exported_data(self):
        details = _details(
            [_deploy_row(path="/data/dts/custom-a", task_name="job1")],
            {"0_worker": [_host("127.0.0.3", 103)]},
        )
        result = self._run(
            details, machines=[_machine("127.0.0.3", "mysql_dts_worker", 103)], clusters=[_cluster(11, "dts-a")]
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.hosts[0]["bk_host_id"], 103)
        self.assertEqual(
            result.delete.call_args.args[1],
            ("/data/dts/custom-a", "/data/dts/dts-a/exported_data.job1"),
        )

    def test_myloader_worker_stops_ticket_myloader_and_deletes_dump_dir(self):
        details = _details(
            [_deploy_row(engine="myloader")],
            {
                "0_master": [_host("127.0.0.2", 102)],
                "0_worker": [_host("127.0.0.3", 103)],
            },
        )
        flow = SimpleNamespace(ticket_id=7, flow_type="INNER_FLOW", flow_obj_id="migrate-root")
        result = self._run(
            details,
            machines=[
                _machine("127.0.0.2", "mysql_dts_master", 102),
                _machine("127.0.0.3", "mysql_dts_worker", 103),
            ],
            clusters=[_cluster(11, "dts-a")],
            flows=[flow],
        )

        self.assertTrue(result.ok)
        worker_call = next(call for call in result.stop.call_args_list if call.args[0].ip == "127.0.0.3")
        master_call = next(call for call in result.stop.call_args_list if call.args[0].ip == "127.0.0.2")
        self.assertIn(("myloader", ("/data/dbbak/migrate-root/dts_myloader",)), worker_call.args[1])
        self.assertNotIn("myloader", [name for name, _markers in master_call.args[1]])
        self.assertIn("/data/dbbak/migrate-root/dts_myloader", result.delete.call_args.args[1])

    def _myloader_world(self, myloader_dir):
        """一行走 myloader 的 deploy，worker 一台，单据里显式填了 myloader_dir。"""
        details = _details(
            [_deploy_row(engine="myloader", myloader_dir=myloader_dir)],
            {"0_worker": [_host("127.0.0.3", 103)]},
        )
        flow = SimpleNamespace(ticket_id=7, flow_type="INNER_FLOW", flow_obj_id="migrate-root")
        return self._run(
            details,
            machines=[_machine("127.0.0.3", "mysql_dts_worker", 103)],
            clusters=[_cluster(11, "dts-a", workers=[{"ip": "127.0.0.3"}])],
            flows=[flow],
        )

    def test_explicit_myloader_dir_on_any_data_disk_is_stopped_and_deleted(self):
        result = self._myloader_world("/data1/dbbak/custom/src")

        self.assertEqual(result.hosts, [{"ip": "127.0.0.3", "bk_cloud_id": 0, "bk_host_id": 103}])
        targets = dict(result.stop.call_args.args[1])
        self.assertEqual(targets["myloader"], ("/data1/dbbak/custom/src", "/data/dbbak/migrate-root/dts_myloader"))
        self.assertEqual(targets["dm-worker"], ("/data/dts/dts-a/bin/dm-worker",))
        self.assertIn("/data1/dbbak/custom/src", result.delete.call_args.args[1])

    def test_myloader_dir_outside_data_disk_backup_holds_the_row(self):
        for bad in (
            "/etc",
            "/home/mysql",
            "/data",
            "/data2",
            "/data/dbbak",
            "/data1/dbbak",
            "/data/dts/x",
            "/",
            "dbbak/x",
        ):
            with self.subTest(myloader_dir=bad):
                result = self._myloader_world(bad)

                self.assertFalse(result.ok)
                self.assertIsNone(result.hosts)
                result.stop.assert_not_called()
                result.delete.assert_not_called()
                result.decommission.assert_not_called()

    def test_same_name_cluster_of_another_ticket_is_not_decommissioned(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(
            details,
            machines=[_machine("127.0.0.2", "mysql_dts_master", 102)],
            clusters=[_cluster(11, "dts-a", masters=[{"ip": "127.0.0.50"}])],
        )

        self.assertEqual(result.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])
        result.decommission.assert_not_called()

    def test_machine_registered_with_another_bk_host_id_is_not_cleaned(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(details, machines=[_machine("127.0.0.2", "mysql_dts_master", 999)], clusters=[])

        self.assertEqual(result.hosts, [])
        result.stop.assert_not_called()
        result.delete.assert_not_called()

    def test_same_ip_in_another_cloud_area_does_not_hold_the_host(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(
            details,
            machines=[_machine("127.0.0.2", "mysql_dts_master", 102)],
            clusters=[_cluster(22, "dts-other", masters=[{"ip": "127.0.0.2"}], cloud=2)],
        )

        self.assertEqual(result.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])

    def test_cluster_still_used_by_another_ticket_is_left_alone(self):
        result = self._deploy_world(dts_infos=[_dts_info(ticket_id=99, cluster_id=11, status="full_online")])

        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [])
        result.stop.assert_not_called()
        result.delete.assert_not_called()
        result.monitor.assert_not_called()
        result.decommission.assert_not_called()

    def test_own_or_finished_migrate_records_do_not_block_cleanup(self):
        result = self._deploy_world(
            dts_infos=[
                _dts_info(ticket_id=7, cluster_id=11, status="todo"),
                _dts_info(ticket_id=99, cluster_id=11, status="terminated"),
            ]
        )

        self.assertEqual([host["bk_host_id"] for host in result.hosts], [102, 103])
        result.decommission.assert_called_once()

    def test_decommission_only_touches_nodes_registered_on_the_cluster(self):
        details = _details(
            [_deploy_row()],
            {"0_master": [_host("127.0.0.2", 102)], "0_worker": [_host("127.0.0.3", 103)]},
        )
        result = self._run(
            details,
            machines=[_machine("127.0.0.2", "mysql_dts_master", 102)],
            clusters=[_cluster(11, "dts-a", masters=[{"ip": "127.0.0.2"}])],
        )

        self.assertEqual([host["bk_host_id"] for host in result.hosts], [102, 103])
        self.assertEqual(result.decommission.call_args.kwargs["target_hosts"], [{"ip": "127.0.0.2", "bk_cloud_id": 0}])

    def test_host_with_mysql_instance_is_not_touched(self):
        result = self._deploy_world(mysql_free=False)

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.guard.assert_called()
        result.stop.assert_not_called()
        result.delete.assert_not_called()
        result.monitor.assert_not_called()
        result.decommission.assert_not_called()

    def test_unstarted_pipeline_returns_hosts_without_any_remote_job(self):
        for flows, flow_nodes in (((), ()), ((_inner_flow(),), ()), ((_inner_flow(),), _UNSTARTED_NODES)):
            with self.subTest(flows=flows, flow_nodes=flow_nodes):
                result = self._deploy_world(flows=flows, flow_nodes=flow_nodes, mysql_free=False)

                self.assertTrue(result.ok)
                self.assertEqual([host["bk_host_id"] for host in result.hosts], [102, 103])
                result.guard.assert_not_called()
                result.stop.assert_not_called()
                result.delete.assert_not_called()
                result.monitor.assert_not_called()

    def test_unstarted_pipeline_still_holds_occupied_or_mismatched_hosts(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        occupied = self._run(
            details,
            flow_nodes=_UNSTARTED_NODES,
            clusters=[_cluster(22, "dts-other", masters=[{"ip": "127.0.0.2"}])],
        )
        mismatched = self._run(
            details, flow_nodes=_UNSTARTED_NODES, machines=[_machine("127.0.0.2", "mysql_dts_master", 999)]
        )

        self.assertEqual(occupied.hosts, [])
        self.assertEqual(mismatched.hosts, [])

    def test_unstarted_pipeline_ignores_bad_paths_since_nothing_is_deleted(self):
        details = _details([_deploy_row(path="/data/dts")], {"0_master": [_host("127.0.0.2", 102)]})
        result = self._run(details, flow_nodes=_UNSTARTED_NODES)

        self.assertEqual(result.hosts, [{"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 102}])
        result.delete.assert_not_called()

    def test_pipeline_with_a_started_or_revoked_node_gets_full_cleanup(self):
        for node in (_flow_node("REVOKED"), _flow_node("CREATED", started_at="2026-10-21 10:00:00")):
            with self.subTest(status=node.status, started_at=node.started_at):
                result = self._deploy_world(flow_nodes=(_flow_node("CREATED"), node))

                self.assertEqual([host["bk_host_id"] for host in result.hosts], [102, 103])
                result.guard.assert_called()
                result.stop.assert_called()
                result.delete.assert_called()
                result.monitor.assert_called()

    def test_flow_node_query_error_fails_without_hosts(self):
        result = self._deploy_world(flow_node_exc=OperationalError("down"))

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)

    def test_unfinished_remote_job_fails_the_step_without_hosts(self):
        result = self._deploy_world(stop_side=RemoteJobUnknown("timeout"))

        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.decommission.assert_not_called()

    def test_revoke_flow_checks_hosts_in_one_act(self):
        _FakeBuilder.instances = []
        with patch(f"{FLOW}.Builder", _FakeBuilder):
            MysqlDtsMigrateRevokeFlow(root_id="root-1", ticket_data={"uid": 7, "bk_biz_id": 1}).revoke_flow()

        builder = _FakeBuilder.instances[0]
        self.assertEqual(builder.root_id, "root-1")
        self.assertEqual(len(builder.acts), 1)
        self.assertEqual(builder.acts[0]["act_component_code"], MysqlDtsMigrateRevokeComponent.code)
        self.assertIn("核对待退回主机", builder.acts[0]["act_name"])

    def test_three_migrate_scenes_expose_revoke_flow(self):
        scenes = (
            MySQLController.mysql_to_mysql_migrate_scene,
            MySQLController.mysql_ha_to_cluster_migrate_scene,
            MySQLController.mysql_rename_migrate_scene,
        )
        for scene in scenes:
            self.assertTrue(hasattr(scene, "revoke_flow"))
            self.assertIs(scene.revoke_flow, MysqlDtsMigrateRevokeFlow.revoke_flow)
            self.assertIs(scene.validator, MysqlDtsMigrateFlowValidator)
        self.assertFalse(hasattr(MySQLController.mysql_dts_cluster_apply_scene, "revoke_flow"))
        self.assertFalse(hasattr(MySQLController.mysql_dts_cluster_destroy_scene, "revoke_flow"))
        self.assertFalse(hasattr(MySQLController.mysql_dts_cluster_reinstall_scene, "revoke_flow"))

    def test_missing_runtime_is_not_treated_as_an_unstarted_pipeline(self):
        from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_migrate_revoke import (
            MetaQueryError,
            migrate_pipeline_started,
        )

        tree = SimpleNamespace(root_id="migrate-root", status="REVOKED", is_expired=False, tree={"activities": {}})
        with patch(f"{MOD}.FlowNode.objects", _Objects([])), patch(f"{MOD}.FlowTree.objects", _Objects([tree])):
            with self.assertRaises(MetaQueryError):
                migrate_pipeline_started("migrate-root")

    def test_other_ticket_todo_with_bound_cluster_blocks_cleanup(self):
        result = self._deploy_world(dts_infos=[_dts_info(99, 11, "todo")])
        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [])
        result.stop.assert_not_called()
        result.decommission.assert_not_called()

    def test_legacy_unbound_todo_uses_ticket_resource_to_block_cleanup(self):
        other = SimpleNamespace(id=99, details={"infos": [_existing_row(11)]})
        result = self._deploy_world(dts_infos=[_dts_info(99, 0, "todo")], other_tickets=[other])
        self.assertTrue(result.ok)
        self.assertEqual(result.hosts, [])
        result.stop.assert_not_called()
        result.decommission.assert_not_called()

    def test_legacy_unbound_todo_on_another_cluster_does_not_block(self):
        other = SimpleNamespace(id=99, details={"infos": [_existing_row(12)]})
        result = self._deploy_world(dts_infos=[_dts_info(99, 0, "todo")], other_tickets=[other])
        self.assertTrue(result.ok)
        self.assertEqual(len(result.hosts), 2)

    def test_missing_legacy_ticket_fails_without_cleanup(self):
        result = self._deploy_world(dts_infos=[_dts_info(99, 0, "todo")])
        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.stop.assert_not_called()

    def test_cleanup_marks_cluster_before_remote_work_and_retry_keeps_protection(self):
        details = _details([_deploy_row()], {"0_master": [_host("127.0.0.2", 102)]})
        cluster = _cluster(11, "dts-a", masters=[{"ip": "127.0.0.2"}])

        def fail_after_claim(host, targets):
            self.assertEqual(cluster.status, "destroying")
            cluster.save.assert_called_with(update_fields=["status", "update_at"])
            return False

        failed = self._run(details, clusters=[cluster], stop_side=fail_after_claim)
        self.assertFalse(failed.ok)
        self.assertEqual(cluster.status, "destroying")
        failed.decommission.assert_not_called()
        retried = self._run(details, clusters=[cluster])
        self.assertTrue(retried.ok)
        self.assertEqual(len(retried.hosts), 1)
        retried.decommission.assert_called_once()

    def test_monitor_failure_is_retryable_without_host_output(self):
        result = self._deploy_world(monitor_return=False)
        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        result.decommission.assert_not_called()

    def test_failed_later_row_does_not_decommission_or_publish_earlier_rows(self):
        details = _details(
            [_deploy_row(), _deploy_row(name="dts-b")],
            {"0_master": [_host("127.0.0.2", 102)], "1_worker": [_host("127.0.0.3", 103)]},
        )
        clusters = [
            _cluster(11, "dts-a", masters=[{"ip": "127.0.0.2"}]),
            _cluster(12, "dts-b", workers=[{"ip": "127.0.0.3"}]),
        ]
        failed = self._run(details, clusters=clusters, delete_side=lambda host, paths: host.ip != "127.0.0.3")
        self.assertFalse(failed.ok)
        self.assertIsNone(failed.hosts)
        failed.decommission.assert_not_called()
        retried = self._run(details, clusters=clusters)
        self.assertTrue(retried.ok)
        self.assertEqual(len(retried.hosts), 2)

    def test_incomplete_backup_download_fails_before_any_remote_cleanup(self):
        from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_revoke_downloads import (
            BackupDownloadPending,
        )

        details = _details([_deploy_row(engine="myloader")], {"0_worker": [_host("127.0.0.3", 103)]})
        result = self._run(details, download_exc=BackupDownloadPending("bill 123 still running"))
        self.assertFalse(result.ok)
        self.assertIsNone(result.hosts)
        self.assertIn("123", result.log_error.call_args.args[0])
        result.downloads.assert_called_once_with("migrate-root")
        result.guard.assert_not_called()
        result.stop.assert_not_called()
        result.delete.assert_not_called()
        result.decommission.assert_not_called()
        retried = self._run(details)
        self.assertTrue(retried.ok)
        self.assertEqual(len(retried.hosts), 1)


class RemoteScriptTest(SimpleTestCase):
    """在本机真实执行生成的脚本，验证停进程只停本行进程、删除脚本能删干净。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.procs = []
        self.addCleanup(self._reap)

    def _reap(self):
        """回收测试里起的进程，避免残留。"""
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)

    def _spawn_myloader(self, subdir):
        """在 subdir 下放一个名为 myloader 的 sleep 副本并启动，进程名是 myloader，命令行带 subdir 路径。"""
        directory = os.path.join(self.tmp, subdir)
        os.makedirs(directory)
        binary = os.path.join(directory, "myloader")
        shutil.copy(shutil.which("sleep"), binary)
        proc = subprocess.Popen([binary, "300"])
        self.procs.append(proc)
        return proc

    def _bash(self, script):
        """用 bash 执行脚本。"""
        return subprocess.run(["bash", "-c", script], timeout=60, capture_output=True, text=True)

    def test_stop_script_kills_only_processes_started_from_this_rows_dirs(self):
        mine = self._spawn_myloader("dbbak/root/dts_myloader/src")
        other = self._spawn_myloader("dbbak/root/dts_myloader2")
        marker = os.path.join(self.tmp, "dbbak/root/dts_myloader")
        dm_marker = os.path.join(self.tmp, "dts/bin/dm-worker")

        run = self._bash(_stop_script((("dm-worker", (dm_marker,)), ("myloader", (marker,)))))

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIsNotNone(mine.wait(timeout=5))
        self.assertIsNone(other.poll())

    def test_delete_script_removes_paths_and_reports_success(self):
        target = os.path.join(self.tmp, "deploy")
        os.makedirs(os.path.join(target, "bin"))

        run = self._bash(_delete_script((target, os.path.join(self.tmp, "missing"))))

        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(os.path.exists(target))

    def test_monitor_script_is_valid_shell_and_removes_keep_alive_entry(self):
        script = _monitor_script()

        self.assertEqual(subprocess.run(["bash", "-n", "-c", script]).returncode, 0)
        self.assertIn("grep -v mysql_crond_keep_alive", script)
        self.assertIn("/home/mysql/mysql-crond/mysql_crond_keep_alive.sh", script)

    def test_mysql_guard_detects_mysqld_process(self):
        directory = os.path.join(self.tmp, "bin")
        os.makedirs(directory)
        binary = os.path.join(directory, "mysqld")
        shutil.copy(shutil.which("sleep"), binary)
        self.procs.append(subprocess.Popen([binary, "300"]))

        run = self._bash(_mysql_guard_script(os.path.join(self.tmp, "none*", "mysqldata")))

        self.assertEqual(run.returncode, 1)

    def test_mysql_guard_detects_mysql_data_dir_on_any_data_disk(self):
        os.makedirs(os.path.join(self.tmp, "data1", "mysqldata"))

        run = self._bash(_mysql_guard_script(os.path.join(self.tmp, "data*", "mysqldata")))

        self.assertEqual(run.returncode, 1)
        self.assertEqual(subprocess.run(["bash", "-n", "-c", _mysql_guard_script()]).returncode, 0)

    def test_delete_refuses_paths_outside_dts_and_backup_dirs_without_dispatch(self):
        host = NodeHost(ip="127.0.0.3", bk_cloud_id=0, bk_host_id=103, roles=("worker",))
        with patch(f"{MOD}.JobApi.fast_execute_script") as dispatch:
            self.assertFalse(delete_remote_paths(host, ("/data/dts/a", "/etc")))
            self.assertFalse(delete_remote_paths(host, ("/data2",)))
        dispatch.assert_not_called()


def _status(finished, status=None):
    """作业平台 get_job_instance_status 的返回。"""
    return {"data": {"finished": finished, "job_instance": {"status": status}}}


class RemoteJobTest(SimpleTestCase):
    """作业下发与轮询：以最终状态为准，结果未知时抛 RemoteJobUnknown。"""

    def test_job_result_follows_the_final_status(self):
        with patch(f"{MOD}.time.sleep"), patch(
            f"{MOD}.JobApi.get_job_instance_status",
            side_effect=[RuntimeError("blip"), _status(False), _status(True, SUCCESS)],
        ):
            self.assertTrue(_job_succeeded(1))
        with patch(f"{MOD}.time.sleep"), patch(f"{MOD}.JobApi.get_job_instance_status", return_value=_status(True, 4)):
            self.assertFalse(_job_succeeded(1))

    def test_job_still_running_after_the_deadline_raises(self):
        clock = iter(range(0, 100000, 10))
        with patch(f"{MOD}.time.sleep"), patch(f"{MOD}.time.monotonic", side_effect=lambda: next(clock)), patch(
            f"{MOD}.JobApi.get_job_instance_status", return_value=_status(False)
        ) as query:
            with self.assertRaises(RemoteJobUnknown):
                _job_succeeded(1)
        self.assertGreater(query.call_count, 12)

    def test_dispatch_failure_raises(self):
        with patch(f"{MOD}.JobApi.fast_execute_script", side_effect=RuntimeError("down")):
            with self.assertRaises(RemoteJobUnknown):
                run_remote_script("127.0.0.3", 0, "exit 0")
        with patch(f"{MOD}.JobApi.fast_execute_script", return_value={"result": False, "data": None}):
            with self.assertRaises(RemoteJobUnknown):
                run_remote_script("127.0.0.3", 0, "exit 0")
