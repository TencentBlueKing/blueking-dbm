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
import copy
import importlib
import json
import logging
import os
from typing import Callable, Dict, List

from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend import env
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.configuration.models.system import SystemSettingsEnum
from backend.db_meta.models import AppCache
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_init.services import Services
from backend.ticket.constants import FlowRetryType, FlowType
from backend.ticket.models import Flow, Ticket

logger = logging.getLogger("root")


class CallBackBuilderMixin(object):
    """为节点添加前置/后继钩子函数信息"""

    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    def pre_callback(self):
        pass

    def post_callback(self):
        pass

    def add_common_params(self):
        self.ticket_data.update(
            {
                "uid": self.ticket.id,
                "ticket_type": self.ticket.ticket_type,
                "created_by": self.ticket.creator,
                "bk_biz_id": self.ticket.bk_biz_id,
            }
        )

    def build_callback_info(self) -> Dict:
        return {
            "pre_callback_module": self.pre_callback.__module__,
            "pre_callback_class": self.pre_callback.__qualname__.split(".")[0],
            "post_callback_module": self.post_callback.__module__,
            "post_callback_class": self.post_callback.__qualname__.split(".")[0],
        }

    def inject_callback_in_params(self, params: Dict = None) -> Dict:
        params = params or {}
        params.update({"callback_info": self.build_callback_info()})
        return params


class FlowParamBuilder(CallBackBuilderMixin):
    """
    Flow 参数构建器
    职责：将单据详情（ticket.details）转化为 Flow 流程运行所需的参数
    """

    # 配置任务流程控制器：流程启动函数
    controller = None

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.ticket_data = copy.deepcopy(ticket.details)

    def build_controller_info(self) -> dict:
        return {
            "func_name": self.controller.__name__,
            "class_name": self.controller.__qualname__.split(".")[0],
            "module": self.controller.__module__,
        }

    def format_ticket_data(self):
        """格式化单据数据，由子类实现"""
        pass

    def get_params(self) -> dict:
        self.add_common_params()
        self.format_ticket_data()

        params = {
            "ticket_data": copy.deepcopy(self.ticket_data),
            "controller_info": self.build_controller_info(),
        }
        params = super().inject_callback_in_params(params=params)

        if env.ENVIRONMENT == "dev":
            logger.info("flow.bamboo.params: \n%s\n", json.dumps(params, indent=2))

        return params


class ItsmParamBuilder(CallBackBuilderMixin):
    """
    ITSM 参数构建器
    职责：将单据详情（ticket.details）转化为 ITSM 单据创建所需的参数
    - 定义单据的审批人，默认取对应 DB 类型的管理员
    - 格式化单据概览，提高单据的可读性
    """

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.details = copy.deepcopy(ticket.details)

    def get_approvers(self):
        db_type = BuilderFactory.registry[self.ticket.ticket_type].group
        approvers = DBAdministrator.get_biz_db_type_admins(self.ticket.bk_biz_id, db_type)
        return ",".join(approvers)

    def format(self):
        pass

    def get_params(self):
        self.format()
        # clusters只是为了给服务单详情展示的信息，不需要在单据中体现
        self.details.pop("clusters", None)
        service_id = SystemSettings.get_setting_value(SystemSettingsEnum.BK_ITSM_SERVICE_ID.value)
        if not service_id:
            Services.auto_create_itsm_service()
            service_id = SystemSettings.get_setting_value(SystemSettingsEnum.BK_ITSM_SERVICE_ID.value)

        title = self.ticket.get_ticket_type_display()
        params = {
            "service_id": service_id,
            "creator": self.ticket.creator,
            "fields": [
                {"key": "title", "value": title},
                {"key": "bk_biz_id", "value": self.ticket.bk_biz_id},
                {"key": "approver", "value": self.get_approvers()},
                {
                    "key": "summary",
                    "value": _("{creator}提交了{title}的单据，请查看详情后进行审批").format(creator=self.ticket.creator, title=title),
                },
            ],
            "dynamic_fields": [
                {
                    "name": _("单据链接"),
                    "type": "LINK",
                    "value": f"{env.BK_SAAS_HOST}/self-service/my-tickets?id={self.ticket.id}",
                },
                {
                    "name": _("需求信息"),
                    "type": "LINK",
                    "value": f"{env.BK_SAAS_HOST}/self-service/my-tickets?id={self.ticket.id}&isFullscreen=true",
                },
            ],
            "meta": {
                "callback_url": f"{env.BK_SAAS_HOST}/apis/tickets/{self.ticket.id}/callback/",
                "state_processors": {},
            },
        }
        params = super().inject_callback_in_params(params=params)

        if env.ENVIRONMENT == "dev":
            logger.debug("flow.itsm.params: \n%s\n", json.dumps(params, indent=2))

        return params


class PauseParamBuilder(CallBackBuilderMixin):
    """
    Pause 参数构造器
    职责：为暂停任务提供单据参数
    预写参数:
     - pause_type: 可表示暂停的类型
    """

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.ticket_data = copy.deepcopy(ticket.details)
        self.params = {"pause_type": None}

    def format(self):
        """
        这里可以为params添加更多参数
        适配更加复杂的场景
        """
        pass

    def get_params(self):
        self.format()
        self.params = super().inject_callback_in_params(params=self.params)
        return self.params


class ResourceApplyParamBuilder(CallBackBuilderMixin):
    """
    ResourceApply资源申请 参数构造器
    职责：为资源申请提供额外参数，并为后继的inner flow节点更新信息
    """

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.ticket_data = copy.deepcopy(ticket.details)

    def format(self):
        """
        这里可以为params添加更多参数
        适配更加复杂的场景
        """
        pass

    def get_params(self):
        self.format()
        super().add_common_params()
        super().inject_callback_in_params(params=self.ticket_data)
        return self.ticket_data

    def post_callback(self):
        """
        部署单据需要有特殊的参数填充或者逻辑处理，
        需要在各自的ResourceApplyParamBuilder重写post_callback
        """
        pass


