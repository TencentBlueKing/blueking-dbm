# -*- coding: utf-8 -*-
"""
接入层灾难恢复：路由预览（只读摘要 + markdown 表格输出到节点日志，结构化 JSON 写入 FlowSummary）。
"""
import logging
from typing import Any, Dict, List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from rest_framework import serializers

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler

logger = logging.getLogger("flow")


class SpiderLayerDisasterRecoverRoutePreviewSerializer(BaseFlowOutputSerializer):
    table_name = "spider_layer_dr_route_preview"
    table_display_name = _("接入层灾难恢复路由预览")
    table_primary_key = "cluster_id"
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    route_preview = serializers.JSONField(help_text=_("路由预览 JSON（含 master_changes/slave_changes/shards 等结构化字段）"))


class SpiderLayerDisasterRecoverRoutePreviewService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        preview = kwargs.get("route_preview") or {}

        # 节点日志输出 markdown 表格（人类可读）
        self.log_info(_render_markdown(preview))

        # 结构化 JSON 写入 FlowSummary，供前端表格化展示
        try:
            FlowOutputHandler(SpiderLayerDisasterRecoverRoutePreviewSerializer).insert_data(
                global_data["job_root_id"],
                {"cluster_id": preview.get("cluster_id", 0), "route_preview": preview},
            )
        except Exception as exc:
            self.log_warning(_("写入路由预览摘要失败，已仅记录日志: {}").format(exc))
        return True


class SpiderLayerDisasterRecoverRoutePreviewComponent(Component):
    name = _("Spider 接入层灾难恢复路由预览")
    code = "spider_layer_disaster_recover_route_preview"
    bound_service = SpiderLayerDisasterRecoverRoutePreviewService


# ─────────────────────────────────────────────────────────────────────────────
# Markdown 渲染辅助（无副作用，可单测）
# ─────────────────────────────────────────────────────────────────────────────
SEP_LINE = "=" * 74


def _render_markdown(preview: Dict[str, Any]) -> str:
    """
    把结构化 preview 渲染为多段 markdown 表格字符串，输出到 flow 节点日志。
    """
    lines: List[str] = [
        "",
        SEP_LINE,
        _("路由预览（接入层灾难恢复）"),
        SEP_LINE,
        "",
    ]
    lines.extend(_render_cluster_info_section(preview))
    lines.append("")
    lines.extend(
        _render_role_changes_section(_("Spider Master 变更"), preview.get("master_changes") or [], with_ctl=True)
    )
    lines.append("")
    lines.extend(
        _render_role_changes_section(_("Spider Slave 变更"), preview.get("slave_changes") or [], with_ctl=False)
    )
    lines.append("")
    lines.extend(_render_shards_section(preview.get("shards") or []))
    return "\n".join(lines)


def _render_cluster_info_section(preview: Dict[str, Any]) -> List[str]:
    rows = [
        (_("集群 ID"), preview.get("cluster_id", "")),
        (_("主域名"), preview.get("immute_domain", "")),
        (_("Spider 端口"), preview.get("resolved_spider_port", "")),
        (_("TDBCTL 端口"), preview.get("resolved_ctl_port", "")),
        (_("恢复 master"), _("是") if preview.get("recover_master") else _("否")),
        (_("恢复 slave"), _("是") if preview.get("recover_slave") else _("否")),
    ]
    return [
        "## " + _("集群信息"),
        "",
        _render_table(headers=[_("字段"), _("值")], rows=[[str(k), str(v)] for k, v in rows]),
    ]


def _render_role_changes_section(title: str, changes: List[Dict[str, Any]], with_ctl: bool) -> List[str]:
    if not changes:
        return ["## " + title, "", _("（本次不涉及该角色变更）")]
    if with_ctl:
        headers = [_("动作"), "IP", _("Spider 端口"), _("中控端口"), "bk_host_id"]
        rows = [
            [
                str(c.get("action", "")),
                str(c.get("ip", "")),
                str(c.get("spider_port", "")),
                str(c.get("ctl_port", "")),
                str(c.get("bk_host_id", "")),
            ]
            for c in changes
        ]
    else:
        headers = [_("动作"), "IP", _("Spider 端口"), "bk_host_id"]
        rows = [
            [
                str(c.get("action", "")),
                str(c.get("ip", "")),
                str(c.get("spider_port", "")),
                str(c.get("bk_host_id", "")),
            ]
            for c in changes
        ]
    return ["## " + title, "", _render_table(headers=headers, rows=rows)]


def _render_shards_section(shards: List[Dict[str, Any]]) -> List[str]:
    title = _("Remote 分片（仅供参考，本次不变更）")
    if not shards:
        return ["## " + title, "", _("（无分片元数据）")]
    headers = [_("分片 ID"), _("Remote Master"), _("Remote Slave")]
    rows = [
        [str(s.get("shard_id", "")), str(s.get("remote_master", "")), str(s.get("remote_slave", ""))] for s in shards
    ]
    return ["## " + title, "", _render_table(headers=headers, rows=rows)]


def _render_table(headers: List[str], rows: List[List[str]]) -> str:
    """
    渲染一个对齐的 markdown 表格字符串：列宽 = max(列内单元格的字符串长度)。
    简单按 len(str) 对齐（中文字符渲染宽度依赖终端，markdown 解析时不影响结构）。
    """
    if not rows:
        return ""
    cols = len(headers)
    widths = [len(headers[i]) for i in range(cols)]
    for r in rows:
        for i in range(cols):
            cell = r[i] if i < len(r) else ""
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: List[str]) -> str:
        padded = [(cells[i] if i < len(cells) else "").ljust(widths[i]) for i in range(cols)]
        return "| " + " | ".join(padded) + " |"

    sep_cells = ["-" * widths[i] for i in range(cols)]
    out = [fmt_row(headers), fmt_row(sep_cells)]
    for r in rows:
        out.append(fmt_row(r))
    return "\n".join(out)
