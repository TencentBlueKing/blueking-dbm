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
from typing import Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service
from rest_framework import serializers

from backend import env
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.ticket.models import Flow


class MongoReplicaSetApplySummarySerializer(BaseFlowOutputSerializer):
    """副本集部署成功后的摘要信息定义，字段顺序即前端表格展示顺序，第一个字段同时作为表格行唯一标识。"""

    table_name = "mongodb_replicaset_info"
    table_display_name = _("副本集信息")
    table_primary_key = "domain_name"
    remark = _("密码等访问凭据请登录 DBM，在对应集群的「获取访问方式」中获取。")

    domain_name = serializers.CharField(help_text=_("域名"))
    region = serializers.CharField(help_text=_("地区"), allow_blank=True, default="")
    port = serializers.IntegerField(help_text=_("端口"))
    password_url = BaseFlowOutputSerializer.URLField(help_text=_("连接方式获取"), allow_blank=True, default="")


class MongoShardApplySummarySerializer(BaseFlowOutputSerializer):
    """分片集群部署成功后的摘要信息定义，字段顺序即前端表格展示顺序，第一个字段同时作为表格行唯一标识。"""

    table_name = "mongodb_shard_info"
    table_display_name = _("分片集群信息")
    table_primary_key = "domain_name"
    remark = _("密码等访问凭据请登录 DBM，在对应集群的「获取访问方式」中获取。")

    domain_name = serializers.CharField(help_text=_("域名"))
    region = serializers.CharField(help_text=_("地区"), allow_blank=True, default="")
    port = serializers.IntegerField(help_text=_("端口"))
    password_url = BaseFlowOutputSerializer.URLField(help_text=_("连接方式获取"), allow_blank=True, default="")


class MongoApplySummaryService(BaseService):
    """
    MongoDB 部署成功后，将集群关键信息(地区/域名/端口)写入 FlowSummary，供前端「执行摘要」展示。

    统一入参格式：kwargs = {"items": [{bk_biz_id, domain_name, region, port}, ...]}。
    单集群写入时 items 传一个元素即可，批量写入时 items 传多个元素。
    无论 items 包含几条记录，最终都只会往同一个流程(root_id)的 FlowSummary 里追加/合并同一张表的记录。
    """

    summary_serializer = None
    list_path = ""

    def _password_url(self, cluster) -> str:
        return "{}/{}/db-manage/mongodb/{}/list/{}?open=access_entry".format(
            env.BK_SAAS_HOST, cluster.bk_biz_id, self.list_path, cluster.id
        )

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
                "port": item["port"],
                "password_url": "",
            }

            try:
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=domain_name)
            except Cluster.DoesNotExist:
                self.log_error(_("写入集群信息摘要失败，集群[{}]不存在").format(domain_name))
                cluster = None

            if cluster:
                summary_data["password_url"] = self._password_url(cluster)

            summary_data_list.append(summary_data)
            self.log_info(_("集群[{}]信息已写入执行摘要").format(domain_name))

        # 该 flow 可能并非由正常单据触发，此时不存在对应的 Flow 记录，跳过即可，不应阻塞流程。
        if not Flow.objects.filter(flow_obj_id=root_id).exists():
            self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入执行摘要").format(root_id))
            return True

        FlowOutputHandler(self.summary_serializer).insert_data(root_id, summary_data_list)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoReplicaSetApplySummaryService(MongoApplySummaryService):
    summary_serializer = MongoReplicaSetApplySummarySerializer
    list_path = "replica-set"


class MongoShardApplySummaryService(MongoApplySummaryService):
    summary_serializer = MongoShardApplySummarySerializer
    list_path = "shared-cluster"


class MongoReplicaSetApplySummaryComponent(Component):
    name = __name__
    code = "mongodb_replicaset_apply_summary"
    bound_service = MongoReplicaSetApplySummaryService


class MongoShardApplySummaryComponent(Component):
    name = __name__
    code = "mongodb_shard_apply_summary"
    bound_service = MongoShardApplySummaryService


def add_mongodb_apply_summary_output_act(
    pipeline,
    bk_biz_id: int,
    domain_name: str,
    region: str,
    port: int,
    component_code: str,
):
    """
    MongoDB 部署成功后，将集群关键信息写入 FlowSummary，供前端「执行摘要」展示。
    该函数需要在「添加关系到 meta」之后调用，这样才能查询到集群信息。
    """
    add_mongodb_batch_apply_summary_output_act(
        pipeline,
        items=[
            {
                "bk_biz_id": bk_biz_id,
                "domain_name": domain_name,
                "region": region,
                "port": port,
            }
        ],
        component_code=component_code,
        act_name=_("{}-写入集群信息摘要").format(domain_name),
    )


def add_mongodb_batch_apply_summary_output_act(
    pipeline,
    items: List[Dict],
    component_code: str,
    act_name: Optional[str] = None,
):
    """
    批量将多个集群关键信息一次性写入 FlowSummary。
    适用于一个流程需要一次性部署多个副本集的场景，只会追加一个流程节点。
    """
    if not items:
        return
    pipeline.add_act(
        act_name=act_name or _("批量写入集群信息摘要"),
        act_component_code=component_code,
        kwargs={"items": items},
    )
