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
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

START = datetime(2026, 11, 23, 9, 3, 0)
SINCE = datetime(2026, 11, 23, 0, 0, 0)


def _ha(mod):
    return mod.ClusterType.TenDBHA.value


def _spider(mod):
    return mod.ClusterType.TenDBCluster.value


def _dispatch_page(mod, config_ids, conf_cnt_map=None, clocks=None):
    return mod.dispatch_page_retries(
        bk_biz_id=1,
        cluster_type=_ha(mod),
        config_ids=config_ids,
        since=SINCE,
        conf_cnt_map=conf_cnt_map if conf_cnt_map is not None else {9: 100},
        clocks=clocks if clocks is not None else {},
        start=START,
    )


class TestClusterRetryClock:
    def test_ha_serial_interval_does_not_accumulate_jitter(self, retry_mod):
        clock = retry_mod.ClusterRetryClock(START, retry_mod.MODE_HA_SERIAL, 50)
        with patch.object(retry_mod.random, "randint", return_value=3):
            eta0, seq0 = clock.next_eta()
            eta1, seq1 = clock.next_eta()
            eta2, seq2 = clock.next_eta()
        assert (seq0, seq1, seq2) == (0, 1, 2)
        assert eta0 == START + timedelta(seconds=3)
        assert eta1 == START + timedelta(seconds=50 + 3)
        assert eta2 == START + timedelta(seconds=100 + 3)

    def test_wave_advances_every_ten_groups(self, retry_mod):
        clock = retry_mod.ClusterRetryClock(START, retry_mod.MODE_WAVE, 350)
        with patch.object(retry_mod.random, "randint", return_value=7):
            etas = [clock.next_eta()[0] for _ in range(11)]
        assert etas[0] == START + timedelta(seconds=7)
        assert etas[9] == START + timedelta(seconds=7)
        assert etas[10] == START + timedelta(seconds=350 + 7)


class TestBuildClusterClock:
    def test_ha_stays_serial_at_schedule_window(self, retry_mod):
        clock = retry_mod.build_cluster_clock(1, _ha(retry_mod), 7000, START)
        assert clock.mode == retry_mod.MODE_HA_SERIAL
        assert clock.interval_seconds == retry_mod.HA_GROUP_INTERVAL_SECONDS

    def test_larger_ha_and_spider_use_wave(self, retry_mod):
        ha_clock = retry_mod.build_cluster_clock(1, _ha(retry_mod), 7100, START)
        spider_clock = retry_mod.build_cluster_clock(2, _spider(retry_mod), 50, START)
        assert ha_clock.mode == retry_mod.MODE_WAVE
        assert ha_clock.interval_seconds == 437
        assert spider_clock.mode == retry_mod.MODE_WAVE
        assert spider_clock.interval_seconds == retry_mod.SCHEDULE_WINDOW_SECONDS

    def test_missing_conf_cnt_uses_min_wave(self, retry_mod):
        clock = retry_mod.build_cluster_clock(1, _ha(retry_mod), None, START)
        assert clock.mode == retry_mod.MODE_WAVE
        assert clock.interval_seconds == retry_mod.MIN_WAVE_INTERVAL_SECONDS


class TestNormalizeExecuteConfig:
    def test_id_is_copied_to_config_id(self, retry_mod):
        cluster_id, config = retry_mod.normalize_execute_config({"id": "12", "cluster_id": "3", "dblike": "db%"})
        assert cluster_id == 3
        assert config["config_id"] == 12
        assert config["dblike"] == "db%"

    def test_existing_config_id_is_kept(self, retry_mod):
        cluster_id, config = retry_mod.normalize_execute_config({"config_id": 8, "id": 9, "cluster_id": 2})
        assert cluster_id == 2
        assert config["config_id"] == 8

    def test_missing_cluster_or_id_returns_none(self, retry_mod):
        assert retry_mod.normalize_execute_config({"id": 1}) is None
        assert retry_mod.normalize_execute_config({"cluster_id": 1}) is None
        assert retry_mod.normalize_execute_config({}) is None
        assert retry_mod.normalize_execute_config(None) is None


