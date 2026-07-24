import json
import time
from unittest.mock import MagicMock, patch

from bk_monitor_report import MonitorReporter
from prometheus_client import CollectorRegistry

from backend.bk_dataview.prometheus.dispatch_metrics import KEY_HEARTBEAT, KEY_LATEST, DispatchMetricsCollector


class InMemoryRedis:
    def __init__(self, initial=None, *, raises=False):
        self.data = dict(initial or {})
        self.raises = raises

    def _check(self):
        if self.raises:
            raise RuntimeError("redis down")

    def set(self, key, value, ex=None, nx=False):
        self._check()
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def get(self, key):
        self._check()
        return self.data.get(key)


def _payload(generated_at=None, *, started_at=1000.0, published=100):
    return {
        "schema_version": 2,
        "generated_at": generated_at or time.time(),
        "queues": [
            {
                "namespace": "ai",
                "pending": 10,
                "pending_ready": 5,
                "pending_delayed": 3,
                "reserved": 2,
                "max_admitted_jobs": 100,
                "max_reserved": 20,
                "budget": 15,
                "congestion_window": 8,
                "pump_paused": 1,
                "producer_paused": 0,
                "reserved_saturated": 1,
                "events": {"published": published, "bogus_event": 7},
                "histograms": {
                    "execution_seconds": {
                        "buckets": [["0.1", 2], ["1", 8], ["+Inf", 10]],
                        "count": 10,
                        "sum": 4.2,
                    }
                },
                "metrics_started_at": started_at,
                "partial": 0,
            }
        ],
        "tasks": [
            {
                "task_key": "ai.task",
                "namespace": "ai",
                "pending": 2,
                "reserved": 1,
                "outcomes": {"success": 30, "bogus_outcome": 1},
                "partial": 0,
            }
        ],
    }


def _collect(collector):
    registry = CollectorRegistry()
    registry.register(collector)
    return list(registry.collect())


def _by_name(families):
    return {family.name: family for family in families}


def _health_status(families):
    health = _by_name(families).get("dbm_dispatch_collector_health")
    if health is None:
        return None
    for sample in health.samples:
        if sample.value == 1.0:
            return sample.labels["status"]
    return None


