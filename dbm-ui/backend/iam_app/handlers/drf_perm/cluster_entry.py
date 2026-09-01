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

from typing import List

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id


class ClusterEntryPermission(ResourceActionPermission):
    """
    告警组相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        cluster_id = get_request_key_id(request, key="cluster_id")
        dbtype = ClusterType.cluster_type_to_db_type(Cluster.objects.get(id=cluster_id).cluster_type)
        self.resource_meta = getattr(ResourceEnum, dbtype.upper())
        return [cluster_id]
