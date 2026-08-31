# -*- coding: utf-8 -*-
"""原地升级下发目标版本配置的 payload 构造测试"""
import pytest

from backend.components.dbconfig.constants import LevelName
from backend.flow.utils.redis import redis_act_playload as mod
from backend.flow.utils.redis.redis_act_playload import RedisActPayload

TARGET_MAJOR_VERSION = "Redis-6"
CURRENT_MAJOR_VERSION = "Redis-5"
# actuator 拿下发的配置整份重建 redis.conf, 少了这两项就是一份没有数据目录的配置
DELIVERABLE_CONF = {"port": "{{port}}", "dir": "{{redis_data_dir}}/data", "maxmemory": "{{maxmemory}}"}


def _new_payload_builder(ticket_data=None):
    """绕开 __init__ 里的 dbconfig / 介质包查询, 只测配置构造逻辑"""
    builder = object.__new__(RedisActPayload)
    builder.ticket_data = ticket_data or {"bk_biz_id": 100, "ticket_type": "REDIS_VERSION_UPDATE_ONLINE"}
    builder.cluster = {}
    builder.bk_biz_id = "100"
    return builder


def _redispatch_info(
    cluster_id=1, ports=None, databases=2, domain="cache-1.test.db", cluster_type="TwemproxyRedisInstance"
):
    return {
        "cluster_id": cluster_id,
        "immute_domain": domain,
        "bk_biz_id": 100,
        "cluster_type": cluster_type,
        "current_version": CURRENT_MAJOR_VERSION,
        "target_version": TARGET_MAJOR_VERSION,
        "databases": databases,
        "ports": ports if ports is not None else [30000, 30001],
    }


@pytest.fixture
def stub_conf_sources(monkeypatch):
    """把 dbconfig 与 module 查询替换成可控的假数据"""
    monkeypatch.setattr(mod, "get_cluster_redis_modules_detail", lambda cluster_id: [])
    monkeypatch.setattr(
        RedisActPayload,
        "build_target_version_conf_map",
        lambda self, **kwargs: (dict(DELIVERABLE_CONF), {}, ["slave-lazy-flush"]),
    )


def test_build_port_conf_configs_expands_cluster_conf_to_its_ports(stub_conf_sources):
    builder = _new_payload_builder()

    got = builder.build_port_conf_configs([_redispatch_info(ports=[30000, 30001])])

    assert sorted(got.keys()) == ["30000", "30001"]
    assert got["30000"]["conf_configs"]["port"] == "{{port}}"
    assert got["30000"]["conf_configs"]["databases"] == "{{databases}}"
    assert got["30000"]["databases"] == 0
    assert got["30000"]["load_modules_detail"] == []


def test_build_port_conf_configs_keeps_per_cluster_conf_separate(monkeypatch):
    monkeypatch.setattr(mod, "get_cluster_redis_modules_detail", lambda cluster_id: [])
    # 主从版一台机器上两个集群, 各自的配置不能互相覆盖
    monkeypatch.setattr(
        RedisActPayload,
        "build_target_version_conf_map",
        lambda self, **kwargs: (dict(DELIVERABLE_CONF, **{"domain-marker": kwargs["cluster_domain"]}), {}, []),
    )
    builder = _new_payload_builder()

    got = builder.build_port_conf_configs(
        [
            _redispatch_info(cluster_id=1, ports=[30000], domain="cache-1.test.db"),
            _redispatch_info(
                cluster_id=2,
                ports=[30001],
                domain="cache-2.test.db",
                databases=4,
                cluster_type="RedisInstance",
            ),
        ]
    )

    assert got["30000"]["conf_configs"]["domain-marker"] == "cache-1.test.db"
    assert got["30000"]["databases"] == 0
    assert got["30001"]["conf_configs"]["domain-marker"] == "cache-2.test.db"
    assert got["30001"]["databases"] == 4


def test_build_port_conf_configs_skips_cluster_with_empty_target_conf(monkeypatch):
    monkeypatch.setattr(mod, "get_cluster_redis_modules_detail", lambda cluster_id: [])
    # 目标版本没有任何配置项时不能下发空配置, 否则会渲染出一份残缺的 redis.conf
    monkeypatch.setattr(RedisActPayload, "build_target_version_conf_map", lambda self, **kwargs: ({}, {}, []))
    builder = _new_payload_builder()

    assert builder.build_port_conf_configs([_redispatch_info()]) == {}


def test_build_port_conf_configs_skips_cluster_without_ports(stub_conf_sources):
    builder = _new_payload_builder()

    assert builder.build_port_conf_configs([_redispatch_info(ports=[])]) == {}


