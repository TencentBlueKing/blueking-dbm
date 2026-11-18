# -*- coding: utf-8 -*-
import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_package.exceptions import PackageNotExistException
from backend.db_package.models import DBVersion, Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis.redis_package_resolver import (
    RedisUpgradePackageResolver,
    RedisUpgradeTarget,
    RedisUpgradeTargetError,
    compare_db_version,
    db_version_engine_family,
    is_cross_engine,
    resolve_ticket_upgrade_targets,
    upgrade_db_versions,
    validate_proxy_upgrade,
    validate_storage_upgrade,
)
from backend.tests.mock_data.db_package.v2 import create_redis_package

pytestmark = pytest.mark.usefixtures("clean_redis_packages")

REDIS = MediumEnum.Redis.value
TENDISPLUS = MediumEnum.TendisPlus.value
PREDIXY = MediumEnum.Predixy.value
TWEMPROXY = MediumEnum.Twemproxy.value

REDIS_CLUSTER = ClusterType.TendisTwemproxyRedisInstance.value
TENDISPLUS_CLUSTER = ClusterType.TendisPredixyTendisplusCluster.value
TWEMPROXY_CLUSTER = ClusterType.TendisTwemproxyRedisInstance.value


@pytest.fixture
def clean_redis_packages(db):
    Package.objects.filter(db_type=DBType.Redis.value).delete()


def _redis_pkg(name, full_version, phase="release", **kwargs):
    kwargs.setdefault("series", "Redis-7")
    return create_redis_package(name, full_version=full_version, phase=phase, **kwargs)


def _dbv(pkg) -> DBVersion:
    return DBVersion.objects.select_related("version_series__distribution").get(pk=pkg.db_version_id)


def _same_version_alpha_and_release():
    alpha = _redis_pkg("redis-7.2.5-a.tar.gz", "7.2.5.0.0.0", "alpha", version_name="v-alpha")
    release = _redis_pkg(
        "redis-7.2.5-r.tar.gz", "7.2.5.0.0.0", "release", version_name="v-release", distribution="test-redis-other"
    )
    return alpha, release


class TestCompareDBVersion:
    @pytest.mark.parametrize(
        "running, expected",
        [("redis-6.2.13", 1), ("redis-6.2.14", 0), ("redis-7.0.0", -1), ("bad", None), ("", None)],
    )
    def test_redis_compares_base_version(self, running, expected):
        pkg = _redis_pkg("redis-6.2.14.tar.gz", "6.2.14.0.0.0", series="Redis-6")

        assert compare_db_version(_dbv(pkg), running) == expected

    def test_tendisplus_rocksdb_build_is_ignored_at_three_segments(self):
        pkg = create_redis_package(
            "tendisplus-2.7.6-rocksdb-v8.5.3.tgz",
            pkg_type=TENDISPLUS,
            series="Tendisplus-2.7",
            full_version="2.7.6.0.0.0",
            phase="release",
        )

        assert compare_db_version(_dbv(pkg), "tendisplus-2.7.6-rocksdb-v8.5.1") == 0
        assert compare_db_version(_dbv(pkg), "tendisplus-2.7.5-rocksdb-v9.0.0") == 1

    def test_twemproxy_compares_six_segments(self):
        pkg = create_redis_package(
            "twemproxy-0.4.1-v36.tar.gz",
            pkg_type=TWEMPROXY,
            series="Twemproxy-latest",
            full_version="0.4.1.36.0.0",
            phase="release",
        )

        assert compare_db_version(_dbv(pkg), "twemproxy-0.4.1-v36") == 0
        assert compare_db_version(_dbv(pkg), "twemproxy-0.4.1-v35") == 1
        assert compare_db_version(_dbv(pkg), "twemproxy-0.4.1-v37") == -1

    def test_engine_family_comes_from_series_name(self):
        valkey = _redis_pkg("valkey-8.0.1.tar.gz", "8.0.1.0.0.0", series="Valkey-8")
        redis = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")

        assert db_version_engine_family(_dbv(valkey)) == "valkey"
        assert db_version_engine_family(_dbv(redis)) == "redis"
        assert is_cross_engine(_dbv(valkey), "redis-7.2.5")
        assert not is_cross_engine(_dbv(valkey), "valkey-8.0.0")


