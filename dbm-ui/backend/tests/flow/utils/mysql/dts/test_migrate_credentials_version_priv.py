# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.migrate_credentials import (
    DTS_MIGRATE_DML_DDL_PRIV,
    DTS_MIGRATE_GLOBAL_PRIV,
    DtsGrantTarget,
    build_dts_add_user_parallel_acts,
    parse_dts_migrate_major_version,
    resolve_dts_migrate_global_priv,
)


class ResolveDtsMigrateGlobalPrivTest(SimpleTestCase):
    def test_mysql_55_includes_super(self):
        priv = resolve_dts_migrate_global_priv("MySQL-5.5")
        self.assertIn(DTS_MIGRATE_GLOBAL_PRIV, priv)
        self.assertIn("SUPER", priv)
        self.assertNotIn("BACKUP_ADMIN", priv)

    def test_mysql_57_base_only(self):
        priv = resolve_dts_migrate_global_priv("MySQL-5.7")
        self.assertEqual(priv, DTS_MIGRATE_GLOBAL_PRIV)
        self.assertNotIn("SUPER", priv)
        self.assertNotIn("BACKUP_ADMIN", priv)

    def test_mysql_80_includes_backup_admin(self):
        priv = resolve_dts_migrate_global_priv("MySQL-8.0")
        self.assertIn(DTS_MIGRATE_GLOBAL_PRIV, priv)
        self.assertIn("BACKUP_ADMIN", priv)
        self.assertNotIn("SUPER", priv)

    def test_empty_or_unparseable_raises(self):
        with self.assertRaises(ValueError):
            resolve_dts_migrate_global_priv("")
        with self.assertRaises(ValueError):
            resolve_dts_migrate_global_priv("not-a-version")
        self.assertEqual(parse_dts_migrate_major_version(""), 0)
        self.assertEqual(parse_dts_migrate_major_version("not-a-version"), 0)

    def test_mixed_targets_get_different_global_priv(self):
        acts = build_dts_add_user_parallel_acts(
            dts_user="dts_u",
            dts_password="dts_p",
            grant_hosts=["127.0.0.1"],
            grant_targets=[
                DtsGrantTarget(bk_cloud_id=0, address="127.0.0.2:3306", cluster_id=1, major_version="MySQL-5.5"),
                DtsGrantTarget(bk_cloud_id=0, address="127.0.0.3:3306", cluster_id=2, major_version="MySQL-8.0"),
            ],
        )
        self.assertEqual(len(acts), 2)
        by_addr = {a["kwargs"]["address"]: a["kwargs"]["global_priv"] for a in acts}
        self.assertIn("SUPER", by_addr["127.0.0.2:3306"])
        self.assertNotIn("BACKUP_ADMIN", by_addr["127.0.0.2:3306"])
        self.assertIn("BACKUP_ADMIN", by_addr["127.0.0.3:3306"])
        self.assertNotIn("SUPER", by_addr["127.0.0.3:3306"])

    def test_mysql_80_spider_omits_backup_admin(self):
        priv = resolve_dts_migrate_global_priv("MySQL-8.0", allow_backup_admin=False)
        self.assertEqual(priv, DTS_MIGRATE_GLOBAL_PRIV)
        self.assertNotIn("BACKUP_ADMIN", priv)
        acts = build_dts_add_user_parallel_acts(
            dts_user="dts_u",
            dts_password="dts_p",
            grant_hosts=["127.0.0.1"],
            grant_targets=[
                DtsGrantTarget(
                    bk_cloud_id=0,
                    address="127.0.0.4:25000",
                    cluster_id=1,
                    major_version="MySQL-8.0",
                    allow_backup_admin=False,
                ),
            ],
        )
        self.assertEqual(len(acts), 1)
        self.assertNotIn("BACKUP_ADMIN", acts[0]["kwargs"]["global_priv"])
        self.assertEqual(acts[0]["kwargs"]["dml_ddl_priv"], DTS_MIGRATE_DML_DDL_PRIV)
        self.assertIn("REFERENCES", acts[0]["kwargs"]["dml_ddl_priv"])
        self.assertNotIn("role", acts[0]["kwargs"])

    def test_only_primary_tdbctl_gets_role(self):
        acts = build_dts_add_user_parallel_acts(
            dts_user="dts_u",
            dts_password="dts_p",
            grant_hosts=["127.0.0.1"],
            grant_targets=[
                DtsGrantTarget(
                    bk_cloud_id=0,
                    address="127.0.0.15:25000",
                    cluster_id=1,
                    major_version="MySQL-5.7",
                    allow_backup_admin=False,
                ),
                DtsGrantTarget(
                    bk_cloud_id=0,
                    address="127.0.0.15:26000",
                    cluster_id=1,
                    major_version="MySQL-5.7",
                    allow_backup_admin=False,
                    primary_tdbctl=True,
                ),
                DtsGrantTarget(
                    bk_cloud_id=0,
                    address="127.0.0.40:20000",
                    cluster_id=1,
                    major_version="MySQL-8.0",
                ),
            ],
        )
        by_addr = {act["kwargs"]["address"]: act["kwargs"] for act in acts}
        self.assertNotIn("role", by_addr["127.0.0.15:25000"])
        self.assertEqual(by_addr["127.0.0.15:26000"]["role"], "tdbctl")
        self.assertNotIn("role", by_addr["127.0.0.40:20000"])
        self.assertNotIn("BACKUP_ADMIN", by_addr["127.0.0.15:26000"]["global_priv"])
        self.assertIn("BACKUP_ADMIN", by_addr["127.0.0.40:20000"]["global_priv"])


