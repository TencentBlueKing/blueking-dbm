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
from datetime import datetime, timedelta, timezone

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models import BizSettings
from backend.db_dirty.constants import MachineEventType
from backend.db_dirty.models import MachineEvent
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.exceptions import AppBaseException
from backend.flow.engine.controller.base import BaseController
from backend.flow.utils.cc_manage import CcManage
from backend.ticket import builders
from backend.ticket.builders import (
    FlowParamBuilder,
    PauseParamBuilder,
    RecycleCleanMachineParamBuilder,
    TicketFlowBuilder,
)
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import Flow
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


class RecycleHostDetailSerializer(serializers.Serializer):
    recycle_hosts = serializers.JSONField(help_text=_("下架机器的回收信息"), default=[])
    group = serializers.ChoiceField(help_text=_("所属组件"), choices=DBType.get_choices())
    cluster_type = serializers.CharField(help_text=_("所属集群"), default="")
    dts_deploy_path = serializers.CharField(help_text=_("DTS 部署目录"), default="", allow_blank=True)
    dts_deploy_path_by_host = serializers.JSONField(help_text=_("按主机的 DTS 部署目录"), required=False, default=dict)
    parent_ticket = serializers.IntegerField(help_text=_("发起单据号"))
    immediate_recycle = serializers.BooleanField(help_text=_("立即回收"), default=False)
    parent_ticket_type = serializers.CharField(help_text=_("发起的单据类型"), default="")


class MachineIdleCheckParamBuilder(FlowParamBuilder):
    """主机空闲检查参数构建"""

    controller = BaseController.machine_idle_check_flow

    def format_ticket_data(self):
        hosts = self.ticket_data["recycle_hosts"]
        self.ticket_data.update(
            {
                "bk_biz_id": self.ticket.bk_biz_id,
                "ticket_id": self.ticket.id,
                "sa_check_ips": [recycle["ip"] for recycle in hosts],
                "operator": self.ticket.creator,
                "db_type": self.ticket_data["group"],
            }
        )


class RecycleHostParamBuilder(FlowParamBuilder):
    """主机回收参数构建"""

    controller = BaseController.machine_recycle_flow

    def format_ticket_data(self):
        self.ticket_data.update(db_type=self.ticket_data["group"], operator=self.ticket.creator)


