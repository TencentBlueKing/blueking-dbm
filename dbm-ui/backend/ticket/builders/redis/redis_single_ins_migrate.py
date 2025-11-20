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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.flow.utils.redis.redis_util import get_migrate_shutdown_hosts
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    fetch_cluster_ids,
)
from backend.ticket.builders.redis.base import BaseRedisInstanceTicketFlowBuilder, RedisBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class RedisSingleInsMigrateDetailSerializer(RedisBaseOperateDetailSerializer):
    class RedisSingleInsMigrateItemSerializer(DisplayInfoSerializer):
        db_version = serializers.CharField(help_text=_("Redis版本"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        migrate_domain = serializers.CharField(help_text=_("迁移的域名"), required=False)
        migrate_ip = serializers.CharField(help_text=_("迁移的ip"), required=False)
        migrate_type = serializers.CharField(help_text=_("迁移的类型"), required=False)
        origin_old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)
        src_cluster = serializers.ListField(child=serializers.JSONField(help_text=_("替换主机信息集合")))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("实例迁移单据详情"), child=RedisSingleInsMigrateItemSerializer())
    old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)

    def validate(self, attrs):
        self.validate_cluster_can_access(attrs)
        attrs = super().validate(attrs=attrs)
        return attrs

    def validate_cluster_can_access(self, attrs):
        """校验集群状态是否可以提单"""
        clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(details=attrs))

        for cluster in clusters:
            if cluster.cluster_type != ClusterType.RedisInstance:
                raise serializers.ValidationError(
                    _(f"Redis cluster[{cluster.id}] type is not {ClusterType.RedisInstance}")
                )


class RedisSingleInsMigrateBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_single_ins_migrate
    # validator = RedisController.redis_single_ins_migrate.validator

    def format_ticket_data(self):
        # 任取一个集群，补充云区域ID
        cluster = Cluster.objects.get(id=self.ticket_data["infos"][0]["src_cluster"][0]["cluster_id"])
        self.ticket_data.update(bk_cloud_id=cluster.bk_cloud_id)


class RedisSingleInstanceApplyResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        self.patch_info_affinity_location(roles=["backend_group"])

    def fetch_cluster_map(self, ticket_data):
        cluster_ids = fetch_cluster_ids(ticket_data)
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        cluster_id__cluster = {cluster.id: cluster for cluster in clusters}
        return cluster_id__cluster

    def patch_instance_migrate_info(self, ticket_data):
        """补充实例迁移的信息"""
        for index, info in enumerate(ticket_data["infos"]):
            info.update(
                dest_master=f'{info["backend_group"][0]["master"]["ip"]}',
                dest_slave=f'{info["backend_group"][0]["slave"]["ip"]}',
            )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        self.patch_instance_migrate_info(next_flow.details["ticket_data"])
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.REDIS_SINGLE_INS_MIGRATE, is_recycle=True)
class RedisSingleInsMigrateBuilder(BaseRedisInstanceTicketFlowBuilder):
    serializer = RedisSingleInsMigrateDetailSerializer
    inner_flow_builder = RedisSingleInsMigrateBuilder
    resource_batch_apply_builder = RedisSingleInstanceApplyResourceParamBuilder
    inner_flow_name = _("Redis 主从指定实例迁移")
    need_patch_recycle_host_details = True

    def patch_ticket_detail(self):
        instance_list = []
        for info in self.ticket.details["infos"]:
            for role in info["origin_old_nodes"]:
                instance_list.extend([f'{node["ip"]}:{node["port"]}' for node in info["origin_old_nodes"][role]])
        self.ticket.details["old_nodes"] = {
            "instance": get_migrate_shutdown_hosts(instance_list, self.ticket.bk_biz_id)
        }
        super().patch_ticket_detail()