def test_build_port_conf_configs_delivers_same_major_cluster(monkeypatch):
    """同 major 小版本升级也要下发完整 conf, 不能只换二进制留下旧 redis.conf."""
    monkeypatch.setattr(mod, "get_cluster_redis_modules_detail", lambda cluster_id: [])
    monkeypatch.setattr(
        RedisActPayload,
        "build_target_version_conf_map",
        lambda self, **kwargs: (dict(DELIVERABLE_CONF), {"maxmemory": "{{maxmemory}}"}, []),
    )
    builder = _new_payload_builder()
    info = _redispatch_info()
    info["current_version"] = info["target_version"] = TARGET_MAJOR_VERSION

    got = builder.build_port_conf_configs([info])

    assert "30000" in got
    assert got["30000"]["conf_configs"]["port"] == "{{port}}"
    assert got["30000"]["conf_configs"]["dir"] == "{{redis_data_dir}}/data"


def test_build_port_conf_configs_pops_replicaof_and_slaveof(monkeypatch):
    monkeypatch.setattr(mod, "get_cluster_redis_modules_detail", lambda cluster_id: [])
    conf = dict(DELIVERABLE_CONF, replicaof="1.1.1.2 30000", slaveof="1.1.1.2 30000")
    monkeypatch.setattr(
        RedisActPayload,
        "build_target_version_conf_map",
        lambda self, **kwargs: (conf, {}, []),
    )
    got = _new_payload_builder().build_port_conf_configs([_redispatch_info(ports=[30000])])
    assert "replicaof" not in got["30000"]["conf_configs"]
    assert "slaveof" not in got["30000"]["conf_configs"]
    assert got["30000"]["conf_configs"]["port"] == "{{port}}"


@pytest.mark.parametrize("missing", ["port", "dir"])
def test_build_port_conf_configs_skips_conf_missing_essential_directive(monkeypatch, missing):
    """缺 port/dir 的配置不能下发: actuator 会照它整份重建, 等于让实例丢掉数据目录"""
    monkeypatch.setattr(mod, "get_cluster_redis_modules_detail", lambda cluster_id: [])
    sparse_conf = {k: v for k, v in DELIVERABLE_CONF.items() if k != missing}
    monkeypatch.setattr(RedisActPayload, "build_target_version_conf_map", lambda self, **kwargs: (sparse_conf, {}, []))
    builder = _new_payload_builder()

    assert builder.build_port_conf_configs([_redispatch_info()]) == {}


def _stub_dbconfig(monkeypatch, src_content, plat_content, app_content=None):
    """集群级查询返回源版本生效配置, plat 级查询返回目标版本定义; APP 缺省时回落 plat."""

    def fake_query_conf_item(params):
        level_name = params["level_name"]
        if level_name == LevelName.PLAT:
            content = plat_content
        elif level_name == LevelName.APP:
            content = plat_content if app_content is None else app_content
        else:
            content = src_content
        return {"content": content}

    monkeypatch.setattr(mod.DBConfigApi, "query_conf_item", fake_query_conf_item)


def _target_conf_map(
    monkeypatch,
    src_content,
    plat_content,
    current_version,
    target_version,
    app_content=None,
    cluster_type="TwemproxyRedisInstance",
):
    _stub_dbconfig(monkeypatch, src_content, plat_content, app_content=app_content)
    return _new_payload_builder().build_target_version_conf_map(
        bk_biz_id=100,
        cluster_domain="cache-1.test.db",
        cluster_type=cluster_type,
        current_version=current_version,
        target_version=target_version,
    )


def test_build_target_version_conf_map_renames_redis_names_for_valkey(monkeypatch):
    """Redis -> Valkey 升级要按 Valkey 的叫法落库, 且必须保住集群调过的取值

    改名要在"目标版本认不认这个配置项"之前做: 反过来的话 slave-priority 在 Valkey-8
    的定义里查不到, 会在改名之前就被过滤掉, 集群调过的取值直接丢失.
    """
    got, _upsert, stale = _target_conf_map(
        monkeypatch,
        src_content={"slave-priority": "77", "hash-max-ziplist-entries": "256", "maxmemory": "2gb"},
        plat_content={"replica-priority": "100", "hash-max-listpack-entries": "128", "maxmemory": "0"},
        current_version="Redis-7",
        target_version="Valkey-8",
    )

    assert got == {"replica-priority": "77", "hash-max-listpack-entries": "256", "maxmemory": "2gb"}
    # 清理列表针对源版本 conf_file, 用的是改名前的旧名
    assert sorted(stale) == ["hash-max-ziplist-entries", "maxmemory", "slave-priority"]


