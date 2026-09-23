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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.redis.rollback.constants import CACHE_CLUSTER_TYPES
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    ClusterValidateMixin,
    RedisBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class ShardSelectionSerializer(serializers.Serializer):
    shard_value = serializers.CharField(help_text=_("该批次当时的分片"))
    round_key = serializers.CharField(help_text=_("轮次"), required=False, allow_blank=True, default="")


class RedisRollbackDetailSerializer(RedisBaseOperateDetailSerializer):
    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=True)
        backup_identify = serializers.CharField(help_text=_("备份批次"), required=True)
        shards = serializers.ListField(
            help_text=_("勾选的分片与轮次，为空表示该批次全部分片取最新一轮"),
            child=ShardSelectionSerializer(),
            required=False,
            allow_empty=True,
        )
        key_white_regex = serializers.CharField(help_text=_("key白名单"), required=False, allow_blank=True, default="")
        key_black_regex = serializers.CharField(help_text=_("key黑名单"), required=False, allow_blank=True, default="")

        def validate(self, attr):
            attr = super().validate(attr)
            cluster = Cluster.objects.get(id=attr.get("cluster_id"))
            if cluster.cluster_type not in CACHE_CLUSTER_TYPES:
                raise serializers.ValidationError(
                    _("集群{} 类型{} 非 Cache，请改用 REDIS_DATA_STRUCTURE 单据").format(
                        cluster.immute_domain, cluster.cluster_type
                    )
                )

            # Host count constraints are evaluated by planner.build(pack=True).
            try:
                RollbackPlanner(cluster, attr).build(pack=True)
            except RollbackPlanError as exc:
                raise serializers.ValidationError(getattr(exc, "message", str(exc)))
            return attr

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())
    skip_mannual_confirm = serializers.BooleanField(help_text=_("跳过人工确认"), default=False)
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )


class RedisRollbackParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_rollback

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisRollbackResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
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


@builders.BuilderFactory.register(TicketType.REDIS_ROLLBACK, is_apply=True)
class RedisRollbackFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisRollbackDetailSerializer
    inner_flow_builder = RedisRollbackParamBuilder  # type: ignore
    inner_flow_name = _("Redis 备份恢复")  # type: ignore
    resource_batch_apply_builder = RedisRollbackResourceParamBuilder  # type: ignore
