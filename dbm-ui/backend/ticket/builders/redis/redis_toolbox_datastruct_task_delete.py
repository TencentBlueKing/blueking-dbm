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
import operator
from functools import reduce

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import DestroyedStatus
from backend.db_meta.models import Cluster, Machine
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import DisplayInfoSerializer
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    RedisBaseOperateDetailSerializer,
    RedisBasePauseParamBuilder,
)
from backend.ticket.constants import TicketType


class RedisDataStructureTaskDeleteDetailSerializer(RedisBaseOperateDetailSerializer):
    """数据构造与实例销毁"""

    class InfoSerializer(DisplayInfoSerializer):
        task_id = serializers.IntegerField(help_text=_("构造记录主键"), required=False)
        related_rollback_bill_id = serializers.CharField(help_text=_("关联单据ID"), required=False)
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)

        def validate(self, attr):
            """业务逻辑校验"""
            attr = super().validate(attr)
            task = self._task_by_id(attr["task_id"]) if attr.get("task_id") else self._task_by_bill(attr)
            attr["task_id"] = task.id
            attr["prod_cluster"] = task.prod_cluster
            attr["cluster_id"] = task.prod_cluster_id
            attr["bk_cloud_id"] = task.bk_cloud_id
            attr["related_rollback_bill_id"] = task.related_rollback_bill_id
            return attr

        @staticmethod
        def _task_by_id(task_id: int) -> TbTendisRollbackTasks:
            try:
                task = TbTendisRollbackTasks.objects.get(id=task_id)
            except TbTendisRollbackTasks.DoesNotExist:
                raise serializers.ValidationError(_("构造记录{}不存在").format(task_id))
            if task.destroyed_status != DestroyedStatus.NOT_DESTROYED:
                raise serializers.ValidationError(_("构造记录{}不是未销毁状态").format(task_id))
            return task

        @staticmethod
        def _task_by_bill(attr: dict) -> TbTendisRollbackTasks:
            missing = [key for key in ("related_rollback_bill_id", "cluster_id", "bk_cloud_id") if key not in attr]
            if missing:
                raise serializers.ValidationError(_("未提供 task_id 时必须提供 {}").format(", ".join(missing)))
            try:
                prod_cluster = Cluster.objects.get(id=attr["cluster_id"])
            except Cluster.DoesNotExist:
                raise serializers.ValidationError(_("目标集群{}不存在，请确认.").format(attr["cluster_id"]))

            tasks = list(
                TbTendisRollbackTasks.objects.filter(
                    related_rollback_bill_id=attr["related_rollback_bill_id"],
                    prod_cluster=prod_cluster.immute_domain,
                    bk_cloud_id=attr["bk_cloud_id"],
                    destroyed_status=DestroyedStatus.NOT_DESTROYED,
                )[:2]
            )
            if not tasks:
                raise serializers.ValidationError(_("集群{}: 没有找到未销毁的实例.").format(prod_cluster.immute_domain))
            if len(tasks) > 1:
                raise serializers.ValidationError(
                    _("集群{}: 单据{}下有多条未销毁的构造记录，请改传 task_id").format(
                        prod_cluster.immute_domain, attr["related_rollback_bill_id"]
                    )
                )
            return tasks[0]

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())
    skip_connections_check = serializers.BooleanField(help_text=_("跳过请求检查"), default=False)


class RedisDataStructureTaskDeleteParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_data_structure_task_delete


@builders.BuilderFactory.register(TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE, is_recycle=True)
class RedisDataStructureTaskDeleteFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisDataStructureTaskDeleteDetailSerializer
    inner_flow_builder = RedisDataStructureTaskDeleteParamBuilder
    inner_flow_name = _("Redis 销毁构造实例")
    pause_node_builder = RedisBasePauseParamBuilder
    need_patch_recycle_host_details = True

    def patch_datastruct_delete_nodes(self):
        drop_machine_filters = []
        for info in self.ticket.details["infos"]:
            task = TbTendisRollbackTasks.objects.get(id=info["task_id"])
            # 过滤销毁实例的主机
            filters = [
                Q(bk_biz_id=task.bk_biz_id, bk_cloud_id=task.bk_cloud_id, ip=instance.split(":")[0])
                for instance in task.temp_instance_range
            ]
            drop_machine_filters.extend(filters)

        old_nodes = Machine.objects.filter(reduce(operator.or_, drop_machine_filters)).values("ip", "bk_host_id")
        self.ticket.details["old_nodes"] = {"datastruct_hosts": list(old_nodes)}

    def patch_ticket_detail(self):
        self.patch_datastruct_delete_nodes()
        super().patch_ticket_detail()
