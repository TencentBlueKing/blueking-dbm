# -*- coding: utf-8 -*-
from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.base import CheckContext
from backend.flow.utils.mysql.dts.precheck.items import charset_collation
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class _Collector:
    def __init__(self, schemas=None, source_pairs=None, target_pairs=None, tables=None):
        self.schemas = schemas or ["app"]
        self.source_pairs = source_pairs or []
        self.target_pairs = target_pairs or []
        self.tables = tables or []

    def user_schemas(self):
        return list(self.schemas)

    def query(self, sql):
        if "information_schema.COLLATIONS" in sql and "TABLES" not in sql:
            return [
                {"CHARACTER_SET_NAME": charset, "COLLATION_NAME": collation}
                for charset, collation in self.target_pairs
            ]
        if "GROUP BY CHARACTER_SET_NAME" in sql:
            return [
                {"CHARACTER_SET_NAME": charset, "COLLATION_NAME": collation, "sample": sample}
                for charset, collation, sample in self.source_pairs
            ]
        return list(self.tables)


class CharsetCollationTest(TestCase):
    def test_missing_collation_fails(self):
        source = _Collector(
            source_pairs=[("utf8mb4", "utf8mb4_bin", "app.t1")],
            tables=[{"TABLE_SCHEMA": "app", "TABLE_NAME": "t1"}],
        )
        target = _Collector(target_pairs=[("utf8mb4", "utf8mb4_general_ci")])
        result = charset_collation.run(CheckContext(source=source, target=target, scope=SyncScope()))[0]
        self.assertFalse(result.ok)
        self.assertEqual(result.details["missing"][0]["collation"], "utf8mb4_bin")

    def test_supported_collation_passes(self):
        source = _Collector(source_pairs=[("utf8mb4", "utf8mb4_bin", "app.t1")])
        target = _Collector(target_pairs=[("utf8mb4", "utf8mb4_bin")])
        result = charset_collation.run(CheckContext(source=source, target=target, scope=SyncScope()))[0]
        self.assertTrue(result.ok)