def test_build_target_version_conf_map_renames_slowlog_for_valkey_9(monkeypatch):
    got, _upsert, _stale = _target_conf_map(
        monkeypatch,
        src_content={"slowlog-max-len": "512"},
        plat_content={"slowlog-max-len": "128", "commandlog-slow-execution-max-len": "128"},
        current_version="Valkey-8",
        target_version="Valkey-9",
    )

    # Valkey-9 两个名字都认, 按映射表的口径落到推荐的 commandlog-*
    assert got == {"commandlog-slow-execution-max-len": "512"}


def test_build_target_version_conf_map_keeps_names_target_version_still_uses(monkeypatch):
    """Redis -> Redis 升级不能被改名影响

    slave-priority 在 Redis-7 的 plat 定义里仍是旧名, 得原样保留;
    slave-lazy-flush 只在 _REDIS_5_LEGACY_CONF_NAME_MAP 里, 要改成 replica-lazy-flush.
    """
    got, _upsert, _stale = _target_conf_map(
        monkeypatch,
        src_content={"slave-priority": "77", "slave-lazy-flush": "yes"},
        plat_content={"slave-priority": "100", "replica-lazy-flush": "no"},
        current_version="Redis-6",
        target_version="Redis-7",
    )

    assert got == {"slave-priority": "77", "replica-lazy-flush": "yes"}


def test_build_target_version_conf_map_drops_names_target_version_dropped(monkeypatch):
    """目标版本已经不认的配置项要丢掉, 否则 redis 起不来"""
    got, _upsert, stale = _target_conf_map(
        monkeypatch,
        src_content={"maxmemory": "2gb", "hash-max-ziplist-entries": "256"},
        plat_content={"maxmemory": "0"},
        current_version="Redis-7",
        target_version="Valkey-8",
    )

    assert got == {"maxmemory": "2gb"}
    assert sorted(stale) == ["hash-max-ziplist-entries", "maxmemory"]


def test_build_target_version_conf_map_fills_new_plat_items_with_app_default(monkeypatch):
    """Redis-4 -> Redis-6: 源没有的目标新项要用业务默认, 不能落到 Redis 官方默认"""
    got, _upsert, stale = _target_conf_map(
        monkeypatch,
        src_content={"maxmemory": "2gb", "port": "30000"},
        plat_content={
            "maxmemory": "0",
            "port": "30000",
            "cluster-allow-replica-migration": "no",
            "cluster-allow-reads-when-down": "no",
        },
        current_version="Redis-4",
        target_version="Redis-6",
        app_content={
            "maxmemory": "0",
            "port": "30000",
            "cluster-allow-replica-migration": "no",
            "cluster-allow-reads-when-down": "no",
        },
    )

    assert got["maxmemory"] == "2gb"
    assert got["cluster-allow-replica-migration"] == "no"
    assert got["cluster-allow-reads-when-down"] == "no"
    assert sorted(stale) == ["maxmemory", "port"]


def test_build_target_version_conf_map_fills_new_plat_items_with_plat_default_when_app_missing(monkeypatch):
    """业务级缺该项时回落目标 plat 默认"""
    got, upsert, _stale = _target_conf_map(
        monkeypatch,
        src_content={"maxmemory": "2gb"},
        plat_content={"maxmemory": "0", "cluster-allow-replica-migration": "no"},
        current_version="Redis-4",
        target_version="Redis-6",
        app_content={"maxmemory": "0"},
    )

    assert got == {"maxmemory": "2gb", "cluster-allow-replica-migration": "no"}
    # plat 补出来的新项不下发到 CLUSTER; upsert 只有源集群客制项
    assert upsert == {"maxmemory": "2gb"}


def test_build_target_version_conf_map_keeps_sparse_for_downgrade(monkeypatch):
    """降级只继承少量指定项, 不能按目标 plat 全量补默认"""
    got, _upsert, stale = _target_conf_map(
        monkeypatch,
        src_content={
            "maxmemory": "2gb",
            "databases": "2",
            "cluster-allow-replica-migration": "yes",
            "port": "30000",
        },
        plat_content={
            "maxmemory": "0",
            "databases": "2",
            "cluster-allow-replica-migration": "no",
            "port": "30000",
        },
        current_version="Redis-6",
        target_version="Redis-4",
    )

    assert got == {"maxmemory": "2gb"}
    assert "cluster-allow-replica-migration" not in got
    assert "databases" not in got
    assert sorted(stale) == ["maxmemory"]


def test_build_target_version_conf_map_redis_instance_downgrade_keeps_databases(monkeypatch):
    """主从版降级仍继承 databases, 这是唯一会改库数的架构."""
    got, _upsert, stale = _target_conf_map(
        monkeypatch,
        src_content={
            "maxmemory": "2gb",
            "databases": "16",
            "cluster-allow-replica-migration": "yes",
            "port": "30000",
        },
        plat_content={
            "maxmemory": "0",
            "databases": "2",
            "cluster-allow-replica-migration": "no",
            "port": "30000",
        },
        current_version="Redis-6",
        target_version="Redis-4",
        cluster_type="RedisInstance",
    )

    assert got == {"maxmemory": "2gb", "databases": "16"}
    assert sorted(stale) == ["databases", "maxmemory"]


