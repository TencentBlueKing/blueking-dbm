# -*- coding: utf-8 -*-
import re
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.utils.translation import gettext as _

from backend.flow.utils.mysql.rocksdb_ghost_collation_check import (
    DRS_ADDRESS_CHUNK_SIZE,
    GHOST_TMP_TABLE_PROBES,
    ROCKSDB_COLLATION_VARS_CMD,
    SUGGESTED_EXCEPTION_PATTERN,
    check_rocksdb_ghost_collation,
    exceptions_cover_ghost_tmp_tables,
    format_ghost_collation_findings,
)


class FakeRelatedManager:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self

    def select_related(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.items)


def make_instance(host, role, status="running", bk_cloud_id=0, port=3306):
    return SimpleNamespace(
        machine=SimpleNamespace(ip=host, bk_cloud_id=bk_cloud_id),
        port=port,
        status=status,
        instance_role=role,
    )


def make_storage_set(shard_id, master, slave):
    return SimpleNamespace(
        shard_id=shard_id,
        storage_instance_tuple=SimpleNamespace(ejector=master, receiver=slave),
    )


def make_cluster(storage_sets=None):
    if storage_sets is None:
        storage_sets = [
            make_storage_set(
                0,
                make_instance("127.0.0.1", "remote_master"),
                make_instance("127.0.0.2", "remote_slave"),
            )
        ]
    return SimpleNamespace(
        id=1,
        immute_domain="test.tendbcluster.db",
        major_version="MySQL-5.7",
        db_module_id=10,
        cluster_type="tendbcluster",
        bk_biz_id=100,
        tendbclusterstorageset_set=FakeRelatedManager(storage_sets),
    )


MODULE_PATH = "backend.flow.utils.mysql.rocksdb_ghost_collation_check"
HEALTHY_VARS = {
    "rocksdb_strict_collation_check": "OFF",
    "rocksdb_strict_collation_exceptions": "",
}


def drs_rpc_from(variables_by_host):
    def rpc(body):
        results = []
        for address in body["addresses"]:
            host = address.split(":")[0]
            value = variables_by_host[host]
            if isinstance(value, Exception):
                results.append({"address": address, "error_msg": str(value), "cmd_results": None})
                continue
            results.append(
                {
                    "address": address,
                    "error_msg": "",
                    "cmd_results": [
                        {"table_data": [{"Variable_name": name, "Value": val} for name, val in value.items()]}
                    ],
                }
            )
        return results

    return rpc


class TestRocksDBGhostCollationCheck(TestCase):
    def check_cluster(self, engine, variables_by_host=None, cluster=None, rpc_side_effect=None):
        mysql_config = {"mysqld": {"default_storage_engine": engine}}
        rpc = rpc_side_effect or drs_rpc_from(variables_by_host or {})
        with (
            patch(f"{MODULE_PATH}.get_cluster_config", return_value=mysql_config),
            patch(f"{MODULE_PATH}.DRSApi.rpc", side_effect=rpc) as mock_rpc,
        ):
            findings = check_rocksdb_ghost_collation(cluster or make_cluster())
        return findings, mock_rpc

    def test_non_rocksdb_returns_no_findings(self):
        findings, mock_rpc = self.check_cluster("innodb")
        assert findings == []
        mock_rpc.assert_not_called()

    def test_rocksdb_check_on_without_exceptions_finds_master_and_slave(self):
        findings, unused = self.check_cluster(
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
        findings, unused = self.check_cluster("rocksdb", {"127.0.0.1": variables, "127.0.0.2": variables})
        assert findings == []

    def test_rocksdb_check_off_returns_no_findings(self):
        findings, unused = self.check_cluster("rocksdb", {"127.0.0.1": HEALTHY_VARS, "127.0.0.2": HEALTHY_VARS})
        assert findings == []

    def test_drs_failure_is_reported_as_query_failed_finding(self):
        with patch(f"{MODULE_PATH}.logger", create=True) as mock_logger:
            findings, unused = self.check_cluster(
                "rocksdb",
                {"127.0.0.1": RuntimeError("DRS unavailable"), "127.0.0.2": HEALTHY_VARS},
            )

        assert len(findings) == 1
        assert findings[0].host == "127.0.0.1"
        assert findings[0].reason == "query_failed"
        assert _("查询失败") in format_ghost_collation_findings(findings)
        mock_logger.error.assert_called_once()

    def test_same_cloud_instances_are_queried_in_one_drs_call(self):
        findings, mock_rpc = self.check_cluster("rocksdb", {"127.0.0.1": HEALTHY_VARS, "127.0.0.2": HEALTHY_VARS})

        assert findings == []
        mock_rpc.assert_called_once()
        body = mock_rpc.call_args.args[0]
        assert sorted(body["addresses"]) == ["127.0.0.1:3306", "127.0.0.2:3306"]
        assert body["cmds"] == [ROCKSDB_COLLATION_VARS_CMD]
        assert body["force"] is True
        assert body["bk_cloud_id"] == 0

    def test_different_clouds_are_queried_separately(self):
        cluster = make_cluster(
            [
                make_storage_set(
                    0,
                    make_instance("127.0.0.1", "remote_master", bk_cloud_id=0),
                    make_instance("127.0.0.2", "remote_slave", bk_cloud_id=1),
                )
            ]
        )
        findings, mock_rpc = self.check_cluster(
            "rocksdb",
            {"127.0.0.1": HEALTHY_VARS, "127.0.0.2": HEALTHY_VARS},
            cluster=cluster,
        )

        assert findings == []
        assert mock_rpc.call_count == 2
        cloud_to_addresses = {
            call.args[0]["bk_cloud_id"]: call.args[0]["addresses"] for call in mock_rpc.call_args_list
        }
        assert cloud_to_addresses[0] == ["127.0.0.1:3306"]
        assert cloud_to_addresses[1] == ["127.0.0.2:3306"]

    def test_drs_addresses_are_chunked(self):
        storage_sets = [
            make_storage_set(
                shard_id,
                make_instance(f"127.0.0.{shard_id * 2 + 1}", "remote_master"),
                make_instance(f"127.0.0.{shard_id * 2 + 2}", "remote_slave"),
            )
            for shard_id in range(2)
        ]
        variables_by_host = {f"127.0.0.{idx}": HEALTHY_VARS for idx in range(1, 5)}
        with patch(f"{MODULE_PATH}.DRS_ADDRESS_CHUNK_SIZE", 3):
            findings, mock_rpc = self.check_cluster(
                "rocksdb",
                variables_by_host,
                cluster=make_cluster(storage_sets),
            )

        assert findings == []
        assert mock_rpc.call_count == 2
        assert [len(call.args[0]["addresses"]) for call in mock_rpc.call_args_list] == [3, 1]
        assert DRS_ADDRESS_CHUNK_SIZE == 20

    def test_batch_rpc_exception_marks_chunk_as_query_failed(self):
        findings, unused = self.check_cluster(
            "rocksdb",
            rpc_side_effect=RuntimeError("DRS down"),
        )

        assert {finding.host for finding in findings} == {"127.0.0.1", "127.0.0.2"}
        assert {finding.reason for finding in findings} == {"query_failed"}

    def test_suggested_exception_matches_each_ghost_probe(self):
        assert exceptions_cover_ghost_tmp_tables(SUGGESTED_EXCEPTION_PATTERN)
        for probe in GHOST_TMP_TABLE_PROBES:
            with self.subTest(probe=probe):
                assert re.search(SUGGESTED_EXCEPTION_PATTERN, probe)
