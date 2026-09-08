# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.migrate_plan import SyncScope
from backend.flow.utils.mysql.dts.sync_scope_exist import scope_to_exist_query


class ScopeToExistQueryTest(SimpleTestCase):
    def test_same_name_scope_keeps_ticket_patterns(self):
        query = scope_to_exist_query(
            SyncScope(
                do_dbs=["db%", "db_a"],
                ignore_dbs=["db_tmp"],
                do_tables=[{"schema": "*", "table": "tb?"}],
                ignore_tables=[{"schema": "*", "table": "tb_old"}],
            )
        )
        self.assertEqual(query.dbs, ["db%", "db_a"])
        self.assertEqual(query.ignore_dbs, ["db_tmp"])
        self.assertEqual(query.tables, ["tb?"])
        self.assertEqual(query.ignore_tables, ["tb_old"])
        self.assertTrue(query.need_check_tables)

    def test_whole_table_does_not_require_table_query(self):
        query = scope_to_exist_query(SyncScope(do_dbs=["*"], do_tables=[{"schema": "*", "table": "*"}]))
        self.assertEqual(query.dbs, ["*"])
        self.assertFalse(query.need_check_tables)

    def test_rename_scope_uses_source_side(self):
        query = scope_to_exist_query(
            SyncScope(
                table_routes=[
                    {
                        "source_db_pattern": "old%",
                        "source_table_pattern": "tb?",
                        "target_db": "new_db",
                        "target_table": "new_tb",
                    }
                ]
            )
        )
        self.assertEqual(query.dbs, ["old%"])
        self.assertEqual(query.tables, ["tb?"])
        self.assertTrue(query.need_check_tables)
