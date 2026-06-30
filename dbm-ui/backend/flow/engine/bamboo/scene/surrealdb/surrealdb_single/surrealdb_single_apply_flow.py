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

from django.utils.translation import gettext as _

from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_single.surrealdb_single_base_flow import (
    K8sSurrealDBSingleBaseFlow,
)
from backend.flow.plugins.components.collections.surrealdb.surrealdb_apply_clb import ApplySurrealDBClbComponent
from backend.flow.plugins.components.collections.surrealdb.surrealdb_clb_detail import GetSurrealDBClbDetailComponent
from backend.flow.plugins.components.collections.surrealdb.surrealdb_dns_manage import SurrealDBDnsManageComponent
from backend.flow.plugins.components.collections.surrealdb.surrealdb_expose_service import (
    ExposeSurrealDBServiceComponent,
)
from backend.flow.plugins.components.collections.surrealdb.surrealdb_single.deploy_surrealdb_single import (
    DeploySurrealDBSingleComponent,
)
from backend.flow.plugins.components.collections.surrealdb.surrealdb_single.surrealdb_meta import (
    SurrealDBMetaComponent,
)
from backend.flow.plugins.components.collections.surrealdb.surrealdb_sync_cluster import SurrealDBSyncClusterComponent
from backend.flow.plugins.components.collections.surrealdb.surrealdb_sync_ticket_id import (
    SurrealDBSyncTicketIdComponent,
)
from backend.flow.utils.surrealdb.consts import DOMAIN_PREFIX, SURREALDB_PORT
from backend.flow.utils.surrealdb.surrealdb_single.surrealdb_context_dataclass import (
    DnsKwargs,
    K8sSurrealDBSingleActKwargs,
    K8sSurrealDBSingleApplyContext,
)

logger = logging.getLogger("flow")


class K8sSurrealDBSingleApplyFlow(K8sSurrealDBSingleBaseFlow):
    """
    构建 surrealdb 单机版申请流程
    """

    def deploy_surrealdb_flow(self):
        """
        部署 surrealdb 集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        surrealdb_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = K8sSurrealDBSingleActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = K8sSurrealDBSingleApplyContext.__name__

        # 调用 dbs 接口创建集群
        surrealdb_pipeline.add_act(
            act_name=_("创建集群"), act_component_code=DeploySurrealDBSingleComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用 dbs 接口申请clb
        surrealdb_pipeline.add_act(
            act_name=_("创建 clb"), act_component_code=ApplySurrealDBClbComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs clb详情接口获取状态和vip
        surrealdb_pipeline.add_act(
            act_name=_("查询 CLB 详情"),
            act_component_code=GetSurrealDBClbDetailComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 添加域名
        domain_name = f"{DOMAIN_PREFIX}.{self.cluster_name}.{self.db_app_abbr}.db"
        dns_kwargs = DnsKwargs(
            bk_cloud_id=self.bk_cloud_id,
            dns_op_type=DnsOpType.CREATE,
            domain_name=domain_name,
            dns_op_exec_port=SURREALDB_PORT,
        )
        surrealdb_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=SurrealDBDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 将集群创建和域名绑定等信息同步到dbm
        surrealdb_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=SurrealDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 将cluster_id 回写给 dbs
        surrealdb_pipeline.add_act(
            act_name=_("回写集群ID"), act_component_code=SurrealDBSyncClusterComponent.code, kwargs=asdict(act_kwargs)
        )

        # 调用dbs服务暴露接口暴露service
        surrealdb_pipeline.add_act(
            act_name=_("暴露服务"), act_component_code=ExposeSurrealDBServiceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 同步ticket_id到 dbs
        surrealdb_pipeline.add_act(
            act_name=_("同步ticketId"),
            act_component_code=SurrealDBSyncTicketIdComponent.code,
            kwargs=asdict(act_kwargs),
        )

        surrealdb_pipeline.run_pipeline()
