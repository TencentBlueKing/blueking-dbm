# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_meta.enums.version_phase import PkgSeries, VersionPhase
from backend.db_package.exceptions import DBPackageBaseException
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.dts.monitor_config import get_dts_monitor_media
from backend.flow.utils.mysql.dts.package_resolver import resolve_v2_mysql_package

_RESOLVE_GET_BY_PHASE = "backend.flow.utils.mysql.dts.package_resolver._get_v2_package_by_phase"


class ResolveV2MysqlPackageTest(SimpleTestCase):
    @patch(_RESOLVE_GET_BY_PHASE)
    def test_prefers_alpha_over_release(self, mock_get):
        alpha_pkg = SimpleNamespace(id=11)
        release_pkg = SimpleNamespace(id=22)

        def _side_effect(**kwargs):
            if kwargs["phase"] == VersionPhase.ALPHA.value:
                return alpha_pkg
            return release_pkg

        mock_get.side_effect = _side_effect
        pkg = resolve_v2_mysql_package(pkg_type=MediumEnum.MySQLMonitor.value, version_series=PkgSeries.LATEST.value)
        self.assertEqual(pkg.id, 11)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_get.call_args.kwargs["phase"], VersionPhase.ALPHA.value)

    @patch(_RESOLVE_GET_BY_PHASE)
    def test_falls_to_release_when_alpha_empty(self, mock_get):
        release_pkg = SimpleNamespace(id=22)

        def _side_effect(**kwargs):
            if kwargs["phase"] == VersionPhase.ALPHA.value:
                return None
            return release_pkg

        mock_get.side_effect = _side_effect
        pkg = resolve_v2_mysql_package(pkg_type=MediumEnum.MySQLCrond.value, version_series=PkgSeries.LATEST.value)
        self.assertEqual(pkg.id, 22)
        phases = [call.kwargs["phase"] for call in mock_get.call_args_list]
        self.assertEqual(phases, [VersionPhase.ALPHA.value, VersionPhase.RELEASE.value])

    @patch(_RESOLVE_GET_BY_PHASE)
    def test_raises_when_both_phases_empty(self, mock_get):
        mock_get.return_value = None
        with self.assertRaises(DBPackageBaseException):
            resolve_v2_mysql_package(pkg_type=MediumEnum.MySQLMonitor.value, version_series=PkgSeries.LATEST.value)


class GetDtsMonitorMediaTest(SimpleTestCase):
    @patch("backend.flow.utils.mysql.dts.monitor_config.env")
    @patch("backend.flow.utils.mysql.dts.monitor_config.resolve_v2_mysql_package")
    def test_returns_v2_bkrepo_paths(self, mock_resolve, mock_env):
        mock_env.BKREPO_PROJECT = "bk-dbm"
        mock_env.BKREPO_BUCKET = "mysql"

        def _side_effect(*, pkg_type, version_series):
            self.assertEqual(version_series, PkgSeries.LATEST.value)
            if pkg_type == MediumEnum.MySQLCrond.value:
                return SimpleNamespace(path="mysql/crond/mysql-crond.tar.gz")
            return SimpleNamespace(path="mysql/monitor/mysql-monitor.tar.gz")

        mock_resolve.side_effect = _side_effect
        file_list, crond_name, monitor_name = get_dts_monitor_media()
        self.assertEqual(
            file_list,
            [
                "bk-dbm/mysql/mysql/crond/mysql-crond.tar.gz",
                "bk-dbm/mysql/mysql/monitor/mysql-monitor.tar.gz",
            ],
        )
        self.assertEqual(crond_name, "mysql-crond.tar.gz")
        self.assertEqual(monitor_name, "mysql-monitor.tar.gz")
        self.assertEqual(mock_resolve.call_count, 2)
