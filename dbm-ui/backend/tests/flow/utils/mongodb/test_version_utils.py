# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest

from backend.flow.utils.mongodb.version_utils import (
    apply_mongodb_metadata_versions_to_cluster,
    check_cluster_instance_mm_consistency,
    compare_mongodb_versions,
    extract_mongodb_major_minor,
    extract_mongodb_version_tuple,
    get_cluster_live_instance_version,
    is_mongodb_major_minor_only,
    normalize_mongodb_cluster_version,
    normalize_mongodb_full_version,
    normalize_mongodb_instance_version,
    resolve_mongodb_flow_db_version,
    resolve_mongodb_metadata_versions,
    resolve_mongodb_persist_version,
    resolve_replaced_instance_version,
)


def test_is_mongodb_major_minor_only():
    assert is_mongodb_major_minor_only("mongodb-7.0") is True
    assert is_mongodb_major_minor_only("7.0") is True
    assert is_mongodb_major_minor_only("mongodb-7.0.14") is False


def test_extract_mongodb_version_tuple():
    assert extract_mongodb_version_tuple("mongodb-6.0.6") == (6, 0, 6)
    assert extract_mongodb_version_tuple("mongodb-7.0") == (7, 0, None)


def test_extract_mongodb_major_minor():
    assert extract_mongodb_major_minor("mongodb-6.0.27") == "6.0"
    assert extract_mongodb_major_minor("mongodb-7.0") == "7.0"


def test_normalize_mongodb_cluster_version():
    assert normalize_mongodb_cluster_version("mongodb-6.0.27") == "mongodb-6.0.27"
    pkg = SimpleNamespace(version="mongodb-7.0.14")
    assert normalize_mongodb_cluster_version("mongodb-7.0", package=pkg) == "mongodb-7.0.14"


def test_normalize_mongodb_instance_version_with_package():
    pkg = SimpleNamespace(version="mongodb-7.0.14")
    assert normalize_mongodb_instance_version("mongodb-7.0", package=pkg) == "mongodb-7.0.14"
    assert normalize_mongodb_instance_version("mongodb-6.0.27") == "mongodb-6.0.27"


def test_resolve_mongodb_metadata_versions():
    pkg = SimpleNamespace(version="mongodb-7.0.14")
    assert resolve_mongodb_metadata_versions("mongodb-7.0", package=pkg) == {
        "cluster": "mongodb-7.0.14",
        "instance": "mongodb-7.0.14",
    }
    assert resolve_mongodb_metadata_versions("mongodb-6.0.27") == {
        "cluster": "mongodb-6.0.27",
        "instance": "mongodb-6.0.27",
    }


def test_compare_mongodb_versions_patch():
    assert compare_mongodb_versions("mongodb-6.0.6", "mongodb-6.0.27") < 0
    assert compare_mongodb_versions("mongodb-6.0.27", "mongodb-6.0.6") > 0
    assert compare_mongodb_versions("mongodb-6.0.27", "mongodb-6.0.27") == 0


def test_compare_mongodb_versions_rejects_both_major_minor_only():
    with pytest.raises(ValueError):
        compare_mongodb_versions("mongodb-7.0", "mongodb-7.0")


def test_compare_mongodb_versions_mixed_major_minor_and_patch():
    assert compare_mongodb_versions("mongodb-6.0", "mongodb-6.0.27") < 0
    assert compare_mongodb_versions("mongodb-6.0.24", "mongodb-6.0") > 0
    assert compare_mongodb_versions("mongodb-7.0", "mongodb-7.0.14") < 0


def test_resolve_persist_version_major_minor_with_package():
    pkg = SimpleNamespace(version="mongodb-7.0.14")
    assert resolve_mongodb_persist_version("mongodb-7.0", package=pkg) == "mongodb-7.0.14"


def test_resolve_persist_version_major_minor_from_db_version():
    pkg = SimpleNamespace(
        version="mongodb-6.0",
        db_version=SimpleNamespace(base_version="6.0.24", name="6.0.24"),
    )
    assert resolve_mongodb_persist_version("mongodb-6.0", package=pkg) == "mongodb-6.0.24"
    assert resolve_mongodb_metadata_versions("mongodb-6.0", package=pkg) == {
        "cluster": "mongodb-6.0.24",
        "instance": "mongodb-6.0.24",
    }


