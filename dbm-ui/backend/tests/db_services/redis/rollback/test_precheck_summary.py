# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.binlogs import select_binlog_chain
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.issues import (
    ISSUE_BEFORE_FULL,
    ISSUE_BINLOG_DUPLICATE,
    ISSUE_BINLOG_GAP,
    ISSUE_BINLOG_HEAD_MISSING,
    ISSUE_BINLOG_NOT_UPLOADED,
    ISSUE_BINLOG_TOO_FEW,
    IssueSummary,
    ShardIssue,
    index_ranges,
    kvstore_ranges,
    short_time,
)
from backend.db_services.redis.rollback.locator import binlog_record
from backend.db_services.redis.rollback.shards import round_key_from_filename
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner

CST = timezone(timedelta(hours=8))
SHARDS = ["0-69999", "70000-139999", "140000-209999", "210000-279999", "280000-349999", "350000-419999"]
FULL_BEGIN = datetime(2026, 11, 3, 5, 0, 0, tzinfo=CST)
# The production batch: full backups ended between 05:00:05 and 05:00:15.
FULL_ENDS = [5, 10, 15, 5, 10, 15]
LAST_BINLOG = datetime(2026, 11, 3, 14, 23, 55, tzinfo=CST)


@pytest.fixture(autouse=True)
def backup_files_still_present():
    def _query(params):
        return [{"task_id": task_id, "status": 4, "expired": "0"} for task_id in params["task_ids"]]

    with patch(
        "backend.db_services.redis.rollback.backup_presence.RedisBackupApi.query_for_task_ids", side_effect=_query
    ):
        yield


def _binlog(index, begin, port=30000):
    name = "binlog-1.1.1.1-{}-{:07d}-{}.log.zst".format(port, index, begin.strftime("%Y%m%d%H%M%S"))
    return binlog_record(name, "binlog-task-{}-{}".format(port, index), 10, "1.1.1.1", port, begin)


def _uploaded_chain(port=30000, skip=()):
    """#25 before the 05:00 full backup, #26.. every ten minutes, #70 at 14:23:55: nothing after 15:02 yet."""
    binlogs = [_binlog(25, datetime(2026, 11, 2, 23, 3, 25, tzinfo=CST), port)]
    binlogs += [
        _binlog(index, datetime(2026, 11, 3, 5, 10, tzinfo=CST) + timedelta(minutes=10 * (index - 26)), port)
        for index in range(26, 70)
    ]
    binlogs.append(_binlog(70, LAST_BINLOG, port))
    return [b for b in binlogs if b["index"] not in skip]


def _record(i):
    port = 30000 + i
    file_name = "5-TENDISSSD-FULL-slave-1.1.1.1-{}-20261103-050000-9.tar".format(port)
    return {
        "shard_value": SHARDS[i],
        "source_ip": "1.1.1.1",
        "server_port": port,
        "file_name": file_name,
        "task_id": "full-task-{}".format(i),
        "size": 100,
        "backup_identify": "SCHEDULED-2026110305",
        "backup_begin_time": FULL_BEGIN.isoformat(),
        "backup_end_time": (FULL_BEGIN + timedelta(seconds=FULL_ENDS[i])).isoformat(),
        "round_key": round_key_from_filename(file_name),
    }


def _planner(recovery_time_point, binlogs=None, **info):
    cluster = MagicMock()
    cluster.id = 1000311
    cluster.immute_domain = "ssd.example.db"
    cluster.cluster_type = ClusterType.TwemproxyTendisSSDInstance.value
    cluster.bk_cloud_id = 0
    cluster.bk_biz_id = 3
    cluster.major_version = "TendisSSD-1.3"
    cluster.proxyinstance_set.first.return_value = MagicMock(port=50000)
    planner = RollbackPlanner(
        cluster,
        {"backup_identify": "SCHEDULED-2026110305", "recovery_time_point": recovery_time_point, **info},
    )
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(return_value=[_record(i) for i in range(len(SHARDS))])
    planner.locator.locate_binlogs = MagicMock(
        side_effect=lambda ip, port, start, end: (binlogs or {}).get(port, _uploaded_chain(port))
    )
    return planner


