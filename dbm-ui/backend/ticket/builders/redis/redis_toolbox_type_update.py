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
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.version.utils import query_versions_by_key
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    ClusterValidateMixin,
    DataCheckRepairSettingSerializer,
    RedisUpdateApplyResourceParamBuilder,
)
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisTypeUpdateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """集群类型变更"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        class ResourceSpecSerializer(serializers.Serializer):
            class SpecSerializer(serializers.Serializer):
                spec_id = serializers.IntegerField(help_text=_("规格ID"))
                count = serializers.IntegerField(help_text=_("数量"))
                affinity = serializers.ChoiceField(
                    help_text=_("亲和性"), choices=AffinityEnum.get_choices(), default=AffinityEnum.NONE
                )

            proxy = SpecSerializer(help_text=_("申请proxy资源"))
            backend_group = SpecSerializer(help_text=_("申请redis主从资源"))

        src_cluster = serializers.IntegerField(help_text=_("集群ID"))
        current_spec_id = serializers.IntegerField(help_text=_("当前规格ID"))
        current_shard_num = serializers.IntegerField(help_text=_("当前分片数"))
        cluster_shard_num = serializers.IntegerField(help_text=_("目标分片数"))
        current_cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), help_text=_("当前集群类型"))
        target_cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), help_text=_("目标集群类型"))
        resource_spec = ResourceSpecSerializer(help_text=_("资源申请"))
        capacity = serializers.IntegerField(help_text=_("当前容量需求"))
        future_capacity = serializers.IntegerField(help_text=_("未来容量需求"))
        db_version = serializers.CharField(help_text=_("版本号"))
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )

        def validate(self, attr):
            """业务逻辑校验"""
            cluster = Cluster.objects.get(id=attr.get("src_cluster"))
            if cluster.cluster_type == attr.get("target_cluster_type"):
                raise serializers.ValidationError(
                    _("集群({})：目标类型({})和原始类型({})相同.").format(
                        cluster.immute_domain,
                        attr.get("target_cluster_type"),
                        cluster.cluster_type,
                    )
                )

            if attr.get("db_version") not in query_versions_by_key(attr.get("target_cluster_type")):
                raise serializers.ValidationError(
                    _("集群({})：{} 类集群不支持版本 {}.").format(
                        cluster.immute_domain,
                        attr.get("target_cluster_type"),
                        attr.get("db_version"),
                    )
                )

            return attr

    data_check_repair_setting = DataCheckRepairSettingSerializer()
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer(), allow_empty=False)


class RedisTypeUpdateParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_type_update

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisTypeUpdateResourceParamBuilder(RedisUpdateApplyResourceParamBuilder):
    def format(self):
        # 亲和性进一步细化：申请的 接入层  至少 1/2 不同机房， 存储层 master 和他的 slave 不能一个机房;
        self.patch_info_affinity_location(roles=["backend_group", "proxy"])
        for info in self.ticket_data["infos"]:
            info["resource_spec"]["proxy"]["group_count"] = 2


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_TYPE_UPDATE, is_apply=True)
class RedisTypeUpdateFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisTypeUpdateDetailSerializer
    inner_flow_builder = RedisTypeUpdateParamBuilder
    inner_flow_name = _("Redis 集群类型变更")
    resource_batch_apply_builder = RedisTypeUpdateResourceParamBuilder
