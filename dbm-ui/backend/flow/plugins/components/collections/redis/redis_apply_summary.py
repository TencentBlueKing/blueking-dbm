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
import logging
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service
from rest_framework import serializers

from backend import env
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.ticket.models import Flow

logger = logging.getLogger("flow")


class RedisApplySummarySerializer(BaseFlowOutputSerializer):
    """redis集群部署成功后的摘要信息定义，字段顺序即前端表格展示顺序，第一个字段同时作为表格行唯一标识"""

    table_name = "redis_cluster_info"
    table_display_name = _("集群信息")
    table_primary_key = "domain_name"
    remark = _("密码等访问凭据请登录 DBM，在对应集群的「获取连接信息」中获取。\n Redis开发最佳实践：https://iwiki.woa.com/p/4013643362")

    domain_name = serializers.CharField(help_text=_("域名"))
    region = serializers.CharField(help_text=_("地区"), allow_blank=True, default="")
    proxy_port = serializers.IntegerField(help_text=_("端口"))
    clb_ip = serializers.CharField(help_text=_("CLB IP"), allow_blank=True, default="")
    clb_domain = serializers.CharField(help_text=_("CLB域名"), allow_blank=True, default="")
    polaris_name = serializers.CharField(help_text=_("北极星服务名称"), allow_blank=True, default="")
    polaris_l5 = serializers.CharField(help_text=_("北极星L5"), allow_blank=True, default="")
    password_url = BaseFlowOutputSerializer.URLField(help_text=_("密码获取"), allow_blank=True, default="")


class RedisApplySummaryService(BaseService):
    """
    redis集群部署成功后，将集群关键信息(地区/域名/端口/CLB/北极星)写入FlowSummary，
    供前端"执行摘要"展示。该节点需要在集群元数据以及CLB/北极星创建节点之后执行，才能查询到完整信息。

    统一入参格式：kwargs = {"items": [{bk_biz_id, domain_name, region, proxy_port, apply_clb, apply_polaris}, ...]}，
    单集群写入时items传一个元素即可(见add_summary_output_act)，批量写入时items传多个元素(见add_batch_summary_output_act)。
    无论items包含几条记录，最终都只会往同一个流程(root_id)的FlowSummary里追加/合并同一张表(table_name)的记录，
    不会产生多条FlowSummary记录。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = self.runtime_attrs.get("root_pipeline_id")

        items = kwargs["items"]

        summary_data_list = []
        for item in items:
            bk_biz_id = item["bk_biz_id"]
            domain_name = item["domain_name"]

            summary_data = {
                "region": item.get("region") or "",
                "domain_name": domain_name,
                "proxy_port": item["proxy_port"],
                "clb_ip": "",
                "clb_domain": "",
                "polaris_name": "",
                "polaris_l5": "",
                "password_url": "",
            }

            try:
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=domain_name)
            except Cluster.DoesNotExist:
                self.log_error(_("写入集群信息摘要失败，集群[{}]不存在").format(domain_name))
                cluster = None

            if cluster:
                # 构造密码获取跳转链接
                summary_data["password_url"] = "{}/{}/db-manage/redis/cluster/list/{}?open=access_entry".format(
                    env.BK_SAAS_HOST, cluster.bk_biz_id, cluster.id
                )
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

            summary_data_list.append(summary_data)
            self.log_info(_("集群[{}]信息已写入执行摘要").format(domain_name))

        # 该flow可能并非由正常单据(ticket)触发，例如DTS内部临时创建目标集群时会用临时root_id直接跑pipeline，
        # 此时不存在对应的Flow记录(ticket.models.Flow)，无法写入FlowSummary，属于预期情况，跳过即可，不应阻塞流程。
        if not Flow.objects.filter(flow_obj_id=root_id).exists():
            self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入执行摘要").format(root_id))
            return True

        # 一次性写入(FlowOutputHandler内部按table_name合并到同一张表的values数组里，不会产生多条FlowSummary记录)
        FlowOutputHandler(RedisApplySummarySerializer).insert_data(root_id, summary_data_list)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisApplySummaryComponent(Component):
    name = __name__
    code = "redis_apply_summary"
    bound_service = RedisApplySummaryService


class RedisInsApplySummarySerializer(BaseFlowOutputSerializer):
    """redis主从实例部署成功后的摘要信息定义，字段顺序即前端表格展示顺序，第一个字段同时作为表格行唯一标识。
    主从实例不涉及CLB/北极星，因此不包含相关字段。"""

    table_name = "redis_ins_info"
    table_display_name = _("主从实例信息")
    table_primary_key = "domain_name"

    domain_name = serializers.CharField(help_text=_("域名"))
    region = serializers.CharField(help_text=_("地区"), allow_blank=True, default="")
    proxy_port = serializers.IntegerField(help_text=_("端口"))
    password_url = BaseFlowOutputSerializer.URLField(help_text=_("密码获取"), allow_blank=True, default="")


class RedisInsApplySummaryService(BaseService):
    """
    redis主从实例部署成功后，将实例关键信息(地区/域名/端口)写入FlowSummary，供前端"执行摘要"展示。
    主从实例无CLB/北极星概念，摘要不包含相关字段。

    统一入参格式：kwargs = {"items": [{bk_biz_id, domain_name, region, proxy_port}, ...]}，
    单实例写入时items传一个元素即可，批量写入时items传多个元素。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = self.runtime_attrs.get("root_pipeline_id")

        items = kwargs["items"]

        summary_data_list = []
        for item in items:
            bk_biz_id = item["bk_biz_id"]
            domain_name = item["domain_name"]

            summary_data = {
                "region": item.get("region") or "",
                "domain_name": domain_name,
                "proxy_port": item["proxy_port"],
                "password_url": "",
            }

            try:
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=domain_name)
            except Cluster.DoesNotExist:
                self.log_error(_("写入主从实例信息摘要失败，集群[{}]不存在").format(domain_name))
                cluster = None

            if cluster:
                # 构造主从实例密码获取跳转链接
                summary_data["password_url"] = "{}/{}/db-manage/redis/cluster-ha/list/{}?open=access_entry".format(
                    env.BK_SAAS_HOST, cluster.bk_biz_id, cluster.id
                )

            summary_data_list.append(summary_data)
            self.log_info(_("主从实例[{}]信息已写入执行摘要").format(item["domain_name"]))

        # 该flow可能并非由正常单据(ticket)触发，跳过写入
        if not Flow.objects.filter(flow_obj_id=root_id).exists():
            self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入执行摘要").format(root_id))
            return True

        FlowOutputHandler(RedisInsApplySummarySerializer).insert_data(root_id, summary_data_list)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisInsApplySummaryComponent(Component):
    name = __name__
    code = "redis_ins_apply_summary"
    bound_service = RedisInsApplySummaryService
