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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.qdrant.qdrant_base_flow import K8sQdrantBaseFlow
from backend.flow.plugins.components.collections.qdrant.k8s_qdrant_restart import RestartK8sQdrantComponent
from backend.flow.plugins.components.collections.qdrant.k8s_qdrant_sync_ticket_id import K8sQdrantSyncTicketIdComponent
from backend.flow.utils.qdrant.qdrant_context_dataclass import K8sQdrantActKwargs, K8sQdrantApplyContext


class K8sQdrantRestartFlow(K8sQdrantBaseFlow):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

    def deploy_qdrant_flow(self):
        """
        重启qdrant集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        qdrant_pipeline = Builder(root_id=self.root_id, data=self.data)
        # trans_files = GetFileList(db_type=DBType.K8sQdrant)
        act_kwargs = K8sQdrantActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = K8sQdrantApplyContext.__name__

        # 调用dbs重启接口
        qdrant_pipeline.add_act(
            act_name=_("重启Qdrant集群"), act_component_code=RestartK8sQdrantComponent.code, kwargs=asdict(act_kwargs)
        )

        # 同步ticketId给dbs
        qdrant_pipeline.add_act(
            act_name=_("同步ticketId"), act_component_code=K8sQdrantSyncTicketIdComponent.code, kwargs=asdict(act_kwargs)
        )

        qdrant_pipeline.run_pipeline()
