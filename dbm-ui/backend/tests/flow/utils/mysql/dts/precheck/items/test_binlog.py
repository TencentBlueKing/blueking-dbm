# -*- coding: utf-8 -*-
from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.base import CheckContext
from backend.flow.utils.mysql.dts.precheck.items import binlog
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class _Collector:
    def __init__(self, variables):
        self.variables = {key.lower(): str(value) for key, value in variables.items()}

    def global_variables(self, names):
        return {name: self.variables.get(name, "") for name in names}


class BinlogTest(TestCase):
    def test_all_rules_pass(self):
        source = _Collector(
            {
                "log_bin": "ON",
                "binlog_format": "ROW",
                "binlog_row_image": "FULL",
                "server_id": "100",
            }
        )
        results = binlog.run(CheckContext(source=source, target=_Collector({}), scope=SyncScope()))
        self.assertTrue(all(result.ok for result in results))

    def test_bad_values_fail(self):
        source = _Collector(
            {
                "log_bin": "OFF",
                "binlog_format": "STATEMENT",
                "binlog_row_image": "MINIMAL",
                "server_id": "0",
            }
        )
        results = {
            result.code: result
            for result in binlog.run(CheckContext(source=source, target=_Collector({}), scope=SyncScope()))
        }
        self.assertFalse(results["binlog.log_bin"].ok)
        self.assertFalse(results["binlog.binlog_format"].ok)
        self.assertFalse(results["binlog.binlog_row_image"].ok)
        self.assertFalse(results["binlog.server_id"].ok)
