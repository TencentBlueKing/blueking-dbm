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

from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    ClusterValidateMixin,
    RedisBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisAddSlaveDetailSerializer(RedisBaseOperateDetailSerializer):
    """新建从库"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        pairs = serializers.ListField(help_text=_("主从切换对"), child=serializers.DictField())
        resource_spec = serializers.JSONField(required=False, help_text=_("资源申请信息"))
        old_nodes = serializers.JSONField(required=False, help_text=_("回收主机信息"))

        def validate(self, attr):
            """业务逻辑校验"""
            cluster = Cluster.objects.get(id=attr["cluster_ids"][0])
            for pair in attr["pairs"]:
                redis_master = pair["redis_master"]["bk_host_id"]
                if not StorageInstanceTuple.objects.filter(
                    ejector__machine__bk_host_id=redis_master,
                    receiver__instance_role=InstanceRole.REDIS_SLAVE,
                    receiver__status=InstanceStatus.UNAVAILABLE,
                ).exists():
                    raise serializers.ValidationError(_("集群{}不存在异常的从库主机").format(cluster.immute_domain))
            return attr

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisAddSlaveParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_add_slave

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisAddSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        for info in self.ticket_data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_ids"][0])

            redis_slaves = StorageInstance.objects.prefetch_related("as_receiver__ejector", "machine").filter(
                cluster=cluster, machine__ip__in=[host["redis_slave"]["ip"] for host in info["pairs"]]
            )
            slave_master_machine_map = {
                slave.machine.ip: [slave.as_receiver.get().ejector.machine] for slave in redis_slaves
            }
            for role in info["resource_spec"]:
                self.patch_common_affinity(
                    info,
                    role=role,
                    cluster=cluster,
                    exclusive_hosts=slave_master_machine_map.get(role.split("_")[-1], []),
                    tolerance=0,
                )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]

        for info_index, info in enumerate(ticket_data["infos"]):
            for pair in info["pairs"]:
                pair["redis_slave"] = info.pop(f"redis_slave_{pair['redis_slave']['ip']}", [])

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(
    TicketType.REDIS_CLUSTER_ADD_SLAVE, is_apply=True, is_recycle=True, iam=ActionEnum.REDIS_MANAGE
)
class RedisAddSlaveFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisAddSlaveDetailSerializer
    inner_flow_builder = RedisAddSlaveParamBuilder
    inner_flow_name = _("Redis 新建从库")
    resource_batch_apply_builder = RedisAddSlaveResourceParamBuilder
    default_need_itsm = False
    need_patch_recycle_host_details = True
