# -*- coding: utf-8 -*-
import pytest

from backend.flow.utils.redis.redis_databases import (
    parse_databases_value_allowed,
    query_plat_databases_range,
    validate_apply_databases,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("[1,16]", (1, 16)),
        ("[1,64]", (1, 64)),
        ("[2, 16]", (2, 16)),
        ("(1,64]", (1, 64)),
        ("1|2|16", None),
        ("", None),
        (None, None),
        ("[10,1]", None),
    ],
)
def test_parse_databases_value_allowed(raw, expected):
    assert parse_databases_value_allowed(raw) == expected


def test_validate_without_plat_range_allows_64(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.query_plat_databases_range",
        lambda *args, **kwargs: None,
    )
    assert validate_apply_databases(64, "RedisInstance", "Redis-74") == 64


def test_validate_rejects_out_of_plat_range(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.query_plat_databases_range",
        lambda *args, **kwargs: (1, 16),
    )
    with pytest.raises(ValueError, match=r"\[1, 16\]"):
        validate_apply_databases(64, "RedisInstance", "Redis-74")


def test_validate_accepts_in_plat_range(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.query_plat_databases_range",
        lambda *args, **kwargs: (1, 64),
    )
    assert validate_apply_databases(64, "RedisInstance", "Redis-74") == 64


def test_query_plat_databases_range(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.DBConfigApi.list_conf_name",
        lambda params: {"conf_names": {"databases": {"value_allowed": "[1,64]"}}},
    )
    assert query_plat_databases_range("RedisInstance", "Redis-74") == (1, 64)


def test_query_plat_databases_range_list_format(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.DBConfigApi.list_conf_name",
        lambda params: {"conf_names": [{"conf_name": "databases", "value_allowed": "[1,64]"}]},
    )
    assert query_plat_databases_range("RedisInstance", "Redis-74") == (1, 64)


def test_query_plat_databases_range_api_error(monkeypatch):
    def _boom(params):
        raise RuntimeError("dbconfig down")

    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.DBConfigApi.list_conf_name",
        _boom,
    )
    assert query_plat_databases_range("RedisInstance", "Redis-74") is None
