# -*- coding: utf-8 -*-
import re
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.utils.translation import gettext as _

from backend.flow.utils.mysql.rocksdb_ghost_collation_check import (
    GHOST_TMP_TABLE_PROBES,
    SUGGESTED_EXCEPTION_PATTERN,
    check_rocksdb_ghost_collation,
    exceptions_cover_ghost_tmp_tables,
    format_ghost_collation_findings,
)


class FakeRelatedManager:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


def make_instance(host, role, status="running"):
    return SimpleNamespace(
        machine=SimpleNamespace(ip=host, bk_cloud_id=0),
        port=3306,
        status=status,
        instance_role=role,
    )


def make_cluster():
    remote_master = make_instance("127.0.0.1", "remote_master")
    remote_slave = make_instance("127.0.0.2", "remote_slave")
    storage_set = SimpleNamespace(
        shard_id=0,
        storage_instance_tuple=SimpleNamespace(ejector=remote_master, receiver=remote_slave),
    )
    return SimpleNamespace(
        id=1,
        immute_domain="test.tendbcluster.db",
        major_version="MySQL-5.7",
        db_module_id=10,
        cluster_type="tendbcluster",
        bk_biz_id=100,
        tendbclusterstorageset_set=FakeRelatedManager([storage_set]),
    )


MODULE_PATH = "backend.flow.utils.mysql.rocksdb_ghost_collation_check"


def query_variables_from(variables_by_host):
    def query_variables(host, port, bk_cloud_id):
        value = variables_by_host[host]
        if isinstance(value, Exception):
            raise value
        return value

    return query_variables


class TestRocksDBGhostCollationCheck(TestCase):
    def check_cluster(self, engine, variables_by_host=None):
        mysql_config = {"mysqld": {"default_storage_engine": engine}}
        with (
            patch(f"{MODULE_PATH}.get_cluster_config", return_value=mysql_config),
            patch(
                f"{MODULE_PATH}.query_mysql_variables",
                side_effect=query_variables_from(variables_by_host or {}),
            ),
        ):
            return check_rocksdb_ghost_collation(make_cluster())

    def test_non_rocksdb_returns_no_findings(self):
        assert self.check_cluster("innodb") == []

    def test_rocksdb_check_on_without_exceptions_finds_master_and_slave(self):
        findings = self.check_cluster(
            "ROCKSDB",
            {
                "127.0.0.1": {
                    "rocksdb_strict_collation_check": "ON",
                    "rocksdb_strict_collation_exceptions": "",
                },
                "127.0.0.2": {
                    "rocksdb_strict_collation_check": "on",
                    "rocksdb_strict_collation_exceptions": "",
                },
            },
        )

        assert {finding.role for finding in findings} == {"remote_master", "remote_slave"}
        assert {finding.reason for finding in findings} == {"missing_exception"}
        formatted = format_ghost_collation_findings(findings)
        assert "RocksDB" in formatted
        assert "Online DDL" in formatted
        assert "SET GLOBAL" in formatted
        assert SUGGESTED_EXCEPTION_PATTERN in formatted
        assert "dbconfig" in formatted

    def test_rocksdb_check_on_with_ghost_exception_returns_no_findings(self):
        variables = {
            "rocksdb_strict_collation_check": "ON",
            "rocksdb_strict_collation_exceptions": SUGGESTED_EXCEPTION_PATTERN,
        }

        assert self.check_cluster("rocksdb", {"127.0.0.1": variables, "127.0.0.2": variables}) == []

    def test_rocksdb_check_off_returns_no_findings(self):
        variables = {
            "rocksdb_strict_collation_check": "OFF",
            "rocksdb_strict_collation_exceptions": "",
        }

        assert self.check_cluster("rocksdb", {"127.0.0.1": variables, "127.0.0.2": variables}) == []

    def test_drs_failure_is_reported_as_query_failed_finding(self):
        variables = {
            "rocksdb_strict_collation_check": "OFF",
            "rocksdb_strict_collation_exceptions": "",
        }
        with patch(f"{MODULE_PATH}.logger", create=True) as mock_logger:
            findings = self.check_cluster(
                "rocksdb",
                {"127.0.0.1": RuntimeError("DRS unavailable"), "127.0.0.2": variables},
            )

        assert len(findings) == 1
        assert findings[0].host == "127.0.0.1"
        assert findings[0].reason == "query_failed"
        assert _("查询失败") in format_ghost_collation_findings(findings)
        mock_logger.error.assert_called_once()

    def test_suggested_exception_matches_each_ghost_probe(self):
        assert exceptions_cover_ghost_tmp_tables(SUGGESTED_EXCEPTION_PATTERN)
        for probe in GHOST_TMP_TABLE_PROBES:
            with self.subTest(probe=probe):
                assert re.search(SUGGESTED_EXCEPTION_PATTERN, probe)