class TestValidateUpgrade:
    def test_storage_rejects_downgrade(self):
        pkg = _redis_pkg("redis-6.2.14.tar.gz", "6.2.14.0.0.0", series="Redis-6")

        with pytest.raises(RedisUpgradeTargetError, match="不支持降级"):
            validate_storage_upgrade(_dbv(pkg), REDIS_CLUSTER, "a.b", {"1.1.1.1": "redis-7.0.0"})

    def test_storage_rejects_cross_engine(self):
        pkg = _redis_pkg("valkey-8.0.1.tar.gz", "8.0.1.0.0.0", series="Valkey-8")

        with pytest.raises(RedisUpgradeTargetError, match="引擎不同"):
            validate_storage_upgrade(_dbv(pkg), REDIS_CLUSTER, "a.b", {"1.1.1.1": "redis-7.0.0"})

    def test_storage_rejects_mismatched_pkg_type(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")

        with pytest.raises(RedisUpgradeTargetError, match="不是 tendisplus 介质版本"):
            validate_storage_upgrade(_dbv(pkg), TENDISPLUS_CLUSTER, "a.b", {"1.1.1.1": "redis-6.0.0"})

    def test_storage_accepts_same_and_higher(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")

        validate_storage_upgrade(
            _dbv(pkg), REDIS_CLUSTER, "a.b", {"1.1.1.1": "redis-7.2.5", "1.1.1.2": "redis-6.2.14"}
        )

    def test_proxy_rejects_noop(self):
        pkg = create_redis_package(
            "twemproxy-0.4.1-v36.tar.gz",
            pkg_type=TWEMPROXY,
            series="Twemproxy-latest",
            full_version="0.4.1.36.0.0",
            phase="release",
        )

        with pytest.raises(RedisUpgradeTargetError, match="无需执行"):
            validate_proxy_upgrade(_dbv(pkg), TWEMPROXY_CLUSTER, "a.b", {"2.2.2.2": "twemproxy-0.4.1-v36"})
        validate_proxy_upgrade(_dbv(pkg), TWEMPROXY_CLUSTER, "a.b", {"2.2.2.2": "twemproxy-0.4.1-v35"})


class TestUpgradeDBVersions:
    def test_annotates_enabled_package_and_skips_versions_without_package(self):
        enabled = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")
        disabled = _redis_pkg("redis-7.2.4.tar.gz", "7.2.4.0.0.0", enable=False)
        orphan = _redis_pkg("redis-7.2.3.tar.gz", "7.2.3.0.0.0")
        orphan_version_id = orphan.db_version_id
        orphan.delete()

        got = {v.id: v.has_enabled_package for v in upgrade_db_versions([REDIS])}

        assert got == {enabled.db_version_id: True, disabled.db_version_id: False}
        assert orphan_version_id not in got


class TestResolveTargetByName:
    def test_exact_name_resolves_any_phase(self):
        _redis_pkg("redis-7.2.4.tar.gz", "7.2.4.0.0.0", version_name="Redis 7.2.4")
        alpha = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0", "alpha", version_name="Redis 7.2.5")

        target = RedisUpgradePackageResolver([REDIS]).resolve_target("Redis 7.2.5")

        assert target == RedisUpgradeTarget(alpha.db_version_id, "Redis 7.2.5")

    def test_package_style_name_matches_full_version(self):
        pkg = _redis_pkg("redis-6.2.14.tar.gz", "6.2.14.0.0.0", series="Redis-6", version_name="6.2.14")

        assert RedisUpgradePackageResolver([REDIS]).resolve_target("redis-6.2.14").db_version_id == pkg.db_version_id
        assert (
            RedisUpgradePackageResolver([REDIS]).resolve_target("redis-6.2.14.tar.gz").db_version_id
            == pkg.db_version_id
        )

    def test_package_style_name_respects_engine_family(self):
        redis = _redis_pkg("redis-8.0.1.tar.gz", "8.0.1.0.0.0", series="Redis-8", version_name="r8")
        valkey = _redis_pkg(
            "valkey-8.0.1.tar.gz", "8.0.1.0.0.0", series="Valkey-8", version_name="v8", distribution="test-valkey"
        )
        resolver = RedisUpgradePackageResolver([REDIS])

        assert resolver.resolve_target("redis-8.0.1").db_version_id == redis.db_version_id
        assert resolver.resolve_target("valkey-8.0.1").db_version_id == valkey.db_version_id

    def test_twemproxy_build_suffix_selects_six_segment_version(self):
        v36 = create_redis_package(
            "twemproxy-0.4.1-v36.tar.gz", pkg_type=TWEMPROXY, series="T", full_version="0.4.1.36.0.0", phase="release"
        )
        create_redis_package(
            "twemproxy-0.4.1-v37.tar.gz", pkg_type=TWEMPROXY, series="T", full_version="0.4.1.37.0.0", phase="release"
        )

        target = RedisUpgradePackageResolver([TWEMPROXY]).resolve_target("twemproxy-0.4.1-v36")

        assert target.db_version_id == v36.db_version_id

    def test_same_full_version_under_two_enabled_versions_is_rejected(self):
        _same_version_alpha_and_release()

        with pytest.raises(RedisUpgradeTargetError, match="无法唯一确定"):
            RedisUpgradePackageResolver([REDIS]).resolve_target("redis-7.2.5")

    def test_disabled_version_loses_when_versions_collide(self):
        alpha, release = _same_version_alpha_and_release()
        DBVersion.objects.filter(pk=alpha.db_version_id).update(enable=False)

        assert (
            RedisUpgradePackageResolver([REDIS]).resolve_target("redis-7.2.5").db_version_id == release.db_version_id
        )

    def test_version_without_enabled_package_loses_when_versions_collide(self):
        alpha, release = _same_version_alpha_and_release()
        Package.objects.filter(pk=alpha.pk).update(enable=False)

        assert (
            RedisUpgradePackageResolver([REDIS]).resolve_target("redis-7.2.5").db_version_id == release.db_version_id
        )

    def test_only_disabled_version_is_still_resolvable(self):
        pkg = _redis_pkg("redis-6.2.14.tar.gz", "6.2.14.0.0.0", version_enable=False)

        assert RedisUpgradePackageResolver([REDIS]).resolve_target("redis-6.2.14").db_version_id == pkg.db_version_id

    def test_package_without_v2_version_is_not_resolvable(self):
        create_redis_package("redis-6.2.14.tar.gz")

        with pytest.raises(RedisUpgradeTargetError, match="找不到"):
            RedisUpgradePackageResolver([REDIS]).resolve_target("redis-6.2.14")

    def test_other_pkg_type_is_ignored(self):
        create_redis_package(
            "predixy-1.6.0.tar.gz", pkg_type=PREDIXY, series="Predixy-2", full_version="1.6.0.0.0.0", phase="beta"
        )

        with pytest.raises(RedisUpgradeTargetError, match="找不到"):
            RedisUpgradePackageResolver([REDIS]).resolve_target("predixy-1.6.0")

    def test_empty_name_is_rejected(self):
        with pytest.raises(RedisUpgradeTargetError, match="为空"):
            RedisUpgradePackageResolver([REDIS]).resolve_target("")


class TestTargetOf:
    def test_id_selects_one_of_same_full_versions(self):
        alpha, _release = _same_version_alpha_and_release()

        target = RedisUpgradePackageResolver([REDIS]).target_of(str(alpha.db_version_id))

        assert target == RedisUpgradeTarget(alpha.db_version_id, "v-alpha")

    def test_id_of_other_pkg_type_is_rejected(self):
        proxy = create_redis_package(
            "predixy-1.6.0.tar.gz", pkg_type=PREDIXY, series="Predixy-2", full_version="1.6.0.0.0.0", phase="beta"
        )

        with pytest.raises(RedisUpgradeTargetError, match="找不到"):
            RedisUpgradePackageResolver([REDIS]).target_of(proxy.db_version_id)

    @pytest.mark.parametrize("bad_id", [None, 0, -1, "abc", True])
    def test_invalid_id_is_rejected(self, bad_id):
        with pytest.raises(RedisUpgradeTargetError, match="不合法"):
            RedisUpgradePackageResolver([REDIS]).target_of(bad_id)


class TestPackageAndSeries:
    def test_package_is_selected_by_version_id(self):
        alpha, release = _same_version_alpha_and_release()
        resolver = RedisUpgradePackageResolver([REDIS])

        assert resolver.package(RedisUpgradeTarget(alpha.db_version_id, "v-alpha")).id == alpha.id
        assert resolver.package(RedisUpgradeTarget(release.db_version_id, "v-release")).id == release.id

    def test_disabled_package_is_still_returned_for_in_flight_tickets(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0", "alpha", enable=False)

        got = RedisUpgradePackageResolver([REDIS]).package(RedisUpgradeTarget(pkg.db_version_id, ""))

        assert got.id == pkg.id

    def test_enabled_package_is_preferred_within_one_version(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")
        disabled = Package.objects.create(
            name="redis-7.2.5.tgz",
            version="Redis-7",
            pkg_type=REDIS,
            db_type=DBType.Redis.value,
            path="/tmp/redis-7.2.5.tgz",
            size=0,
            md5="",
            enable=False,
            priority=9,
            db_version_id=pkg.db_version_id,
            permit_os_type=pkg.permit_os_type,
            creator="test",
            updater="test",
        )

        got = RedisUpgradePackageResolver([REDIS]).package(RedisUpgradeTarget(pkg.db_version_id, ""))

        assert got.id == pkg.id != disabled.id

    def test_missing_package_raises(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")

        with pytest.raises(PackageNotExistException):
            RedisUpgradePackageResolver([PREDIXY]).package(RedisUpgradeTarget(pkg.db_version_id, ""))

    def test_series_name_comes_from_version_series(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0", "alpha", series="Redis-7-dev")

        assert RedisUpgradePackageResolver.series_name(RedisUpgradeTarget(pkg.db_version_id, "")) == "Redis-7-dev"


class TestResolveTicketTargets:
    def test_version_names_are_written_back_from_ids(self):
        storage = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0", "alpha", version_name="Redis 7.2.5")
        proxy = create_redis_package(
            "predixy-1.6.0.tar.gz", pkg_type=PREDIXY, series="Predixy-2", full_version="1.6.0.0.0.0", phase="beta"
        )
        infos = [
            {
                "node_type": "Backend",
                "target_versions": [
                    {"ip": "1.1.1.1", "db_version_id": storage.db_version_id},
                    {"ip": "1.1.1.2", "db_version_id": str(storage.db_version_id)},
                ],
            },
            {"node_type": "Proxy", "target_versions": [{"ip": "2.2.2.2", "db_version_id": proxy.db_version_id}]},
        ]

        db_versions = resolve_ticket_upgrade_targets(infos)

        assert set(db_versions) == {storage.db_version_id, proxy.db_version_id}
        assert [t["version_name"] for t in infos[0]["target_versions"]] == ["Redis 7.2.5"] * 2
        assert [t["db_version_id"] for t in infos[0]["target_versions"]] == [storage.db_version_id] * 2
        assert infos[1]["target_versions"][0]["version_name"] == "predixy-1.6.0.tar.gz"

    def test_submitted_version_name_is_overwritten(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0", version_name="Redis 7.2.5")
        entry = {"ip": "1.1.1.1", "version_name": "redis-6.0.0", "db_version_id": pkg.db_version_id}

        resolve_ticket_upgrade_targets([{"node_type": "Backend", "target_versions": [entry]}])

        assert entry["version_name"] == "Redis 7.2.5"

    def test_disabled_version_is_rejected_only_when_required(self):
        pkg = _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0", version_enable=False)

        def infos():
            return [
                {"node_type": "Backend", "target_versions": [{"ip": "1.1.1.1", "db_version_id": pkg.db_version_id}]}
            ]

        with pytest.raises(RedisUpgradeTargetError, match="已禁用"):
            resolve_ticket_upgrade_targets(infos(), require_enabled=True)
        assert set(resolve_ticket_upgrade_targets(infos())) == {pkg.db_version_id}

    @pytest.mark.parametrize("entry", ["redis-7.2.5", {"ip": "1.1.1.1", "version": "redis-7.2.5"}])
    def test_entry_without_id_is_rejected(self, entry):
        _redis_pkg("redis-7.2.5.tar.gz", "7.2.5.0.0.0")

        with pytest.raises(RedisUpgradeTargetError, match="格式不合法"):
            resolve_ticket_upgrade_targets([{"node_type": "Backend", "target_versions": [entry]}])

    def test_storage_entry_does_not_match_proxy_version(self):
        proxy = create_redis_package(
            "predixy-1.6.0.tar.gz", pkg_type=PREDIXY, series="Predixy-2", full_version="1.6.0.0.0.0", phase="beta"
        )

        with pytest.raises(RedisUpgradeTargetError, match="找不到"):
            resolve_ticket_upgrade_targets(
                [
                    {
                        "node_type": "Backend",
                        "target_versions": [{"ip": "1.1.1.1", "db_version_id": proxy.db_version_id}],
                    }
                ]
            )


def test_target_round_trips_through_dict():
    target = RedisUpgradeTarget(12, "Redis 7.2.5")

    assert target.to_dict() == {"db_version_id": 12, "version_name": "Redis 7.2.5"}
    assert RedisUpgradeTarget.from_dict(target.to_dict()) == target
    assert RedisUpgradeTarget.from_dict({"db_version_id": "12"}) == RedisUpgradeTarget(12, "")
    assert RedisUpgradeTarget.from_dict(None) is None


def test_target_from_package_requires_v2_version():
    pkg = create_redis_package("redis-6.2.14.tar.gz")

    with pytest.raises(RedisUpgradeTargetError):
        RedisUpgradeTarget.from_package(pkg)