def test_redis_conf_names_by_cluster_type_equal_versions_inherit_all():
    names, rename_ver = RedisActPayload.redis_conf_names_by_cluster_type(
        "TwemproxyRedisInstance",
        "Redis-6",
        target_cluster_type="TwemproxyRedisInstance",
        target_version="Redis-6",
    )
    assert names is None
    assert rename_ver == "Redis-6"


def _stub_latest_pkg(monkeypatch, captured=None):
    def fake(version, name_prefix=None):
        if captured is not None:
            captured["version"] = version
            captured["name_prefix"] = name_prefix
        return type("P", (), {"name": "p.tar.gz", "md5": "md5"})

    monkeypatch.setattr(mod, "get_latest_redis_package_by_version", fake)


def test_version_update_payload_without_redispatch_infos_keeps_legacy_shape(monkeypatch):
    _stub_latest_pkg(monkeypatch)
    builder = _new_payload_builder()

    got = builder.redis_cluster_version_update_online_payload(
        params={
            "db_version": TARGET_MAJOR_VERSION,
            "cluster_type": "TwemproxyRedisInstance",
            "ip": "1.1.1.1",
            "ports": [30000],
            "role": "redis_slave",
        }
    )

    # 在途单据没有 conf_redispatch_infos, actuator 必须保持"只换二进制"的旧行为
    assert "port_conf_configs" not in got["payload"]
    # 同理: 没下发这几项时 actuator 保持"带着本地数据重启、不碰主从关系"的旧行为
    assert "sync_masters" not in got["payload"]
    assert "discard_local_data_on_restart" not in got["payload"]
    assert "sync_wait_timeout_seconds" not in got["payload"]


def test_version_update_payload_carries_empty_start_and_sync_masters(monkeypatch):
    _stub_latest_pkg(monkeypatch)

    got = _new_payload_builder().redis_cluster_version_update_online_payload(
        params={
            "db_version": TARGET_MAJOR_VERSION,
            "cluster_type": "TwemproxyRedisInstance",
            "ip": "1.1.1.1",
            "ports": [30000],
            "role": "redis_master",
            "sync_masters": {"30000": "1.1.1.2:30000"},
            "discard_local_data_on_restart": True,
            "sync_wait_timeout_seconds": 21600,
        }
    )

    assert got["payload"]["sync_masters"] == {"30000": "1.1.1.2:30000"}
    assert got["payload"]["discard_local_data_on_restart"] is True
    assert got["payload"]["sync_wait_timeout_seconds"] == 21600


def _version_update_payload(monkeypatch):
    _stub_latest_pkg(monkeypatch)
    return _new_payload_builder().redis_cluster_version_update_online_payload(
        params={
            "db_version": TARGET_MAJOR_VERSION,
            "cluster_type": "TwemproxyRedisInstance",
            "ip": "1.1.1.1",
            "ports": [30000, 30001],
            "role": "redis_slave",
            "conf_redispatch_infos": [_redispatch_info(ports=[30000, 30001])],
        }
    )


def test_version_update_payload_includes_port_conf_configs(monkeypatch, stub_conf_sources):
    got = _version_update_payload(monkeypatch)

    assert sorted(got["payload"]["port_conf_configs"].keys()) == ["30000", "30001"]


def test_version_update_payload_forwards_pkg_name_prefix(monkeypatch):
    captured = {}
    _stub_latest_pkg(monkeypatch, captured)

    _new_payload_builder().redis_cluster_version_update_online_payload(
        params={
            "db_version": TARGET_MAJOR_VERSION,
            "pkg_name_prefix": "redis-6.2.14",
            "cluster_type": "TwemproxyRedisInstance",
            "ip": "1.1.1.1",
            "ports": [30000],
            "role": "redis_slave",
        }
    )

    assert captured == {"version": TARGET_MAJOR_VERSION, "name_prefix": "redis-6.2.14"}


def test_version_update_payload_without_prefix_looks_up_by_series_only(monkeypatch):
    captured = {}
    _stub_latest_pkg(monkeypatch, captured)

    _new_payload_builder().redis_cluster_version_update_online_payload(
        params={
            "db_version": TARGET_MAJOR_VERSION,
            "cluster_type": "TwemproxyRedisInstance",
            "ip": "1.1.1.1",
            "ports": [30000],
            "role": "redis_slave",
        }
    )

    assert captured == {"version": TARGET_MAJOR_VERSION, "name_prefix": None}
