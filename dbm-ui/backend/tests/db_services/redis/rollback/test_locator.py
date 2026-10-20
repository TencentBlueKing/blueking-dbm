# -*- coding: utf-8 -*-
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.constants import (
    LOCATOR_SOURCE_BKLOG,
    LOCATOR_SOURCE_TABLE,
    SINGLE_INSTANCE_SHARD_VALUE,
)
from backend.db_services.redis.rollback.locator import BackupLocator, row_to_backup_system_format


def test_row_to_backup_system_format_from_dict():
    record = row_to_backup_system_format(
        {
            "backup_tag": "REDIS_FULL",
            "status": "to_backup_system_success",
            "end_time": "2026-01-01T02:00:00+00:00",
            "start_time": "2026-01-01T01:00:00+00:00",
            "backup_file_size": 128,
            "server_ip": "1.1.1.1",
            "server_port": 30000,
            "backup_taskid": "task-1",
            "backup_file": "/data/dbbak/foo.aof.zst",
            "shard_value": "0-104999",
            "backup_identify": "SCHEDULED-2026010101",
        }
    )
    assert record["file_name"] == "foo.aof.zst"
    assert record["source_ip"] == "1.1.1.1"
    assert record["task_id"] == "task-1"
    assert record["round_key"] == "foo.aof.zst"
    assert record["shard_value"] == "0-104999"


@pytest.mark.parametrize(
    "row,expected",
    [
        ({"redis_role": "slave", "backup_file": "x.aof"}, "slave"),
        ({"role": "master", "backup_file": "x.aof"}, "master"),
        ({"backup_file": "/data/dbbak/5005578-redis-slave-1.1.1.1-30000-20260929-050000.aof.zst"}, "slave"),
        ({"redis_role": "", "backup_file": "5005578-redis-master-1.1.1.1-30000-20260929-050000.rdb"}, "master"),
        ({"backup_file": "foo.aof.zst"}, ""),
    ],
)
def test_source_role_from_field_then_file_name(row, expected):
    assert row_to_backup_system_format(row)["source_role"] == expected


def test_source_role_from_table_row():
    row = MagicMock(redis_role="slave", backup_file="x.aof", backup_file_size=1, backup_port=30000)
    assert row_to_backup_system_format(row)["source_role"] == "slave"


# --- result table and BKLog merged ------------------------------------------------------

from datetime import datetime, timedelta, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from backend.db_services.redis.rollback.locator import dedupe, identify_window, merge_sources  # noqa: E402

NOW = datetime.now(timezone.utc)


def _locator():
    cluster = MagicMock()
    cluster.immute_domain = "cache.example.db"
    return BackupLocator(cluster)


def _table_record(task_id, file_name=None, source="table"):
    return {
        "task_id": task_id,
        "shard_value": "0-1",
        "file_name": file_name or "{}.rdb".format(task_id),
        "source": source,
    }


def _bklog_record(task_id, file_name=None):
    return _table_record(task_id, file_name, source="bklog")


def _full(locator, method, table, bklog, *args):
    with patch.object(locator, "_query_table", return_value=table) as query_table, patch.object(
        locator, "_query_bklog", return_value=bklog
    ) as query_bklog:
        records = getattr(locator, method)(*args)
    query_table.assert_called_once()
    query_bklog.assert_called_once()
    return records


FULL_QUERIES = [
    ("locate_full_by_identify", ("SCHEDULED-2026101321",)),
    ("locate_full_by_task_ids", (["t1", "t2"],)),
    ("list_full_in_window", (NOW - timedelta(days=7), NOW)),
]


@pytest.mark.parametrize("method,args", FULL_QUERIES)
def test_table_only(method, args):
    locator = _locator()
    records = _full(locator, method, [_table_record("t1"), _table_record("t2")], [], *args)
    assert [(r["task_id"], r["source"]) for r in records] == [("t1", "table"), ("t2", "table")]
    assert locator.locator_source == LOCATOR_SOURCE_TABLE


@pytest.mark.parametrize("method,args", FULL_QUERIES)
def test_bklog_repeating_the_table_stays_table(method, args):
    locator = _locator()
    records = _full(
        locator, method, [_table_record("t1"), _table_record("t2")], [_bklog_record("t2"), _bklog_record("t1")], *args
    )
    assert [(r["task_id"], r["source"]) for r in records] == [("t1", "table"), ("t2", "table")]
    assert locator.locator_source == LOCATOR_SOURCE_TABLE


@pytest.mark.parametrize("method,args", FULL_QUERIES)
@pytest.mark.parametrize("table", [[], None], ids=["empty", "error"])
def test_bklog_only(method, args, table):
    locator = _locator()
    records = _full(locator, method, table, [_bklog_record("t1")], *args)
    assert [(r["task_id"], r["source"]) for r in records] == [("t1", "bklog")]
    assert locator.locator_source == LOCATOR_SOURCE_BKLOG


