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
from backend.flow.plugins.components.collections.k8s_vm.apply_k8s_vm_vminsert_clb import ApplyK8sVmVminsertClbComponent
from backend.flow.plugins.components.collections.k8s_vm.apply_k8s_vm_vmselect_clb import ApplyK8sVmVmselectClbComponent
from backend.flow.plugins.components.collections.k8s_vm.create_k8s_vm_cluster import CreateK8sVmClusterComponent
from backend.flow.plugins.components.collections.k8s_vm.expose_k8s_vm_vminsert_service import (
    ExposeK8sVmVminsertServiceComponent,
)
from backend.flow.plugins.components.collections.k8s_vm.expose_k8s_vm_vmselect_service import (
    ExposeK8sVmVmselectServiceComponent,
)
from backend.flow.plugins.components.collections.k8s_vm.get_k8s_vm_vminsert_clb_detail import (
    GetK8sVmVminsertClbDetailComponent,
)
from backend.flow.plugins.components.collections.k8s_vm.get_k8s_vm_vmselect_clb_detail import (
    GetK8sVmVmselectClbDetailComponent,
)
from backend.flow.plugins.components.collections.k8s_vm.k8s_vm_sync_ticket_id import K8sVmSyncTicketIdComponent
from backend.flow.plugins.components.collections.k8s_vm.vm_db_meta import VmDBMetaComponent
from backend.flow.plugins.components.collections.k8s_vm.vm_sync_cluster import VmSyncClusterComponent
from backend.flow.plugins.components.collections.k8s_vm.vm_vminsert_dns_manage import VmVminsertDnsManageComponent
from backend.flow.plugins.components.collections.k8s_vm.vm_vmselect_dns_manage import VmVmselectDnsManageComponent
from backend.flow.utils.k8s_vm.consts import (
    VMINSERT_DOMAIN_PREFIX,
    VMINSERT_PORT,
    VMSELECT_DOMAIN_PREFIX,
    VMSELECT_PORT,
)
from backend.flow.utils.k8s_vm.k8s_vm_context_dataclass import DnsKwargs, K8sVmActKwargs, K8sVmApplyContext

logger = logging.getLogger("flow")


class K8sVmApplyFlow(K8sVmBaseFlow):
    """
    构建k8s vm申请流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

    def deploy_vm_flow(self):
        """
        部署k8s vm集群
        """
        vm_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = K8sVmActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = K8sVmApplyContext.__name__

        # 调用dbs接口创建集群
        vm_pipeline.add_act(
            act_name=_("创建集群"), act_component_code=CreateK8sVmClusterComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs接口申请vminsert clb
        vm_pipeline.add_act(
            act_name=_("创建vminsert CLB"),
            act_component_code=ApplyK8sVmVminsertClbComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 调用dbs接口申请vmselect clb
        vm_pipeline.add_act(
            act_name=_("创建vmselect CLB"),
            act_component_code=ApplyK8sVmVmselectClbComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 调用dbs clb详情接口获取vminsert状态和vip
        vm_pipeline.add_act(
            act_name=_("查询vminsert CLB详情"),
            act_component_code=GetK8sVmVminsertClbDetailComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 调用dbs clb详情接口获取vmselect状态和vip
        vm_pipeline.add_act(
            act_name=_("查询vmselect CLB详情"),
            act_component_code=GetK8sVmVmselectClbDetailComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 添加vminsert域名
        vminsert_domain = "{}.{}.{}.db".format(VMINSERT_DOMAIN_PREFIX, self.cluster_name, self.db_app_abbr)
        vminsert_dns_kwargs = DnsKwargs(
            bk_cloud_id=self.bk_cloud_id,
            dns_op_type=DnsOpType.CREATE,
            domain_name=vminsert_domain,
            dns_op_exec_port=VMINSERT_PORT,
        )
        vm_pipeline.add_act(
            act_name=_("添加vminsert域名"),
            act_component_code=VmVminsertDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(vminsert_dns_kwargs)},
        )

        # 添加vmselect域名
        vmselect_domain = "{}.{}.{}.db".format(VMSELECT_DOMAIN_PREFIX, self.cluster_name, self.db_app_abbr)
        vmselect_dns_kwargs = DnsKwargs(
            bk_cloud_id=self.bk_cloud_id,
            dns_op_type=DnsOpType.CREATE,
            domain_name=vmselect_domain,
            dns_op_exec_port=VMSELECT_PORT,
        )
        vm_pipeline.add_act(
            act_name=_("添加vmselect域名"),
            act_component_code=VmVmselectDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(vmselect_dns_kwargs)},
        )

        # 将集群创建和域名绑定等信息同步到dbm
        vm_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=VmDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 将cluster_id回写给dbs
        vm_pipeline.add_act(
            act_name=_("回写集群ID"), act_component_code=VmSyncClusterComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs服务暴露接口暴露vminsert service
        vm_pipeline.add_act(
            act_name=_("暴露vminsert服务"),
            act_component_code=ExposeK8sVmVminsertServiceComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 调用dbs服务暴露接口暴露vmselect service
        vm_pipeline.add_act(
            act_name=_("暴露vmselect服务"),
            act_component_code=ExposeK8sVmVmselectServiceComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 同步ticket_id给dbs
        vm_pipeline.add_act(
            act_name=_("同步ticketId"), act_component_code=K8sVmSyncTicketIdComponent.code, kwargs=asdict(act_kwargs)
        )

        vm_pipeline.run_pipeline()
