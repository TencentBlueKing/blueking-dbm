# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

DOMAIN = "kafka.test.db"


def local(year, month, day, hour=0, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def ts_ms(moment):
    return int(moment.timestamp() * 1000)


def make_series(domain=DOMAIN, ip="127.0.0.1", mount="/data", points=()):
    return {
        "dimensions": {"cluster_domain": domain, "bk_target_ip": ip, "mount_point": mount},
        "datapoints": [[value, ts_ms(moment)] for value, moment in points],
    }


class TestResolveWindow:
    def test_morning_uses_yesterday_and_excludes_today(self, check_mod):
        now = local(2026, 11, 5, 9, 25)
        check_day, start, end = check_mod._resolve_window("morning", now)
        assert check_day == date(2026, 11, 4)
        assert end == local(2026, 11, 5)
        # 往前取 9 天：判定日 -2 天需要它之前的 7 天
        assert start == local(2026, 10, 26)

    def test_afternoon_uses_today_until_now(self, check_mod):
        now = local(2026, 11, 5, 16, 25)
        check_day, start, end = check_mod._resolve_window("afternoon", now)
        assert check_day == date(2026, 11, 5)
        assert end == now
        assert start == local(2026, 10, 27)


class TestPointSlot:
    def test_midnight_point_belongs_to_previous_day(self, check_mod):
        # 整点 00:00 的点是它之前一个小时的最大值，属于前一天的最后一个小时窗口（序号 23）
        assert check_mod._point_slot(ts_ms(local(2026, 11, 5, 0, 0))) == (date(2026, 11, 4), 23)

    def test_other_hours(self, check_mod):
        assert check_mod._point_slot(ts_ms(local(2026, 11, 5, 1, 0))) == (date(2026, 11, 5), 0)
        assert check_mod._point_slot(ts_ms(local(2026, 11, 5, 23, 0))) == (date(2026, 11, 5), 22)


def day_points(day, value=50.0, missing=(), peak_hour=None, peak=None):
    """某天 24 个小时点，序号 h 的点时间戳是窗口结束时刻 (h+1):00，missing 里的小时不返回"""
    midnight = local(day.year, day.month, day.day)
    points = []
    for hour in range(24):
        if hour in missing:
            continue
        points.append((peak if hour == peak_hour else value, midnight + timedelta(hours=hour + 1)))
    return points


def full_days_except(*skip_days, first=date(2026, 10, 26), last=date(2026, 11, 4)):
    """first..last 每天都有完整 24 个点，skip_days 里的日子不返回，用来隔离出被测的那一天"""
    points = []
    day = first
    while day <= last:
        if day not in skip_days:
            points += day_points(day)
        day += timedelta(days=1)
    return points


@pytest.fixture
def no_sleep(check_mod):
    with patch.object(check_mod.time, "sleep"):
        yield


class TestFetchDailyPeaks:
    START = local(2026, 10, 26)
    END = local(2026, 11, 5)

    def test_day_peaks_from_hourly_points(self, check_mod, no_sleep):
        points = day_points(date(2026, 11, 3), peak_hour=14, peak=62.0) + day_points(
            date(2026, 11, 4), peak_hour=23, peak=58.0  # 23 点窗口的点时间戳是次日 00:00，仍归 11-04
        )
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END)
        assert result[(DOMAIN, "127.0.0.1", "/data")] == {date(2026, 11, 3): 62.0, date(2026, 11, 4): 58.0}

    def test_points_after_end_ignored(self, check_mod, no_sleep):
        points = day_points(date(2026, 11, 4), peak_hour=9, peak=60.0) + [(99.0, local(2026, 11, 6, 9))]
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END)
        assert result[(DOMAIN, "127.0.0.1", "/data")] == {date(2026, 11, 4): 60.0}

    def test_invalid_values_are_not_counted(self, check_mod, no_sleep):
        points = full_days_except(date(2026, 11, 4)) + day_points(date(2026, 11, 4), value=50.0, missing=range(6, 24))
        points += [
            (None, local(2026, 11, 4, 8)),
            (float("nan"), local(2026, 11, 4, 9)),
            (float("inf"), local(2026, 11, 4, 10)),
        ]
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END, stats)
        assert date(2026, 11, 4) not in result[(DOMAIN, "127.0.0.1", "/data")]
        assert stats["dropped_days"][(DOMAIN, "127.0.0.1", "/data")] == {date(2026, 11, 4)}
        assert stats["coverage_reasons"]["insufficient_points"] == 1

    def test_duplicate_points_in_one_hour_count_once(self, check_mod, no_sleep):
        # 只有 10 个不同的小时，每个小时重复 3 个点也不能凑够 20
        points = []
        for hour in range(10):
            moment = local(2026, 11, 4, hour + 1)
            points += [(50.0, moment), (51.0, moment), (52.0, moment)]
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END)
        assert result[(DOMAIN, "127.0.0.1", "/data")] == {}

    def test_same_hour_keeps_the_highest_value(self, check_mod, no_sleep):
        points = day_points(date(2026, 11, 4), value=50.0) + [
            (71.0, local(2026, 11, 4, 10)),
            (55.0, local(2026, 11, 4, 10)),
        ]
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END)
        assert result[(DOMAIN, "127.0.0.1", "/data")][date(2026, 11, 4)] == 71.0

    @pytest.mark.parametrize(
        "missing, kept",
        [
            (range(0, 4), False),  # 有效点 20 够了，但连续缺失 4 > 2
            ((3, 4), True),  # 连续缺失 2，有效点 22
            ((3, 4, 5), False),  # 连续缺失 3 > 2
            ((1, 5, 9, 13), True),  # 缺 4 个且不连续，有效点 20，刚好够
            ((1, 5, 9, 13, 17), False),  # 不连续但有效点 19 < 20
        ],
    )
    def test_history_day_coverage(self, check_mod, no_sleep, missing, kept):
        points = day_points(date(2026, 11, 3), missing=missing)
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END)
        assert (date(2026, 11, 3) in result[(DOMAIN, "127.0.0.1", "/data")]) is kept

    def test_dropped_day_is_recorded_with_reason(self, check_mod, no_sleep):
        points = full_days_except(date(2026, 11, 3)) + day_points(date(2026, 11, 3), missing=range(0, 4))
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END, stats)
        assert stats["dropped_days"][(DOMAIN, "127.0.0.1", "/data")] == {date(2026, 11, 3)}
        assert stats["coverage_reasons"]["long_gap"] == 1
        assert "longest_gap=4" in stats["coverage_details"][0] and "valid=20" in stats["coverage_details"][0]

    def test_coverage_details_are_capped(self, check_mod, no_sleep, monkeypatch):
        monkeypatch.setattr(check_mod, "COVERAGE_DETAIL_LIMIT", 2)
        bad = full_days_except(date(2026, 11, 3)) + day_points(date(2026, 11, 3), missing=range(0, 6))
        series = [make_series(ip=f"127.0.0.{index}", points=bad) for index in range(1, 6)]
        stats = {"failed_batches": 0}
        with patch.object(check_mod.BKMonitorV3Api, "unify_query", return_value={"series": series}):
            check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END, stats)
        assert len(stats["coverage_details"]) == 2
        assert stats["coverage_reasons"]["long_gap"] == 5

    def test_afternoon_today_needs_80_percent_of_finished_hours(self, check_mod, no_sleep):
        end = local(2026, 11, 5, 16, 25)  # 已走完 16 个小时窗口，至少需要 13 个
        today = date(2026, 11, 5)
        ok = [p for p in day_points(today, missing=(2, 7, 11)) if p[1] <= end]  # 13 个有效点
        short = [p for p in day_points(today, missing=(2, 7, 11, 12)) if p[1] <= end]  # 12 个
        for points, expected in ((ok, True), (short, False)):
            with patch.object(
                check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
            ):
                result = check_mod.fetch_daily_peaks([DOMAIN], local(2026, 10, 26), end)
            assert (today in result[(DOMAIN, "127.0.0.1", "/data")]) is expected

    def test_afternoon_today_last_finished_hour_must_exist(self, check_mod, no_sleep):
        end = local(2026, 11, 5, 16, 25)
        today = date(2026, 11, 5)
        points = [p for p in day_points(today, missing=(15,)) if p[1] <= end]  # 15:00-16:00 缺失，其余 15 个
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], local(2026, 10, 26), end, stats)
        assert today not in result[(DOMAIN, "127.0.0.1", "/data")]
        assert stats["coverage_reasons"]["last_hour_missing"] == 1

    def test_afternoon_unfinished_hour_can_raise_peak_but_is_not_required(self, check_mod, no_sleep):
        end = local(2026, 11, 5, 16, 25)
        today = date(2026, 11, 5)
        points = [p for p in day_points(today) if p[1] <= end]
        # 16:00-16:25 这个未走完的窗口，时间戳是窗口结束时刻 17:00，晚于终点；若监控返回了 16:25 的点则可以用
        points.append((77.0, local(2026, 11, 5, 16, 25)))
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], local(2026, 10, 26), end)
        assert result[(DOMAIN, "127.0.0.1", "/data")][today] == 77.0

    def test_history_day_with_no_data_at_all_is_recorded(self, check_mod, no_sleep):
        # 11-03 整天没有任何点：不能悄悄略过，要计入覆盖不足，否则严重监控中断时统计是 0
        points = full_days_except(date(2026, 11, 3))
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END, stats)
        key = (DOMAIN, "127.0.0.1", "/data")
        assert date(2026, 11, 3) not in result[key]
        assert stats["dropped_days"][key] == {date(2026, 11, 3)}
        assert stats["coverage_reasons"]["insufficient_points"] == 1
        assert "valid=0 expected=24" in stats["coverage_details"][0]

    def test_today_with_only_invalid_values_is_recorded(self, check_mod, no_sleep):
        end = local(2026, 11, 5, 16, 25)
        today = date(2026, 11, 5)
        points = full_days_except(today, last=date(2026, 11, 4)) + [
            (None, local(2026, 11, 5, 3)),
            (float("nan"), local(2026, 11, 5, 4)),
            (float("inf"), local(2026, 11, 5, 5)),
        ]
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], local(2026, 10, 26), end, stats)
        key = (DOMAIN, "127.0.0.1", "/data")
        assert today not in result[key]
        assert stats["dropped_days"][key] == {today}
        assert stats["coverage_reasons"]["last_hour_missing"] == 1
        assert "valid=0 expected=16" in stats["coverage_details"][0]

    def test_morning_end_day_is_not_checked(self, check_mod, no_sleep):
        # 早间查询终点是今天 00:00，今天一个小时都没走完（expected=0），不能记成缺失
        points = full_days_except()
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [make_series(points=points)]}
        ):
            result = check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END, stats)
        assert "dropped_days" not in stats
        assert date(2026, 11, 5) not in result[(DOMAIN, "127.0.0.1", "/data")]

    def test_series_without_dimensions_skipped(self, check_mod, no_sleep):
        broken = make_series(ip="", points=[(60.0, local(2026, 11, 4, 9))])
        with patch.object(check_mod.BKMonitorV3Api, "unify_query", return_value={"series": [broken]}):
            assert check_mod.fetch_daily_peaks([DOMAIN], self.START, self.END) == {}

    def test_batches_domains_and_anchors_regex(self, check_mod, no_sleep):
        domains = [f"c{index}.test.db" for index in range(120)]
        with patch.object(check_mod.BKMonitorV3Api, "unify_query", return_value={"series": []}) as query:
            check_mod.fetch_daily_peaks(domains, self.START, self.END)
        assert query.call_count == 3
        first_params = query.call_args_list[0][0][0]
        promql = first_params["query_configs"][0]["promql"]
        assert 'cluster_domain=~"^(c0.test.db|c1.test.db' in promql
        assert promql.count("c49.test.db") == 1 and "c50.test.db" not in promql
        assert 'c49.test.db)$"' in promql
        # PromQL 的 =~ 是全匹配：ext 匹配不到 ext4，必须是 ext.? 才能覆盖 ext2/3/4
        assert 'device_type=~"ext.?|xfs"' in promql
        assert all(re.fullmatch("ext.?|xfs", fs) for fs in ("ext", "ext4", "xfs"))
        assert first_params["type"] == "range"
        assert first_params["query_configs"][0]["interval"] == check_mod.STEP_SECONDS
        assert first_params["start_time"] == int(self.START.timestamp())
        assert query.call_args_list[0][1] == {"use_admin": True}

    def test_truncated_batch_is_split_and_requeried(self, check_mod, no_sleep, monkeypatch):
        monkeypatch.setattr(check_mod, "SERIES_LIMIT", 2)
        full = [make_series(ip="127.0.0.1"), make_series(ip="127.0.0.2")]
        responses = [{"series": full}, {"series": [full[0]]}, {"series": [full[1]]}]
        with patch.object(check_mod.BKMonitorV3Api, "unify_query", side_effect=responses) as query:
            check_mod.fetch_daily_peaks(["a.test.db", "b.test.db", "c.test.db", "d.test.db"], self.START, self.END)
        assert query.call_count == 3
        halves = [call[0][0]["query_configs"][0]["promql"] for call in query.call_args_list[1:]]
        assert "a.test.db|b.test.db" in halves[0] and "c.test.db|d.test.db" in halves[1]

    def test_failed_batch_does_not_abort(self, check_mod, no_sleep):
        domains = [f"c{index}.test.db" for index in range(60)]
        ok = make_series(points=day_points(date(2026, 11, 4), value=60.0))
        stats = {"failed_batches": 0}
        with patch.object(
            check_mod.BKMonitorV3Api, "unify_query", side_effect=[RuntimeError("429"), {"series": [ok]}]
        ):
            result = check_mod.fetch_daily_peaks(domains, self.START, self.END, stats)
        assert stats["failed_batches"] == 1
        assert list(result) == [(DOMAIN, "127.0.0.1", "/data")]

    def test_sleeps_between_queries(self, check_mod):
        domains = [f"c{index}.test.db" for index in range(60)]
        with patch.object(check_mod.BKMonitorV3Api, "unify_query", return_value={"series": []}), patch.object(
            check_mod.time, "sleep"
        ) as sleep:
            check_mod.fetch_daily_peaks(domains, self.START, self.END)
        assert sleep.call_count == 2


