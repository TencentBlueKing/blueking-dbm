# -*- coding: utf-8 -*-
from types import SimpleNamespace

from backend.flow.consts import MediumEnum
from backend.flow.plugins.components.collections.redis.trans_flies import apply_redis_tools_snapshot_to_file_list
from backend.flow.utils.redis import redis_act_playload as payload_mod
from backend.flow.utils.redis.redis_act_playload import (
    RedisActPayload,
    ensure_redis_tools_pkg_snapshot,
    resolve_redis_tools_pkg,
)

SNAPSHOT_A = {
    "pkg": "dbtools-A.tgz",
    "pkg_md5": "md5A",
    "path": "redis/dbtools/dbtools-A.tgz",
}
LATEST_B = SimpleNamespace(name="dbtools-B.tgz", md5="md5B", path="redis/dbtools/dbtools-B.tgz")
SRC_IP = "1.1.1.1"


def _latest_pkg_factory(redis_tools=LATEST_B, others=None):
    others = others or SimpleNamespace(name="other.tgz", md5="other", path="other.tgz")

    def fake_get_latest_package(**kwargs):
        if kwargs.get("pkg_type") == MediumEnum.RedisTools:
            return redis_tools
        return others

    return fake_get_latest_package


def _payload_builder(tools_pkg, cluster=None):
    builder = object.__new__(RedisActPayload)
    builder.ticket_data = {"bk_biz_id": 100, "ticket_type": "REDIS_DATACOPY_CHECK_REPAIR"}
    builder.bk_biz_id = "100"
    builder.tools_pkg = tools_pkg
    builder.cluster = cluster or {
        "dts_copy_type": "copy",
        "src_redis_password": "p",
        "src_cluster_addr": "src.test.db",
        "dst_cluster_addr": "dst.test.db",
        "dst_cluster_password": "p",
        "key_white_regex": "*",
        "key_black_regex": "",
        "path": "/tmp",
        "domain_name": "cache.test.db",
        "white_regex": "*",
        "black_regex": "",
        SRC_IP: [{"port": 30000}],
    }
    return builder


