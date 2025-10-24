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
from collections import defaultdict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.flow.utils.redis.redis_util import get_migrate_shutdown_hosts
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, DisplayInfoSerializer
from backend.ticket.builders.redis.base import BaseRedisInstanceTicketFlowBuilder, RedisBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class RedisClusterInsMigrateDetailSerializer(RedisBaseOperateDetailSerializer):
    class RedisClusterInsMigrateItemSerializer(DisplayInfoSerializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        origin_old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)
        migrate_instance = serializers.CharField(help_text=_("迁移的实例"), required=False)
        db_version = serializers.ListField(help_text=_("集群版本"), child=serializers.CharField())

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("实例迁移单据详情"), child=RedisClusterInsMigrateItemSerializer())
    old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs=attrs)
        return attrs


class RedisClusterInsMigrateBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_ins_migrate
    # validator = RedisController.redis_cluster_ins_migrate.validator

    def format_ticket_data(self):
        # 任取一个集群，补充云区域ID
        cluster = Cluster.objects.get(id=self.ticket_data["infos"][0]["cluster_id"])
        self.ticket_data.update(bk_cloud_id=cluster.bk_cloud_id)


class RedisClusterInstanceApplyResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        self.patch_info_affinity_location(roles=["backend_group"])

    def get_master_slave_map(self, origin_old_nodes):
        master_slave_map = {}
        for master in origin_old_nodes["master"]:
            for slave in origin_old_nodes["slave"]:
                if master["port"] == slave["port"]:
                    master_slave_map[f'{master["ip"]}:{master["port"]}'] = f'{slave["ip"]}:{slave["port"]}'
                    break
        return master_slave_map

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        cluster__migrate_list_map = defaultdict(list)
        # 按照集群ID进行聚合
        for info in ticket_data["infos"]:
            master_slave_map = self.get_master_slave_map(info["origin_old_nodes"])
            migrate_info = [
                {
                    "resource_spec": info["resource_spec"],
                    "src_master": master,
                    "src_slave": slave,
                    "dest_master": f'{info["backend_group"][0]["master"]["ip"]}',
                    "dest_slave": f'{info["backend_group"][0]["slave"]["ip"]}',
                }
                for master, slave in master_slave_map.items()
            ]
            cluster__migrate_list_map[info["cluster_id"]].extend(migrate_info)
        # 平铺聚合信息
        ticket_data["infos"] = [
            {"cluster_id": cluster_id, "migrate_list": migrate_list}
            for cluster_id, migrate_list in cluster__migrate_list_map.items()
        ]
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_INS_MIGRATE, is_recycle=True)
class RedisClusterInsMigrateBuilder(BaseRedisInstanceTicketFlowBuilder):
    serializer = RedisClusterInsMigrateDetailSerializer
    inner_flow_builder = RedisClusterInsMigrateBuilder
    resource_batch_apply_builder = RedisClusterInstanceApplyResourceParamBuilder
    inner_flow_name = _("Redis 集群指定实例迁移")
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
