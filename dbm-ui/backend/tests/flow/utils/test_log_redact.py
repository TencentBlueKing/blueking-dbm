# -*- coding: utf-8 -*-
from backend.flow.utils.log_redact import redact_log_secrets

TEST_SECRET = "xxxx"


def test_redact_mongo_uri_cli_and_named_passwords():
    command = " ".join(
        (
            "mongosh",
            "--host",
            "h",
            "-u",
            "dba",
            "-p",
            "'{}'".format(TEST_SECRET),
        )
    )
    raw = " ".join(
        (
            "{}://{}:{}@{}/admin".format("mongodb", "dba", TEST_SECRET, "127.0.0.1:27017"),
            command,
            "admin.createUser({{user:'u',pwd:'{}',roles:[]}})".format(TEST_SECRET),
            "{{'adminPassword': '{}'}}".format(TEST_SECRET),
        )
    )
    out = redact_log_secrets(raw)
    assert TEST_SECRET not in out
    assert "{}://{}:{}@{}/admin".format("mongodb", "dba", "***", "127.0.0.1:27017") in out
    assert "-p ***" in out
    assert "pwd:'***'" in out
    assert "'adminPassword': '***'" in out


def test_redact_leaves_non_secret_text():
    assert redact_log_secrets("collector started") == "collector started"
    assert redact_log_secrets(None) is None


def test_redact_cli_password_variants():
    password_args = (
        "-p{}".format(TEST_SECRET),
        "-p'{}'".format(TEST_SECRET),
        "--password={}".format(TEST_SECRET),
    )
    commands = (
        "mysql -uroot {} -h h".format(password_args[0]),
        "mongo -u dba {}".format(password_args[1]),
        "x {}".format(password_args[2]),
    )
    out = redact_log_secrets("; ".join(commands))
    assert TEST_SECRET not in out


def test_redact_keeps_mkdir_and_port_flags():
    raw = "mkdir -p /data/dbbak/recover && mysql -h 127.0.0.1 -P 3306"
    assert redact_log_secrets(raw) == raw
