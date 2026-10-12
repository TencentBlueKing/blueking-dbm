# -*- coding: utf-8 -*-
from backend.flow.utils.mysql.remote_master_var_consistency import (
    KIND_ABSENT,
    KIND_DIFFERENT,
    InstanceVarMap,
    diff_remote_masters,
)


def test_innodb_large_prefix_on_vs_off_is_different():
    mismatches = diff_remote_masters(
        [
            InstanceVarMap(ip="127.0.0.2", port=20000, variables={"innodb_large_prefix": "ON"}),
            InstanceVarMap(ip="127.0.0.3", port=20000, variables={"innodb_large_prefix": "OFF"}),
        ]
    )
    assert [(item.name, item.kind) for item in mismatches] == [("innodb_large_prefix", KIND_DIFFERENT)]


def test_innodb_strict_mode_on_and_one_are_equal():
    mismatches = diff_remote_masters(
        [
            InstanceVarMap(ip="127.0.0.2", port=20000, variables={"innodb_strict_mode": "ON"}),
            InstanceVarMap(ip="127.0.0.3", port=20000, variables={"innodb_strict_mode": "1"}),
        ]
    )
    assert mismatches == []


def test_unchecked_variables_do_not_mismatch():
    mismatches = diff_remote_masters(
        [
            InstanceVarMap(
                ip="127.0.0.2",
                port=20000,
                variables={
                    "innodb_large_prefix": "ON",
                    "sql_mode": "ONLY_A",
                    "collation_server": "utf8_bin",
                    "tokudb_row_format": "tokudb_zlib",
                    "default_storage_engine": "innodb",
                },
            ),
            InstanceVarMap(
                ip="127.0.0.3",
                port=20000,
                variables={
                    "innodb_large_prefix": "ON",
                    "sql_mode": "ONLY_B",
                    "collation_server": "utf8mb3_general_ci",
                    "tokudb_row_format": "tokudb_quicklz",
                    "default_storage_engine": "rocksdb",
                },
            ),
        ]
    )
    assert mismatches == []


def test_missing_rocksdb_vars_are_skipped_when_innodb_large_prefix_matches():
    mismatches = diff_remote_masters(
        [
            InstanceVarMap(ip="127.0.0.2", port=20000, variables={"innodb_large_prefix": "ON"}),
            InstanceVarMap(ip="127.0.0.3", port=20000, variables={"innodb_large_prefix": "ON"}),
        ]
    )
    assert mismatches == []


def test_one_master_missing_innodb_large_prefix_is_absent():
    mismatches = diff_remote_masters(
        [
            InstanceVarMap(ip="127.0.0.2", port=20000, variables={"innodb_large_prefix": "ON"}),
            InstanceVarMap(ip="127.0.0.3", port=20000, variables={}),
        ]
    )
    assert [(item.name, item.kind) for item in mismatches] == [("innodb_large_prefix", KIND_ABSENT)]


def test_one_master_returns_empty():
    mismatches = diff_remote_masters(
        [InstanceVarMap(ip="127.0.0.2", port=20000, variables={"innodb_large_prefix": "ON", "sql_mode": "ONLY"})]
    )
    assert mismatches == []


def test_rocksdb_strict_collation_check_on_vs_off_is_different_without_engine():
    mismatches = diff_remote_masters(
        [
            InstanceVarMap(ip="127.0.0.2", port=20000, variables={"rocksdb_strict_collation_check": "ON"}),
            InstanceVarMap(ip="127.0.0.3", port=20000, variables={"rocksdb_strict_collation_check": "OFF"}),
        ]
    )
    assert [(item.name, item.kind) for item in mismatches] == [("rocksdb_strict_collation_check", KIND_DIFFERENT)]
