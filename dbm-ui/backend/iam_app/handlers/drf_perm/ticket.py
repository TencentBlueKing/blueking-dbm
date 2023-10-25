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

import logging

from backend.db_meta.models import ExtraProcessInstance
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import TicketType
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("root")


class CreateTicketPermission(ResourceActionPermission):
    """
    创建单据相关动作鉴权
    """

    def __init__(self, ticket_type: TicketType) -> None:
        self.ticket_type = ticket_type
        action = BuilderFactory.ticket_type__iam_action.get(ticket_type)
        actions = [action] if action else []
        # 默认只考虑关联一种资源
        resource_meta = action.related_resource_types[0] if action else None

        if resource_meta == ResourceEnum.INFLUXDB:
            # 对于influxdb没有集群概念，特殊考虑
            instance_ids_getter = self.instance_influxdb_ids_getter
        elif resource_meta == ResourceEnum.BUSINESS:
            instance_ids_getter = self.instance_biz_ids_getter
        elif action in ActionEnum.get_match_actions("tbinlogdumper"):
            # 对应dumper相关操作，需要根据dumper的实例ID反查出相关的集群
            instance_ids_getter = self.instance_dumper_cluster_ids_getter
        else:
            instance_ids_getter = self.instance_cluster_ids_getter

        super().__init__(actions, resource_meta, instance_ids_getter=instance_ids_getter)

    def instance_biz_ids_getter(self, request, view):
        return [request.data["bk_biz_id"]]

    def instance_cluster_ids_getter(self, request, view):
        # 集群ID从details解析，如果没有detail(比如sql模拟执行)，则直接取request.data
        details = request.data.get("details") or request.data
        cluster_key_fields = ["cluster_id", "cluster_ids", "src_cluster", "dst_cluster"]
        cluster_ids = get_target_items_from_details(details, match_keys=cluster_key_fields)
        # 排除非int型的cluster id(比如redis的构造实例恢复集群使用ip表示的)
        cluster_ids = [int(id) for id in cluster_ids if isinstance(id, int) or (isinstance(id, str) and id.isdigit())]
        return cluster_ids

    def instance_influxdb_ids_getter(self, request, view):
        details = request.data.get("details") or request.data
        return get_target_items_from_details(details, match_keys=["instance_id", "instance_ids"])

    def instance_dumper_cluster_ids_getter(self, request, view):
        details = request.data.get("details") or request.data
        dumper_instance_ids = details.get("dumper_instance_ids", [])
        cluster_ids = list(
            ExtraProcessInstance.objects.filter(id__in=dumper_instance_ids).values_list("cluster_id", flat=True)
        )
        return cluster_ids