# --- the two production requests -----------------------------------------------------------


def test_binlogs_not_uploaded_yet_lead_the_errors_with_the_latest_time_to_pick():
    planner = _planner("2026-11-03T15:02:00+08:00", shard_values=["0-69999"], resource_spec={"redis": {"count": 1}})
    result = planner.precheck()

    assert result["exist"] is False
    assert result["errors"] == ["分片 0-69999：15:02 之后还没有 binlog（#25~#70，最新 14:23:55），请选不晚于 14:23:55 或稍后重试"]
    assert "binlog-" not in result["errors"][0]
    assert not any("主机数量" in error for error in result["errors"])

    (group,) = result["error_groups"]
    assert group["code"] == ISSUE_BINLOG_NOT_UPLOADED and group["summary"] == result["errors"][0]
    (detail,) = group["shards"]
    assert (detail["shard_value"], detail["source_ip"], detail["source_port"]) == ("0-69999", "1.1.1.1", 30000)
    assert "右边界缺失" in detail["message"] and "binlog-1.1.1.1-30000-0000070-" in detail["message"]
    assert detail["data"]["first"]["index"] == 25 and detail["data"]["last"]["index"] == 70
    assert detail["data"]["latest_begin"].startswith("2026-11-03")
    assert "errors" not in result["shards"][0]


def test_time_before_the_batch_is_one_line_for_every_shard_and_no_host_count_error():
    planner = _planner("2026-11-03T00:07:00+08:00", resource_spec={"redis": {"count": 6}})
    result = planner.precheck()

    assert result["errors"] == ["6 个分片：回档时刻 00:07 早于全备完成（最晚 05:00:15），请选不早于 05:00:15 的时刻"]
    (group,) = result["error_groups"]
    assert group["code"] == ISSUE_BEFORE_FULL
    assert [shard["shard_value"] for shard in group["shards"]] == sorted(SHARDS)
    assert all("早于该分片全备完成时间" in shard["message"] for shard in group["shards"])
    planner.locator.locate_binlogs.assert_not_called()


def test_ticket_validation_leads_with_the_precheck_summary_and_keeps_the_detail():
    planner = _planner("2026-11-03T15:02:00+08:00", shard_values=["0-69999"], resource_spec={"redis": {"count": 1}})
    top = planner.precheck()["errors"][0]
    with pytest.raises(RollbackPlanError) as exc:
        planner.build(pack=False)

    assert exc.value.message.startswith(top)
    assert "binlog-1.1.1.1-30000-0000070-" in exc.value.message
    assert "主机数量" not in exc.value.message


# --- short forms ------------------------------------------------------------------------


def test_gap_names_the_missing_indexes_as_ranges():
    binlogs = {30000: _uploaded_chain(skip=(31, 32, 33, 40))}
    result = _planner("2026-11-03T14:00:00+08:00", binlogs=binlogs, shard_values=["0-69999"]).precheck()

    assert result["errors"] == ["分片 0-69999：binlog 缺 #31-33,#40（#25~#70），可开启“允许 binlog 不连续”"]
    detail = result["error_groups"][0]["shards"][0]
    assert result["error_groups"][0]["code"] == ISSUE_BINLOG_GAP
    assert detail["data"]["missing"] == [31, 32, 33, 40] and detail["data"]["missing_count"] == 4


def test_several_reasons_share_the_top_line_and_get_a_line_each():
    after_target = _binlog(71, datetime(2026, 11, 3, 15, 10, tzinfo=CST), port=30001)
    gapped = {30001: _uploaded_chain(port=30001, skip=(31, 32, 33)) + [after_target]}
    result = _planner("2026-11-03T15:02:00+08:00", binlogs=gapped, shard_values=SHARDS[:3]).precheck()

    assert result["errors"] == [
        "3 个分片无法构造：2 个 15:02 之后还没有 binlog（最新 14:23:55）；分片 70000-139999 binlog 缺 #31-33（#25~#71）",
        "2 个分片：15:02 之后还没有 binlog（最新 14:23:55），请选不晚于 14:23:55 或稍后重试",
        "分片 70000-139999：binlog 缺 #31-33（#25~#71），可开启“允许 binlog 不连续”",
    ]
    assert [group["code"] for group in result["error_groups"]] == [ISSUE_BINLOG_NOT_UPLOADED, ISSUE_BINLOG_GAP]