def test_ensure_writes_pkg_md5_path(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    data = {"bk_biz_id": 100}
    ensure_redis_tools_pkg_snapshot(data)
    assert data["redis_tools_pkg"] == {
        "pkg": "dbtools-B.tgz",
        "pkg_md5": "md5B",
        "path": "redis/dbtools/dbtools-B.tgz",
    }


def test_ensure_keeps_existing_snapshot(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    data = {"redis_tools_pkg": SNAPSHOT_A}
    ensure_redis_tools_pkg_snapshot(data)
    assert data["redis_tools_pkg"] == SNAPSHOT_A


def test_ensure_none_is_noop():
    assert ensure_redis_tools_pkg_snapshot(None) is None


def test_keys_extract_flow_freezes_on_init(monkeypatch):
    from backend.flow.engine.bamboo.scene.redis.redis_keys_extract import RedisKeysExtractFlow

    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    data = {"bk_biz_id": 100, "rules": []}
    RedisKeysExtractFlow(root_id="r", data=data)
    assert data["redis_tools_pkg"]["pkg"] == "dbtools-B.tgz"


def test_resolve_prefers_ticket_snapshot_over_latest(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    pkg = resolve_redis_tools_pkg({"redis_tools_pkg": SNAPSHOT_A})
    assert pkg.name == "dbtools-A.tgz"
    assert pkg.md5 == "md5A"
    assert pkg.path == "redis/dbtools/dbtools-A.tgz"


def test_resolve_without_snapshot_uses_latest(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    pkg = resolve_redis_tools_pkg({"bk_biz_id": 100})
    assert pkg.name == "dbtools-B.tgz"
    assert pkg.md5 == "md5B"


def test_datacheck_payload_keeps_snapshot_when_latest_changes(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    builder = _payload_builder(SimpleNamespace(name="dbtools-A.tgz", md5="md5A"))
    result = builder.redis_dts_datacheck_payload(ip=SRC_IP, params={})
    assert result["payload"]["pkg"] == "dbtools-A.tgz"
    assert result["payload"]["pkg_md5"] == "md5A"


def test_keys_extract_payload_keeps_snapshot_when_latest_changes(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    monkeypatch.setattr(RedisActPayload, "_RedisActPayload__get_fileserver", staticmethod(lambda: {}))
    builder = _payload_builder(SimpleNamespace(name="dbtools-A.tgz", md5="md5A"))
    result = builder.keys_extract_payload(ip=SRC_IP)
    assert result["payload"]["pkg"] == "dbtools-A.tgz"
    assert result["payload"]["pkg_md5"] == "md5A"


def test_datarepair_payload_keeps_snapshot_when_latest_changes(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    builder = _payload_builder(SimpleNamespace(name="dbtools-A.tgz", md5="md5A"))
    result = builder.redis_dts_datarepair_payload(ip=SRC_IP, params={})
    assert result["payload"]["pkg"] == "dbtools-A.tgz"
    assert result["payload"]["pkg_md5"] == "md5A"


def test_act_payload_init_prefers_ticket_snapshot(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    monkeypatch.setattr(RedisActPayload, "_RedisActPayload__init_dbconfig_params", lambda self: None)
    payload = RedisActPayload(
        {
            "bk_biz_id": 100,
            "ticket_type": "REDIS_DATACOPY_CHECK_REPAIR",
            "redis_tools_pkg": SNAPSHOT_A,
        },
        {},
    )
    assert payload.tools_pkg.name == "dbtools-A.tgz"
    assert payload.tools_pkg.md5 == "md5A"


def test_bkdbmon_header_uses_passed_tools_pkg(monkeypatch):
    monkeypatch.setattr(RedisActPayload, "get_common_config", staticmethod(lambda **kwargs: {}))
    monkeypatch.setattr(payload_mod, "get_dbmon_maxmemory_config_by_bkbizid", lambda **kwargs: {})
    monkeypatch.setattr(
        payload_mod.SystemSettings,
        "get_setting_value",
        lambda key: {"event": {"data_id": 1, "token": "t"}, "metric": {"data_id": 2, "token": "t"}},
    )
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    header = RedisActPayload.get_bkdbmon_payload_header(
        "100", tools_pkg=SimpleNamespace(name="dbtools-A.tgz", md5="md5A")
    )
    assert header["dbtoolspkg"] == {"pkg": "dbtools-A.tgz", "pkg_md5": "md5A"}


def test_payload_without_snapshot_matches_latest(monkeypatch):
    monkeypatch.setattr(payload_mod.Package, "get_latest_package", _latest_pkg_factory())
    pkg = resolve_redis_tools_pkg({})
    builder = _payload_builder(pkg)
    result = builder.redis_dts_datacheck_payload(ip=SRC_IP, params={})
    assert result["payload"]["pkg"] == "dbtools-B.tgz"
    assert result["payload"]["pkg_md5"] == "md5B"


def test_transfile_replaces_existing_dbtools(monkeypatch):
    monkeypatch.setattr("backend.flow.plugins.components.collections.redis.trans_flies.env.BKREPO_PROJECT", "bk-dbm")
    monkeypatch.setattr("backend.flow.plugins.components.collections.redis.trans_flies.env.BKREPO_BUCKET", "redis")
    file_list = [
        "bk-dbm/redis/dbactuator/dbactuator.tar.gz",
        "bk-dbm/redis/dbtools/dbtools-old.tgz",
        "bk-dbm/redis/dbmon/bk-dbmon.tgz",
    ]
    got = apply_redis_tools_snapshot_to_file_list(file_list, SNAPSHOT_A)
    assert got == [
        "bk-dbm/redis/dbactuator/dbactuator.tar.gz",
        "bk-dbm/redis/redis/dbtools/dbtools-A.tgz",
        "bk-dbm/redis/dbmon/bk-dbmon.tgz",
    ]


def test_transfile_does_not_append_when_no_dbtools(monkeypatch):
    monkeypatch.setattr("backend.flow.plugins.components.collections.redis.trans_flies.env.BKREPO_PROJECT", "bk-dbm")
    monkeypatch.setattr("backend.flow.plugins.components.collections.redis.trans_flies.env.BKREPO_BUCKET", "redis")
    file_list = ["bk-dbm/redis/dbactuator/dbactuator.tar.gz"]
    got = apply_redis_tools_snapshot_to_file_list(file_list, SNAPSHOT_A)
    assert got == file_list


def test_transfile_drops_extra_dbtools_with_warning(monkeypatch):
    monkeypatch.setattr("backend.flow.plugins.components.collections.redis.trans_flies.env.BKREPO_PROJECT", "bk-dbm")
    monkeypatch.setattr("backend.flow.plugins.components.collections.redis.trans_flies.env.BKREPO_BUCKET", "redis")
    file_list = [
        "bk-dbm/redis/dbtools/dbtools-old.tgz",
        "bk-dbm/redis/dbtools/dbtools-other.tgz",
    ]
    got = apply_redis_tools_snapshot_to_file_list(file_list, SNAPSHOT_A)
    assert got == ["bk-dbm/redis/redis/dbtools/dbtools-A.tgz"]


def test_transfile_without_snapshot_keeps_file_list():
    file_list = ["bk-dbm/redis/dbtools/dbtools-old.tgz"]
    assert apply_redis_tools_snapshot_to_file_list(file_list, None) is file_list
    assert apply_redis_tools_snapshot_to_file_list(file_list, {}) is file_list


def test_spawn_check_repair_inherits_parent_snapshot(monkeypatch):
    from backend.flow.plugins.components.collections.redis import redis_dts as dts_mod

    captured = {}

    class FakeFlow:
        def __init__(self, root_id, data):
            captured["ticket_data"] = data

        def redis_cluster_data_check_repair_flow(self):
            return None

    monkeypatch.setattr(dts_mod, "RedisClusterDataCheckRepairFlow", FakeFlow)
    monkeypatch.setattr(dts_mod, "generate_root_id", lambda: "root")

    svc = object.__new__(dts_mod.RedisDtsExecuteService)
    svc.log_info = lambda *args, **kwargs: None
    dts_job = SimpleNamespace(
        bill_id=1,
        src_cluster="src.test.db",
        dst_cluster="dst.test.db",
        key_white_regex="*",
        key_black_regex="",
    )
    global_data = {
        "uid": 1,
        "bk_biz_id": 100,
        "created_by": "tester",
        "data_check_repair_setting": {"type": dts_mod.DtsDataCheckType.DATA_CHECK_AND_REPAIR.value},
        "sync_disconnect_setting": {"type": "keep"},
        "redis_tools_pkg": SNAPSHOT_A,
    }
    svc._RedisDtsExecuteService__new_data_check_repair_job(global_data, dts_job)
    assert captured["ticket_data"]["redis_tools_pkg"] == SNAPSHOT_A


def test_spawn_online_switch_inherits_parent_snapshot(monkeypatch):
    from backend.flow.engine.bamboo.scene.redis import redis_cluster_data_copy as datacopy_mod
    from backend.flow.plugins.components.collections.redis import redis_dts as dts_mod

    captured = {}

    class FakeFlow:
        def __init__(self, root_id, data):
            captured["ticket_data"] = data

        def online_switch_flow(self):
            return None

    job_row = SimpleNamespace(
        online_switch_flow_id="",
        online_switch_type="user_confirm",
        bill_id=1,
        src_cluster="src.test.db",
        dst_cluster="dst.test.db",
        save=lambda **kwargs: None,
    )
    monkeypatch.setattr(datacopy_mod, "RedisClusterDataCopyFlow", FakeFlow)
    monkeypatch.setattr(dts_mod, "generate_root_id", lambda: "root")
    monkeypatch.setattr(dts_mod.TbTendisDTSJob, "objects", SimpleNamespace(get=lambda **kwargs: job_row))

    class FakeData:
        def __init__(self, inputs):
            self._inputs = inputs
            self.outputs = {}

        def get_one_of_inputs(self, key):
            return self._inputs.get(key)

    data = FakeData(
        {
            "kwargs": {
                "cluster": {
                    "src": {"cluster_addr": "src.test.db"},
                    "dst": {"cluster_addr": "dst.test.db"},
                },
                "set_trans_data_dataclass": "RedisDtsContext",
            },
            "global_data": {
                "uid": 1,
                "bk_biz_id": 100,
                "created_by": "tester",
                "redis_tools_pkg": SNAPSHOT_A,
            },
            "trans_data": SimpleNamespace(),
        }
    )

    svc = object.__new__(dts_mod.NewDtsOnlineSwitchJobAndWatchStatus)
    svc.log_info = lambda *args, **kwargs: None
    assert svc._execute(data, {}) is True
    assert captured["ticket_data"]["redis_tools_pkg"] == SNAPSHOT_A
