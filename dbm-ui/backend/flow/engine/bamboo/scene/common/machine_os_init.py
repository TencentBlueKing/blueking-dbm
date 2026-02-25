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

from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.exceptions import InvalidOperationException
from rest_framework import serializers

from backend import env
from backend.components.dbresource.client import DBResourceApi
from backend.components.hcm.client import HCMApi
from backend.components.xwork.client import XworkApi
from backend.configuration.constants import DBType, SystemSettingsEnum
from backend.configuration.models import BizSettings, SystemSettings
from backend.db_dirty.constants import MachineEventType
from backend.db_dirty.models import MachineEvent
from backend.db_meta.models import Machine
from backend.db_services.cmdb.biz import get_or_create_resource_module, get_resource_biz
from backend.db_services.dbbase.constants import IpDest
from backend.db_services.ipchooser.constants import BK_OS_CODE__TYPE, BkOsType
from backend.flow.consts import LINUX_ADMIN_USER_FOR_CHECK, WINDOW_ADMIN_USER_FOR_CHECK
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent
from backend.flow.plugins.components.collections.common.resource_replenish import HCMResourceReplenishComponent
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.common.sa_init import SaInitComponent
from backend.flow.plugins.components.collections.common.transfer_host_service import TransferHostServiceComponent
from backend.flow.plugins.components.collections.common.transfer_host_to_pool import TransferHostToPoolComponent
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.flow.utils.common_act_dataclass import (
    ImportMachinePollKwargs,
    InitCheckForResourceKwargs,
    ResourceHcmReplenishKwargs,
    ResourceImportContext,
)
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket, Todo


def insert_host_event(params, data, kwargs, global_data):
    """导入资源池成功后，记录主机事件"""
    hosts, operator = params["hosts"], params["operator"]
    ticket_id = params.get("ticket_id") or params.get("uid") or 0
    ticket = Ticket.objects.filter(id=ticket_id).first()
    event_bk_biz_id = ticket.bk_biz_id if ticket else global_data["bk_biz_id"]
    event = MachineEventType.ReturnResource if params.get("return_resource") else MachineEventType.ImportResource
    hosts = [{"bk_host_id": host["host_id"], **host} for host in hosts]
    # 记录主机事件
    MachineEvent.host_event_trigger(event_bk_biz_id, hosts, event=event, operator=operator, ticket=ticket)
    # 资源导入记录
    import_record = {"task_id": str(ticket_id), "operator": operator, "hosts": hosts}
    DBResourceApi.import_operation_create(params=import_record)
    # 主机代办删除
    host_ids = [host["bk_host_id"] for host in hosts]
    Todo.host_todo_trigger(host_ids, [operator], event, ticket)