class TestBatchQueryRetention:
    @staticmethod
    def make_cluster(domain, version="2.4.0"):
        return SimpleNamespace(immute_domain=domain, major_version=version)

    def test_parses_and_groups_by_version(self, check_mod):
        clusters = [
            self.make_cluster("a.test.db"),
            self.make_cluster("b.test.db"),
            self.make_cluster("c.test.db", "3.8.0"),
        ]
        content = {"a.test.db": {"retention_hours": "4"}, "b.test.db": {}, "c.test.db": {"retention_hours": 24}}
        with patch.object(check_mod.DBConfigApi, "batch_get_conf_item", return_value={"content": content}) as api:
            result = check_mod._batch_query_retention(clusters)
        assert result == {"a.test.db": 4, "c.test.db": 24}
        assert api.call_count == 2
        params = api.call_args_list[0][1]["params"]
        assert params["conf_name"] == "retention_hours" and params["conf_file"] == "2.4.0"
        assert params["level_values"] == ["a.test.db", "b.test.db"]

    def test_api_failure_returns_empty(self, check_mod):
        with patch.object(check_mod.DBConfigApi, "batch_get_conf_item", side_effect=RuntimeError("down")):
            assert check_mod._batch_query_retention([self.make_cluster("a.test.db")]) == {}

    def test_non_numeric_value_ignored(self, check_mod):
        content = {"a.test.db": {"retention_hours": "forever"}}
        with patch.object(check_mod.DBConfigApi, "batch_get_conf_item", return_value={"content": content}):
            assert check_mod._batch_query_retention([self.make_cluster("a.test.db")]) == {}


