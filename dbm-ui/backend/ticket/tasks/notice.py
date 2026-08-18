# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _


def build_html_table_from_data(data_list):
    """
    将数据列表转换为HTML表格字符串。
    每个元素包含 'titles', 'values', 'table_name'。
    返回完整的HTML表格（含标题和表头）。
    """
    if not data_list:
        return _("<p>无数据</p>")

    html_parts = []
    remark_list = []
    for table_index, table_data in enumerate(data_list):
        titles = table_data.get("titles", [])
        values = table_data.get("values", [])
        table_name = table_data.get("table_display_name", _("表格 {}").format(table_index + 1))
        if table_data.get("remark"):
            remark_list.append(table_data["remark"].replace("\n", "<br/>"))
        if not titles or not values:
            continue

        # 构建 id -> display_name 映射，便于取值
        id_to_display = {item["id"]: item["display_name"] for item in titles}
        # 获取所有列ID（按 titles 顺序）
        column_ids = [item["id"] for item in titles]

        # 开始构建表格HTML
        table_html = f"<h3>{table_name}</h3>"
        table_html += (
            '<table border="1" cellpadding="5" cellspacing="0"'
            ' style="border-collapse:collapse; font-family:Arial, sans-serif;">'
        )
        # 表头
        table_html += "<thead><tr>"
        for col_id in column_ids:
            display = id_to_display.get(col_id, col_id)
            table_html += f'<th style="background-color:#f2f2f2; text-align:left;">{display}</th>'
        table_html += "</tr></thead>"
        # 表体
        table_html += "<tbody>"
        for row in values:
            table_html += "<tr>"
            for col_id in column_ids:
                value = row.get(col_id, "")
                # 处理 None 和空值
                if value is None:
                    value = ""
                table_html += f"<td>{value}</td>"
            table_html += "</tr>"
        table_html += "</tbody></table>"

        html_parts.append(table_html)
    html_parts.extend(remark_list)
    return "<br>".join(html_parts)


def get_mail_context(ticket_id, flow_summary, ticket_dir):
    context = _('<p>单据 <a href="{ticket_dir}">{ticket_id}</a> 已完成，交付信息如下：</p><br>').format(
        ticket_dir=ticket_dir, ticket_id=ticket_id
    )
    for summary in flow_summary:
        html_context = build_html_table_from_data(summary.summary)
        context += html_context

    return context


def get_rtx_context(ticket_id, flow_summary):
    context = _("单据 {ticket_id} 已完成。\n").format(ticket_id=ticket_id)
    count = 0
    cluster_info = []
    table_title = []
    remark_list = []
    for summary in flow_summary:
        data_list = summary.summary
        if not data_list:
            continue

        fields = [title["id"] for title in data_list[0]["titles"][:3]]
        table_title = [title["display_name"] for title in data_list[0]["titles"][:3]]
        for data in data_list:
            if data.get("remark"):
                remark_list.append(data["remark"])
            for value in data["values"]:
                cluster_info.append([str(value.get(field, "")) for field in fields])
        count += len(summary.summary)

    context += _("集群共 {count} 个：\n").format(count=count)
    context += " ".join(table_title) + "\n"
    for info in cluster_info:
        context += " ".join(info) + "\n"
    if remark_list:
        context += "\n".join(remark_list)
    return context
