# -*- coding: utf-8 -*-
"""Unit tests for redis-capacity MCP helpers."""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from backend.db_services.redis.capacity_evaluate_service.services.evaluate_service import EVAL_QPS_MODEL
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpClusterNotFoundException
from backend.dbm_aiagent.mcp_tools.redis.impl.mip_action import (
    ActWindow,
    analyze_mip_capacity,
    build_expand_suggest,
    calc_supported_qps_from_topo,
    evaluate_mip_action,
    get_cluster_spec,
    list_active_mip_actions,
    list_last_failed_clusters,
    list_mip_actions,
    max_sum_qps_with_window,
    parse_key_pattern,
    rebuild_action_info,
    rebuild_req,
)


class FakeQS(list):
    """Minimal QuerySet stand-in supporting filter/order_by/slice."""

    def filter(self, **kwargs):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self[0] if self else None


def _aware(year, month, day, hour=0, minute=0, second=0):
    return timezone.make_aware(datetime.datetime(year, month, day, hour, minute, second))


def _fake_record(**overrides):
    now = timezone.now()
    data = {
        "action_id": "act-1",
        "action_name": "demo",
        "action_type": "incr",
        "action_user": "alice",
        "bk_biz_id": 100,
        "bk_biz_name": "biz",
        "cluster_id": 1,
        "cluster_domain": "cache.test.db",
        "cluster_type": "TwemproxyRedisInstance",
        "evaluate_method": "",
        "evaluate_time": now,
        "start_time": now,
        "end_time": now,
        "req_qps_k": 10,
        "req_capacity_m": 1024,
        "key_pattern": '["user:*"]',
        "req_flag_no_big_key_with_a_lot_of_member": True,
        "req_flag_no_big_result": False,
        "req_flag_no_big_value": False,
        "req_flag_no_hot_key": True,
        "req_flag_no_use_dns": 0,
        "is_force": 0,
        "last_approved_user": "system",
        "last_approved_status": 1,
        "last_approved_time": now,
    }
    data.update(overrides)
    record = SimpleNamespace(**data)
    record.__data__ = lambda: {
        "action_id": record.action_id,
        "action_name": record.action_name,
        "action_type": record.action_type,
        "bk_biz_id": record.bk_biz_id,
        "bk_biz_name": record.bk_biz_name,
        "cluster_id": record.cluster_id,
        "cluster_domain": record.cluster_domain,
        "cluster_type": record.cluster_type,
        "evaluate_time": record.evaluate_time,
        "start_time": record.start_time,
        "end_time": record.end_time,
        "req_qps_k": record.req_qps_k,
        "req_capacity_m": record.req_capacity_m,
        "key_pattern": record.key_pattern,
        "req_flag_no_big_key_with_a_lot_of_member": record.req_flag_no_big_key_with_a_lot_of_member,
        "req_flag_no_big_result": record.req_flag_no_big_result,
        "req_flag_no_big_value": record.req_flag_no_big_value,
        "req_flag_no_hot_key": record.req_flag_no_hot_key,
        "req_flag_no_use_dns": record.req_flag_no_use_dns,
        "is_force": record.is_force,
        "action_user": record.action_user,
        "last_approved_user": record.last_approved_user,
        "last_approved_status": record.last_approved_status,
        "last_approved_time": record.last_approved_time,
    }
    return record


class TestParseKeyPattern:
    def test_json_list(self):
        assert parse_key_pattern('["a","b"]') == ["a", "b"]

    def test_empty(self):
        assert parse_key_pattern("") == []
        assert parse_key_pattern(None) == []

    def test_plain_string(self):
        assert parse_key_pattern("user:*") == ["user:*"]


class TestRebuild:
    def test_rebuild_action_info_force_override(self):
        record = _fake_record(is_force=0)
        info = rebuild_action_info(record, is_force=1)
        assert info["is_force"] == 1
        assert info["user"] == "alice"
        assert info["action_id"] == "act-1"

    def test_rebuild_req(self):
        record = _fake_record()
        req = rebuild_req(record, is_force=1)
        assert req["cluster_domain"] == "cache.test.db"
        assert req["key_pattern"] == ["user:*"]
        assert req["req_flag_no_big_key_with_a_lot_of_member"] == 1
        assert req["is_force"] == 1