class TestDispatchMetricsCollector:
    def test_describe_lists_metric_names_without_redis(self):
        collector = DispatchMetricsCollector(client=InMemoryRedis(raises=True))
        names = {family.name for family in collector.describe()}
        assert "dbm_dispatch_collector_health" in names
        assert "dbm_dispatch_pending" in names
        assert "dbm_dispatch_events" in names
        assert "dbm_dispatch_latency_seconds" in names
        assert "dbm_dispatch_task_outcome" in names
        assert "dbm_dispatch_metrics_started_at_timestamp_seconds" in names
        assert all(not family.samples for family in collector.describe())

    def test_generates_counters_histogram_and_live_samples(self):
        collector = DispatchMetricsCollector(client=InMemoryRedis({KEY_LATEST: json.dumps(_payload())}))
        families = _collect(collector)

        assert _health_status(families) == "ok"
        by_name = _by_name(families)
        pending = list(by_name["dbm_dispatch_pending"].samples)
        assert pending[0].labels == {"namespace": "ai"}
        assert pending[0].value == 10.0

        event_samples = list(by_name["dbm_dispatch_events"].samples)
        assert any(
            sample.name == "dbm_dispatch_events_total"
            and sample.labels == {"namespace": "ai", "event": "published"}
            and sample.value == 100.0
            for sample in event_samples
        )
        assert all(sample.labels["event"] != "bogus_event" for sample in event_samples)

        histogram_samples = list(by_name["dbm_dispatch_latency_seconds"].samples)
        buckets = [sample for sample in histogram_samples if sample.name.endswith("_bucket")]
        assert [(sample.labels["le"], sample.value) for sample in buckets] == [
            ("0.1", 2.0),
            ("1", 8.0),
            ("+Inf", 10.0),
        ]
        assert any(sample.name.endswith("_count") and sample.value == 10.0 for sample in histogram_samples)
        assert any(sample.name.endswith("_sum") and sample.value == 4.2 for sample in histogram_samples)

        outcomes = list(by_name["dbm_dispatch_task_outcome"].samples)
        assert any(sample.name == "dbm_dispatch_task_outcome_total" and sample.value == 30 for sample in outcomes)
        assert all(sample.labels["outcome"] != "bogus_outcome" for sample in outcomes)

        started = list(by_name["dbm_dispatch_metrics_started_at_timestamp_seconds"].samples)
        assert started[0].value == 1000.0
        partial = list(by_name["dbm_dispatch_report_partial"].samples)
        assert partial[0].labels == {"namespace": "ai"}
        assert partial[0].value == 0

    def test_monitor_reporter_preserves_total_bucket_count_sum_and_le(self):
        registry = CollectorRegistry()
        registry.register(DispatchMetricsCollector(client=InMemoryRedis({KEY_LATEST: json.dumps(_payload())})))
        reporter = MonitorReporter(
            data_id=1,
            access_token="test",
            target="dispatch-poc",
            url="http://127.0.0.1",
            registry=registry,
        )
        records = reporter.generate_report_data()["data"]
        names = {next(iter(record["metrics"])) for record in records}
        assert "dbm_dispatch_events_total" in names
        assert "dbm_dispatch_task_outcome_total" in names
        assert "dbm_dispatch_latency_seconds_bucket" in names
        assert "dbm_dispatch_latency_seconds_count" in names
        assert "dbm_dispatch_latency_seconds_sum" in names
        bucket = next(
            record
            for record in records
            if "dbm_dispatch_latency_seconds_bucket" in record["metrics"] and record["dimension"].get("le") == "+Inf"
        )
        assert bucket["dimension"] == {"le": "+Inf", "namespace": "ai", "stage": "execution"}

    def test_reset_is_exposed_as_lower_counter_and_new_generation(self):
        first = DispatchMetricsCollector(client=InMemoryRedis({KEY_LATEST: json.dumps(_payload(published=100))}))
        reset = DispatchMetricsCollector(
            client=InMemoryRedis({KEY_LATEST: json.dumps(_payload(started_at=2000.0, published=3))})
        )
        first_events = _by_name(first._build_families(_payload(published=100)))["dbm_dispatch_events"].samples
        reset_families = _by_name(reset._build_families(_payload(started_at=2000.0, published=3)))
        reset_events = reset_families["dbm_dispatch_events"].samples
        assert first_events[0].value == 100
        assert reset_events[0].value == 3
        assert reset_families["dbm_dispatch_metrics_started_at_timestamp_seconds"].samples[0].value == 2000

    def test_heartbeat_emits_stored_epoch(self):
        now = time.time()
        client = InMemoryRedis({KEY_LATEST: json.dumps(_payload()), KEY_HEARTBEAT: str(now)})
        families = _collect(DispatchMetricsCollector(client=client))
        heartbeat = _by_name(families)["dbm_dispatch_publisher_heartbeat_timestamp_seconds"].samples
        assert heartbeat[0].value == now

    def test_lease_holder_only_emits_data(self):
        client = InMemoryRedis({KEY_LATEST: json.dumps(_payload())})
        assert _collect(DispatchMetricsCollector(client=client))
        assert _collect(DispatchMetricsCollector(client=client)) == []

    def test_cache_miss_health(self):
        assert _health_status(_collect(DispatchMetricsCollector(client=InMemoryRedis()))) == "cache_miss"

    def test_parse_error_and_wrong_schema_health(self):
        corrupt = InMemoryRedis({KEY_LATEST: "not json"})
        assert _health_status(_collect(DispatchMetricsCollector(client=corrupt))) == "parse_error"
        old = InMemoryRedis({KEY_LATEST: json.dumps({"schema_version": 1})})
        assert _health_status(_collect(DispatchMetricsCollector(client=old))) == "parse_error"

    def test_malformed_schema_v2_never_raises(self):
        malformed = _payload()
        malformed["queues"][0]["histograms"]["execution_seconds"]["buckets"] = [["1", "not-a-number"]]
        client = InMemoryRedis({KEY_LATEST: json.dumps(malformed)})
        assert _health_status(_collect(DispatchMetricsCollector(client=client))) == "parse_error"

    def test_stale_health(self):
        stale = InMemoryRedis({KEY_LATEST: json.dumps(_payload(generated_at=time.time() - 120))})
        assert _health_status(_collect(DispatchMetricsCollector(client=stale))) == "cache_stale"

    def test_redis_error_health_and_never_raises(self):
        collector = DispatchMetricsCollector(client=InMemoryRedis(raises=True))
        assert _health_status(_collect(collector)) == "redis_error"


class TestRegisterDispatchCollector:
    def test_register_is_idempotent(self):
        import backend.bk_dataview.prometheus.config as cfg

        fake_registry = MagicMock()
        with (
            patch.object(cfg, "_dispatch_collector_registered", False),
            patch.object(cfg, "_dispatch_collector", None),
            patch("prometheus_client.REGISTRY", fake_registry),
        ):
            cfg.register_dispatch_collector()
            cfg.register_dispatch_collector()
        assert fake_registry.register.call_count == 1
