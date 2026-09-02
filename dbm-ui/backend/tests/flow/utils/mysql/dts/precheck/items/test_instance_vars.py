# -*- coding: utf-8 -*-
from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel
from backend.flow.utils.mysql.dts.precheck.constants import DTS_PRECHECK_ONE_GB
from backend.flow.utils.mysql.dts.precheck.items import instance_vars
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class _Collector:
    def __init__(self, variables, schemas=None, tables=None, processlist=None):
        self.variables = {key.lower(): str(value) for key, value in variables.items()}
        self.schemas = schemas or ["app"]
        self.tables = tables or []
        self.processlist = processlist or []

    def global_variables(self, names):
        return {name: self.variables.get(name, "") for name in names}

    def user_schemas(self):
        return list(self.schemas)

    def query(self, sql):
        if "PROCESSLIST" in sql:
            return list(self.processlist)
        return list(self.tables)


class InstanceVarsTest(TestCase):
    def test_fail_and_warn_rules(self):
        source = _Collector(
            {
                "lower_case_table_names": "0",
                "max_allowed_packet": "1",
                "connect_timeout": "9",
            },
            tables=[{"TABLE_SCHEMA": "app", "TABLE_NAME": "t1", "ROW_FORMAT": "Fixed"}],
            processlist=[
                {"ID": 1, "USER": "root", "HOST": "a", "DB": "app", "TIME": 30, "STATE": "query", "INFO": "select 1"}
            ],
        )
        target = _Collector(
            {
                "lower_case_table_names": "1",
                "max_allowed_packet": str(DTS_PRECHECK_ONE_GB - 1),
                "connect_timeout": "9",
            }
        )
        results = {
            result.code: result
            for result in instance_vars.run(CheckContext(source=source, target=target, scope=SyncScope()))
        }
        self.assertFalse(results["instance_vars.row_format"].ok)
        self.assertFalse(results["instance_vars.lower_case_table_names"].ok)
        self.assertNotIn("instance_vars.max_allowed_packet", results)
        self.assertFalse(results["instance_vars.connect_timeout"].ok)
        self.assertFalse(results["instance_vars.long_sql"].ok)
        self.assertEqual(results["instance_vars.long_sql"].level, CheckLevel.WARN)

    def test_pass_when_healthy(self):
        source = _Collector(
            {
                "lower_case_table_names": "1",
                "max_allowed_packet": "1",
                "connect_timeout": "10",
            },
            tables=[{"TABLE_SCHEMA": "app", "TABLE_NAME": "t1", "ROW_FORMAT": "Dynamic"}],
        )
        target = _Collector(
            {
                "lower_case_table_names": "1",
                "max_allowed_packet": str(DTS_PRECHECK_ONE_GB),
                "connect_timeout": "10",
            }
        )
        results = instance_vars.run(CheckContext(source=source, target=target, scope=SyncScope()))
        self.assertTrue(all(result.ok for result in results))
