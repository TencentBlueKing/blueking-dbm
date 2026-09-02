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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.surrealdb.surrealdb_base_flow import K8sSurrealDBBaseFlow
from backend.flow.plugins.components.collections.surrealdb.surrealdb_destroy import DestroySurrealDBComponent
from backend.flow.plugins.components.collections.surrealdb.surrealdb_dns_manage import SurrealDBDnsManageComponent
from backend.flow.plugins.components.collections.surrealdb.surrealdb_single.surrealdb_meta import (
    SurrealDBMetaComponent,
)
from backend.flow.plugins.components.collections.surrealdb.surrealdb_sync_ticket_id import (
    SurrealDBSyncTicketIdComponent,
)
from backend.flow.utils.k8s_db.surrealdb.surrealdb_context_dataclass import (
    DnsKwargs,
    K8sSurrealDBActKwargs,
    K8sSurrealDBApplyContext,
)


class K8sSurrealDBDestroyFlow(K8sSurrealDBBaseFlow):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

    def destroy_surrealdb_flow(self):
        """
        删除surrealdb集群
        """
        surrealdb_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = K8sSurrealDBActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = K8sSurrealDBApplyContext.__name__

        # 调用dbs删除接口
        surrealdb_pipeline.add_act(
            act_name=_("删除SurrealDB集群"), act_component_code=DestroySurrealDBComponent.code, kwargs=asdict(act_kwargs)
        )

        # 清理域名
        dns_kwargs = DnsKwargs(bk_cloud_id=self.bk_cloud_id, dns_op_type=DnsOpType.CLUSTER_DELETE)
        surrealdb_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=SurrealDBDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        surrealdb_pipeline.add_act(
            act_name=_("修改Meta"), act_component_code=SurrealDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 同步ticketId给dbs
        surrealdb_pipeline.add_act(
            act_name=_("同步ticketId"), act_component_code=SurrealDBSyncTicketIdComponent.code, kwargs=asdict(act_kwargs)
        )

        surrealdb_pipeline.run_pipeline()
