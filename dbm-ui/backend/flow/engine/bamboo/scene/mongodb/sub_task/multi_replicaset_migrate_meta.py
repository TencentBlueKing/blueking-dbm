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

from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.migrate_meta import cluster_migrate
from backend.flow.utils.mongodb.mongodb_migrate_dataclass import MigrateActKwargs


def multi_replicaset_migrate(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_kwargs: MigrateActKwargs,
) -> SubBuilder:
    """
    多个replicaset迁移元数据
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)
    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 多个replicaset迁移元数据——串行
    for replicaset_info in sub_get_kwargs.multi_replicaset_info:
        sub_get_kwargs.source_cluster_info = replicaset_info
        flow = cluster_migrate(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            cluster=False,
        )
        sub_pipeline.add_sub_pipeline(sub_flow=flow)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--复制集迁移元数据"))
