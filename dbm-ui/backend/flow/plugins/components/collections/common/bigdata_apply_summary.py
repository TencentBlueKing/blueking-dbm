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
from typing import List

from django.utils.translation import gettext as _
from pipeline.core.flow.activity import Service

from backend import env
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.ticket.models import Flow


class BigDataApplySummaryService(BaseService):
    """
    大数据组件部署成功后，将集群关键信息写入FlowSummary，供前端"执行摘要"展示的公共基类。
    该节点需要在集群元数据创建之后执行，才能查询到集群信息。

    子类需声明:
    - summary_serializer: 对应的 XxxApplySummarySerializer
    - detail_path: 前端集群详情页的路由路径段(如"kafka"/"elastic-search")
    - port_field: 摘要里代表访问端口的字段名(如"port"/"rpc_port"/"query_port")
    仅在需要额外字段(如ES的CLB/北极星信息)时才覆写 build_summary_data/build_extra。

    统一入参格式：kwargs = {"items": [{bk_biz_id, domain_name, region, version, <port_field>, ...}, ...]}，
    单集群写入时items传一个元素即可。
    """

    summary_serializer = None
    detail_path = ""
    port_field = ""

    def build_summary_data(self, item: dict) -> dict:
        return {
            "region": item.get("region") or "",
            "domain_name": item["domain_name"],
            "version": item.get("version") or "",
            self.port_field: item[self.port_field],
            "access_entry_url": "",
        }

    def build_extra(self, cluster, item: dict, summary_data: dict) -> None:
        """子类覆写此方法补充产品专属字段(如ES的CLB/北极星信息)，此时cluster已确认存在"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = self.runtime_attrs.get("root_pipeline_id")

        items = kwargs["items"]

        summary_data_list = []
        for item in items:
            bk_biz_id = item["bk_biz_id"]
            domain_name = item["domain_name"]

            try:
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=domain_name)
            except Cluster.DoesNotExist:
                self.log_error(_("写入集群信息摘要失败，集群[{}]不存在").format(domain_name))
                continue

            summary_data = self.build_summary_data(item)
            summary_data["access_entry_url"] = "{}/{}/db-manage/{}/detail/{}?open=access_entry".format(
                env.BK_SAAS_HOST, cluster.bk_biz_id, self.detail_path, cluster.id
            )
            self.build_extra(cluster, item, summary_data)

            summary_data_list.append(summary_data)
            self.log_info(_("集群[{}]信息已写入执行摘要").format(domain_name))

        if not summary_data_list:
            self.log_warning(_("没有可写入执行摘要的集群信息，跳过摘要写入"))
            return True

        # 该flow可能并非由正常单据(ticket)触发，此时不存在对应的Flow记录，属于预期情况，跳过即可，不应阻塞流程
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