@pytest.mark.parametrize("method,args", FULL_QUERIES)
def test_table_and_bklog_each_hold_a_part(method, args):
    """Just switched to the table, stopped reporting mid-window, or only some task_ids reported."""
    locator = _locator()
    table = [_table_record("t2"), _table_record("t3")]
    bklog = [_bklog_record("t1"), _bklog_record("t2"), _bklog_record("t2"), _bklog_record("t4")]
    records = _full(locator, method, table, bklog, *args)
    assert [(r["task_id"], r["source"]) for r in records] == [
        ("t2", "table"),
        ("t3", "table"),
        ("t1", "bklog"),
        ("t4", "bklog"),
    ]
    assert locator.locator_source == LOCATOR_SOURCE_BKLOG


def test_same_task_id_different_files_are_kept():
    records, from_bklog = merge_sources(
        [_table_record("t1", "a.tar.split.0")],
        [_bklog_record("t1", "a.tar.split.0"), _bklog_record("t1", "a.tar.split.1")],
    )
    assert [(r["file_name"], r["source"]) for r in records] == [("a.tar.split.0", "table"), ("a.tar.split.1", "bklog")]
    assert from_bklog


def test_locator_source_follows_the_latest_full_query():
    locator = _locator()
    _full(locator, "locate_full_by_task_ids", [], [_bklog_record("t1")], ["t1"])
    assert locator.locator_source == LOCATOR_SOURCE_BKLOG
    _full(locator, "locate_full_by_identify", [_table_record("t1")], [], "SCHEDULED-1")
    assert locator.locator_source == LOCATOR_SOURCE_TABLE


def test_table_query_error_is_none_and_no_rows_is_empty():
    locator = _locator()
    with patch("backend.db_services.redis.rollback.locator.RedisBackupResult") as model:
        model.objects.using.side_effect = RuntimeError("down")
        assert locator._query_table(backup_identify="SCHEDULED-1") is None
        model.objects.using.side_effect = None
        model.objects.using.return_value.filter.return_value.filter.return_value = []
        assert locator._query_table(backup_identify="SCHEDULED-1") == []


def test_bklog_times_are_utc_iso_like_table_times():
    table = row_to_backup_system_format(
        SimpleNamespace(
            backup_tag="REDIS_FULL",
            backup_status="to_backup_system_success",
            backup_begin_time=datetime(2026, 10, 9, 13, 42, tzinfo=timezone.utc),
            backup_end_time=datetime(2026, 10, 9, 13, 50, tzinfo=timezone.utc),
            backup_file_size=1,
            backup_host="1.1.1.1",
            backup_port=30000,
            redis_role="slave",
            backup_taskid="t1",
            backup_file="a.rdb",
            shard_value="0-1",
            backup_identify="SCHEDULED-2026100921",
        )
    )
    bklog = row_to_backup_system_format(_full_log("t2", "b.rdb", "SCHEDULED-2026100921"))
    for key in ("backup_begin_time", "backup_end_time", "file_last_mtime", "uptime"):
        assert bklog[key] == table[key]
    assert bklog["backup_begin_time"] == "2026-10-09T13:42:00+00:00"
    # the merged batch's bounds and order compare strings, so mixed zones would sort wrong
    assert sorted([bklog["backup_begin_time"], "2026-10-09T13:00:00+00:00"])[0] == "2026-10-09T13:00:00+00:00"


@pytest.mark.parametrize("value", ["", None, "not-a-time"])
def test_bklog_time_missing_or_unparseable_is_empty(value):
    record = row_to_backup_system_format({"backup_file": "a.rdb", "start_time": value, "end_time": value})
    assert record["backup_begin_time"] == record["backup_end_time"] == ""


def _binlog_row(index, begin):
    return SimpleNamespace(
        backup_file="binlog-1.1.1.1-30000-{:07d}-{}.log.zst".format(index, begin.strftime("%Y%m%d%H%M%S")),
        backup_taskid="t{}".format(index),
        backup_file_size=5,
        backup_host="1.1.1.1",
        backup_port=30000,
        backup_begin_time=begin,
    )


def _binlog_log(index, begin):
    return {
        "backup_file": "binlog-1.1.1.1-30000-{:07d}-{}.log.zst".format(index, begin.strftime("%Y%m%d%H%M%S")),
        "backup_taskid": "t{}".format(index),
        "backup_file_size": 5,
        "server_ip": "1.1.1.1",
        "server_port": 30000,
        "start_time": begin.isoformat(),
    }