def test_resolve_persist_version_major_minor_without_db_version_raises():
    pkg = SimpleNamespace(version="mongodb-6.0", db_version=None, db_version_id=None)
    with pytest.raises(ValueError):
        resolve_mongodb_persist_version("mongodb-6.0", package=pkg)


def test_resolve_persist_version_major_minor_without_package_raises():
    with pytest.raises(ValueError):
        resolve_mongodb_persist_version("mongodb-7.0")


def test_normalize_mongodb_full_version_still_pads_for_non_persist_use():
    assert normalize_mongodb_full_version("mongodb-7.0") == "mongodb-7.0.0"


def _make_cluster(storage_versions, proxy_versions=None, major_version="mongodb-6.0"):
    proxy_versions = proxy_versions or []

    class FakeQuerySet:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

        def filter(self, **kwargs):
            id_set = set(kwargs.get("id__in", []))
            if id_set:
                return FakeQuerySet([item for item in self._items if item.id in id_set])
            return self

        def update(self, version):
            count = 0
            for item in self._items:
                item.version = version
                count += 1
            return count

    storage_items = [SimpleNamespace(id=i + 1, version=v) for i, v in enumerate(storage_versions)]
    proxy_items = [SimpleNamespace(id=100 + i, version=v) for i, v in enumerate(proxy_versions)]
    cluster = SimpleNamespace(
        id=1,
        immute_domain="test.mongo.db",
        major_version=major_version,
        storageinstance_set=FakeQuerySet(storage_items),
        proxyinstance_set=FakeQuerySet(proxy_items),
        save=lambda **kwargs: None,
    )
    return cluster, storage_items, proxy_items


def test_get_cluster_live_instance_version_min_patch():
    cluster, _, _ = _make_cluster(["mongodb-6.0.27", "mongodb-6.0.6", ""])
    assert get_cluster_live_instance_version(cluster) == "mongodb-6.0.6"


def test_get_cluster_live_instance_version_fallback_to_cluster():
    cluster, _, _ = _make_cluster(["", ""], major_version="mongodb-6.0.18")
    assert get_cluster_live_instance_version(cluster) == "mongodb-6.0.18"


def test_get_cluster_live_instance_version_includes_proxy():
    cluster, _, _ = _make_cluster(["mongodb-6.0.20"], ["mongodb-6.0.10"])
    assert get_cluster_live_instance_version(cluster) == "mongodb-6.0.10"


def test_check_cluster_instance_mm_consistency_ok():
    cluster, _, _ = _make_cluster(["mongodb-6.0.6", "mongodb-6.0.27"], major_version="mongodb-6.0")
    assert check_cluster_instance_mm_consistency(cluster) is None


def test_check_cluster_instance_mm_consistency_warn():
    cluster, _, _ = _make_cluster(["mongodb-7.0.1"], major_version="mongodb-6.0")
    assert "inconsistent" in check_cluster_instance_mm_consistency(cluster)


def test_apply_mongodb_metadata_versions_to_cluster_full():
    cluster, storage_items, proxy_items = _make_cluster(["", ""], [""], major_version="mongodb-6.0")
    pkg = SimpleNamespace(version="mongodb-6.0.27")
    apply_mongodb_metadata_versions_to_cluster(cluster, "mongodb-6.0.27", package=pkg)
    assert cluster.major_version == "mongodb-6.0.27"
    assert all(item.version == "mongodb-6.0.27" for item in storage_items + proxy_items)


def test_apply_mongodb_metadata_versions_to_cluster_partial_instances():
    cluster, storage_items, _ = _make_cluster(["mongodb-6.0.6", ""], major_version="mongodb-6.0")
    pkg = SimpleNamespace(version="mongodb-6.0.27")
    apply_mongodb_metadata_versions_to_cluster(
        cluster,
        "mongodb-6.0.27",
        package=pkg,
        instance_ids=[storage_items[1].id],
    )
    assert storage_items[0].version == "mongodb-6.0.6"
    assert storage_items[1].version == "mongodb-6.0.27"


def test_resolve_mongodb_flow_db_version_from_live_instances():
    cluster, _, _ = _make_cluster(["mongodb-6.0.6", "mongodb-6.0.27"], major_version="mongodb-6.0")
    assert resolve_mongodb_flow_db_version(cluster) == "mongodb-6.0.6"