class TicketFlowBuilder:
    """
    单据流程构建器
    职责：定义单据流程（ticket_flow），实例化单据流程对象并结合 FlowParamBuilder/ItsmParamBuilder 生成所需参数
    """

    ticket_type = None
    group = None
    serializer = None

    # 默认的参数构造器
    inner_flow_name: str = ""
    inner_flow_builder: FlowParamBuilder = None
    pause_node_builder: PauseParamBuilder = None
    # resource_apply_builder和resource_batch_apply_builder只能存在其一，表示是资源池单次申请还是批量申请
    resource_apply_builder: ResourceApplyParamBuilder = None
    resource_batch_apply_builder: ResourceApplyParamBuilder = None
    # inner flow互斥的重试类型，默认为自动重试
    retry_type: FlowRetryType = FlowRetryType.AUTO_RETRY

    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def type(cls):
        return cls.__name__.lower()

    @classmethod
    def enabled(cls) -> bool:
        """
        是否开启，默认开启
        可考虑使用功能开关控制
        """
        return True

    @property
    def need_itsm(self):
        """是否需要itsm审批节点"""
        return True

    @property
    def need_manual_confirm(self):
        """是否需要人工确认节点"""
        return False

    @property
    def need_resource_pool(self):
        """是否存在资源池接入"""
        return self.ticket.details.get("ip_source") == IpSource.RESOURCE_POOL

    def custom_ticket_flows(self):
        return []

    def init_ticket_flows(self):
        """
        自定义流程，默认流程是：
        单据审批(可选, 默认有) --> 人工确认(可选, 默认无) --> 资源申请(由单据参数判断) ---> inner节点 --> 资源交付(由单据参数判断)
        如果有特殊的flow需求，可在custom_ticket_flows中定制，会替换掉inner节点为custom流程
        对于复杂流程，可以直接覆写init_ticket_flows
        """
        flows = []

        # 判断并添加审批节点
        if self.need_itsm:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.BK_ITSM.value,
                    details=ItsmParamBuilder(self.ticket).get_params(),
                    flow_alias=_("单据审批"),
                )
            )

        # 判断并添加人工确认节点
        if self.need_manual_confirm:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.PAUSE.value,
                    details=self.pause_node_builder(self.ticket).get_params(),
                    flow_alias=_("人工确认"),
                ),
            )

        # 判断并添加资源申请节点
        if self.need_resource_pool:

            if not self.resource_apply_builder:
                flow_type, resource_builder = FlowType.RESOURCE_BATCH_APPLY, self.resource_batch_apply_builder
            else:
                flow_type, resource_builder = FlowType.RESOURCE_APPLY, self.resource_apply_builder

            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=flow_type,
                    details=resource_builder(self.ticket).get_params(),
                    flow_alias=_("资源申请"),
                ),
            )

        # 若单据有特殊的自定义流程，则优先使用。否则使用默认的 inner_param_builder
        custom_ticket_flows = self.custom_ticket_flows()
        if custom_ticket_flows:
            flows.extend(custom_ticket_flows)
        else:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=self.inner_flow_builder(self.ticket).get_params(),
                    flow_alias=self.inner_flow_name,
                    retry_type=self.retry_type,
                )
            )

        # 如果使用资源池，则在最后需要进行资源交付
        if self.need_resource_pool:
            flow_type = FlowType.RESOURCE_DELIVERY if self.resource_apply_builder else FlowType.RESOURCE_BATCH_APPLY
            flows.append(Flow(ticket=self.ticket, flow_type=flow_type))

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def patch_ticket_detail(self):
        """补充单据详情"""
        pass


class BuilderFactory:
    registry = {}

    @classmethod
    def register(cls, ticket_type: str) -> Callable:
        def inner_wrapper(wrapped_class: TicketFlowBuilder) -> TicketFlowBuilder:
            if ticket_type in cls.registry:
                logger.warning(f"Builder [{ticket_type}] already exists. Will replace it")
            cls.registry[ticket_type] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_builder_cls(cls, ticket_type: str):
        """获取构造器类"""
        if ticket_type not in cls.registry:
            logger.warning(f"Ticket Type: [{ticket_type}] does not exist in the registry")
            raise NotImplementedError

        return cls.registry[ticket_type]

    @classmethod
    def get_serializer(cls, ticket_type: str):
        try:
            return cls.get_builder_cls(ticket_type).serializer()
        except NotImplementedError:
            return serializers.Serializer()

    @classmethod
    def create_builder(cls, ticket: Ticket):
        """创建构造器实例"""
        builder_cls = cls.get_builder_cls(ticket.ticket_type)
        return builder_cls(ticket)


def register_all_builders(path=os.path.dirname(__file__), module_path="backend.ticket.builders"):
    """递归注册当前目录下所有的构建器"""
    for name in os.listdir(path):
        # 忽略无效文件
        if name.endswith(".pyc") or name in ["__init__.py", "__pycache__"]:
            continue

        if os.path.isdir(os.path.join(path, name)):
            register_all_builders(os.path.join(path, name), ".".join([module_path, name]))
        else:
            try:
                module_name = name.replace(".py", "")
                import_path = ".".join([module_path, module_name])
                print(f"register_all_builders: {import_path}")
                importlib.import_module(import_path)
            except ModuleNotFoundError as e:
                logger.warning(e)
