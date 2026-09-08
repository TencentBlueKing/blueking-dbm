# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.migrate_plan import SyncScope
from backend.flow.utils.mysql.dts.sync_scope_overlap import landing_object_set, objects_overlap, source_object_set


class SourceObjectsTest(SimpleTestCase):
    def test_empty_scope_is_empty_set(self):
        self.assertEqual(set(source_object_set(SyncScope()).includes), set())

    def test_named_db_with_star_table(self):
        self.assertEqual(
            set(source_object_set(SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "*"}])).includes),
            {("db_a", "*")},
        )

    def test_star_db_is_whole_instance(self):
        self.assertEqual(
            set(source_object_set(SyncScope(do_dbs=["*"], do_tables=[{"schema": "*", "table": "*"}])).includes),
            {("*", "*")},
        )

    def test_cartesian_db_and_table_patterns(self):
        self.assertEqual(
            set(source_object_set(SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "t1"}])).includes),
            {("db_a", "t1")},
        )


class ObjectsOverlapTest(SimpleTestCase):
    def test_different_dbs_do_not_overlap(self):
        self.assertFalse(
            objects_overlap(
                source_object_set(SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "*"}])),
                source_object_set(SyncScope(do_dbs=["db_b"], do_tables=[{"schema": "*", "table": "*"}])),
            )
        )

    def test_same_db_table_overlaps(self):
        left = SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "t1"}])
        right = SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "t1"}])
        self.assertTrue(objects_overlap(source_object_set(left), source_object_set(right)))

    def test_whole_db_covers_table(self):
        table_scope = SyncScope(table_routes=[{"source_db": "db_a", "source_table": "t1"}])
        self.assertTrue(
            objects_overlap(
                source_object_set(SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "*"}])),
                source_object_set(table_scope),
            )
        )

    def test_star_covers_any_object(self):
        self.assertTrue(
            objects_overlap(
                source_object_set(SyncScope(do_dbs=["*"], do_tables=[{"schema": "*", "table": "*"}])),
                source_object_set(SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "*"}])),
            )
        )

    def test_pattern_overlaps_conservatively(self):
        left = SyncScope(table_routes=[{"source_db_pattern": "shard_*", "source_table": "t1"}])
        right = SyncScope(table_routes=[{"source_db": "shard_1", "source_table": "t1"}])
        self.assertTrue(objects_overlap(source_object_set(left), source_object_set(right)))

    def test_empty_does_not_overlap(self):
        self.assertFalse(
            objects_overlap(
                source_object_set(SyncScope()),
                source_object_set(SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "*"}])),
            )
        )

    def test_ignore_db_does_not_overlap_exact_row(self):
        left = SyncScope(do_dbs=["db%"], do_tables=[{"schema": "*", "table": "*"}], ignore_dbs=["db3"])
        right = SyncScope(do_dbs=["db3"], do_tables=[{"schema": "*", "table": "*"}])
        self.assertFalse(objects_overlap(source_object_set(left), source_object_set(right)))

    def test_ignore_table_does_not_overlap_exact_row(self):
        left = SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "tb%"}], ignore_tables=["tb1%"])
        right = SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "tb10"}])
        self.assertFalse(objects_overlap(source_object_set(left), source_object_set(right)))

    def test_ignore_all_makes_scope_empty(self):
        scope = SyncScope(do_dbs=["db%"], do_tables=[{"schema": "*", "table": "*"}], ignore_dbs=["*"])
        self.assertFalse(source_object_set(scope))


class LandingObjectsTest(SimpleTestCase):
    def test_explicit_target_collision(self):
        left = SyncScope(
            table_routes=[{"source_db": "db_a", "source_table": "t1", "target_db": "app", "target_table": "t"}]
        )
        right = SyncScope(
            table_routes=[{"source_db": "db_b", "source_table": "t2", "target_db": "app", "target_table": "t"}]
        )
        self.assertTrue(objects_overlap(landing_object_set(left), landing_object_set(right)))

    def test_missing_target_falls_back_to_source(self):
        left = SyncScope(table_routes=[{"source_db": "db_a", "source_table": "t1", "target_db": "db_a"}])
        right = SyncScope(do_dbs=["db_a"], do_tables=[{"schema": "*", "table": "*"}])
        self.assertTrue(objects_overlap(landing_object_set(left), landing_object_set(right)))
