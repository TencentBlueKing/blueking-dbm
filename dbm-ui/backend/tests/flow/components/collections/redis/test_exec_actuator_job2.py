# -*- coding: utf-8 -*-
from backend.flow.plugins.components.collections.redis.exec_actuator_job2 import (
    SENSITIVE_PLACEHOLDER,
    redact_sensitive,
)


def test_redact_sensitive_masks_secrets():
    # 二次确认 maxmemory-policy 节点的 db_act_template，打印前必须脱敏
    db_act_template = {
        "action": "keystat_set_maxmemory_policy",
        "payload": {
            "redis_password": "plain-redis-pwd",
            "proxy_pwd": "plain-proxy-pwd",
            "db_cloud_token": "plain-token",
            "addrs": ["127.0.0.1:30000"],
            "addr_policies": {"127.0.0.1:30000": "noeviction"},
        },
    }
    redacted = redact_sensitive(db_act_template)

    assert redacted["payload"]["redis_password"] == SENSITIVE_PLACEHOLDER
    assert redacted["payload"]["proxy_pwd"] == SENSITIVE_PLACEHOLDER
    assert redacted["payload"]["db_cloud_token"] == SENSITIVE_PLACEHOLDER
    assert redacted["action"] == "keystat_set_maxmemory_policy"
    assert redacted["payload"]["addrs"] == ["127.0.0.1:30000"]
    assert redacted["payload"]["addr_policies"] == {"127.0.0.1:30000": "noeviction"}
    # 脱敏只作用于日志副本，实际下发的 payload 不受影响
    assert db_act_template["payload"]["redis_password"] == "plain-redis-pwd"


def test_redact_sensitive_nested_list():
    value = {"ins_list": [{"addr": "127.0.0.1:30000", "password": "p"}]}
    assert redact_sensitive(value) == {"ins_list": [{"addr": "127.0.0.1:30000", "password": SENSITIVE_PLACEHOLDER}]}


def test_redact_sensitive_keeps_non_dict_values():
    assert redact_sensitive("plain") == "plain"
    assert redact_sensitive(["a", 1, None]) == ["a", 1, None]
