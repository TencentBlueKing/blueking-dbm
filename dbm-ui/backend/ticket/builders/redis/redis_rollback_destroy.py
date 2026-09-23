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
from backend.db_meta.models import Machine
from backend.db_services.redis.rollback.constants import DATASTRUCTURE_VERSION, ROLLBACK_VERSION
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


class RedisRollbackDestroyDetailSerializer(RedisBaseOperateDetailSerializer):
    class InfoSerializer(DisplayInfoSerializer):
        task_id = serializers.IntegerField(help_text=_("构造记录主键"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)

        def validate(self, attr):
            attr = super().validate(attr)
            try:
                task = TbTendisRollbackTasks.objects.get(id=attr["task_id"])
            except TbTendisRollbackTasks.DoesNotExist:
                raise serializers.ValidationError(_("构造记录{}不存在").format(attr["task_id"]))
            version = getattr(task, "rollback_version", None) or DATASTRUCTURE_VERSION
            if version != ROLLBACK_VERSION:
                raise serializers.ValidationError(
                    _("记录 {} 是 {} 构造产物，请改用 REDIS_DATA_STRUCTURE_TASK_DELETE").format(task.id, version)
                )
            if task.destroyed_status != DestroyedStatus.NOT_DESTROYED:
                raise serializers.ValidationError(_("构造记录{}不是未销毁状态").format(task.id))
            attr["prod_cluster"] = task.prod_cluster
            attr["bk_cloud_id"] = task.bk_cloud_id
            attr["cluster_id"] = task.prod_cluster_id
            attr["related_rollback_bill_id"] = task.related_rollback_bill_id
            return attr

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())
    skip_connections_check = serializers.BooleanField(help_text=_("跳过请求检查"), default=False)


class RedisRollbackDestroyParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_rollback_destroy


@builders.BuilderFactory.register(TicketType.REDIS_ROLLBACK_DESTROY, is_recycle=True)
class RedisRollbackDestroyFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisRollbackDestroyDetailSerializer
    inner_flow_builder = RedisRollbackDestroyParamBuilder  # type: ignore
    inner_flow_name = _("Redis 备份恢复实例删除")  # type: ignore
    pause_node_builder = RedisBasePauseParamBuilder  # type: ignore
    need_patch_recycle_host_details = True

    def patch_rollback_destroy_nodes(self):
        drop_machine_filters = []
        for info in self.ticket.details["infos"]:
            task = TbTendisRollbackTasks.objects.get(id=info["task_id"])
            filters = [
                Q(bk_biz_id=task.bk_biz_id, bk_cloud_id=task.bk_cloud_id, ip=instance.split(":")[0])
                for instance in task.temp_instance_range
            ]
            drop_machine_filters.extend(filters)
        if not drop_machine_filters:
            self.ticket.details["old_nodes"] = {"datastruct_hosts": []}
            return
        old_nodes = Machine.objects.filter(reduce(operator.or_, drop_machine_filters)).values("ip", "bk_host_id")
        self.ticket.details["old_nodes"] = {"datastruct_hosts": list(old_nodes)}

    def patch_ticket_detail(self):
        self.patch_rollback_destroy_nodes()
        super().patch_ticket_detail()