def test_request_level_errors_still_come_back_alone():
    result = _planner("not-a-time").precheck()
    assert result["shards"] == [] and result["error_groups"] == []
    assert len(result["errors"]) == 1 and "recovery_time_point" in result["errors"][0]


def _plus_issue(kvstore, latest_minute, first=1, last=9):
    data = {
        "first": {"index": first, "begin_time": LAST_BINLOG - timedelta(hours=5)},
        "last": {"index": last, "begin_time": LAST_BINLOG},
        "latest_begin": LAST_BINLOG + timedelta(minutes=latest_minute),
        "kvstore": kvstore,
    }
    return ShardIssue(ISSUE_BINLOG_NOT_UPLOADED, "kvstore {}: 右边界缺失".format(kvstore), data)


def test_tendisplus_kvstores_with_the_same_problem_are_merged():
    shard = SimpleNamespace(
        shard_value="0-5460",
        source_ip="1.1.1.1",
        source_port=30000,
        issues=[_plus_issue(0, 0), _plus_issue(1, 3, last=8), _plus_issue(2, 5), _plus_issue(5, 1)],
    )
    summary = IssueSummary.of([shard], datetime(2026, 11, 3, 15, 2, tzinfo=CST))

    assert summary.lines() == ["分片 0-5460：kv0-2,kv5 15:02 之后还没有 binlog（最新 14:23:55），请选不晚于 14:23:55 或稍后重试"]
    assert [detail["kvstore"] for detail in summary.error_groups()[0]["shards"]] == [0, 1, 2, 5]


def test_short_form_helpers():
    assert index_ranges([31, 32, 33, 40]) == "#31-33,#40"
    assert index_ranges([31, 32, 33, 40, 45, 50]) == "#31-33,#40,#45 等6个"
    assert index_ranges([31, 32], total=12) == "#31-32 等12个"
    assert kvstore_ranges([5, 0, 1, 2]) == "kv0-2,kv5"
    ref = datetime(2026, 11, 3, 15, 2, tzinfo=CST)
    assert short_time(LAST_BINLOG, ref, seconds=True) == "14:23:55"
    assert short_time(datetime(2026, 11, 2, 23, 3, tzinfo=CST), ref) == "11-02 23:03"


# --- every chain failure carries its code and data ---------------------------------------


T0 = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)


def _chain(*pairs):
    return [_binlog(index, T0 + timedelta(minutes=minutes)) for index, minutes in pairs]


@pytest.mark.parametrize(
    "binlogs,recover_minutes,code,key",
    [
        (((3, 10), (5, 70)), 60, ISSUE_BINLOG_HEAD_MISSING, "full_start"),
        (((1, -40), (2, -20), (3, 10)), 60, ISSUE_BINLOG_NOT_UPLOADED, "latest_begin"),
        (((1, 0),), 0, ISSUE_BINLOG_TOO_FEW, "first"),
        (((1, -40), (2, -20), (3, 10), (3, 70)), 60, ISSUE_BINLOG_DUPLICATE, "duplicated"),
        (((1, -40), (2, -20), (3, 10), (5, 70)), 60, ISSUE_BINLOG_GAP, "missing"),
        (((7, -20), (8, 10), (1, 40), (2, 70)), 60, ISSUE_BINLOG_GAP, "restarted"),
    ],
)
def test_chain_failures_carry_a_code_and_data(binlogs, recover_minutes, code, key):
    chain = _chain(*binlogs)
    if code == ISSUE_BINLOG_DUPLICATE:
        chain[-1] = dict(chain[-1], file_name=chain[-1]["file_name"] + ".dup")
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(
            chain, T0, T0 + timedelta(minutes=recover_minutes), allow_nonconsecutive=key == "restarted"
        )
    assert exc.value.issue_code == code
    assert exc.value.issue_data.get(key) is not None
