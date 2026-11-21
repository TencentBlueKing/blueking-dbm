# -*- coding: utf-8 -*-
from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel
from backend.flow.utils.mysql.dts.precheck.constants import DTS_PRECHECK_ONE_GB
from backend.flow.utils.mysql.dts.precheck.items import warnings
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class _Collector:
    def __init__(self, variables):
        self.variables = {key.lower(): str(value) for key, value in variables.items()}

    def global_variables(self, names):
        return {name: self.variables.get(name, "") for name in names}


class WarningsTest(TestCase):
    def test_warning_rules(self):
        source = _Collector(
            {
                "max_allowed_packet": str(DTS_PRECHECK_ONE_GB),
                "character_set_server": "utf8mb4",
                "sql_mode": "STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION",
            }
        )
        target = _Collector(
            {
                "max_allowed_packet": str(DTS_PRECHECK_ONE_GB - 1),
                "character_set_server": "latin1",
                "sql_mode": "NO_ENGINE_SUBSTITUTION",
            }
        )
        results = {
            result.code: result
            for result in warnings.run(CheckContext(source=source, target=target, scope=SyncScope()))
        }
        self.assertFalse(results["warnings.max_allowed_packet_ge_source"].ok)
        self.assertNotIn("warnings.max_allowed_packet_gt_1gb", results)
        self.assertFalse(results["warnings.character_set_server"].ok)
        self.assertFalse(results["warnings.sql_mode"].ok)
        self.assertTrue(all(result.level == CheckLevel.WARN for result in results.values()))

    def test_equal_packet_is_accepted(self):
        value = str(DTS_PRECHECK_ONE_GB + 1)
        source = _Collector(
            {
                "max_allowed_packet": value,
                "character_set_server": "utf8mb4",
                "sql_mode": "STRICT_TRANS_TABLES",
            }
        )
        target = _Collector(
            {
                "max_allowed_packet": value,
                "character_set_server": "utf8mb4",
                "sql_mode": "STRICT_TRANS_TABLES",
            }
        )
        results = {
            result.code: result
            for result in warnings.run(CheckContext(source=source, target=target, scope=SyncScope()))
        }
        self.assertTrue(results["warnings.max_allowed_packet_ge_source"].ok)

    def test_sql_mode_ignores_order(self):
        source = _Collector({"sql_mode": "A,B", "max_allowed_packet": "2", "character_set_server": "utf8mb4"})
        target = _Collector(
            {
                "sql_mode": "B,A",
                "max_allowed_packet": "3",
                "character_set_server": "utf8mb4",
            }
        )
        results = warnings.run(CheckContext(source=source, target=target, scope=SyncScope()))
        by_code = {result.code: result for result in results}
        self.assertTrue(by_code["warnings.sql_mode"].ok)