class CalcRecycleApplyHostParamBuilder(FlowParamBuilder):
    """计算新机回收参数构建"""

    # 该 controller 需要计算出新机回收主机，并且将主机挪用到 pending 模块
    controller = None

    def build_controller_info(self):
        """反射父单据 inner_flow 挂载的 revoke 类，生成 controller_info。

        功能说明 / 怎么做：
          - 从父单据 TERMINATED 的 flow 读取已挂载的 ``revoke_flow_class``（由
            ``@revoke_with`` 装饰器在 import 期挂载），作为"实际执行回退"的类引用；
          - 据此直接以 ``revoke_class.__name__`` / ``__module__`` 写入 class_name / module，
            避免依赖 ``revoke_flow.__qualname__.split(".")[0]`` 推断（后者在子类未
            自定义 revoke_flow 方法时，会固化为"方法真实定义所在的父类名"，导致后续
            :meth:`Flow.get_inner_controller_func` 反射构造出错误的父类实例，继而
            ``self.EXTRACTOR_CLASS`` / ``self._LOG_PREFIX`` 走到父类版本）。

        :return: dict，含 func_name / class_name / module 三元组
        边界：
          - 父单据不存在 TERMINATED flow -> ``Flow.DoesNotExist``
          - 父 inner flow 未挂 ``revoke_flow_class`` 属性（历史未装饰或装饰器未升级）
            -> ``AttributeError``，让问题在首次 revoke 立即暴露
        """
        parent_flow = Flow.objects.get(status=TicketFlowStatus.TERMINATED, ticket_id=self.ticket_data["parent_ticket"])
        inner_func = parent_flow.get_inner_controller_func()
        # revoke_flow_class：@revoke_with 装饰器挂载的"回退流程类对象"（权威真源）
        revoke_class = inner_func.revoke_flow_class
        self.controller = revoke_class.revoke_flow
        return {
            "func_name": "revoke_flow",
            "class_name": revoke_class.__name__,
            "module": revoke_class.__module__,
        }

    def format_ticket_data(self):
        # 计算参数来源于原来的单据flow信息
        parent_flow = Flow.objects.get(status=TicketFlowStatus.TERMINATED, ticket_id=self.ticket_data["parent_ticket"])
        self.ticket_data.update(parent_flow.details["ticket_data"])
        # 增加通用参数
        super().add_common_params()

    @staticmethod
    def __standardized(recycle_hosts):
        """标准化资源主机信息"""
        # 统一将回收主机挪到 pending 模块
        bk_host_ids = [host["bk_host_id"] for host in recycle_hosts]
        CcManage(bk_biz_id=env.DBA_APP_BK_BIZ_ID, cluster_type="").recycle_host_pending_module(bk_host_ids)
        recycle_hosts = ResourceHandler.standardized_resource_host(recycle_hosts)
        return recycle_hosts

    def post_callback(self):
        """F1「核对待退回主机」结束后：根据 revoke_flow 产出的回收主机清单，决定后续 flow 的走向。

        功能说明 / 怎么做：
          - 数据源：``current_flow.output_data``，真源是 ``FlowSummary.summary``，由 revoke_flow
            内各节点通过 ``FlowOutputHandler(RecycleOutputContext.*Serializer).insert_data`` 落地；
          - 空 ``output_data`` == revoke_flow 判定无机器需回收， 等价于空清单，跳过后续
            PAUSE / 分池 flow，让单据顺利收尾；
          - 非空清单 → 标准化（挪到 pending 模块 + 补标签）后写入分池 flow 的 ticket_data。

        :return: None
        边界 / 异常：
          - 当前 Flow 未 ``SUCCEEDED``（如 bamboo 节点首次失败触发状态信号 → 走失败分支调到
            本回调）直接 return，避免把下游 PAUSE / 分池 Flow 错误置为 ``SKIPPED``；
            节点重试成功后会再次触发本回调，走正常分支。
          - ``output_data == []`` -> ``recycle_hosts = []``，走 SKIPPED 分支，禁止再抛
            IndexError 导致单据静默 hang；
          - 其它 ``AppBaseException`` -> ``run_error_status_handler`` 落 ``Flow.err_msg``。
        """
        current_flow = self.ticket.current_flow()
        # 关键守卫：Flow 自身未成功（首次失败 / 重试中）绝不推进 SKIPPED 分支，否则下游
        # 「人工确认」+「退回主机分池处理」会被置为 SKIPPED，且后续重试成功时无法恢复，
        # 导致 DBA 看到的现象是："已申领主机退回" 读取不到待退回主机、直接跳过。
        if current_flow.status != TicketFlowStatus.SUCCEEDED:
            logger.info(
                "[CalcRecycleApplyHostParamBuilder] skip post_callback: "
                "ticket_id=%s flow_id=%s flow_obj_id=%s status=%s",
                self.ticket.id,
                current_flow.id,
                current_flow.flow_obj_id,
                current_flow.status,
            )
            return

        # 需要根据确定的回收主机，修改数据清理和分池处理的参数
        try:
            # 空 output_data == revoke_flow 判定无机器需要回收，等价于空清单
            output_data = current_flow.output_data
            recycle_hosts = output_data[0]["values"] if output_data else []
            if recycle_hosts:
                recycle_hosts = self.__standardized(recycle_hosts)
            ticket_flows = list(self.ticket.flows.all())
        except AppBaseException as e:
            BaseTicketFlow(current_flow).run_error_status_handler(e)
        else:
            # 如果没有回收的机器，则后面两个流程跳过
            if not recycle_hosts:
                for flow in ticket_flows[1:]:
                    flow.status = TicketFlowStatus.SKIPPED
                    flow.save(update_fields=["status"])
                return

            # 将新机回收同步给分池处理
            recycle_flow = ticket_flows[-1]
            recycle_flow.details["ticket_data"]["recycle_hosts"] = recycle_hosts
            recycle_flow.save(update_fields=["details"])


