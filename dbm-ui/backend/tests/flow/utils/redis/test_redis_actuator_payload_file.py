# -*- coding: utf-8 -*-
from jinja2.sandbox import SandboxedEnvironment as Environment

from backend.flow.utils.redis.redis_script_template import (
    REDIS_PAYLOAD_ARGV_SOFT_LIMIT,
    redis_actuator_should_use_payload_file,
    select_redis_actuator_template,
)


def _render(template: str, **ctx) -> str:
    return Environment().from_string(template).render(ctx)


def _dbactuator_cmd(script: str) -> str:
    """The execve line, not the heredoc body."""
    for line in script.replace("\\\n", " ").splitlines():
        stripped = line.strip()
        if "dbactuator_redis" in stripped and "--atom-job-list" in stripped:
            return stripped
    raise AssertionError(f"no dbactuator cmd in script:\n{script}")


def test_payload_file_gate_version_update_even_if_short():
    assert redis_actuator_should_use_payload_file("redis_version_update", "short")
    assert not redis_actuator_should_use_payload_file("proxy_version_upgrade", "x")


def test_payload_file_gate_keeps_small_non_upgrade_on_argv():
    assert not redis_actuator_should_use_payload_file("redis_backup", "a" * 16)
    assert not redis_actuator_should_use_payload_file("sysinit", "")


def test_payload_file_gate_long_payload_any_action():
    assert redis_actuator_should_use_payload_file("redis_backup", "p" * REDIS_PAYLOAD_ARGV_SOFT_LIMIT)


def test_select_template_version_update_uses_payload_file():
    tpl = select_redis_actuator_template(True)
    script = _render(
        tpl,
        data_dir="/data",
        uid="1",
        root_id="r",
        node_id="n1",
        version_id="v1",
        payload="ZXlK",
        action="redis_version_update",
    )
    cmd = _dbactuator_cmd(script)
    assert "--payload_file=" in cmd
    assert "--payload " not in cmd
    assert "B64EOF" in script
    assert "ZXlK" in script


def test_select_template_short_backup_keeps_payload_argv():
    tpl = select_redis_actuator_template(False)
    script = _render(
        tpl,
        data_dir="/data",
        uid="1",
        root_id="r",
        node_id="n1",
        version_id="v1",
        payload="ZXlK",
        action="redis_backup",
    )
    cmd = _dbactuator_cmd(script)
    assert "--payload ZXlK" in cmd
    assert "--payload_file" not in cmd
