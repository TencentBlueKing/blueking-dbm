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
from backend.flow.engine.bamboo.scene.qdrant.qdrant_base_flow import K8sQdrantBaseFlow
from backend.flow.plugins.components.collections.qdrant.apply_k8s_qdrant_clb import ApplyK8sQdrantClbComponent
from backend.flow.plugins.components.collections.qdrant.create_k8s_qdrant_cluster import (
    CreateK8sQdrantClusterComponent,
)
from backend.flow.plugins.components.collections.qdrant.expose_k8s_qdrant_service import (
    ExposeK8sQdrantServiceComponent,
)
from backend.flow.plugins.components.collections.qdrant.get_k8s_qdrant_clb_detail import GetK8sQdrantClbDetailComponent
from backend.flow.plugins.components.collections.qdrant.k8s_qdrant_sync_ticket_id import K8sQdrantSyncTicketIdComponent
from backend.flow.plugins.components.collections.qdrant.qdrant_db_meta import QdrantDBMetaComponent
from backend.flow.plugins.components.collections.qdrant.qdrant_dns_manage import QdrantDnsManageComponent
from backend.flow.plugins.components.collections.qdrant.qdrant_sync_cluster import QdrantSyncClusterComponent
from backend.flow.utils.qdrant.qdrant_context_dataclass import DnsKwargs, K8sQdrantActKwargs, K8sQdrantApplyContext

logger = logging.getLogger("flow")


class K8sQdrantApplyFlow(K8sQdrantBaseFlow):
    """
    构建qdrant申请流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

    def deploy_qdrant_flow(self):
        """
        部署qdrant集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        qdrant_pipeline = Builder(root_id=self.root_id, data=self.data)
        # trans_files = GetFileList(db_type=DBType.K8sQdrant)
        act_kwargs = K8sQdrantActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = K8sQdrantApplyContext.__name__

        # 调用dbs接口创建集群
        qdrant_pipeline.add_act(
            act_name=_("创建集群"), act_component_code=CreateK8sQdrantClusterComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs接口申请clb
        qdrant_pipeline.add_act(
            act_name=_("创建clb"), act_component_code=ApplyK8sQdrantClbComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs clb详情接口获取状态和vip
        qdrant_pipeline.add_act(
            act_name=_("查询CLB详情"), act_component_code=GetK8sQdrantClbDetailComponent.code, kwargs=asdict(act_kwargs)
        )

        # 添加域名
        domain_name = "qdrant.{}.{}.db".format(self.cluster_name, self.db_app_abbr)
        dns_kwargs = DnsKwargs(
            bk_cloud_id=self.bk_cloud_id,
            dns_op_type=DnsOpType.CREATE,
            domain_name=domain_name,
            dns_op_exec_port=6333,
        )
        qdrant_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=QdrantDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 将集群创建和域名绑定等信息同步到dbm
        qdrant_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=QdrantDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 将cluster_id回写给kbs
        qdrant_pipeline.add_act(
            act_name=_("回写集群ID"), act_component_code=QdrantSyncClusterComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs服务暴露接口暴露service
        qdrant_pipeline.add_act(
            act_name=_("暴露服务"), act_component_code=ExposeK8sQdrantServiceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 同步ticket_id给dbs
        qdrant_pipeline.add_act(
            act_name=_("同步ticketId"), act_component_code=K8sQdrantSyncTicketIdComponent.code, kwargs=asdict(act_kwargs)
        )

        qdrant_pipeline.run_pipeline()
