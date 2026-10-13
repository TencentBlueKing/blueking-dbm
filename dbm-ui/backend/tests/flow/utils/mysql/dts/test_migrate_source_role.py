# -*- coding: utf-8 -*-
from types import SimpleNamespace

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.utils.mysql.dts.constants import FullLoadEngine, MigrateTopology
from backend.flow.utils.mysql.dts.migrate_helper import resolve_dump_endpoint, resolve_source_endpoint
from backend.flow.utils.mysql.dts.migrate_plan import (
    build_migrate_plan,
    build_migrate_plans,
    dts_task_spec_from_dict,
    dts_task_spec_to_dict,
    merge_backup_local,
    reject_role_on_myloader,
)


def _source(cluster_id, backup_local=None):
    source = {"cluster_id": cluster_id, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}}
    if backup_local is not None:
        source["backup_local"] = backup_local
    return source


def _one_to_one(src, dst, backup_local=None):
    return {
        "topology": MigrateTopology.ONE_TO_ONE.value,
        "one_to_one": {
            "source": _source(src, backup_local),
            "target": {"cluster_id": dst},
        },
    }


def _row(src, dst, dts_cluster_id, backup_local=None):
    return {
        "dts_resource": {"dts_cluster_id": dts_cluster_id},
        "migrate": _one_to_one(src, dst, backup_local),
        "task": {"task_mode": "all", "full_load": {"engine": FullLoadEngine.BUILTIN.value}},
    }


def _single(src=100, dst=200, backup_local=None, engine=FullLoadEngine.BUILTIN.value, task_mode="all"):
    details = {
        "dts_resource": {"dts_cluster_id": 1},
        "migrate": _one_to_one(src, dst, backup_local),
        "task": {"task_mode": task_mode, "full_load": {"engine": engine}},
    }
    return details


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
        return _QS(items)

    def order_by(self, *fields):
        items = list(self._items)
        for field in reversed(fields):
            name = str(field)[1:] if str(field).startswith("-") else str(field)
            items.sort(key=lambda item, field_name=name: getattr(item, field_name))
        return _QS(items)

    def first(self):
        return self._items[0] if self._items else None


def _ins(ip, role, ins_id, is_stand_by=False):
    return SimpleNamespace(
        id=ins_id,
        machine=SimpleNamespace(ip=ip),
        port=20000,
        instance_role=role,
        is_stand_by=is_stand_by,
        status="running",
    )


def _ha(cluster_id, master_ip, standby_ip):
    cluster = SimpleNamespace(
        id=cluster_id,
        cluster_type=ClusterType.TenDBHA.value,
        storageinstance_set=_QS(
            [
                _ins(master_ip, InstanceRole.BACKEND_MASTER.value, cluster_id),
                _ins(standby_ip, InstanceRole.BACKEND_SLAVE.value, cluster_id + 100, is_stand_by=True),
            ]
        ),
    )
    return cluster


class MergeSourceRoleTest(SimpleTestCase):
    def test_blank_pair_is_empty(self):
        self.assertEqual(merge_backup_local("", None), "")
        self.assertEqual(merge_backup_local("  ", ""), "")

    def test_one_side_wins(self):
        self.assertEqual(merge_backup_local("slave", ""), "slave")
        self.assertEqual(merge_backup_local("", "master"), "master")
        self.assertEqual(merge_backup_local("slave", "slave"), "slave")

    def test_conflict_fails(self):
        with self.assertRaises(ValueError) as ctx:
            merge_backup_local("slave", "master")
        self.assertIn("不一致", str(ctx.exception))

    def test_unknown_value_fails(self):
        with self.assertRaises(ValueError) as ctx:
            merge_backup_local("primary", "")
        self.assertIn("master", str(ctx.exception))


