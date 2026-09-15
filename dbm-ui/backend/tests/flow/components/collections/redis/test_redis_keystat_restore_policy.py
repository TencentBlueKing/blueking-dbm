# -*- coding: utf-8 -*-
from backend.flow.plugins.components.collections.redis.redis_keystat_restore_policy import (
    get_maxmemory_policies,
    inject_keystat_restore_policies,
    need_keystat_maxmemory_policy_steps,
    parse_confxx_get_value,
    redis_major_from_version,
)


def test_redis_major_from_version():
    assert redis_major_from_version("Redis-2.8") == 2
    assert redis_major_from_version("Redis-5") == 5
    assert redis_major_from_version("Redis-6") == 6
    assert redis_major_from_version("Redis-6.2") == 6
    assert redis_major_from_version("Valkey-8") == 8
    assert redis_major_from_version("") == 0


def test_need_keystat_maxmemory_policy_steps():
    assert not need_keystat_maxmemory_policy_steps("Redis-2.8")
    assert not need_keystat_maxmemory_policy_steps("Redis-5")
    assert need_keystat_maxmemory_policy_steps("Redis-6")
    assert need_keystat_maxmemory_policy_steps("Redis-7")
    assert need_keystat_maxmemory_policy_steps("Valkey-8")


def test_parse_confxx_get_value():
    assert parse_confxx_get_value("maxmemory-policy\nnoeviction\n", "maxmemory-policy") == "noeviction"
    assert parse_confxx_get_value("MAXMEMORY-POLICY\r\nvolatile-lru\r\n", "maxmemory-policy") == "volatile-lru"
    assert parse_confxx_get_value("", "maxmemory-policy") == ""
    # 多一行 banner/序号时不猜第二行；能精确匹配 key 则取下一行
    assert parse_confxx_get_value("1)\nmaxmemory-policy\nnoeviction\n", "maxmemory-policy") == "noeviction"
    assert parse_confxx_get_value("ERR unknown\nmaxmemory-policy\n", "maxmemory-policy") == ""
    assert parse_confxx_get_value("banner\nnot-a-policy\n", "maxmemory-policy") == ""


def test_get_maxmemory_policies():
    calls = []

    def redis_rpc(params):
        calls.append(params["command"])
        cmd = params["command"]
        if cmd.startswith("confxx"):
            return [
                {"address": "127.0.0.1:30000", "result": "maxmemory-policy\nnoeviction\n", "error_msg": ""},
                {"address": "127.0.0.2:30000", "result": "", "error_msg": "ERR unknown command `confxx`"},
            ]
        return [
            {"address": "127.0.0.2:30000", "result": "maxmemory-policy\nvolatile-lru\n", "error_msg": ""},
        ]

    policies, errors = get_maxmemory_policies(
        addrs=["127.0.0.1:30000", "127.0.0.2:30000"], password="x", bk_cloud_id=0, redis_rpc=redis_rpc
    )
    assert policies == {"127.0.0.1:30000": "noeviction", "127.0.0.2:30000": "volatile-lru"}
    assert errors == []
    assert calls == ["confxx get maxmemory-policy", "CONFIG GET maxmemory-policy"]


def test_get_maxmemory_policies_timeout_no_fallback():
    calls = []

    def redis_rpc(params):
        calls.append(params["command"])
        return [
            {"address": "127.0.0.1:30000", "result": "", "error_msg": "timeout"},
        ]

    policies, errors = get_maxmemory_policies(
        addrs=["127.0.0.1:30000"], password="x", bk_cloud_id=0, redis_rpc=redis_rpc
    )
    assert policies == {}
    assert len(errors) == 1
    assert "timeout" in errors[0]
    assert calls == ["confxx get maxmemory-policy"]


def test_is_unknown_command_err():
    from backend.flow.plugins.components.collections.redis.redis_keystat_restore_policy import is_unknown_command_err

    assert is_unknown_command_err("ERR unknown command `confxx`")
    assert is_unknown_command_err("ERR Unknown Command 'confxx'")
    assert not is_unknown_command_err("timeout")
    assert not is_unknown_command_err("")


def test_inject_keystat_restore_policies():
    class Ctx:
        keystat_origin_maxmemory_policies = {
            "127.0.0.1:30000": "noeviction",
            "127.0.0.1:30001": "volatile-lru",
        }

    tpl = {"payload": {"addrs": ["127.0.0.1:30000"], "redis_password": "x", "addr_policies": {}}}
    out = inject_keystat_restore_policies(tpl, Ctx())
    assert out["payload"]["addr_policies"] == {"127.0.0.1:30000": "noeviction"}


def test_inject_keystat_restore_policies_missing_raises():
    class Ctx:
        keystat_origin_maxmemory_policies = {}

    try:
        inject_keystat_restore_policies({"payload": {"addrs": ["127.0.0.1:30000"]}}, Ctx())
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "no recorded" in str(exc)
