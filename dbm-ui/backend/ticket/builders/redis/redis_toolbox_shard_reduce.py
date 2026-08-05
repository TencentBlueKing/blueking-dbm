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
from backend.db_meta.models import Cluster, Machine
from backend.flow.engine.controller.redis import RedisController
from backend.flow.utils.redis.redis_proxy_util import get_major_version_by_version_name
from backend.flow.utils.redis.redis_util import get_tendisplus_shutdown_hosts
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    ClusterValidateMixin,
    RedisBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisShardReduceDetailSerializer(RedisBaseOperateDetailSerializer):
    """redis集群容量变更"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        shard_num = serializers.IntegerField(help_text=_("集群分片数"))
        group_num = serializers.IntegerField(help_text=_("部署机器组数"))
        current_group_num = serializers.IntegerField(help_text=_("当前组数"), required=False)
        spec_id = serializers.IntegerField(help_text=_("当前规格ID"), required=False)
        db_version = serializers.CharField(help_text=_("版本号"))
        capacity = serializers.FloatField(help_text=_("当前容量需求"))
        future_capacity = serializers.FloatField(help_text=_("未来容量需求"))
        update_mode = serializers.CharField(help_text=_("容量变更类型"), required=False)
        old_nodes = serializers.JSONField(help_text=_("主机回收信息"), required=False)
        row_key = serializers.CharField(help_text=_("唯一值"), required=False)

        def validate(self, attr):
            self.check_not_tendisplus_cluster(attr["cluster_id"], _("分片变更（Slot 迁移）"))
            return attr

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisShardReduceParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_slots_migrate_for_contraction

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["db_version"] = get_major_version_by_version_name(info["db_version"]) or info["db_version"]
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_SHARD_REDUCE, is_recycle=True, iam=ActionEnum.REDIS_MANAGE)
class RedisShardReduceFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisShardReduceDetailSerializer
    inner_flow_builder = RedisShardReduceParamBuilder
    inner_flow_name = _("Redis 集群减少分片数")
    need_patch_recycle_host_details = True
    validator = RedisController.redis_slots_migrate_for_contraction.validator

    def patch_ticket_detail(self):
        cluster_ids = [info["cluster_id"] for info in self.ticket.details["infos"]]
        id__cluster_type = {cluster.id: cluster.cluster_type for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket.details["infos"]:
            if id__cluster_type[info["cluster_id"]] in [
                ClusterType.TendisPredixyTendisplusCluster.value,
                ClusterType.TendisPredixyRedisCluster.value,
            ]:
                info["old_nodes"] = {}
                info["old_nodes"]["backend_hosts"] = []
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
