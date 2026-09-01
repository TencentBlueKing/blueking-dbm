# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.migrate_plan import SyncScope
from backend.flow.utils.mysql.dts.sync_scope_overlap import landing_objects, objects_overlap, source_objects


class SourceObjectsTest(SimpleTestCase):
    def test_empty_scope_is_empty_set(self):
        self.assertEqual(source_objects(SyncScope()), set())

    def test_do_dbs_named_db_is_whole_schema(self):
        self.assertEqual(source_objects(SyncScope(do_dbs=["db_a"])), {("db_a", "*")})

    def test_star_db_is_whole_instance(self):
        self.assertEqual(source_objects(SyncScope(do_dbs=["*"])), {("*", "*")})


class ObjectsOverlapTest(SimpleTestCase):
    def test_different_dbs_do_not_overlap(self):
        self.assertFalse(
            objects_overlap(source_objects(SyncScope(do_dbs=["db_a"])), source_objects(SyncScope(do_dbs=["db_b"])))
        )

    def test_whole_db_covers_table(self):
        table_scope = SyncScope(table_routes=[{"source_db": "db_a", "source_table": "t1"}])
        self.assertTrue(objects_overlap(source_objects(SyncScope(do_dbs=["db_a"])), source_objects(table_scope)))

    def test_star_covers_any_object(self):
        self.assertTrue(
            objects_overlap(source_objects(SyncScope(do_dbs=["*"])), source_objects(SyncScope(do_dbs=["db_a"])))
        )

    def test_pattern_overlaps_conservatively(self):
        left = SyncScope(table_routes=[{"source_db_pattern": "shard_*", "source_table": "t1"}])
        right = SyncScope(table_routes=[{"source_db": "shard_1", "source_table": "t1"}])
        self.assertTrue(objects_overlap(source_objects(left), source_objects(right)))

    def test_empty_does_not_overlap(self):
        self.assertFalse(objects_overlap(source_objects(SyncScope()), source_objects(SyncScope(do_dbs=["db_a"]))))


class LandingObjectsTest(SimpleTestCase):
    def test_explicit_target_collision(self):
        left = SyncScope(
            table_routes=[{"source_db": "db_a", "source_table": "t1", "target_db": "app", "target_table": "t"}]
        )
        right = SyncScope(
            table_routes=[{"source_db": "db_b", "source_table": "t2", "target_db": "app", "target_table": "t"}]
        )
        self.assertTrue(objects_overlap(landing_objects(left), landing_objects(right)))

    def test_missing_target_falls_back_to_source(self):
        left = SyncScope(table_routes=[{"source_db": "db_a", "source_table": "t1", "target_db": "db_a"}])
        right = SyncScope(do_dbs=["db_a"])
        self.assertTrue(objects_overlap(landing_objects(left), landing_objects(right)))