def test_binlog_chain_is_merged_across_sources():
    recover_at = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    begins = {i: recover_at + timedelta(minutes=20 * (i - 3)) for i in range(1, 6)}
    locator = _locator()
    # head reported to the table only, tail to BKLog only, the middle to both and twice to BKLog
    logs = [_binlog_log(i, begins[i]) for i in (2, 3, 3, 4, 5)]
    locator._esquery = MagicMock(return_value=logs)
    with patch("backend.db_services.redis.rollback.locator.RedisBinlogResult") as model:
        model.objects.using.return_value.filter.return_value = [_binlog_row(i, begins[i]) for i in (1, 2, 3)]
        records = locator.locate_binlogs("1.1.1.1", 30000, recover_at - timedelta(hours=1), recover_at)
    locator._esquery.assert_called_once()
    assert sorted(r["index"] for r in records) == [1, 2, 3, 4, 5]
    # a binlog query leaves the full backup source alone
    assert locator.locator_source == LOCATOR_SOURCE_TABLE


def test_binlog_table_error_still_reads_bklog():
    recover_at = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    locator = _locator()
    locator._esquery = MagicMock(return_value=[_binlog_log(1, recover_at)])
    with patch("backend.db_services.redis.rollback.locator.RedisBinlogResult") as model:
        model.objects.using.side_effect = RuntimeError("down")
        records = locator.locate_binlogs("1.1.1.1", 30000, recover_at - timedelta(hours=1), recover_at)
    assert [r["index"] for r in records] == [1]


def _full_log(task_id, file_name, identify, size=100):
    return {
        "backup_taskid": task_id,
        "backup_file": "/data/dbbak/" + file_name,
        "backup_identify": identify,
        "backup_file_size": size,
        "server_ip": "1.1.1.1",
        "server_port": 30000,
        "shard_value": "0-1",
        "start_time": "2026-10-09T21:42:00+08:00",
        "end_time": "2026-10-09T21:50:00+08:00",
    }


def test_bklog_filters_identify_after_parsing_and_dedupes():
    locator = _locator()
    logs = [
        _full_log("t1", "a.tar.split.0", "SCHEDULED-2026100921"),
        _full_log("t1", "a.tar.split.0", "SCHEDULED-2026100921"),
        _full_log("t2", "a.tar.split.1", "SCHEDULED-2026100921"),
        _full_log("t2", "a.tar.split.1", "SCHEDULED-2026100921"),
        _full_log("t9", "b.rdb", "SCHEDULED-2026100922"),
    ]
    locator._esquery = MagicMock(return_value=logs)
    with patch.object(locator, "_query_table", return_value=[]):
        records = locator.locate_full_by_identify("SCHEDULED-2026100921")

    start, end, query_string = locator._esquery.call_args.args
    assert "backup_identify" not in query_string
    assert "SCHEDULED" not in query_string
    assert "domain: cache.example.db" in query_string
    # a batch four days old is still in the window: it starts at the stamped hour
    assert start == datetime(2026, 10, 9, 13, 0, tzinfo=timezone.utc)
    assert end - start == timedelta(days=1)
    assert [(r["task_id"], r["file_name"]) for r in records] == [("t1", "a.tar.split.0"), ("t2", "a.tar.split.1")]
    assert sum(r["size"] for r in records) == 200


def test_bklog_task_ids_stay_in_query_string():
    locator = _locator()
    locator._esquery = MagicMock(return_value=[])
    with patch.object(locator, "_query_table", return_value=[]):
        locator.locate_full_by_task_ids(["t1"])
    assert 'backup_taskid: "t1"' in locator._esquery.call_args.args[2]


def test_identify_without_hour_keeps_default_window():
    assert identify_window("UNKNOWN") is None
    assert identify_window("SCHEDULED-2026101399") is None
    start, end = identify_window("BILL123-2026101305")
    assert start == datetime(2026, 10, 12, 21, 0, tzinfo=timezone.utc)


def test_dedupe_keeps_records_without_key():
    assert len(dedupe([{"a": None}, {"a": None}, {"a": 1}, {"a": 1}], "a")) == 3


# --- 12.10 one failing source does not drop the other ------------------------------------


def _hit(log):
    return {"_source": {"log": log if isinstance(log, str) else json.dumps(log)}}


@pytest.mark.parametrize("error", [RuntimeError("bklog down"), TimeoutError("timed out")])
@pytest.mark.parametrize("method,args", FULL_QUERIES)
def test_bklog_failure_keeps_table_records(method, args, error):
    locator = _locator()
    with patch.object(locator, "_query_table", return_value=[_table_record("t1")]), patch(
        "backend.db_services.redis.rollback.locator.BKLogApi.esquery_search", side_effect=error
    ), patch("backend.db_services.redis.rollback.locator.logger") as log:
        records = getattr(locator, method)(*args)
    assert [(r["task_id"], r["source"]) for r in records] == [("t1", "table")]
    assert locator.locator_source == LOCATOR_SOURCE_TABLE
    log.exception.assert_called_once()
    merge_log = log.info.call_args.args
    assert merge_log[3:5] == (1, "error")