def test_resolve_mongodb_flow_db_version_major_minor_with_package():
    cluster, _, _ = _make_cluster(["", ""], major_version="mongodb-7.0")
    pkg = SimpleNamespace(
        version="mongodb-7.0.14",
        db_version=SimpleNamespace(base_version="7.0.14", name="7.0.14"),
    )

    def fake_lookup(raw, package=None):
        return pkg

    import backend.flow.utils.mongodb.version_utils as vu

    original = vu.lookup_mongodb_package
    vu.lookup_mongodb_package = fake_lookup
    try:
        assert resolve_mongodb_flow_db_version(cluster) == "mongodb-7.0.14"
    finally:
        vu.lookup_mongodb_package = original


def test_resolve_mongodb_flow_db_version_major_minor_from_db_version():
    cluster, _, _ = _make_cluster(["", ""], major_version="mongodb-6.0")
    pkg = SimpleNamespace(
        version="mongodb-6.0",
        db_version=SimpleNamespace(base_version="6.0.24", name="6.0.24"),
    )

    def fake_lookup(raw, package=None):
        return pkg

    import backend.flow.utils.mongodb.version_utils as vu

    original = vu.lookup_mongodb_package
    vu.lookup_mongodb_package = fake_lookup
    try:
        assert resolve_mongodb_flow_db_version(cluster) == "mongodb-6.0.24"
    finally:
        vu.lookup_mongodb_package = original


def test_lookup_mongodb_package_major_70_full_patch():
    pkg = SimpleNamespace(
        id=144,
        version="mongodb-7.0",
        db_version=SimpleNamespace(base_version="7.0.28", name="7.0.28"),
    )

    class FakeQuerySet:
        def __init__(self, items):
            self._items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def select_related(self, *args, **kwargs):
            return self

        def first(self):
            return self._items[0] if self._items else None

        def __iter__(self):
            return iter(self._items)

    from backend.db_package.models import Package

    original_objects = Package.objects

    class FakeManager:
        def filter(self, *args, **kwargs):
            return FakeQuerySet([pkg])

    Package.objects = FakeManager()
    try:
        import backend.flow.utils.mongodb.version_utils as vu

        assert vu.lookup_mongodb_package("mongodb-7.0.28").id == 144
    finally:
        Package.objects = original_objects


def test_lookup_mongodb_package_full_patch_matches_major_minor_package():
    pkg_624 = SimpleNamespace(
        id=145,
        version="mongodb-6.0",
        db_version=SimpleNamespace(base_version="6.0.24", name="6.0.24"),
    )
    pkg_627 = SimpleNamespace(
        id=153,
        version="mongodb-6.0",
        db_version=SimpleNamespace(base_version="6.0.27", name="6.0.27"),
    )

    class FakeQuerySet:
        def __init__(self, items):
            self._items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def select_related(self, *args, **kwargs):
            return self

        def first(self):
            return self._items[0] if self._items else None

        def __iter__(self):
            return iter(self._items)

    import backend.flow.utils.mongodb.version_utils as vu
    from backend.db_package.models import Package

    original_objects = Package.objects

    class FakeManager:
        def filter(self, *args, **kwargs):
            return FakeQuerySet([pkg_627, pkg_624])

    Package.objects = FakeManager()
    try:
        assert vu.lookup_mongodb_package("mongodb-6.0.27").id == 153
    finally:
        Package.objects = original_objects


def test_resolve_replaced_instance_version_prefers_old():
    cluster, storage_items, _ = _make_cluster(["mongodb-6.0.27"], major_version="mongodb-6.0")
    old = storage_items[0]
    assert resolve_replaced_instance_version(cluster, old) == "mongodb-6.0.27"


def test_resolve_mongodb_flow_db_version_raises_without_package():
    cluster, _, _ = _make_cluster(["", ""], major_version="mongodb-7.0")

    import backend.flow.utils.mongodb.version_utils as vu

    original = vu.lookup_mongodb_package
    vu.lookup_mongodb_package = lambda raw, package=None: None
    try:
        with pytest.raises(ValueError, match="no mongodb package found"):
            resolve_mongodb_flow_db_version(cluster)
    finally:
        vu.lookup_mongodb_package = original