def rising_peaks(day):
    """持续创新高的日峰值序列，最后一天是 day"""
    values = [50, 50, 50, 50, 50, 50, 50, 55, 58, 62]
    return {day - timedelta(days=len(values) - 1 - index): float(value) for index, value in enumerate(values)}


def flat_peaks(day):
    return {day - timedelta(days=offset): 40.0 for offset in range(10)}


class TestCheckKafkaDiskGrowth:
    @pytest.fixture
    def env(self, check_mod):
        cluster = SimpleNamespace(
            id=1, bk_biz_id=3, bk_cloud_id=0, immute_domain=DOMAIN, major_version="2.4.0", phase="online"
        )
        day = date(2026, 11, 4)
        peaks = {
            (DOMAIN, "127.0.0.1", "/data"): rising_peaks(day),
            (DOMAIN, "127.0.0.2", "/data"): flat_peaks(day),
            ("offline.test.db", "127.0.0.3", "/data"): rising_peaks(day),
        }
        with patch.object(check_mod.Cluster, "objects") as clusters, patch.object(
            check_mod, "fetch_daily_peaks", return_value=peaks
        ) as fetch, patch.object(check_mod, "KafkaDiskGrowthReport") as report_cls, patch.object(
            check_mod, "AppCache"
        ) as app_cache, patch.object(
            check_mod, "DBAdministrator"
        ) as dba, patch.object(
            check_mod, "_batch_query_retention", return_value={DOMAIN: 4}
        ), patch.object(
            check_mod, "_previous_failed_days", return_value={(DOMAIN, "127.0.0.1", "/data"): 1}
        ) as previous_days, patch.object(
            check_mod, "_submit_ai_analysis", return_value=1
        ) as submit, patch.object(
            check_mod, "_cleanup"
        ) as cleanup:
            clusters.filter.return_value = [cluster]
            app_cache.objects.filter.return_value.first.return_value = SimpleNamespace(db_app_abbr="test_app")
            dba.return_value.get_biz_db_type_admins.return_value = ["admin"]
            report_cls.objects.update_or_create.side_effect = lambda defaults, **lookup: (
                SimpleNamespace(**lookup, **defaults, ai_status="not_submitted"),
                True,
            )
            yield SimpleNamespace(
                cluster=cluster,
                fetch=fetch,
                report_cls=report_cls,
                submit=submit,
                cleanup=cleanup,
                peaks=peaks,
                previous_days=previous_days,
            )

    def test_only_hits_of_online_clusters_are_reported(self, check_mod, env):
        summary = check_mod.check_kafka_disk_growth("morning", now=local(2026, 11, 5, 9, 25))
        assert env.report_cls.objects.update_or_create.call_count == 1
        call = env.report_cls.objects.update_or_create.call_args[1]
        row = {**call, **call["defaults"]}
        assert (row["domain"], row["ip"], row["mount_point"]) == (DOMAIN, "127.0.0.1", "/data")
        assert row["rule"] == "continuous_new_high"
        assert row["check_day"] == date(2026, 11, 4) and row["run_kind"] == "morning"
        assert row["retention_hours"] == 4 and row["failed_days"] == 2
        assert row["app"] == "test_app" and row["dba"] == ["admin"] and row["state"] == "warning"
        assert summary["hits"] == 1 and summary["ai_submitted"] == 1 and summary["series"] == 3

    def test_queries_only_online_cluster_domains(self, check_mod, env):
        check_mod.check_kafka_disk_growth("morning", now=local(2026, 11, 5, 9, 25))
        assert env.fetch.call_args[0][0] == [DOMAIN]

    def test_submits_reports_for_ai_and_cleans_up(self, check_mod, env):
        check_mod.check_kafka_disk_growth("morning", now=local(2026, 11, 5, 9, 25))
        reports, cluster_by_domain, check_day, run_kind = env.submit.call_args[0]
        assert len(reports) == 1 and reports[0].domain == DOMAIN
        assert cluster_by_domain == {DOMAIN: env.cluster}
        assert check_day == date(2026, 11, 4) and run_kind == "morning"
        env.cleanup.assert_called_once()

    def test_afternoon_judges_today(self, check_mod, env):
        # 午后巡检判定今天：数据里最后一天是 11-04，今天是 11-05，没有当天数据，不判定
        summary = check_mod.check_kafka_disk_growth("afternoon", now=local(2026, 11, 5, 16, 25))
        assert summary["hits"] == 0
        env.report_cls.objects.update_or_create.assert_not_called()
        assert summary["check_day"] == "2026-11-05"

    def test_failed_days_are_looked_up_once_for_all_hits(self, check_mod, env):
        # 命中多个挂载点时只查一次库，避免 N+1
        day = date(2026, 11, 4)
        env.fetch.return_value = {
            (DOMAIN, "127.0.0.1", "/data"): rising_peaks(day),
            (DOMAIN, "127.0.0.1", "/data1"): rising_peaks(day),
            (DOMAIN, "127.0.0.2", "/data"): rising_peaks(day),
        }
        summary = check_mod.check_kafka_disk_growth("morning", now=local(2026, 11, 5, 9, 25))
        assert summary["hits"] == 3
        env.previous_days.assert_called_once_with([DOMAIN], date(2026, 11, 4))
        failed = {
            call[1]["mount_point"]: call[1]["defaults"]["failed_days"]
            for call in env.report_cls.objects.update_or_create.call_args_list
            if call[1]["ip"] == "127.0.0.1"
        }
        assert failed == {"/data": 2, "/data1": 1}  # 只有 /data 前一天命中过

    def test_running_twice_writes_the_same_row_key(self, check_mod, env):
        now = local(2026, 11, 5, 9, 25)
        check_mod.check_kafka_disk_growth("morning", now=now)
        check_mod.check_kafka_disk_growth("morning", now=now)
        lookups = [
            {k: v for k, v in call[1].items() if k != "defaults"}
            for call in env.report_cls.objects.update_or_create.call_args_list
        ]
        assert lookups[0] == lookups[1]
        assert set(lookups[0]) == {"domain", "ip", "mount_point", "check_day", "run_kind"}

    def test_mount_with_dropped_recent_day_is_not_judged(self, check_mod, env):
        # 此前 7 天里有一天因覆盖不足被丢弃：即使日期看起来齐全也不判定
        bad_day = date(2026, 11, 2)
        peaks = {(DOMAIN, "127.0.0.1", "/data"): rising_peaks(date(2026, 11, 4))}
        env.fetch.return_value = peaks

        def fake_fetch(domains, start, end, stats):
            stats["dropped_days"] = {(DOMAIN, "127.0.0.1", "/data"): {bad_day}}
            stats["coverage_reasons"] = {"long_gap": 1}
            return peaks

        env.fetch.side_effect = fake_fetch
        summary = check_mod.check_kafka_disk_growth("morning", now=local(2026, 11, 5, 9, 25))
        assert summary["hits"] == 0 and summary["coverage_skipped"] == 1
        assert summary["coverage_dropped_days"] == 1 and summary["coverage_reasons"] == {"long_gap": 1}

    def test_dropped_older_day_does_not_block_judgement(self, check_mod, env):
        # 判定窗口之外更早的缺失日期不影响：这里 10-27 早于判定日 11-04 往前 7 天
        peaks = {(DOMAIN, "127.0.0.1", "/data"): rising_peaks(date(2026, 11, 4))}

        def fake_fetch(domains, start, end, stats):
            stats["dropped_days"] = {(DOMAIN, "127.0.0.1", "/data"): {date(2026, 10, 27)}}
            return peaks

        env.fetch.side_effect = fake_fetch
        summary = check_mod.check_kafka_disk_growth("morning", now=local(2026, 11, 5, 9, 25))
        assert summary["hits"] == 1 and summary["coverage_skipped"] == 0