class TestListMipActions:
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    def test_list_filters_and_limit(self, mock_filter):
        record = _fake_record()
        qs = FakeQS([record])
        mock_filter.return_value = qs

        out = list_mip_actions(bk_biz_id=100, action_id="act-1", cluster_domain="cache.test.db", limit=10)
        mock_filter.assert_called_once_with(bk_biz_id=100)
        assert out["count"] == 1
        assert out["records"][0]["action_id"] == "act-1"


class TestEvaluateMipAction:
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    def test_missing_record_raises(self, mock_filter):
        mock_filter.return_value = FakeQS()
        with pytest.raises(DBMMcpBaseException):
            evaluate_mip_action(bk_biz_id=100, action_id="missing")

    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateService.evaluate_one")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.DbmClusterRepository.get_cluster_by_domain")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    def test_evaluate_existing_calls_service_with_record_cluster_id(
        self, mock_filter, mock_get_cluster, mock_evaluate_one
    ):
        record = _fake_record()
        mock_filter.return_value = FakeQS([record])
        mock_get_cluster.return_value = SimpleNamespace(id=1, bk_biz_id=100)
        mock_resp = MagicMock()
        mock_resp.to_dict.return_value = {"cluster_domain": "cache.test.db", "status": "success", "message": "ok"}
        mock_evaluate_one.return_value = mock_resp

        out = evaluate_mip_action(bk_biz_id=100, action_id="act-1", is_force=1)
        assert out["action_id"] == "act-1"
        assert len(out["results"]) == 1
        mock_evaluate_one.assert_called_once()
        action_info, one_req, bk_biz_id, cluster_id = mock_evaluate_one.call_args[0]
        assert action_info["action_id"] == "act-1"
        assert action_info["is_force"] == 1
        assert one_req["req_qps_k"] == 10
        assert one_req["is_force"] == 1
        assert bk_biz_id == 100
        assert cluster_id == record.cluster_id

    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateService.evaluate_one")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.DbmClusterRepository.get_cluster_by_domain")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    def test_cluster_id_mismatch_rejects_to_avoid_new_action(self, mock_filter, mock_get_cluster, mock_evaluate_one):
        record = _fake_record(cluster_id=1)
        mock_filter.return_value = FakeQS([record])
        mock_get_cluster.return_value = SimpleNamespace(id=999, bk_biz_id=100)

        with pytest.raises(DBMMcpBaseException) as exc_info:
            evaluate_mip_action(bk_biz_id=100, action_id="act-1")
        assert "集群 ID" in str(exc_info.value)
        mock_evaluate_one.assert_not_called()

    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateService.evaluate_one")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.DbmClusterRepository.get_cluster_by_domain")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    def test_biz_mismatch_rejects(self, mock_filter, mock_get_cluster, mock_evaluate_one):
        record = _fake_record(cluster_id=1)
        mock_filter.return_value = FakeQS([record])
        mock_get_cluster.return_value = SimpleNamespace(id=1, bk_biz_id=200)

        with pytest.raises(DBMMcpBaseException) as exc_info:
            evaluate_mip_action(bk_biz_id=100, action_id="act-1")
        assert "业务" in str(exc_info.value)
        mock_evaluate_one.assert_not_called()


class TestSupportedQps:
    def _topo(self, proxy_num, shard_num, shard_cpu_core_m, ssd=False):
        topo = MagicMock()
        topo.cluster_domain = "cache.test.db"
        topo.proxy_num = proxy_num
        topo.shard_num = shard_num
        topo.shard_cpu_core_m = shard_cpu_core_m
        topo.shard_spec = "2c4g"
        topo.get_shard_cpu_core_limit.return_value = 1000
        topo.is_tendis_ssd.return_value = ssd
        topo.is_tendisplus.return_value = False
        return topo

    def test_supported_is_min_of_proxy_and_backend(self):
        topo = self._topo(proxy_num=2, shard_num=2, shard_cpu_core_m=1000, ssd=False)
        out = calc_supported_qps_from_topo(topo, EVAL_QPS_MODEL)
        assert out["proxy_qps_k_total"] == 40
        assert out["backend_qps_k_total"] == 120
        assert out["supported_qps_k"] == 40
        assert out["model"] == EVAL_QPS_MODEL

    def test_ssd_uses_ssd_model(self):
        topo = self._topo(proxy_num=1, shard_num=10, shard_cpu_core_m=1000, ssd=True)
        out = calc_supported_qps_from_topo(topo, EVAL_QPS_MODEL)
        assert out["proxy_qps_k_total"] == 20
        assert out["backend_qps_k_total"] == 60
        assert out["supported_qps_k"] == 20
        assert out["model"]["ssd_shard_qps_per_core"] == 6000

    def test_default_model_matches_evaluate_service_constant(self):
        topo = self._topo(proxy_num=1, shard_num=1, shard_cpu_core_m=1000, ssd=False)
        out = calc_supported_qps_from_topo(topo)
        assert out["model"] == EVAL_QPS_MODEL
        assert EVAL_QPS_MODEL["proxy_qps"] == 20000
        assert EVAL_QPS_MODEL["shard_qps_per_core"] == 60000
        assert EVAL_QPS_MODEL["ssd_shard_qps_per_core"] == 6000


