# -*- coding: utf-8 -*-
from backend.flow.plugins.components.collections.redis.redis_keystat_restore_policy import (
    get_maxmemory_policies,
    need_keystat_maxmemory_policy_steps,
    parse_confxx_get_value,
    policies_equal,
    redis_major_from_version,
    restore_maxmemory_policies,
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


def test_policies_equal():
    assert policies_equal("noeviction", "NoEviction")
    assert not policies_equal("noeviction", "volatile-lru")


def test_get_maxmemory_policies():
    def redis_rpc(params):
        return [
            {"address": "127.0.0.1:30000", "result": "maxmemory-policy\nnoeviction\n", "error_msg": ""},
            {"address": "127.0.0.2:30000", "result": "", "error_msg": "timeout"},
        ]

    policies, errors = get_maxmemory_policies(
        addrs=["127.0.0.1:30000", "127.0.0.2:30000"], password="x", bk_cloud_id=0, redis_rpc=redis_rpc
    )
    assert policies == {"127.0.0.1:30000": "noeviction"}
    assert len(errors) == 1
    assert "timeout" in errors[0]


def test_restore_skips_when_already_expected():
    calls = []

    def redis_rpc(params):
        calls.append(params["command"])
        return [{"address": "127.0.0.1:30000", "result": "maxmemory-policy\nnoeviction\n", "error_msg": ""}]

    errors = restore_maxmemory_policies(
        addr_policies={"127.0.0.1:30000": "noeviction"},
        password="x",
        bk_cloud_id=0,
        redis_rpc=redis_rpc,
    )
    assert errors == []
    assert calls == ["confxx get maxmemory-policy"]


def test_restore_sets_when_policy_differs():
    calls = []

    def redis_rpc(params):
        calls.append(params["command"])
        if params["command"].startswith("confxx get"):
            return [{"address": "127.0.0.1:30000", "result": "maxmemory-policy\nvolatile-lru\n", "error_msg": ""}]
        return [{"address": "127.0.0.1:30000", "result": "OK", "error_msg": ""}]

    errors = restore_maxmemory_policies(
        addr_policies={"127.0.0.1:30000": "noeviction"},
        password="x",
        bk_cloud_id=0,
        redis_rpc=redis_rpc,
    )
    assert errors == []
    assert calls == ["confxx get maxmemory-policy", "confxx set maxmemory-policy noeviction"]


def test_restore_collects_set_error():
    def redis_rpc(params):
        if params["command"].startswith("confxx get"):
            return [{"address": "127.0.0.1:30000", "result": "maxmemory-policy\nvolatile-lru\n", "error_msg": ""}]
        return [{"address": "127.0.0.1:30000", "result": "", "error_msg": "timeout"}]

    errors = restore_maxmemory_policies(
        addr_policies={"127.0.0.1:30000": "noeviction"},
        password="x",
        bk_cloud_id=0,
        redis_rpc=redis_rpc,
    )
    assert len(errors) == 1
    assert "timeout" in errors[0]
