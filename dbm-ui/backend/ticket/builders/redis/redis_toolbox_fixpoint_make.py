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

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import TicketType
from backend.utils.time import str2datetime


class RedisFixPointMakeDetailSerializer(serializers.Serializer):
    """定点构造"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        master_instances = serializers.ListField(help_text=_("master实例列表"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=True)
        recovery_time_point = DBTimezoneField(help_text=_("待构造时间点"))

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
                    _("集群{}: 主机数量({})不能大于实例数量({}).").format(cluster.immute_domain, host_count, instance_count)
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
                raise serializers.ValidationError(_("集群{}: 不支持部分实例构造.").format(cluster.immute_domain))

            now = datetime.datetime.now(timezone.utc)
            recovery_time_point = str2datetime(recovery_time_point)
            if recovery_time_point >= now or now - recovery_time_point > datetime.timedelta(days=15):
                raise serializers.ValidationError(_("集群{}: 构造时间最多向前追溯15天.").format(cluster.immute_domain))

            return attr

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisFixPointMakeParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_data_structure

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisFixPointMakeResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        # 申请的机器 和 现网集群同城即可， 无所谓是否 跨机房、同机房
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = id__cluster[info["cluster_id"]]
            info["resource_spec"]["redis"].update(
                affinity=AffinityEnum.NONE.value, location_spec={"city": cluster.region, "sub_zone_ids": []}
            )
            info.update(bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=self.ticket.bk_biz_id)

    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_DATA_STRUCTURE, is_apply=True)
class RedisFixPointMakeFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisFixPointMakeDetailSerializer
    inner_flow_builder = RedisFixPointMakeParamBuilder
    inner_flow_name = _("Redis 定点构造")
    resource_batch_apply_builder = RedisFixPointMakeResourceParamBuilder