class RecycleHostFlowBuilder(TicketFlowBuilder):
    serializer = RecycleHostDetailSerializer
    machine_clean_flow_builder = RecycleCleanMachineParamBuilder
    recycle_flow_builder = RecycleHostParamBuilder
    # 此单据不属于任何db，暂定为common
    group = "common"
    editable = False


@builders.BuilderFactory.register(TicketType.RECYCLE_APPLY_HOST)
class RecycleApplyHostFlowBuilder(RecycleHostFlowBuilder):
    calc_recycle_apply_host_flow_builder = CalcRecycleApplyHostParamBuilder
    pause_node_builder = PauseParamBuilder

    def init_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.HOST_RECYCLE.value,
                details=self.calc_recycle_apply_host_flow_builder(self.ticket).get_params(),
                flow_alias=_("核对待退回主机"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.PAUSE.value,
                details=self.pause_node_builder(self.ticket).get_params(),
                flow_alias=_("人工确认"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.HOST_RECYCLE.value,
                details=self.recycle_flow_builder(self.ticket).get_params(),
                flow_alias=_("退回主机分池处理"),
            ),
        ]

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))


@builders.BuilderFactory.register(TicketType.RECYCLE_OLD_HOST)
class RecycleOldHostFlowBuilder(RecycleHostFlowBuilder):
    machine_idle_check_flow_builder = MachineIdleCheckParamBuilder

    def check_independent_recycle(self):
        # sqlserver 业务均为独立管控业务，且下架派生的回收单 cluster_type 仅能取到 db_type 级别的
        if self.ticket.details["cluster_type"] == DBType.Sqlserver.value:
            return self.ticket.ticket_type == TicketType.RECYCLE_OLD_HOST

        cluster_type = self.ticket.details.get("cluster_type") or self.ticket.details["group"]
        hosting_biz = BizSettings.get_exact_hosting_biz(self.ticket.bk_biz_id, cluster_type)
        return self.ticket.ticket_type == TicketType.RECYCLE_OLD_HOST and hosting_biz != env.DBA_APP_BK_BIZ_ID

    def init_ticket_flows(self):
        flows = []

        # 对于独立管控的回收单，跳过空闲检查和数据清理
        if not self.check_independent_recycle():
            # 定时执行 - 如果父单据设置了immediate_recycle标志，则跳过定时器
            immediate_recycle = self.ticket.details.get("immediate_recycle", False)
            if env.HOST_RECYCLE_RETENTION_DAYS and not immediate_recycle:
                flows.append(
                    Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")),
                )

            # 主机空闲检查
            if env.SA_CHECK_TEMPLATE_ID:
                flows.append(
                    Flow(
                        ticket=self.ticket,
                        flow_type=FlowType.HOST_RECYCLE.value,
                        details=self.machine_idle_check_flow_builder(self.ticket).get_params(),
                        flow_alias=_("主机空闲检查"),
                    ),
                )

            # 数据清理
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.HOST_RECYCLE.value,
                    details=self.machine_clean_flow_builder(self.ticket).get_params(),
                    flow_alias=_("主机数据清理"),
                ),
            )

        # 主机分池处理
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.HOST_RECYCLE.value,
                details=self.recycle_flow_builder(self.ticket).get_params(),
                flow_alias=_("主机分池处理"),
            ),
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def patch_ticket_detail(self):
        trigger_time = datetime2str(datetime.now(timezone.utc) + timedelta(days=env.HOST_RECYCLE_RETENTION_DAYS))
        self.ticket.update_details(trigger_time=trigger_time)
        # 记录主机操作记录
        event = MachineEventType.RemoveHost
        MachineEvent.create_machine_events(
            self.ticket.bk_biz_id,
            self.ticket.details["recycle_hosts"],
            event,
            "",
            self.ticket.creator,
            self.ticket,
            remark=_("已下架主机自动进入处理流程"),
        )