class TestSubmitAiAnalysis:
    @staticmethod
    def report(report_id, domain, peak, ai_status="not_submitted"):
        return SimpleNamespace(
            id=report_id,
            domain=domain,
            peak=peak,
            ip="127.0.0.1",
            mount_point="/data",
            rule="continuous_new_high",
            excess=4.0,
            daily_growth=4.0,
            peaks=[{"day": "2026-11-04", "peak": peak}],
            retention_hours=4,
            ai_status=ai_status,
        )

    @staticmethod
    def clusters(*domains):
        return {
            domain: SimpleNamespace(id=index, immute_domain=domain, bk_biz_id=3)
            for index, domain in enumerate(domains)
        }

    @pytest.fixture
    def task(self, check_mod):
        task = MagicMock()
        task.task_key = "kafka.disk_growth_analysis"
        task.config = SimpleNamespace(enabled=True, max_submit_per_run=50)
        task.submit.side_effect = lambda items: [
            SimpleNamespace(outcome=check_mod.DispatchOutcomeType.ENQUEUED) for _ in items
        ]
        with patch.object(check_mod, "KafkaDiskGrowthAnalysisTask", return_value=task), patch.object(
            check_mod, "KafkaDiskGrowthReport"
        ) as report_cls:
            task.report_cls = report_cls
            yield task

    def test_disabled_does_not_submit(self, check_mod, task):
        task.config.enabled = False
        reports = [self.report(1, "a.test.db", 70)]
        assert check_mod._submit_ai_analysis(reports, self.clusters("a.test.db"), date(2026, 11, 4), "morning") == 0
        task.submit.assert_not_called()
        task.report_cls.objects.filter.assert_not_called()

    def test_no_reports(self, check_mod, task):
        assert check_mod._submit_ai_analysis([], {}, date(2026, 11, 4), "morning") == 0
        task.submit.assert_not_called()

    def test_groups_rows_by_cluster_and_marks_pending(self, check_mod, task):
        reports = [self.report(1, "a.test.db", 70), self.report(2, "a.test.db", 65), self.report(3, "b.test.db", 80)]
        submitted = check_mod._submit_ai_analysis(
            reports, self.clusters("a.test.db", "b.test.db"), date(2026, 11, 4), "morning"
        )
        assert submitted == 2
        items = task.submit.call_args[0][0]
        # 峰值高的集群排前面
        assert [item["domain"] for item in items] == ["b.test.db", "a.test.db"]
        assert items[1]["report_ids"] == [1, 2] and len(items[1]["hits"]) == 2
        assert items[0]["check_day"] == "2026-11-04" and items[0]["run_kind"] == "morning"
        pending_calls = [call[1] for call in task.report_cls.objects.filter.call_args_list]
        assert {tuple(call["id__in"]) for call in pending_calls} == {(3,), (1, 2)}
        task.report_cls.objects.filter.return_value.update.assert_called_with(ai_status="pending")
        # 只改还没被 worker 推进过的行，避免覆盖已写入的 success / skipped
        assert all(call["ai_status"] == "not_submitted" for call in pending_calls)

    def test_rerun_does_not_resubmit_rows_already_analysed(self, check_mod, task):
        reports = [
            self.report(1, "a.test.db", 70, ai_status="pending"),
            self.report(2, "b.test.db", 80, ai_status="success"),
            self.report(3, "c.test.db", 65),
        ]
        submitted = check_mod._submit_ai_analysis(
            reports, self.clusters("a.test.db", "b.test.db", "c.test.db"), date(2026, 11, 4), "morning"
        )
        assert submitted == 1
        assert [item["domain"] for item in task.submit.call_args[0][0]] == ["c.test.db"]

    def test_nothing_to_submit_when_all_rows_already_handled(self, check_mod, task):
        reports = [self.report(1, "a.test.db", 70, ai_status="success")]
        assert check_mod._submit_ai_analysis(reports, self.clusters("a.test.db"), date(2026, 11, 4), "morning") == 0
        task.submit.assert_not_called()

    def test_submit_limit_keeps_highest_peaks(self, check_mod, task):
        task.config.max_submit_per_run = 2
        reports = [self.report(1, "a.test.db", 61), self.report(2, "b.test.db", 90), self.report(3, "c.test.db", 75)]
        submitted = check_mod._submit_ai_analysis(
            reports, self.clusters("a.test.db", "b.test.db", "c.test.db"), date(2026, 11, 4), "morning"
        )
        assert submitted == 2
        assert [item["domain"] for item in task.submit.call_args[0][0]] == ["b.test.db", "c.test.db"]

    def test_not_enqueued_stays_not_submitted(self, check_mod, task):
        task.submit.side_effect = lambda items: [
            SimpleNamespace(outcome=check_mod.DispatchOutcomeType.ENQUEUE_DUPLICATE) for _ in items
        ]
        reports = [self.report(1, "a.test.db", 70)]
        assert check_mod._submit_ai_analysis(reports, self.clusters("a.test.db"), date(2026, 11, 4), "morning") == 0
        task.report_cls.objects.filter.assert_not_called()

    def test_submit_error_is_swallowed(self, check_mod, task):
        task.submit.side_effect = RuntimeError("redis down")
        reports = [self.report(1, "a.test.db", 70)]
        assert check_mod._submit_ai_analysis(reports, self.clusters("a.test.db"), date(2026, 11, 4), "morning") == 0


class TestCleanup:
    def test_deletes_old_rows_and_expires_stale_pending(self, check_mod):
        now = local(2026, 11, 5, 9, 25)
        with patch.object(check_mod, "KafkaDiskGrowthReport") as report_cls:
            check_mod._cleanup(now)
        calls = report_cls.objects.filter.call_args_list
        assert calls[0][1] == {"create_at__lt": now - timedelta(days=60)}
        report_cls.objects.filter.return_value.delete.assert_called_once()
        assert calls[1][1] == {"ai_status": "pending", "create_at__lt": now - timedelta(hours=36)}
        update_kwargs = report_cls.objects.filter.return_value.update.call_args[1]
        assert update_kwargs["ai_status"] == "failed" and update_kwargs["update_at"] == now
