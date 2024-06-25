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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DnsOpType, VmRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.vm.vm_base_flow import (
    VmBaseFlow,
    get_all_node_ips_in_ticket,
    get_node_ips_in_ticket_by_role,
    get_vm_ips,
    role_exists_in_ticket,
)
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.plugins.components.collections.vm.exec_vm_actuator_script import ExecuteVmActuatorScriptComponent
from backend.flow.plugins.components.collections.vm.get_vm_payload import GetVmActPayloadComponent
from backend.flow.plugins.components.collections.vm.get_vm_resource import GetVmResourceComponent
from backend.flow.plugins.components.collections.vm.vm_db_meta import VmMetaComponent
from backend.flow.plugins.components.collections.vm.vm_dns_manage import VmDnsManageComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs
from backend.flow.utils.vm.consts import VMINSERT_STORAGE_PORT, VMSELECT_STORAGE_PORT
from backend.flow.utils.vm.vm_act_payload import VmActPayload
from backend.flow.utils.vm.vm_context_dataclass import VmActKwargs, VmApplyContext

logger = logging.getLogger("flow")


class VmScaleUpFlow(VmBaseFlow):
    """
    Vm扩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        vmstorage_ips = get_vm_ips(VmRoleEnum.VMSTORAGE.value, data)
        self.vminsert_storage_node = ",".join(f"{address}:{VMINSERT_STORAGE_PORT}" for address in vmstorage_ips)
        self.vmselect_storage_node = ",".join(f"{address}:{VMSELECT_STORAGE_PORT}" for address in vmstorage_ips)

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["vminsert_storage_node"] = self.vminsert_storage_node
        flow_data["vmselect_storage_node"] = self.vmselect_storage_node
        flow_data["nodes"] = self.nodes
        return flow_data

    def scale_up_vm_flow(self):
        """
        定义扩容vm集群
        :return:
        """
        scale_up_data = self.__get_flow_data()

        vm_pipeline = Builder(root_id=self.root_id, data=scale_up_data)

        trans_files = GetFileList(db_type=DBType.Vm)
        act_kwargs = VmActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = VmApplyContext.__name__
        act_kwargs.file_list = trans_files.vm_apply(db_version=self.db_version)

        vm_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetVmActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        vm_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetVmResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=scale_up_data)
        vm_pipeline.add_act(
            act_name=_("下发vm介质和dbactuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 新节点统一初始化流程
        sub_common_pipelines = self.new_common_sub_flows(
            act_kwargs=act_kwargs,
            data=scale_up_data,
        )
        # 并发执行所有子流程
        vm_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_common_pipelines)

        # 扩容vmstorage
        if role_exists_in_ticket(role=VmRoleEnum.VMSTORAGE.value, data=scale_up_data):
            vm_act_list = self.new_vminstall_act_list(
                role=VmRoleEnum.VMSTORAGE.value, act_kwargs=act_kwargs, data=scale_up_data
            )
            vm_pipeline.add_parallel_acts(acts_list=vm_act_list)

        # 扩容vminsert
        if role_exists_in_ticket(role=VmRoleEnum.VMINSERT.value, data=scale_up_data):
            vm_act_list = self.new_vminstall_act_list(
                role=VmRoleEnum.VMINSERT.value, act_kwargs=act_kwargs, data=scale_up_data
            )
            vm_pipeline.add_parallel_acts(acts_list=vm_act_list)

        # 扩容vmselect
        if role_exists_in_ticket(role=VmRoleEnum.VMSELECT.value, data=scale_up_data):
            vm_act_list = self.new_vminstall_act_list(
                role=VmRoleEnum.VMSELECT.value, act_kwargs=act_kwargs, data=scale_up_data
            )
            vm_pipeline.add_parallel_acts(acts_list=vm_act_list)

        # 扩容vmauth
        if role_exists_in_ticket(role=VmRoleEnum.VMAUTH.value, data=scale_up_data):
            vm_act_list = self.new_vminstall_act_list(
                role=VmRoleEnum.VMAUTH.value, act_kwargs=act_kwargs, data=scale_up_data
            )
            vm_pipeline.add_parallel_acts(acts_list=vm_act_list)

        # 如果扩容的是vmstorage，需要重启vminsert跟vmselect
        # 先重启vmselect, 再重启vminsert, 逐台重启
        if role_exists_in_ticket(role=VmRoleEnum.VMSTORAGE.value, data=scale_up_data):
            # vmselect
            act_kwargs.get_vm_payload_func = VmActPayload.reload_vmselect_payload.__name__
            act_kwargs.exec_ip = get_vm_ips(role=VmRoleEnum.VMSELECT.value, data=scale_up_data)
            vm_pipeline.add_act(
                act_name=_("Reload vmselect"),
                act_component_code=ExecuteVmActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            # vminsert
            act_kwargs.get_vm_payload_func = VmActPayload.reload_vminsert_payload.__name__
            act_kwargs.exec_ip = get_vm_ips(role=VmRoleEnum.VMINSERT.value, data=scale_up_data)
            vm_pipeline.add_act(
                act_name=_("Reload vminsert"),
                act_component_code=ExecuteVmActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

        if role_exists_in_ticket(role=VmRoleEnum.VMINSERT.value, data=scale_up_data):
            # 添加vminsert域名
            dns_kwargs = CreateDnsKwargs(
                bk_cloud_id=scale_up_data["bk_cloud_id"],
                dns_op_type=DnsOpType.CREATE,
                add_domain_name=self.vminsert_domain,
                dns_op_exec_port=self.vminsert_port,
                exec_ip=get_node_ips_in_ticket_by_role(data=scale_up_data, role=VmRoleEnum.VMINSERT.value),
            )
            vm_pipeline.add_act(
                act_name=_("添加vminsert域名"),
                act_component_code=VmDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

        if role_exists_in_ticket(role=VmRoleEnum.VMSELECT.value, data=scale_up_data):
            # 添加vmselect域名
            dns_kwargs = CreateDnsKwargs(
                bk_cloud_id=scale_up_data["bk_cloud_id"],
                dns_op_type=DnsOpType.CREATE,
                add_domain_name=self.vmselect_domain,
                dns_op_exec_port=self.vmselect_port,
                exec_ip=get_node_ips_in_ticket_by_role(data=scale_up_data, role=VmRoleEnum.VMSELECT.value),
            )
            vm_pipeline.add_act(
                act_name=_("添加vmselect域名"),
                act_component_code=VmDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

        # 添加到DBMeta并转模块
        vm_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=VmMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        vm_pipeline.run_pipeline()
