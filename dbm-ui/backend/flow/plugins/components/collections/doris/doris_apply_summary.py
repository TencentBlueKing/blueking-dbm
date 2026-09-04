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

from backend.flow.plugins.components.collections.common.bigdata_apply_summary import BigDataApplySummaryService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer


class DorisApplySummarySerializer(BaseFlowOutputSerializer):
    """Doris集群部署成功后的摘要信息定义，字段顺序即前端表格展示顺序，第一个字段同时作为表格行唯一标识"""

    table_name = "doris_cluster_info"
    table_display_name = _("Doris集群信息")
    table_primary_key = "domain_name"
    remark = _("访问凭据请登录 DBM，在对应集群详情页的「获取访问方式」中查看。")

    domain_name = serializers.CharField(help_text=_("域名"))
    region = serializers.CharField(help_text=_("地区"), allow_blank=True, default="")
    version = serializers.CharField(help_text=_("版本"), allow_blank=True, default="")
    query_port = serializers.IntegerField(help_text=_("查询端口"))
    access_entry_url = BaseFlowOutputSerializer.URLField(help_text=_("获取访问方式"), allow_blank=True, default="")


class DorisApplySummaryService(BigDataApplySummaryService):
    """
    Doris集群部署成功后，将集群关键信息(地区/域名/端口)写入FlowSummary，供前端"执行摘要"展示。

    统一入参格式：kwargs = {"items": [{bk_biz_id, domain_name, region, version, query_port}, ...]}，
    单集群写入时items传一个元素即可(见add_doris_apply_summary_output_act)。
    """

    summary_serializer = DorisApplySummarySerializer
    detail_path = "doris"
    port_field = "query_port"


class DorisApplySummaryComponent(Component):
    name = __name__
    code = "doris_apply_summary"
    bound_service = DorisApplySummaryService


def add_doris_apply_summary_output_act(
    doris_pipeline,
    bk_biz_id: int,
    domain_name: str,
    region: str,
    version: str,
    query_port: int,
):
    """
    Doris集群部署成功后，将集群关键信息(地区/域名/端口)写入FlowSummary，供前端"执行摘要"展示。
    该函数需要在"添加到DBMeta"以及冷存储资源关联子流程(如果有)之后调用。
    @param doris_pipeline: 当前Doris部署流程的Builder实例，节点会直接追加到该流程中
    @param bk_biz_id: 业务id
    @param domain_name: 集群主域名
    @param region: 地区(城市代码)
    @param version: 集群版本号
    @param query_port: 客户端查询使用的端口
    """
    item = {
        "bk_biz_id": bk_biz_id,
        "domain_name": domain_name,
        "region": region,
        "version": version,
        "query_port": query_port,
    }
    doris_pipeline.add_act(
        act_name=_("{}-写入集群信息摘要").format(domain_name),
        act_component_code=DorisApplySummaryComponent.code,
        kwargs={"items": [item]},
    )
