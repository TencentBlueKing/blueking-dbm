# -*- coding: utf-8 -*-
"""Mongo autofix ticket remark helpers."""

from django.utils.translation import gettext as _


def autofix_core_tag(core_id) -> str:
    """备注片段：-自愈#{id}；无效 id 返回空串。"""
    try:
        cid = int(core_id or 0)
    except (TypeError, ValueError):
        return ""
    return f"{_('-自愈#')}{cid}" if cid > 0 else ""
