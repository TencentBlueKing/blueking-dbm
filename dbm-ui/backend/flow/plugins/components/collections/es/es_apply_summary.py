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
from pipeline.component_framework.component import Component
from rest_framework import serializers

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import ClusterEntry
from backend.flow.plugins.components.collections.common.bigdata_apply_summary import BigDataApplySummaryService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class EsApplySummarySerializer(BaseFlowOutputSerializer):
    """ES集群部署成功后的摘要信息定义，字段顺序即前端表格展示顺序，第一个字段同时作为表格行唯一标识"""

    table_name = "es_cluster_info"
    table_display_name = _("ES集群信息")
    table_primary_key = "domain_name"
    remark = _("访问凭据请登录 DBM，在对应集群详情页的「获取访问方式」中查看。")

    domain_name = serializers.CharField(help_text=_("域名"))
    region = serializers.CharField(help_text=_("地区"), allow_blank=True, default="")
    version = serializers.CharField(help_text=_("版本"), allow_blank=True, default="")
    http_port = serializers.IntegerField(help_text=_("HTTP端口"))
    clb_ip = serializers.CharField(help_text=_("CLB IP"), allow_blank=True, default="")
    clb_domain = serializers.CharField(help_text=_("CLB域名"), allow_blank=True, default="")
    polaris_name = serializers.CharField(help_text=_("北极星服务名称"), allow_blank=True, default="")
    polaris_l5 = serializers.CharField(help_text=_("北极星L5"), allow_blank=True, default="")
    entry_remark = serializers.CharField(help_text=_("备注"), allow_blank=True, default="")
    access_entry_url = BaseFlowOutputSerializer.URLField(help_text=_("获取访问方式"), allow_blank=True, default="")


class EsApplySummaryService(BigDataApplySummaryService):
    """
    ES集群部署成功后，将集群关键信息(地区/域名/端口/CLB/北极星)写入FlowSummary，
    供前端"执行摘要"展示。该节点需要在集群元数据以及CLB/北极星创建节点之后执行，才能查询到完整信息。

    统一入参格式：kwargs = {"items": [{bk_biz_id, domain_name, region, version, http_port,
    apply_clb, apply_polaris}, ...]}，单集群写入时items传一个元素即可(见add_es_apply_summary_output_act)。
    """

    summary_serializer = EsApplySummarySerializer
    detail_path = "elastic-search"
    port_field = "http_port"

    def build_summary_data(self, item: dict) -> dict:
        summary_data = super().build_summary_data(item)
        summary_data.update({"clb_ip": "", "clb_domain": "", "polaris_name": "", "polaris_l5": "", "entry_remark": ""})
        return summary_data

    def build_extra(self, cluster, item: dict, summary_data: dict) -> None:
        domain_name = item["domain_name"]
        missing_remarks = []

        if item.get("apply_clb"):
            clb_entry = ClusterEntry.objects.filter(
                cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value
            ).first()
            if clb_entry:
                detail = clb_entry.detail
                summary_data["clb_ip"] = detail.get("clb_ip", "") or ""
                summary_data["clb_domain"] = detail.get("clb_domain", "") or ""
            else:
                self.log_error(_("集群[{}]未查询到CLB信息").format(domain_name))
                missing_remarks.append(_("CLB信息未查询到"))

        if item.get("apply_polaris"):
            polaris_entry = ClusterEntry.objects.filter(
                cluster=cluster, cluster_entry_type=ClusterEntryType.POLARIS.value
            ).first()
            if polaris_entry:
                detail = polaris_entry.detail
                summary_data["polaris_name"] = detail.get("polaris_name", "") or ""
                summary_data["polaris_l5"] = detail.get("polaris_l5", "") or ""
            else:
                self.log_error(_("集群[{}]未查询到北极星信息").format(domain_name))
                missing_remarks.append(_("北极星信息未查询到"))

        if missing_remarks:
            summary_data["entry_remark"] = "；".join(missing_remarks)


class EsApplySummaryComponent(Component):
    name = __name__
    code = "es_apply_summary"
    bound_service = EsApplySummaryService


def add_es_apply_summary_output_act(
    es_pipeline,
    bk_biz_id: int,
    domain_name: str,
    region: str,
    version: str,
    http_port: int,
    apply_clb: bool = False,
    apply_polaris: bool = False,
):
    """
    ES集群部署成功后，将集群关键信息(地区/域名/端口/CLB/北极星)写入FlowSummary，供前端"执行摘要"展示。
    该函数需要在"添加到DBMeta"以及CLB/北极星创建子流程(如果有)之后调用，这样才能查询到完整的CLB/北极星信息。
    @param es_pipeline: 当前ES部署流程的Builder实例，节点会直接追加到该流程中
    @param bk_biz_id: 业务id
    @param domain_name: 集群主域名
    @param region: 地区(城市代码)
    @param version: 集群版本号
    @param http_port: 集群端口
    @param apply_clb: 单据是否创建了clb
    @param apply_polaris: 单据是否创建了北极星
    """
    item = {
        "bk_biz_id": bk_biz_id,
        "domain_name": domain_name,
        "region": region,
        "version": version,
        "http_port": http_port,
        "apply_clb": apply_clb,
        "apply_polaris": apply_polaris,
    }
    es_pipeline.add_act(
        act_name=_("{}-写入集群信息摘要").format(domain_name),
        act_component_code=EsApplySummaryComponent.code,
        kwargs={"items": [item]},
    )