class TestMaxSumQpsWithWindow:
    def test_disjoint_windows_peak_is_max_single(self):
        acts = [
            ActWindow(_aware(2026, 1, 1), _aware(2026, 1, 2), 10, 1),
            ActWindow(_aware(2026, 1, 3), _aware(2026, 1, 4), 20, 2),
        ]
        peak, start, end = max_sum_qps_with_window(acts)
        assert peak == 20
        assert start is not None and end is not None

    def test_full_overlap_sums(self):
        acts = [
            ActWindow(_aware(2026, 1, 1), _aware(2026, 1, 10), 10, 1),
            ActWindow(_aware(2026, 1, 1), _aware(2026, 1, 10), 15, 2),
        ]
        peak, _, _ = max_sum_qps_with_window(acts)
        assert peak == 25

    def test_staggered_overlap(self):
        acts = [
            ActWindow(_aware(2026, 1, 1), _aware(2026, 1, 5, 23, 59, 59), 10, 1),
            ActWindow(_aware(2026, 1, 3), _aware(2026, 1, 7, 23, 59, 59), 20, 2),
        ]
        peak, start, end = max_sum_qps_with_window(acts)
        assert peak == 30
        assert start.day == 3
        assert end.day == 5

    def test_empty(self):
        peak, start, end = max_sum_qps_with_window([])
        assert peak == 0
        assert start is None and end is None


class TestBuildExpandSuggest:
    def test_failed_suggests_diff(self):
        last = {
            "cluster_domain": "cache.test.db",
            "approved_status": "failed",
            "proxy_count": 2,
            "req_qps_k_total": 100,
            "free_g": 10,
            "req_g": 30,
            "total_g": 40,
        }
        suggest = build_expand_suggest(last)
        assert suggest["req_proxy_count"] == 5.0
        assert suggest["proxy_count_diff"] == 3
        assert suggest["need_capacity_g"] == 20
        assert suggest["need_proxy_count"] == 3

    def test_success_zero_need(self):
        last = {
            "cluster_domain": "cache.test.db",
            "approved_status": "success",
            "proxy_count": 2,
            "req_qps_k_total": 100,
            "free_g": 10,
            "req_g": 30,
            "total_g": 40,
        }
        suggest = build_expand_suggest(last)
        assert suggest["need_capacity_g"] == 0
        assert suggest["need_proxy_count"] == 0
        assert suggest["proxy_count_diff"] == 0


class TestListActiveMipActions:
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    def test_filters_end_time_gt_current(self, mock_filter):
        qs = FakeQS([_fake_record()])
        mock_filter.return_value = qs
        current = _aware(2026, 3, 1)
        out = list_active_mip_actions("cache.test.db", current_time=current)
        mock_filter.assert_called_once()
        kwargs = mock_filter.call_args.kwargs
        assert kwargs["cluster_domain"] == "cache.test.db"
        assert kwargs["end_time__gt"] == current
        assert len(out) == 1


class TestAnalyzeMipCapacity:
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateRecord.objects.filter")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.get_last_evaluate")
    def test_illegal_history_json_degrades(self, mock_last, mock_filter):
        record = _fake_record(
            start_time=_aware(2026, 1, 1),
            end_time=_aware(2026, 12, 31),
            req_qps_k=10,
            req_capacity_m=2048,
        )
        mock_filter.return_value = FakeQS([record])
        history = SimpleNamespace(
            action_id="act-1",
            action_name="demo",
            action_user="alice",
            approved_status="failed",
            approved_comment="no",
            approved_user="system",
            evaluate_time=_aware(2026, 2, 1),
            cluster_domain="cache.test.db",
            proxy_count=2,
            req_qps_k=10,
            req_capacity_m=2048,
            req_qps_k_total=50,
            req_capacity_m_total=4096,
            total_size_mb=10240,
            free_size_mb=1024,
            not_finished_records_json="{not-json",
        )
        mock_last.return_value = history

        out = analyze_mip_capacity("cache.test.db", current_time=_aware(2026, 3, 1))
        assert out["cluster_domain"] == "cache.test.db"
        assert out["active_summary"]["count"] == 1
        assert out["last_evaluate"]["approved_status"] == "failed"
        assert out["suggest"]["need_capacity_g"] >= 0
        assert "note" in out["related_summary"]


