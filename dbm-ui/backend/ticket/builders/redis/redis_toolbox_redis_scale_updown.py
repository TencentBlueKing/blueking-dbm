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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import RedisCapacityUpdateType
from backend.flow.engine.controller.redis import RedisController
from backend.flow.utils.redis.redis_proxy_util import get_major_version_by_version_name
from backend.flow.utils.redis.redis_util import get_tendisplus_shutdown_hosts
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostInfoSerializer,
    HostRecycleSerializer,
    SkipToRepresentationMixin,
)
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisScaleUpDownDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """redis集群容量变更"""

    class InfoSerializer(DisplayInfoSerializer, ClusterValidateMixin):
        class ResourceSpecSerializer(serializers.Serializer):
            class BackendGroupSerializer(serializers.Serializer):
                spec_id = serializers.IntegerField(help_text=_("规格ID"))
                count = serializers.IntegerField(help_text=_("数量"))
                affinity = serializers.ChoiceField(
                    help_text=_("亲和性"), choices=AffinityEnum.get_choices(), default=AffinityEnum.NONE
                )

            backend_group = BackendGroupSerializer()

        class OldNodesSerializer(serializers.Serializer):
            backend_hosts = serializers.ListSerializer(child=HostInfoSerializer(help_text=_("待下架的机器")))

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        shard_num = serializers.IntegerField(help_text=_("集群分片数"))
        group_num = serializers.IntegerField(help_text=_("部署机器组数"))
        db_version = serializers.CharField(help_text=_("版本号"))
        capacity = serializers.FloatField(help_text=_("当前容量需求"))
        future_capacity = serializers.FloatField(help_text=_("未来容量需求"))
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )
        update_mode = serializers.ChoiceField(
            help_text=_("容量变更类型"), choices=RedisCapacityUpdateType.get_choices(), required=False
        )
        resource_spec = ResourceSpecSerializer(help_text=_("资源申请"))
        old_nodes = OldNodesSerializer(help_text=_("下架机器"))

        def validate(self, attr):
            if attr["shard_num"] % attr["group_num"] != 0:
                raise serializers.ValidationError(_("所选方案分片数不能整除机器组数"))
            return attr

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisScaleUpDownParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_backend_scale

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["db_version"] = get_major_version_by_version_name(info["db_version"]) or info["db_version"]
        super().format_ticket_data()


class RedisScaleUpDownResourceParamBuilder(BaseOperateResourceParamBuilder):
    allow_resource_empty = True

    def format(self):
        self.patch_info_affinity_location(roles=["backend_group"])

    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_SCALE_UPDOWN, is_apply=True, is_recycle=True)
class RedisScaleUpDownFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisScaleUpDownDetailSerializer
    inner_flow_builder = RedisScaleUpDownParamBuilder
    inner_flow_name = _("Redis 集群容量变更")
    resource_batch_apply_builder = RedisScaleUpDownResourceParamBuilder
    need_patch_recycle_host_details = True

    def patch_ticket_detail(self):
        cluster_ids = [info["cluster_id"] for info in self.ticket.details["infos"]]
        id__cluster_type = {cluster.id: cluster.cluster_type for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket.details["infos"]:
            if id__cluster_type[info["cluster_id"]] == ClusterType.TendisPredixyTendisplusCluster.value:

                shutdown_master_hosts, shutdown_slave_hosts = get_tendisplus_shutdown_hosts(
                    info["cluster_id"], info["group_num"], info["update_mode"]
                )
                info.update(
                    {"shutdown_master_hosts": shutdown_master_hosts, "shutdown_slave_hosts": shutdown_slave_hosts}
                )
                # 主从主机一一对应，只需要判断主即可
                if not shutdown_master_hosts:
                    continue
                machine_ips = shutdown_master_hosts + shutdown_slave_hosts
                machine_infos = Machine.objects.filter(ip__in=machine_ips, bk_cloud_id=info["bk_cloud_id"]).values(
                    "ip", "bk_biz_id", "bk_host_id", "bk_cloud_id"
                )
                info["old_nodes"]["backend_hosts"].extend(machine_infos)

        self.ticket.save(update_fields=["details"])
        super().patch_ticket_detail()
