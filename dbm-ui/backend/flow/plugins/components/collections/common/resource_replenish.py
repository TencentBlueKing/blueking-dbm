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
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components.hcm.client import HCMApi
from backend.db_meta.models import Spec
from backend.db_services.cmdb.biz import get_hcm_apply_resource_biz
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.ticket.models import Flow, Ticket


class HCMResourceReplenishService(BaseService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def __get_ticket_flow(self, global_data):
        try:
            ticket = Ticket.objects.get(id=global_data["uid"])
            flow = ticket.flows.get(flow_obj_id=self.runtime_attrs["root_pipeline_id"])
            return ticket, flow
        except (Ticket.DoesNotExist, Flow.DoesNotExist):
            raise Exception(_("关联单据/flow不存在，推测此流程已结束/已废弃，建议终止任务"))

    def _execute(self, data, parent_data):
        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = get_hcm_apply_resource_biz()

        # 获取当前单据信息和申请补货信息
        ticket, flow = self.__get_ticket_flow(global_data)
        city, subzone, os_name, count = kwargs["city"], kwargs["subzone"], kwargs["os_name"], kwargs["count"]
        spec = Spec.objects.get(spec_id=kwargs["spec_id"])

        # 修正补货数量，排除已经申请的机器
        apply_count = count - len(flow.output_data[0]["values"]) if flow.output_data else count
        data.outputs.apply_count = apply_count

        if not apply_count:
            self.log_info(_("补货数量已满足，忽略此次申请"))
            return True

        if not spec.device_class:
            self.log_error(_("该规格{}不存在机型，无法进行资源补货").format(spec.spec_name))
            return False

        # 第一次申请发起新的申请单，如果已有申请单，则重试申请。
        apply_id, suborder_id = flow.context.get("apply_id"), flow.context.get("suborder_id")
        if not suborder_id:
            apply_id = HCMApi.create_apply(
                bk_biz_id=bk_biz_id,
                username=ticket.creator,
                city=city,
                subzone=subzone,
                os_name=os_name,
                device_type=spec.device_class[0],
                disk=[{"disk_type": s["type"], "disk_size": s["min"]} for s in spec.storage_spec if s.get("min")],
                count=apply_count,
            )
        else:
            # 先判断单据状态，如果已经非失败暂停，则不进行重试(可能是在海磊平台操作了)
            apply_ticket = HCMApi.get_apply_status(params={"order_id": apply_id}, use_admin=True)["info"][0]
            if apply_ticket["stage"] != "SUSPEND":
                self.log_info(_("单据{}状态为{}，非失败暂停状态跳过重试").format(apply_id, apply_ticket["stage"]))
            else:
                HCMApi.update_ticket_apply_start(
                    {"bk_biz_id": bk_biz_id, "suborder_id": [suborder_id]}, use_admin=True
                )

        self.log_info(_("海磊资源单发起成功，单号: {}").format(apply_id))
        data.outputs.apply_id = apply_id
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        global_data = data.get_one_of_inputs("global_data")
        apply_id = data.get_one_of_outputs("apply_id")
        apply_count = data.get_one_of_outputs("apply_count")
        ticket, flow = self.__get_ticket_flow(global_data)
        bk_biz_id = get_hcm_apply_resource_biz()

        if not apply_count:
            self.finish_schedule()
            return True

        # 查询单据执行阶段
        # "UNCOMMIT": 未提交, "AUDIT": 审核中, "RUNNING": 生产中, "SUSPEND": 失败暂停, "TERMINATE": 终止, "DONE": 已完成
        # 单据终止-退出; 单据进行中-继续轮询
        apply_ticket = HCMApi.get_apply_status(params={"order_id": apply_id}, use_admin=True)["info"][0]
        if apply_ticket["stage"] == "TERMINATE":
            self.log_error(_("备货异常：{}，流程退出").format(apply_id))
            return False
        elif apply_ticket["stage"] not in ["DONE", "SUSPEND"]:
            self.log_info(_("资源申请中，单号: {}, 状态: {}").format(apply_id, apply_ticket["stage"]))
            return True

        # 更新flow上下文，存海磊单据信息
        suborder_id = apply_ticket["suborder_id"]
        flow.update_context(suborder_id=suborder_id, apply_id=apply_id)

        # 已经申请到资源，获取申请资源详情给到资源导入
        apply_detail = HCMApi.get_apply_device(
            params={"order_id": apply_id, "suborder_id": suborder_id}, use_admin=True
        )["info"]

        if not apply_detail:
            self.log_error(_("没有申请到任何资源，流程退出"))
            return False

        # 格式化申请的主机信息
        host_ips = [host["ip"] for host in apply_detail]
        tree_node = {"bk_biz_id": bk_biz_id, "bk_inst_id": "", "bk_obj_id": ""}
        conditions = [{"field": "bk_host_innerip", "operator": "in", "value": host_ips}]
        resp = ResourceQueryHelper.query_cc_hosts(tree_node, conditions, page_size=len(host_ips), bk_cloud_id=0)
        hosts = ResourceHandler.standardized_resource_host(resp["info"])

        # 申请到的机器和cc查询机器数量不一致，可能录入有延迟，推迟到下个周期查询
        if len(host_ips) != len(hosts):
            self.log_info(_("申请到的机器数量与CC查询到的机器数量不一致，推迟到下个周期查询"))
            return True

        # 校验主机是否与申请机型参数一致(暂时仅打印日志提示)
        spec = Spec.objects.get(spec_id=ticket.details["spec_id"])
        expected_device_class = spec.device_class[0] if spec.device_class else ""
        for host in hosts:
            if host["device_class"] != expected_device_class:
                self.log_error(_("主机{}机型与申请机型{}不一致").format(host["device_class"], expected_device_class))

        # 写入单据摘要和上下文信息，要排除已经申请的机器
        from backend.flow.engine.bamboo.scene.common.machine_os_init import ResourceReplenishOutputSerializer

        exist_hosts = flow.output_data[0]["values"] if flow.output_data else []
        exist_host_ids = [host["bk_host_id"] for host in exist_hosts]
        hosts = [host for host in hosts if host["bk_host_id"] not in exist_host_ids]

        root_id = self.runtime_attrs["root_pipeline_id"]
        FlowOutputHandler(ResourceReplenishOutputSerializer).insert_data(root_id, hosts)

        data.outputs.trans_data = {"hosts": hosts}
        self.log_info(_("成功申请到的机器信息：{}").format(hosts))

        self.finish_schedule()
        return True


class HCMResourceReplenishComponent(Component):
    name = _("海磊-主机资源补货")
    code = "RESOURCE_HCM_REPLENISH"
    bound_service = HCMResourceReplenishService