class HostOutputSerializer(BaseFlowOutputSerializer):
    ip = serializers.CharField(help_text=_("IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("管控区域"))
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
    city = serializers.CharField(help_text=_("地域"), allow_null=True, allow_blank=True, default="")
    sub_zone = serializers.CharField(help_text=_("园区"), allow_null=True, allow_blank=True, default="")
    rack_id = serializers.CharField(help_text=_("机架"), allow_null=True, allow_blank=True, default="")
    os_name = serializers.CharField(help_text=_("操作系统"), allow_null=True, allow_blank=True, default="")
    device_class = serializers.CharField(help_text=_("机型"), allow_null=True, allow_blank=True, default="")
    remark = serializers.CharField(help_text=_("备注"), required=False, default="")


class RecycleOutputContext:
    """回收上下文序列化器"""

    class ToFailSerializer(HostOutputSerializer):
        table_name = IpDest.Fault.value
        table_display_name = _("退回故障池")

    class ToResourceSerializer(HostOutputSerializer):
        table_name = IpDest.Resource.value
        table_display_name = _("退回资源池")

    class ToRecycleSerializer(HostOutputSerializer):
        table_name = IpDest.Recycle.value
        table_display_name = _("退回待回收池")

    class ToRecycledSerializer(HostOutputSerializer):
        table_name = IpDest.Recycled.value
        table_display_name = _("退回CC待回收")


class ResourceReplenishOutputSerializer(HostOutputSerializer):
    """资源池补充流程"""

    bk_cpu = serializers.CharField(help_text=_("cpu"), allow_null=True, allow_blank=True, default="")
    bk_mem = serializers.CharField(help_text=_("内存"), allow_null=True, allow_blank=True, default="")
    bk_disk = serializers.CharField(help_text=_("磁盘"), allow_null=True, allow_blank=True, default="")

    table_name = _("交付结果")


class ImportResourceInitStepFlow(object):
    """
    机器初始化步骤
    """

    def __init__(self, root_id: str, data: Optional[Dict]) -> None:
        self.root_id = root_id
        self.data = data
        self.data["task_id"] = self.root_id

    def __build_machine_import_pipeline(self, p, data):
        host_list = data["hosts"]
        host_ids = [host["host_id"] for host in host_list]
        bk_biz_id = data["bk_biz_id"]

        os_type = str(data.get("os_type", BkOsType.LINUX.value))
        if os_type.isdigit():
            os_type = BK_OS_CODE__TYPE[os_type]
        if os_type == BkOsType.WINDOWS.value:
            # 如果是window类型机器，用administrator账号
            account_name = WINDOW_ADMIN_USER_FOR_CHECK
        else:
            account_name = LINUX_ADMIN_USER_FOR_CHECK

        # 先执行空闲检查
        if env.SA_RECYCLE_IDLE_CHECK_TEMPLATE_ID or env.SA_CHECK_TEMPLATE_ID:
            p.add_act(
                act_name=_("执行sa空闲检查(严格)") if env.SA_RECYCLE_IDLE_CHECK_TEMPLATE_ID else _("执行sa空闲检查"),
                act_component_code=CheckMachineIdleComponent.code,
                kwargs=asdict(
                    InitCheckForResourceKwargs(
                        ips=[host["ip"] for host in host_list],
                        bk_biz_id=bk_biz_id,
                        account_name=account_name,
                        strict_idle_check=bool(env.SA_RECYCLE_IDLE_CHECK_TEMPLATE_ID),
                    )
                ),
            )

        # 在执行sa初始化
        if env.SA_INIT_TEMPLATE_ID:
            # 执行sa初始化
            p.add_act(
                act_name=_("执行sa初始化"),
                act_component_code=SaInitComponent.code,
                kwargs={
                    "ips": [host["ip"] for host in host_list],
                    "bk_biz_id": bk_biz_id,
                    "account_name": account_name,
                },
            )

        # 调用资源导入接口
        resource_kwargs = {
            "set_trans_data_dataclass": ResourceImportContext.__name__,
            "api_import_path": DBResourceApi.__module__,
            "api_import_module": "DBResourceApi",
            "success_callback_path": f"{insert_host_event.__module__}.{insert_host_event.__name__}",
        }
        if data.get("reimport"):
            p.add_act(
                act_name=_("主机资源重导入"),
                act_component_code=ExternalServiceComponent.code,
                kwargs={"params": data, "api_call_func": "resource_reimport", **resource_kwargs},
            )
        else:
            p.add_act(
                act_name=_("资源池导入"),
                act_component_code=ExternalServiceComponent.code,
                kwargs={"params": data, "api_call_func": "resource_import", **resource_kwargs},
            )

        # 转移模块到资源池业务
        p.add_act(
            act_name=_("主机转移至资源池空闲模块"),
            act_component_code=TransferHostServiceComponent.code,
            kwargs={
                "bk_biz_id": get_resource_biz(),
                "bk_module_ids": [get_or_create_resource_module()],
                "bk_host_ids": host_ids,
                "update_host_properties": {"dbm_meta": [], "need_monitor": False, "update_operator": False},
            },
        )

        # 主机安装节点管理插件
        # p.add_sub_pipeline(install_nodeman_plugins(self.root_id, self.data["uid"], host_ids))

    def machine_init_flow(self):
        """资源池导入"""
        p = Builder(root_id=self.root_id, data=self.data)
        self.__build_machine_import_pipeline(p, self.data)
        p.run_pipeline()

    def machine_recycle_flow(self):
        """已下架主机处理"""

        def __add_host_remark(add_hosts, remark):
            for h in add_hosts:
                h.update(remark=remark)
            return add_hosts

        p = Builder(root_id=self.root_id, data=self.data)

        hosts = self.data["recycle_hosts"]
        revoke_ticket = Ticket.objects.get(id=self.data["uid"])

        # 检查主机不应该存在于主机池
        host_ids = [host["bk_host_id"] for host in self.data["recycle_hosts"]]
        exist_hosts = Machine.objects.filter(bk_host_id__in=host_ids).values_list("ip", flat=True)
        if self.data["ticket_type"] == TicketType.RECYCLE_OLD_HOST and exist_hosts:
            raise InvalidOperationException(_("流程校验不通过，存在元数据主机: {}").format(exist_hosts))

        # 故障池
        fault_hosts: List = []
        # 待回收池主机
        recycle_hosts: List = []
        # 资源池主机
        resource_hosts: List = []
        # 转移CC待回收模块主机
        recycled_hosts: List = []

        # 如果是独立业务下架，则直接转移到待回收
        cluster_type = self.data.get("cluster_type") or self.data["group"]
        hosting_biz = BizSettings.get_exact_hosting_biz(revoke_ticket.bk_biz_id, cluster_type)
        if self.data["ticket_type"] == TicketType.RECYCLE_OLD_HOST and hosting_biz != env.DBA_APP_BK_BIZ_ID:
            recycled_hosts.extend(hosts)
            hosts = []
        __add_host_remark(recycled_hosts, _("检测该业务为独立管控业务"))

        # sqlserver机器直接转移到待回收
        windows_host_switch = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.WINDOWS_HOST_TO_RECYCLE_SWITCH, default=False
        )
        if windows_host_switch:
            if self.data["ticket_type"] == TicketType.RECYCLE_OLD_HOST and self.data["group"] == DBType.Sqlserver:
                recycle_hosts.extend(hosts)
                hosts = []
            __add_host_remark(recycle_hosts, _("检测主机为Windows机器"))

        # 直连区域：存在uwork的主机需要回到故障池，存在裁撤单的主机需要回到待回收池，否则退回资源池
        host_ids = [host["bk_host_id"] for host in hosts if host["bk_cloud_id"] == 0]
        dissolved_switch = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.HOST_DISSOLVED_SWITCH, default=False
        )
        host_to_fault_switch = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.HOST_TO_FAULT_SWITCH, default=False
        )
        dissolved_hosts = [] if not dissolved_switch else HCMApi.check_host_is_dissolved(host_ids)
        uwork_hosts = {} if not host_to_fault_switch else HCMApi.check_host_has_uwork(host_ids)

        host_ip__host_id_map = {host["ip"]: host["bk_host_id"] for host in hosts if host["bk_cloud_id"] == 0}
        xwork_hosts = {} if not host_to_fault_switch else XworkApi.check_xwork_list(host_ip__host_id_map)

        for host in hosts:
            if host["bk_host_id"] in uwork_hosts.keys():
                host.update(remark=_("检测主机有关联的uwork单据"))
                fault_hosts.append(host)
            elif host["bk_host_id"] in xwork_hosts.keys():
                host.update(remark=_("检测主机有关联的xwork单据"))
                fault_hosts.append(host)
            elif host["bk_host_id"] in dissolved_hosts:
                host.update(remark=_("检测主机为待裁撤主机"))
                recycle_hosts.append(host)
            else:
                resource_hosts.append(host)

        common_kwargs = ImportMachinePollKwargs(
            bk_biz_id=self.data["bk_biz_id"],
            db_type=self.data["group"],
            cluster_type=self.data.get("cluster_type", ""),
            operator=self.data["operator"],
            ticket_id=self.data["uid"],
        )

        # 转移主机到故障池
        if fault_hosts:
            common_kwargs.hosts = fault_hosts
            common_kwargs.event = MachineEventType.ToFault.value
            p.add_act(
                act_name=_("主机转入故障池"),
                act_component_code=TransferHostToPoolComponent.code,
                kwargs=asdict(common_kwargs),
            )
            FlowOutputHandler(RecycleOutputContext.ToFailSerializer).insert_data(self.root_id, fault_hosts)

        # 转移主机到待回收池
        if recycle_hosts:
            common_kwargs.hosts = recycle_hosts
            common_kwargs.event = MachineEventType.ToRecycle.value
            p.add_act(
                act_name=_("主机转入待回收池"),
                act_component_code=TransferHostToPoolComponent.code,
                kwargs=asdict(common_kwargs),
            )
            FlowOutputHandler(RecycleOutputContext.ToRecycleSerializer).insert_data(self.root_id, recycle_hosts)

        # 转移主机到CC待回收
        if recycled_hosts:
            common_kwargs.hosts = recycled_hosts
            common_kwargs.event = MachineEventType.Recycled.value
            p.add_act(
                act_name=_("主机转移到CC待回收池"),
                act_component_code=TransferHostToPoolComponent.code,
                kwargs=asdict(common_kwargs),
            )
            FlowOutputHandler(RecycleOutputContext.ToRecycledSerializer).insert_data(self.root_id, recycled_hosts)

        # 转移主机到资源池
        if resource_hosts:
            from backend.ticket.builders.common.base import fetch_apply_hosts

            resource_kwargs = asdict(common_kwargs)
            resource_biz = get_resource_biz()
            resource_kwargs.update(
                # 固定回收到公共资源池
                for_biz=0,
                # 导入业务是资源池业务
                bk_biz_id=resource_biz,
                resource_type=common_kwargs.db_type,
                os_type=resource_hosts[0]["os_type"],
                hosts=resource_hosts,
                return_resource=True,
                # 是否资源重导入
                reimport=self.data["ticket_type"] == TicketType.RECYCLE_APPLY_HOST,
            )
            # 如果单据类型是，新主机退回，则需要拿到原始申请的主机信息进行回退(原始的标签、主机属性等)
            if resource_kwargs["reimport"]:
                parent_ticket = Ticket.objects.get(id=self.data["parent_ticket"])
                apply_hosts = fetch_apply_hosts(parent_ticket.details)
                host_ids = [host["bk_host_id"] for host in resource_hosts]
                resource_kwargs["hosts"] = [host for host in apply_hosts if host["bk_host_id"] in host_ids]
                # 注意这里回收的主机已经统一放到了pending模块，所以要修改下业务ID
                for host in resource_kwargs["hosts"]:
                    host["bk_biz_id"] = resource_biz

            sub_p = SubBuilder(data=self.data, root_id=self.root_id)
            self.__build_machine_import_pipeline(sub_p, resource_kwargs)
            p.add_sub_pipeline(sub_p.build_sub_process(sub_name=_("主机退回资源池")))

            FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(self.root_id, resource_hosts)

        p.run_pipeline()

    def machine_idle_check_flow(self):
        p = Builder(root_id=self.root_id, data=self.data)

        # 已下架主机处理，检查回收主机不能存在元数据
        host_ids = [host["bk_host_id"] for host in self.data["recycle_hosts"]]
        exist_hosts = Machine.objects.filter(bk_host_id__in=host_ids).values_list("ip", flat=True)
        if self.data["ticket_type"] == TicketType.RECYCLE_OLD_HOST and exist_hosts:
            raise InvalidOperationException(_("流程校验不通过，存在元数据主机: {}").format(exist_hosts))

        kwargs = InitCheckForResourceKwargs(
            ips=self.data["sa_check_ips"],
            # 主机目前已回收到资源池业务的pending模块
            bk_biz_id=get_resource_biz(),
            account_name=WINDOW_ADMIN_USER_FOR_CHECK
            if self.data["db_type"] == DBType.Sqlserver
            else LINUX_ADMIN_USER_FOR_CHECK,
        )
        p.add_act(
            act_name=_("执行sa空闲检查"),
            act_component_code=CheckMachineIdleComponent.code,
            kwargs=asdict(kwargs),
        )

        p.run_pipeline()

    def resource_hcm_replenish_flow(self):
        """海磊主机资源池补充"""

        p = Builder(root_id=self.root_id, data=self.data)

        # 海磊申请主机
        p.add_act(
            act_name=_("海磊申请主机"),
            act_component_code=HCMResourceReplenishComponent.code,
            kwargs=asdict(
                ResourceHcmReplenishKwargs(
                    subzone=self.data["subzone"],
                    city=self.data["city"],
                    count=self.data["count"],
                    spec_id=self.data["spec_id"],
                    os_name=self.data["os_name"],
                )
            ),
        )

        # 转移模块到资源池
        # 这里提前转移是可能海磊申请主机的业务≠资源池业务
        p.add_act(
            act_name=_("主机纳管到资源池业务"),
            act_component_code=TransferHostServiceComponent.code,
            kwargs={
                "bk_biz_id": get_resource_biz(),
                "bk_module_ids": [get_or_create_resource_module()],
                "update_host_properties": {"dbm_meta": [], "need_monitor": False, "update_operator": False},
            },
        )

        # 资源池导入
        self.__build_machine_import_pipeline(p, self.data)
        p.run_pipeline()