class SourceRolePlanTest(SimpleTestCase):
    def test_single_row_outer_slave_reaches_standby(self):
        details = _single()
        details["backup_local"] = "slave"
        plan = build_migrate_plan(details, require_task_name=False)
        source = plan.task_specs[0].sources[0]
        self.assertEqual(source.backup_local, "slave")
        self.assertNotIn("backup_local", details["migrate"]["one_to_one"]["source"])
        cluster = _ha(100, "127.0.0.10", "127.0.0.12")
        self.assertEqual(resolve_source_endpoint(source, cluster), ("127.0.0.10", 20000))
        self.assertEqual(resolve_dump_endpoint(source, cluster), ("127.0.0.12", 20000))

    def test_infos_outer_slave_uses_each_cluster_standby(self):
        details = {
            "backup_local": "slave",
            "infos": [_row(100, 200, 1), _row(101, 201, 2)],
        }
        plans = build_migrate_plans(details, require_task_name=False)
        self.assertEqual(plans[0].task_specs[0].sources[0].backup_local, "slave")
        self.assertEqual(plans[1].task_specs[0].sources[0].backup_local, "slave")
        self.assertNotIn("backup_local", details["infos"][0]["migrate"]["one_to_one"]["source"])
        self.assertNotIn("backup_local", details["infos"][1]["migrate"]["one_to_one"]["source"])
        first_cluster = _ha(100, "127.0.0.10", "127.0.0.12")
        second_cluster = _ha(101, "127.0.0.20", "127.0.0.22")
        first = plans[0].task_specs[0].sources[0]
        second = plans[1].task_specs[0].sources[0]
        self.assertEqual(resolve_source_endpoint(first, first_cluster), ("127.0.0.10", 20000))
        self.assertEqual(resolve_dump_endpoint(first, first_cluster), ("127.0.0.12", 20000))
        self.assertEqual(resolve_source_endpoint(second, second_cluster), ("127.0.0.20", 20000))
        self.assertEqual(resolve_dump_endpoint(second, second_cluster), ("127.0.0.22", 20000))

    def test_infos_outer_slave_conflicts_with_row_master(self):
        details = {
            "backup_local": "slave",
            "infos": [_row(100, 200, 1), _row(101, 201, 2, backup_local="master")],
        }
        with self.assertRaises(ValueError) as ctx:
            build_migrate_plans(details, require_task_name=False)
        self.assertIn("不一致", str(ctx.exception))
        self.assertEqual(details["infos"][1]["migrate"]["one_to_one"]["source"]["backup_local"], "master")

    def test_many_to_one_outer_slave_is_allowed(self):
        details = {
            "backup_local": "slave",
            "dts_resource": {"dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {
                    "sources": [_source(100), _source(101)],
                    "target": {"cluster_id": 200},
                },
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        self.assertEqual([source.backup_local for source in plan.task_specs[0].sources], ["slave", "slave"])
        self.assertNotIn("backup_local", details["migrate"]["many_to_one"]["sources"][0])

    def test_many_to_one_mixed_roles_are_allowed(self):
        details = {
            "dts_resource": {"dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {
                    "sources": [_source(100, "slave"), _source(101, "master")],
                    "target": {"cluster_id": 200},
                },
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        self.assertEqual([source.backup_local for source in plan.task_specs[0].sources], ["slave", "master"])

    def test_many_to_one_single_source_slave_reaches_standby(self):
        details = {
            "backup_local": "slave",
            "dts_resource": {"dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {"sources": [_source(100)], "target": {"cluster_id": 200}},
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        source = plan.task_specs[0].sources[0]
        self.assertEqual(source.backup_local, "slave")
        cluster = _ha(100, "127.0.0.10", "127.0.0.12")
        self.assertEqual(resolve_source_endpoint(source, cluster), ("127.0.0.10", 20000))
        self.assertEqual(resolve_dump_endpoint(source, cluster), ("127.0.0.12", 20000))

    def test_many_to_one_all_master_is_allowed(self):
        details = {
            "dts_resource": {"dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {
                    "sources": [_source(100, "master"), _source(101, "master")],
                    "target": {"cluster_id": 200},
                },
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        roles = [source.backup_local for source in plan.task_specs[0].sources]
        self.assertEqual(roles, ["master", "master"])

    def test_many_to_one_empty_roles_are_allowed(self):
        details = {
            "dts_resource": {"dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {"sources": [_source(100), _source(101)], "target": {"cluster_id": 200}},
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        self.assertEqual([source.backup_local for source in plan.task_specs[0].sources], ["", ""])

    def test_one_to_many_slave_is_allowed(self):
        details = {
            "backup_local": "slave",
            "dts_resource": {"dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.ONE_TO_MANY.value,
                "one_to_many": {"source": _source(100), "targets": [{"cluster_id": 200}, {"cluster_id": 201}]},
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        self.assertEqual([spec.sources[0].backup_local for spec in plan.task_specs], ["slave", "slave"])
        self.assertEqual([len(spec.sources) for spec in plan.task_specs], [1, 1])

    def test_myloader_with_role_fails_and_builtin_keeps_role(self):
        reject_role_on_myloader(FullLoadEngine.BUILTIN.value, "slave")
        kept = build_migrate_plan(_single(backup_local="slave"), require_task_name=False)
        self.assertEqual(kept.task_specs[0].sources[0].backup_local, "slave")
        with self.assertRaises(ValueError) as ctx:
            build_migrate_plan(
                _single(backup_local="slave", engine=FullLoadEngine.MYLOADER.value),
                require_task_name=False,
            )
        self.assertIn("myloader", str(ctx.exception))

    def test_backup_local_roundtrip_stays_on_task_spec(self):
        plan = build_migrate_plan(_single(backup_local="slave"), require_task_name=False)
        payload = dts_task_spec_to_dict(plan.task_specs[0])
        self.assertEqual(payload["sources"][0]["backup_local"], "slave")
        restored = dts_task_spec_from_dict(payload)
        self.assertEqual(restored.sources[0].backup_local, "slave")
