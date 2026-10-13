# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.engine.bamboo.scene.mysql.validate.mysql_dts_migrate_validator import MysqlDtsMigrateFlowValidator
from backend.flow.utils.mysql.dts.constants import FullLoadEngine, MigrateTopology


class _QS:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, **kwargs):
        items = self._items
        if "instance_role" in kwargs:
            wanted = getattr(kwargs["instance_role"], "value", kwargs["instance_role"])
            items = [item for item in items if getattr(item.instance_role, "value", item.instance_role) == wanted]
        if "is_stand_by" in kwargs:
            items = [item for item in items if item.is_stand_by is kwargs["is_stand_by"]]
        if "status" in kwargs:
            wanted = getattr(kwargs["status"], "value", kwargs["status"])
            items = [item for item in items if getattr(item.status, "value", item.status) == wanted]
        if "machine__ip" in kwargs:
            items = [item for item in items if item.machine.ip == kwargs["machine__ip"]]
        if "port" in kwargs:
            items = [item for item in items if item.port == kwargs["port"]]
        return _QS(items)

    def order_by(self, *fields):
        items = list(self._items)
        for field in reversed(fields):
            name = str(field)[1:] if str(field).startswith("-") else str(field)
            items.sort(key=lambda item, field_name=name: getattr(item, field_name))
        return _QS(items)

    def first(self):
        return self._items[0] if self._items else None


def _ins(ip, role, ins_id, version, is_stand_by=False):
    return SimpleNamespace(
        id=ins_id,
        machine=SimpleNamespace(ip=ip),
        port=20000,
        instance_role=role,
        is_stand_by=is_stand_by,
        status="running",
        version=version,
    )


def _cluster(cluster_id, cluster_type, storages):
    return SimpleNamespace(
        id=cluster_id,
        cluster_type=cluster_type,
        bk_biz_id=1,
        bk_cloud_id=0,
        immute_domain="c{}.db".format(cluster_id),
        major_version="MySQL-5.7",
        db_module_id=1,
        storageinstance_set=_QS(storages),
    )


def _details(backup_local="", task_mode="all", local_role=None):
    source = {"cluster_id": 100, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}}
    if local_role is not None:
        source["backup_local"] = local_role
    return {
        "bk_biz_id": 1,
        "backup_local": backup_local,
        "dts_resource": {"dts_cluster_id": 1},
        "migrate": {
            "topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {"source": source, "target": {"cluster_id": 200}},
        },
        "task": {"task_mode": task_mode, "full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        "check_non_table_object": False,
    }


def _replica_row(host="127.0.0.10", port="20000", io_running="Yes", sql_running="Yes"):
    return {
        "Master_Host": host,
        "Master_Port": port,
        "Slave_IO_Running": io_running,
        "Slave_SQL_Running": sql_running,
    }


class SourceRoleValidatorTest(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        self.replica_rows = [_replica_row()]
        self.log_row = {"log_bin": 1, "log_updates": 1}
        self.version = "5.7.20"
        prefix = "backend.flow.engine.bamboo.scene.mysql.validate.mysql_dts_migrate_validator"
        patchers = [
            patch(prefix + ".Cluster.objects.filter", side_effect=self._clusters),
            patch(prefix + ".query_source_charset_collations", return_value=[]),
            patch(prefix + ".query_target_collations", return_value=[]),
            patch(prefix + ".query_non_table_objects", return_value=[]),
            patch(prefix + ".get_cluster_config", return_value={"mysqld": {"default_storage_engine": "innodb"}}),
            patch(prefix + ".DRSApi.rpc_mysql_replica_compat", side_effect=self._rpc),
        ]
        for patcher in patchers:
            self.addCleanup(patcher.stop)
            patcher.start()

    def _clusters(self, *args, **kwargs):
        ids = list(kwargs.get("id__in") or [])
        master = _ins("127.0.0.10", InstanceRole.BACKEND_MASTER.value, 1, self.version)
        standby = _ins("127.0.0.12", InstanceRole.BACKEND_SLAVE.value, 2, self.version, is_stand_by=True)
        target = _ins("127.0.0.20", InstanceRole.BACKEND_MASTER.value, 3, "5.7.20")
        found = {
            100: _cluster(100, ClusterType.TenDBHA.value, [master, standby]),
            200: _cluster(200, ClusterType.TenDBHA.value, [target]),
        }
        return [found[cluster_id] for cluster_id in ids]

    def _rpc(self, params):
        sql = params["cmds"][0]
        self.calls.append((params["addresses"][0], sql))
        if sql == "show slave status":
            rows = self.replica_rows
        else:
            rows = [self.log_row]
        return [{"error_msg": "", "cmd_results": [{"table_data": rows}]}]

    def _run(self, **kwargs):
        return MysqlDtsMigrateFlowValidator(_details(**kwargs))

    def test_matching_replica_passes_without_log_query(self):
        self.log_row = {"log_bin": 0, "log_updates": 0}
        self.assertIsNone(self._run(backup_local="slave", task_mode="all"))
        self.assertEqual(self.calls, [("127.0.0.12:20000", "show slave status")])

    def test_port_text_matches_master_port(self):
        self.replica_rows = [_replica_row(port="20000"), _replica_row(host="127.0.0.99", port="20000")]
        self.assertIsNone(self._run(backup_local="slave", task_mode="incremental"))

    def test_empty_replica_status_fails(self):
        self.replica_rows = []
        errors = self._run(backup_local="slave")
        self.assertEqual(errors[0]["field"], "cluster_id")
        self.assertIn("没有复制状态", errors[0]["errors"])
        self.assertIn("127.0.0.12", errors[0]["errors"])

    def test_host_match_with_different_port_fails(self):
        self.replica_rows = [_replica_row(port="20001")]
        errors = self._run(backup_local="slave")
        self.assertIn("未同时对上", errors[0]["errors"])
        self.assertIn("127.0.0.10", errors[0]["errors"])

    def test_matched_row_with_sql_thread_down_fails(self):
        self.replica_rows = [_replica_row(sql_running="No")]
        errors = self._run(backup_local="slave")
        self.assertIn("未同时对上", errors[0]["errors"])

    def test_master_and_empty_role_do_not_query_replica(self):
        self.assertIsNone(self._run(backup_local=""))
        self.assertIsNone(self._run(backup_local="master"))
        self.assertEqual(self.calls, [])

    def test_full_does_not_query_log_updates(self):
        self.assertIsNone(self._run(backup_local="slave", task_mode="full"))
        self.assertEqual(self.calls, [("127.0.0.12:20000", "show slave status")])