class AddUserRoleForwardTest(SimpleTestCase):
    def _execute(self, kwargs):
        from backend.flow.plugins.components.collections.mysql.create_user import AddUserService

        service = AddUserService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        data = MagicMock()

        def get_one(name):
            if name == "kwargs":
                return kwargs
            if name == "global_data":
                return {"bk_biz_id": 1, "created_by": "tester"}
            return None

        data.get_one_of_inputs.side_effect = get_one
        with patch(
            "backend.flow.plugins.components.collections.mysql.create_user.DBPrivManagerApi.add_priv_without_account_rule"
        ) as api:
            ok = service._execute(data, parent_data=None)
        return ok, api.call_args.kwargs["params"]

    def test_ordinary_address_omits_role(self):
        ok, params = self._execute(
            {
                "bk_cloud_id": 0,
                "user": "dts_u",
                "psw": "dts_p",
                "hosts": ["127.0.0.1"],
                "dbname": "%",
                "dml_ddl_priv": "SELECT",
                "global_priv": "RELOAD",
                "address": "127.0.0.40:20000",
            }
        )
        self.assertTrue(ok)
        self.assertNotIn("role", params)
        self.assertEqual(params["address"], "127.0.0.40:20000")

    def test_primary_tdbctl_forwards_role(self):
        ok, params = self._execute(
            {
                "bk_cloud_id": 0,
                "user": "dts_u",
                "psw": "dts_p",
                "hosts": ["127.0.0.1"],
                "dbname": "%",
                "dml_ddl_priv": "SELECT",
                "global_priv": "RELOAD",
                "address": "127.0.0.15:26000",
                "role": "tdbctl",
            }
        )
        self.assertTrue(ok)
        self.assertEqual(params["role"], "tdbctl")
        self.assertEqual(params["address"], "127.0.0.15:26000")


class GrantTargetDictRoundTripTest(SimpleTestCase):
    def test_dict_keeps_primary_tdbctl(self):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow import _resolve_temp_account
        from backend.flow.utils.mysql.dts.context import MysqlDtsMigrateSubflowInput

        inp = MysqlDtsMigrateSubflowInput(
            root_id="root",
            bk_biz_id=1,
            ticket_id=1,
            migrate_plan=None,
            dts_user="dts_u",
            dts_password="dts_p",
            grant_hosts=["127.0.0.1"],
            grant_targets=[
                {
                    "bk_cloud_id": 0,
                    "address": "127.0.0.15:26000",
                    "cluster_id": 1,
                    "major_version": "MySQL-5.7",
                    "allow_backup_admin": False,
                    "primary_tdbctl": True,
                },
                {
                    "bk_cloud_id": 0,
                    "address": "127.0.0.40:20000",
                    "cluster_id": 1,
                    "major_version": "MySQL-8.0",
                },
            ],
        )
        unused_user, unused_password, hosts, targets = _resolve_temp_account(inp)
        self.assertEqual(hosts, ["127.0.0.1"])
        by_addr = {item.address: item for item in targets}
        self.assertTrue(by_addr["127.0.0.15:26000"].primary_tdbctl)
        self.assertFalse(by_addr["127.0.0.15:26000"].allow_backup_admin)
        self.assertFalse(by_addr["127.0.0.40:20000"].primary_tdbctl)
        self.assertTrue(by_addr["127.0.0.40:20000"].allow_backup_admin)
