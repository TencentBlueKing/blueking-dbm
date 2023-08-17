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
import datetime

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType
from backend.utils.time import str2datetime


class RedisFixPointMakeDetailSerializer(serializers.Serializer):
    """定点构造"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        master_instances = serializers.ListField(help_text=_("master实例列表"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=True)
        recovery_time_point = serializers.CharField(help_text=_("待构造时间点"))

        def validate(self, attr):
            """业务逻辑校验"""
            master_instances = attr.get("master_instances")
            recovery_time_point = attr.get("recovery_time_point")
            resource_spec = attr.get("resource_spec")
            cluster = Cluster.objects.get(id=attr.get("cluster_id"))

            redis_instances = [s.ip_port for s in cluster.storageinstance_set.all()]
            host_count = resource_spec["redis"]["count"]
            instance_count = len(master_instances)
            if host_count > instance_count:
                raise serializers.ValidationError(
                    _(f"集群{cluster.immute_domain}: " f"主机数量({host_count})不能大于实例数量({instance_count}).")
                )

            # tendisplus 要求所有实例
            if (
                cluster.cluster_type
                in [
                    ClusterType.TendisPredixyTendisplusCluster,
                    ClusterType.TendisTwemproxyTendisplusIns,
                    ClusterType.TendisTendisplusInsance,
                    ClusterType.TendisTendisplusCluster,
                ]
                and len(master_instances) != len(redis_instances) / 2
            ):
                raise serializers.ValidationError(_(f"集群{cluster.immute_domain}: 不支持部分实例构造."))

            now = datetime.datetime.now()
            recovery_time_point = str2datetime(recovery_time_point)
            if recovery_time_point >= now or now - recovery_time_point > datetime.timedelta(days=15):
                raise serializers.ValidationError(_(f"集群{cluster.immute_domain}: 构造时间最多向前追溯15天."))

            return attr

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisFixPointMakeParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_data_structure

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisFixPointMakeResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_DATA_STRUCTURE)
class RedisFixPointMakeFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisFixPointMakeDetailSerializer
    inner_flow_builder = RedisFixPointMakeParamBuilder
    inner_flow_name = _("Redis 定点构造")
    resource_batch_apply_builder = RedisFixPointMakeResourceParamBuilder

    @property
    def need_itsm(self):
        return False
