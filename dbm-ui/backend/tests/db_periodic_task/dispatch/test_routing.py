from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.routing import DispatchRoutingError
from backend.db_periodic_task.models import DispatchQueueRoute

TWO_ALIASES = ["dispatch_0", "dispatch_1"]
THREE_ALIASES = ["dispatch_0", "dispatch_1", "dispatch_2"]


@pytest.fixture(autouse=True)
@pytest.mark.django_db
def clean_route_table():
    """Routing tests assume an empty, deterministic route map."""
    DispatchQueueRoute.objects.all().delete()
    yield
    DispatchQueueRoute.objects.all().delete()


@pytest.mark.django_db
class TestAssignRoute:
    def test_assigns_least_loaded_with_pool_order_tie_break(self):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            DispatchQueueRoute.objects.create(
                namespace="ns-a",
                redis_alias="dispatch_0",
                creator="tester",
                updater="tester",
            )
            assert routing.assign_route("ns-b") == "dispatch_1"
            assert routing.assign_route("ns-c") == "dispatch_0"
            assert routing.assign_route("ns-d") == "dispatch_1"

        counts = {
            "dispatch_0": DispatchQueueRoute.objects.filter(redis_alias="dispatch_0").count(),
            "dispatch_1": DispatchQueueRoute.objects.filter(redis_alias="dispatch_1").count(),
        }
        assert counts == {"dispatch_0": 2, "dispatch_1": 2}

    def test_assign_is_idempotent_and_never_rewrites_existing_row(self):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            DispatchQueueRoute.objects.create(
                namespace="ns-a",
                redis_alias="dispatch_1",
                creator="tester",
                updater="tester",
            )
            assert routing.assign_route("ns-a") == "dispatch_1"
            assert DispatchQueueRoute.objects.filter(namespace="ns-a").count() == 1
            assert DispatchQueueRoute.objects.get(namespace="ns-a").redis_alias == "dispatch_1"

    def test_incremental_assignment_keeps_balance(self):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            DispatchQueueRoute.objects.create(
                namespace="ns-a",
                redis_alias="dispatch_0",
                creator="tester",
                updater="tester",
            )
            assert routing.assign_route("ns-b") == "dispatch_1"
            assert routing.assign_route("ns-c") == "dispatch_0"

    def test_growing_pool_never_reshuffles_existing_namespaces(self):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            assert routing.assign_route("ns-a") == "dispatch_0"
            assert routing.assign_route("ns-b") == "dispatch_1"

        with override_settings(DISPATCH_REDIS_ALIASES=THREE_ALIASES):
            assert routing.assign_route("ns-a") == "dispatch_0"
            assert routing.assign_route("ns-b") == "dispatch_1"
            # New namespaces land on the least-loaded (new) alias.
            assert routing.assign_route("ns-c") == "dispatch_2"

        rows = {row.namespace: row.redis_alias for row in DispatchQueueRoute.objects.all()}
        assert rows == {"ns-a": "dispatch_0", "ns-b": "dispatch_1", "ns-c": "dispatch_2"}

    def test_assigns_non_registry_namespaces(self):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            assert routing.assign_route("default") == "dispatch_0"
            assert routing.assign_route("ephemeral-gone") == "dispatch_1"

        assert DispatchQueueRoute.objects.filter(namespace__in=("default", "ephemeral-gone")).count() == 2

    @pytest.mark.parametrize("namespace", ["bad:ns", "has*star", "q?mark", "br[ack]et", "back\\slash"])
    def test_rejects_invalid_namespace_charset(self, namespace):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            with pytest.raises(ValidationError):
                routing.assign_route(namespace)

    @pytest.mark.parametrize("namespace", ["registered", "config"])
    def test_rejects_reserved_namespaces(self, namespace):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            with pytest.raises(ValidationError):
                routing.assign_route(namespace)


@pytest.mark.django_db
class TestResolveAndCache:
    def test_resolve_alias_reads_persisted_map_and_assigns_lazily(self):
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES):
            DispatchQueueRoute.objects.create(
                namespace="existing",
                redis_alias="dispatch_1",
                creator="tester",
                updater="tester",
            )
            assert routing.resolve_alias("existing") == "dispatch_1"
            assert routing.resolve_alias("lazy") == "dispatch_0"

    def test_assign_invalidates_whole_map_cache(self):
        cache_mock = MagicMock()
        cache_mock.get.side_effect = [{"stale": "dispatch_0"}, None]
        with override_settings(DISPATCH_REDIS_ALIASES=TWO_ALIASES), patch.object(routing, "cache", cache_mock):
            routing.assign_route("fresh")
            cache_mock.delete.assert_called_once_with(routing._ROUTE_CACHE_KEY)
            routes = routing._get_routes()
            assert "fresh" in routes

    def test_cold_memo_raises_when_map_unresolvable(self):
        routing.reset_route_cache()
        with patch.object(
            routing,
            "_get_routes",
            side_effect=DispatchRoutingError("route map unavailable"),
        ):
            with pytest.raises(DispatchRoutingError):
                routing.conn_for_namespace("default")

    def test_named_ttl_constants_define_remap_convergence(self):
        assert routing.ROUTE_MEMO_TTL_SECONDS == 30
        assert routing.ROUTE_CACHE_TTL_SECONDS == 60
        assert routing.ROUTE_MEMO_TTL_SECONDS + routing.ROUTE_CACHE_TTL_SECONDS == 90


class TestNamespaceForJobId:
    def test_longest_prefix_resolution(self):
        registry = {
            "alpha.task": SimpleNamespace(namespace="alpha"),
            "alpha.task.nested": SimpleNamespace(namespace="alpha"),
            "beta.task": SimpleNamespace(namespace="beta"),
        }
        with patch.dict("backend.db_periodic_task.dispatch.registry.DISPATCH_REGISTRY", registry, clear=True):
            assert routing.namespace_for_job_id("alpha.task.nested:item") == "alpha"
            assert routing.namespace_for_job_id("alpha.task:item") == "alpha"
            assert routing.namespace_for_job_id("beta.task:item") == "beta"
            assert routing.namespace_for_job_id("unknown.task:item") == ""

    def test_candidate_namespaces_merges_registry_and_route_table(self):
        with patch("backend.db_periodic_task.dispatch.queue.DispatchQueue.ensure_queues_loaded"), patch(
            "backend.db_periodic_task.dispatch.queue.DispatchQueue.registered_queues",
            return_value=[
                SimpleNamespace(namespace="registered-a"),
                SimpleNamespace(namespace="registered-b"),
            ],
        ), patch.dict(
            "backend.db_periodic_task.dispatch.registry.DISPATCH_REGISTRY",
            {"t1": SimpleNamespace(namespace="task-ns")},
            clear=True,
        ), patch(
            "backend.db_periodic_task.models.DispatchQueueRoute.objects.values_list",
            return_value=["route-only"],
        ):
            candidates = routing.candidate_namespaces()

        assert candidates == {"registered-a", "registered-b", "task-ns", "route-only"}
