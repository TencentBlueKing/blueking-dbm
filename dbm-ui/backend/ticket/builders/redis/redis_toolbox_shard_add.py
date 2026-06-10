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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.flow.utils.redis.redis_proxy_util import get_major_version_by_version_name
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    ClusterValidateMixin,
    RedisBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisShardAddDetailSerializer(RedisBaseOperateDetailSerializer):
    """redis集群容量变更"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        shard_num = serializers.IntegerField(help_text=_("集群分片数"))
        group_num = serializers.IntegerField(help_text=_("部署机器组数"))
        db_version = serializers.CharField(help_text=_("版本号"))
        capacity = serializers.FloatField(help_text=_("当前容量需求"))
        future_capacity = serializers.FloatField(help_text=_("未来容量需求"))
        update_mode = serializers.CharField(help_text=_("容量变更类型"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源申请"))
        row_key = serializers.CharField(help_text=_("唯一值"), required=False)

        def validate(self, attr):
            self.check_not_tendisplus_cluster(attr["cluster_id"], _("分片变更（Slot 迁移）"))
            return attr

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisShardAddParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_slots_migrate_for_expansion

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["db_version"] = get_major_version_by_version_name(info["db_version"]) or info["db_version"]
        super().format_ticket_data()


class RedisShardAddResourceParamBuilder(BaseOperateResourceParamBuilder):
    allow_resource_empty = True

    def format(self):
        self.patch_info_common_affinity(role="backend_group", tolerance=0)

    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_SHARD_ADD, is_apply=True)
class RedisShardAddFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisShardAddDetailSerializer
    inner_flow_builder = RedisShardAddParamBuilder
    inner_flow_name = _("Redis 集群增加分片数")
    resource_batch_apply_builder = RedisShardAddResourceParamBuilder
    validator = RedisController.redis_slots_migrate_for_expansion.validator
