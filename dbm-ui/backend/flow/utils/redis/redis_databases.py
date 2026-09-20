# -*- coding: utf-8 -*-
"""
Redis 主从 databases 数量约束.

范围以平台 dbconfig 的 databases.value_allowed 为准（如 [1,64]），
运营改平台配置即可扩/缩上限，不必再发版改硬编码.
查不到或解析失败时只保证正整数，不回退到历史写死的 16.
"""
import re
from typing import Optional, Tuple

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.flow.consts import ConfigTypeEnum

_RANGE_RE = re.compile(r"^[\[(]\s*(-?\d+)\s*,\s*(-?\d+)\s*[\])]\s*$")


def parse_databases_value_allowed(value_allowed: str) -> Optional[Tuple[int, int]]:
    """解析 dbconfig value_allowed 区间，如 [1,16] / [1,64]. 解析不了返回 None."""
    if not value_allowed:
        return None
    matched = _RANGE_RE.match(str(value_allowed).strip())
    if not matched:
        return None
    low, high = int(matched.group(1)), int(matched.group(2))
    if low > high:
        return None
    return low, high


def query_plat_databases_range(cluster_type: str, db_version: str) -> Optional[Tuple[int, int]]:
    """读平台 dbconf 的 databases.value_allowed. 失败返回 None."""
    if not cluster_type or not db_version:
        return None
    try:
        resp = DBConfigApi.list_conf_name(
            {
                "conf_file": db_version,
                "namespace": cluster_type,
                "conf_type": ConfigTypeEnum.DBConf.value,
            }
        )
    except Exception:  # noqa: BLE001
        return None

    conf_names = (resp or {}).get("conf_names") if isinstance(resp, dict) else None
    item = None
    if isinstance(conf_names, dict):
        item = conf_names.get("databases")
    elif isinstance(conf_names, list):
        item = next((row for row in conf_names if row.get("conf_name") == "databases"), None)
    if not isinstance(item, dict):
        return None
    return parse_databases_value_allowed(item.get("value_allowed") or "")


def validate_apply_databases(databases, cluster_type: str, db_version: str) -> int:
    """
    校验申请单的 databases.
    有平台范围则必须落在范围内；没有范围则只要是 >=1 的整数.
    """
    try:
        value = int(databases)
    except (TypeError, ValueError):
        raise ValueError(_("databases 必须是整数"))
    if value < 1:
        raise ValueError(_("databases 必须 >= 1，当前 {}").format(value))

    allowed = query_plat_databases_range(cluster_type, db_version)
    if allowed is None:
        return value
    low, high = allowed
    if value < low or value > high:
        raise ValueError(
            _("databases 必须在平台配置范围内 [{}, {}]（{}/{}），当前 {}").format(low, high, cluster_type, db_version, value)
        )
    return value
