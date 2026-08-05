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

from django.utils.translation import gettext as _

from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.k8s_vm.k8s_vm_base_flow import K8sVmBaseFlow
from backend.flow.plugins.components.collections.k8s_vm.k8s_vm_delete import K8sVmDeleteComponent
from backend.flow.plugins.components.collections.k8s_vm.k8s_vm_sync_ticket_id import K8sVmSyncTicketIdComponent
from backend.flow.plugins.components.collections.k8s_vm.vm_db_meta import VmDBMetaComponent
from backend.flow.plugins.components.collections.k8s_vm.vm_dns_manage import VmDnsManageComponent
from backend.flow.utils.k8s_vm.k8s_vm_context_dataclass import (
    DnsKwargs,
    K8sVmActKwargs,
    K8sVmApplyContext,
)

logger = logging.getLogger("flow")


class K8sVmDeleteFlow(K8sVmBaseFlow):
    """
    构建k8s vm删除流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

    def deploy_vm_flow(self):
        """
        删除k8s vm集群
        """
        vm_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = K8sVmActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = K8sVmApplyContext.__name__

        # 调用dbs删除接口(关闭删除保护 -> 等待生效 -> 删除集群)
        vm_pipeline.add_act(
            act_name=_("删除VictoriaMetrics集群"),
            act_component_code=K8sVmDeleteComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 清理域名(按cluster_id级联清理vminsert/vmselect双域名)
        dns_kwargs = DnsKwargs(bk_cloud_id=self.bk_cloud_id, dns_op_type=DnsOpType.CLUSTER_DELETE)
        vm_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=VmDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 将集群删除同步到dbm
        vm_pipeline.add_act(
            act_name=_("修改Meta"),
            act_component_code=VmDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 同步ticket_id给dbs
        vm_pipeline.add_act(
            act_name=_("同步ticketId"),
            act_component_code=K8sVmSyncTicketIdComponent.code,
            kwargs=asdict(act_kwargs),
        )

        vm_pipeline.run_pipeline()
