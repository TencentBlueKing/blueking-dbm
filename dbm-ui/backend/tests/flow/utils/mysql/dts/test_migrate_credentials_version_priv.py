# -*- coding: utf-8 -*-
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
        for act in acts:
            self.assertEqual(act["kwargs"]["dml_ddl_priv"], DTS_MIGRATE_DML_DDL_PRIV)
            self.assertIn("REFERENCES", act["kwargs"]["dml_ddl_priv"])