def test_both_sources_failing_returns_nothing():
    locator = _locator()
    with patch.object(locator, "_query_table", return_value=None), patch(
        "backend.db_services.redis.rollback.locator.BKLogApi.esquery_search", side_effect=RuntimeError("down")
    ):
        assert locator.locate_full_by_identify("SCHEDULED-1") == []
    assert locator.locator_source == LOCATOR_SOURCE_BKLOG


def test_bklog_binlog_failure_keeps_table_binlogs():
    recover_at = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    locator = _locator()
    with patch("backend.db_services.redis.rollback.locator.RedisBinlogResult") as model, patch(
        "backend.db_services.redis.rollback.locator.BKLogApi.esquery_search", side_effect=RuntimeError("down")
    ):
        model.objects.using.return_value.filter.return_value = [_binlog_row(1, recover_at - timedelta(minutes=10))]
        records = locator.locate_binlogs("1.1.1.1", 30000, recover_at - timedelta(hours=1), recover_at)
    assert [r["index"] for r in records] == [1]


def test_bad_bklog_hit_is_skipped_alone():
    locator = _locator()
    good = _full_log("t1", "a.rdb", "SCHEDULED-2026100921")
    resp = {
        "hits": {
            "hits": [
                _hit("{not json"),
                {"_source": {}},
                _hit(good),
                _hit(dict(_full_log("t2", "b.rdb", "SCHEDULED-2026100921"), backup_file_size="n/a")),
            ]
        }
    }
    with patch.object(locator, "_query_table", return_value=[]), patch(
        "backend.db_services.redis.rollback.locator.BKLogApi.esquery_search", return_value=resp
    ):
        records = locator.locate_full_by_identify("SCHEDULED-2026100921")
    # broken JSON, a hit without a log and a record whose size will not parse are each dropped alone
    assert [r["task_id"] for r in records] == ["t1"]
    assert locator.locator_source == LOCATOR_SOURCE_BKLOG


def _page(start, count):
    return {
        "hits": {
            "hits": [
                dict(_hit(_full_log("t{}".format(i), "{}.rdb".format(i), "SCHEDULED-2026100921")), sort=[i])
                for i in range(start, start + count)
            ]
        }
    }


def test_bklog_pages_past_one_request():
    locator = _locator()
    with patch("backend.db_services.redis.rollback.locator._BKLOG_PAGE_SIZE", 2), patch(
        "backend.db_services.redis.rollback.locator.BKLogApi.esquery_search",
        side_effect=[_page(0, 2), _page(2, 2), _page(4, 1)],
    ) as search:
        logs = locator._esquery(NOW - timedelta(days=1), NOW, "*")
    assert [log["backup_taskid"] for log in logs] == ["t0", "t1", "t2", "t3", "t4"]
    assert [c.args[0]["search_after"] for c in search.call_args_list] == [[], [1], [3]]


def test_bklog_matching_too_many_logs_counts_as_failed():
    locator = _locator()
    with patch("backend.db_services.redis.rollback.locator._BKLOG_PAGE_SIZE", 2), patch(
        "backend.db_services.redis.rollback.locator._BKLOG_MAX_HITS", 4
    ), patch(
        "backend.db_services.redis.rollback.locator.BKLogApi.esquery_search",
        side_effect=[_page(0, 2), _page(2, 2), _page(4, 2)],
    ):
        assert locator._esquery(NOW - timedelta(days=1), NOW, "*") is None


@pytest.mark.parametrize(
    "cluster_type,expected",
    [
        (ClusterType.TendisRedisInstance.value, SINGLE_INSTANCE_SHARD_VALUE),
        (ClusterType.TendisTwemproxyRedisInstance.value, ""),
    ],
)
def test_master_slave_empty_shard_value_is_its_only_shard(cluster_type, expected):
    locator = _locator()
    locator.cluster.cluster_type = cluster_type
    identify = "SCHEDULED-2026102001"
    table = row_to_backup_system_format(dict(_full_log("t1", "a.aof.zst", identify), shard_value=""))
    locator._esquery = MagicMock(return_value=[dict(_full_log("t2", "b.aof.zst", identify), shard_value="")])
    with patch.object(locator, "_query_table", return_value=[table]):
        records = locator.locate_full_by_identify(identify)
    assert [r["shard_value"] for r in records] == [expected, expected]