class TestDispatchPageRetries:
    def test_success_is_not_dispatched(self, retry_mod):
        with patch.object(retry_mod, "_fetch_execution_sets_for_config_ids", return_value=({1}, {2})), patch.object(
            retry_mod, "query_conf_by_ids", return_value=[{"id": 2, "cluster_id": 9}, {"id": 3, "cluster_id": 9}]
        ) as query, patch.object(retry_mod, "dispatch_retry_group") as dispatched:
            fail_cnt, not_run_cnt, group_cnt = _dispatch_page(retry_mod, [1, 2, 3])
        assert (fail_cnt, not_run_cnt, group_cnt) == (1, 1, 1)
        assert query.call_args[0][2] == [2, 3]
        configs = dispatched.call_args[0][2]
        assert [item["config_id"] for item in configs] == [2, 3]

    def test_groups_by_cluster_and_hundred(self, retry_mod):
        config_ids = list(range(1, 152))

        def query(_bk_biz_id, _cluster_type, ids):
            return [{"id": config_id, "cluster_id": 9 if config_id <= 150 else 8} for config_id in ids]

        with patch.object(
            retry_mod, "_fetch_execution_sets_for_config_ids", return_value=(set(), set())
        ), patch.object(retry_mod, "query_conf_by_ids", side_effect=query), patch.object(
            retry_mod, "dispatch_retry_group"
        ) as dispatched:
            _fail, not_run_cnt, group_cnt = _dispatch_page(retry_mod, config_ids, conf_cnt_map={9: 150, 8: 1})
        assert not_run_cnt == 151
        assert group_cnt == 3
        assert dispatched.call_count == 3
        assert [call.args[1] for call in dispatched.call_args_list] == [9, 9, 8]
        assert [len(call.args[2]) for call in dispatched.call_args_list] == [100, 50, 1]

    def test_query_error_drops_only_that_chunk(self, retry_mod):
        config_ids = list(range(1, 102))

        def query(_bk_biz_id, _cluster_type, ids):
            if ids[0] == 1:
                raise RuntimeError("partition api down")
            return [{"id": config_id, "cluster_id": 9} for config_id in ids]

        with patch.object(
            retry_mod, "_fetch_execution_sets_for_config_ids", return_value=(set(), set())
        ), patch.object(retry_mod, "query_conf_by_ids", side_effect=query), patch.object(
            retry_mod, "dispatch_retry_group"
        ) as dispatched:
            _fail, not_run_cnt, group_cnt = _dispatch_page(retry_mod, config_ids)
        assert not_run_cnt == 101
        assert group_cnt == 1
        assert [item["config_id"] for item in dispatched.call_args[0][2]] == [101]


class TestDispatchRetryGroup:
    def test_empty_configs_does_not_enqueue(self, retry_mod):
        with patch.object(retry_mod.execute_tendbha_partition_task, "apply_async") as apply_async:
            retry_mod.dispatch_retry_group(_ha(retry_mod), 9, [], START, 0)
        apply_async.assert_not_called()


class TestRetryOneBiz:
    def _run(self, retry_mod, conf_cnt_map):
        built = {}
        real_build = retry_mod.build_cluster_clock

        def spy(*args, **kwargs):
            clock = real_build(*args, **kwargs)
            built["clock"] = clock
            built["conf_cnt"] = args[2]
            return clock

        with patch.object(retry_mod, "_iter_biz_config_ids", return_value=[[1]]), patch.object(
            retry_mod, "_fetch_execution_sets_for_config_ids", return_value=(set(), set())
        ), patch.object(retry_mod, "query_conf_by_ids", return_value=[{"id": 1, "cluster_id": 9}]), patch.object(
            retry_mod, "dispatch_retry_group"
        ) as dispatched, patch.object(
            retry_mod, "build_cluster_clock", side_effect=spy
        ):
            retry_mod.retry_one_biz_partition_task(1, _ha(retry_mod), conf_cnt_map)
        assert dispatched.call_count == 1
        return built

    def test_string_keys_are_coerced_and_used(self, retry_mod):
        built = self._run(retry_mod, {"9": "7000"})
        assert built["conf_cnt"] == 7000
        assert built["clock"].mode == retry_mod.MODE_HA_SERIAL

    def test_missing_map_still_dispatches_with_min_wave(self, retry_mod):
        built = self._run(retry_mod, None)
        assert built["conf_cnt"] is None
        assert built["clock"].mode == retry_mod.MODE_WAVE
        assert built["clock"].interval_seconds == retry_mod.MIN_WAVE_INTERVAL_SECONDS


class TestSchedulePartitionRetry:
    def test_loads_conf_cnt_once_and_passes_the_same_map(self, retry_mod):
        conf_cnt_map = {9: 100}
        businesses = [
            SimpleNamespace(bk_biz_id=1, config_count=10),
            SimpleNamespace(bk_biz_id=2, config_count=0),
            SimpleNamespace(bk_biz_id=3, config_count=4),
        ]
        with patch.object(retry_mod, "load_conf_cnt", return_value=conf_cnt_map) as load, patch.object(
            retry_mod, "_iter_check_biz", return_value=businesses
        ), patch.object(retry_mod.retry_one_biz_partition_task, "apply_async") as apply_async:
            retry_mod.schedule_partition_retry(_ha(retry_mod))
        load.assert_called_once_with(_ha(retry_mod))
        sent = [call.kwargs["args"] for call in apply_async.call_args_list]
        assert sent == [[1, _ha(retry_mod), conf_cnt_map], [3, _ha(retry_mod), conf_cnt_map]]
        assert sent[0][2] is sent[1][2]

    def test_load_failure_still_enqueues_with_none(self, retry_mod):
        businesses = [SimpleNamespace(bk_biz_id=1, config_count=10)]
        with patch.object(retry_mod, "load_conf_cnt", side_effect=RuntimeError("down")), patch.object(
            retry_mod, "_iter_check_biz", return_value=businesses
        ), patch.object(retry_mod.retry_one_biz_partition_task, "apply_async") as apply_async:
            retry_mod.schedule_partition_retry(_spider(retry_mod))
        apply_async.assert_called_once_with(args=[1, _spider(retry_mod), None])