class TestGetClusterSpec:
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.DbmClusterRepository.get_cluster_by_domain")
    def test_domain_not_found(self, mock_get):
        mock_get.return_value = None
        with pytest.raises(DBMMcpClusterNotFoundException):
            get_cluster_spec("missing.db")

    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityCalculateService.get_cluster_info")
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.DbmClusterRepository.get_cluster_by_domain")
    def test_projects_compact_fields(self, mock_get, mock_info):
        mock_get.return_value = SimpleNamespace(
            id=7, bk_biz_id=100, cluster_type="TwemproxyRedisInstance", immute_domain="cache.test.db"
        )
        mock_info.return_value = {
            "cluster_info": {
                "cluster_id": 7,
                "cluster_domain": "cache.test.db",
                "bk_biz_id": 100,
                "cluster_type": "TwemproxyRedisInstance",
                "proxy_num": 3,
                "shard_num": 12,
                "proxy_spec": "(2c4g)x3",
                "shard_spec": "(2c8g)x12",
                "proxy_cpu_total": 6000,
                "proxy_mem_total": 12288,
                "storage_cpu_total": 24000,
                "storage_mem_total_m": 98304,
                "storage_disk_total": 0,
                "shard_cpu_core_m": 2000,
            },
            "proxy_list": [{"ip": "127.0.0.1"}],
            "shard_list": [],
            "host_infos": [],
        }
        out = get_cluster_spec("cache.test.db")
        assert out["cluster_id"] == 7
        assert out["proxy_num"] == 3
        assert out["shard_num"] == 12
        assert out["proxy_spec"] == "(2c4g)x3"
        assert out["storage_type"] == "memory"
        assert "proxy_list" not in out
        assert "host_infos" not in out


class TestListLastFailedClusters:
    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateHistory.objects.filter")
    def test_empty_all_biz(self, mock_filter):
        empty = MagicMock()
        empty.values.return_value.annotate.return_value.values_list.return_value = []
        mock_filter.return_value = empty
        out = list_last_failed_clusters(bk_biz_id=None)
        assert out["count"] == 0
        assert out["bk_biz_id"] is None
        assert out["cluster_domains"] == []
        mock_filter.assert_called_once_with()

    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateHistory.objects.filter")
    def test_empty(self, mock_filter):
        # values().annotate().values_list chain
        empty = MagicMock()
        empty.values.return_value.annotate.return_value.values_list.return_value = []
        mock_filter.return_value = empty
        out = list_last_failed_clusters(bk_biz_id=100)
        assert out["count"] == 0
        assert out["cluster_domains"] == []

    @patch("backend.dbm_aiagent.mcp_tools.redis.impl.mip_action.CapacityEvaluateHistory.objects.filter")
    def test_returns_failed_latest_only(self, mock_filter):
        # First filter(bk_biz_id) -> annotate max ids
        annotate_qs = MagicMock()
        annotate_qs.values.return_value.annotate.return_value.values_list.return_value = [11, 22]

        failed_h = SimpleNamespace(
            cluster_domain="fail.cache.db",
            cluster_id=1,
            bk_biz_id=100,
            approved_status="failed",
            approved_comment="not enough",
            action_id="a1",
            action_name="n1",
            evaluate_time=_aware(2026, 3, 1),
            req_qps_k_total=50,
            req_capacity_m_total=1024,
        )

        class _OrderSlice:
            def order_by(self, *args):
                return self

            def __getitem__(self, item):
                return [failed_h]

        failed_qs = _OrderSlice()

        def _filter_side_effect(*args, **kwargs):
            if "id__in" in kwargs:
                return failed_qs
            return annotate_qs

        mock_filter.side_effect = _filter_side_effect
        out = list_last_failed_clusters(bk_biz_id=100, limit=10)
        assert out["count"] == 1
        assert out["cluster_domains"] == ["fail.cache.db"]
        assert out["records"][0]["approved_status"] == "failed"
        assert out["records"][0]["action_id"] == "a1"
