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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.core.notify.constants import MsgType
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import AffinityEnum, BaseOperateResourceParamBuilder, IpSource
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, Cluster, RedisOpsBaseDetailSerializer
from backend.ticket.constants import TicketStatus, TicketType


class RedisRollbackExerciseDetailSerializer(RedisOpsBaseDetailSerializer):
    """Redis backup rollback exercise serializer"""

    class RollbackExerciseInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        instance_ip = serializers.CharField(help_text=_("实例IP"))
        instance_port = serializers.IntegerField(help_text=_("实例端口"))
        recovery_time_point = serializers.CharField(help_text=_("恢复时间点"))
        task_id = serializers.IntegerField(help_text=_("任务记录ID"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    infos = serializers.ListSerializer(help_text=_("回滚演练信息"), child=RollbackExerciseInfoSerializer())
    drill_config = serializers.JSONField(help_text=_("演练设置"), required=True)
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"),
        choices=IpSource.get_choices(),
        default=IpSource.RESOURCE_POOL,
    )


class RedisRollbackExerciseParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_rollback_exercise

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisRollbackExerciseResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        infos = self.ticket_data["infos"]
        cluster_ids = [info["cluster_id"] for info in infos]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in infos:
            cluster: Cluster = id__cluster[info["cluster_id"]]
            info["resource_spec"]["redis"].update(
                affinity=AffinityEnum.NONE.value, location_spec={"city": cluster.region, "sub_zone_ids": []}
            )
            info.update(bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=self.ticket.bk_biz_id)

    def post_callback(self):
        """
        Set recycle_hosts after resource application but before inner flow starts.
        This ensures recycle_hosts is available when ticket_status_trigger is called with SUCCEEDED.
        """
        applied_hosts = []
        nodes = self.ticket_data.get("nodes", {})

        for hosts in nodes.values():
            for host in hosts:
                applied_hosts.append(
                    {
                        "bk_host_id": host["bk_host_id"],
                        "ip": host["ip"],
                        "bk_cloud_id": host["bk_cloud_id"],
                    }
                )

        if applied_hosts:
            self.ticket.details["recycle_hosts"] = ResourceHandler.standardized_resource_host(applied_hosts)
            self.ticket.details["immediate_recycle"] = True
            # Only send notification when recycle ticket fails, explicitly disable all other statuses
            self.ticket.details["send_msg_config"] = {
                status: {MsgType.RTX: True} if status == TicketStatus.FAILED else {}
                for status in TicketStatus.get_values()
            }
            self.ticket.save(update_fields=["details"])


@builders.BuilderFactory.register(
    TicketType.REDIS_ROLLBACK_EXERCISE,
    is_apply=True,
    is_recycle=True,
)
class RedisRollbackExerciseFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisRollbackExerciseDetailSerializer
    inner_flow_builder = RedisRollbackExerciseParamBuilder
    resource_batch_apply_builder = RedisRollbackExerciseResourceParamBuilder
    inner_flow_name = _("Redis 回档演练")
    default_need_itsm = False
    default_need_manual_confirm = False
