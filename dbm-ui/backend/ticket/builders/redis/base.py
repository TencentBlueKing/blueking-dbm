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
import os

import humanize
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.core.storages.storage import get_storage
from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.db_services.redis.constants import KeyDeleteType
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import RedisTicketFlowBuilderPatchMixin
from backend.ticket.constants import CheckRepairFrequencyType, DataCheckRepairSettingType

KEY_FILE_PREFIX = "/redis/keyfiles"


class BaseRedisTicketFlowBuilder(RedisTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Redis.value


class RedisSingleOpsBaseDetailSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    def to_representation(self, details):
        return details

    def validate(self, attrs):
        """
        公共校验：集群操作互斥校验
        """
        super().validate(attrs)

        # TODO: 暂时忽略单据互斥，后续可能改为执行互斥
        try:
            cluster = Cluster.objects.get(id=attrs["cluster_id"])

            # 锁定检测
            if Cluster.is_exclusive(cluster.id, self.context["ticket_type"]):
                raise serializers.ValidationError(_("集群【{}({})】锁定中，请等待").format(cluster.name, cluster.id))
        except Cluster.DoesNotExist:
            raise serializers.ValidationError(_("集群【{}】不存在").format(attrs["cluster_id"]))

        return attrs


class RedisOpsBaseDetailSerializer(serializers.Serializer):
    # TODO: rules内部校验
    rules = serializers.JSONField(help_text=_("提取/删除/备份规则列表"))

    def to_representation(self, details):
        return details

    def validate(self, attrs):
        """
        公共校验：集群操作互斥校验
        """
        super().validate(attrs)
        return attrs


class RedisKeyBaseDetailSerializer(RedisOpsBaseDetailSerializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)
        ticket = self.context["ticket_ctx"].ticket

        # 提单，跳过信息补充
        if not ticket:
            return result

        # 查看单，补充key文件信息
        storage = get_storage()
        delete_type = result.get("delete_type")
        for rule in result["rules"]:
            if delete_type == KeyDeleteType.BY_FILES:
                rule["path"] = os.path.join(KEY_FILE_PREFIX, rule["path"])
            else:
                # 拼接key文件路径，集群维度存储
                biz_domain_name = f'{ticket.id}.{rule["domain"]}'
                rule["path"] = f"{KEY_FILE_PREFIX}/{biz_domain_name}"

            # 目录大小计算
            _, files = storage.listdir(rule["path"])
            rule["total_size"] = humanize.naturalsize(sum(f["size"] for f in files))

        return result


class RedisBasePauseParamBuilder(builders.PauseParamBuilder):
    """人工确认"""

    pass


class DataCheckRepairSettingSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=DataCheckRepairSettingType.get_choices(), allow_null=True, allow_blank=True)
    execution_frequency = serializers.ChoiceField(
        choices=CheckRepairFrequencyType.get_choices(), allow_null=True, allow_blank=True
    )


class RedisUpdateApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            group_num = info["resource_spec"]["backend_group"]["count"]
            shard_num = info["cluster_shard_num"]

            min_mem = min([g["master"]["bk_mem"] for g in info["backend_group"]])
            cluster_maxmemory = min_mem * group_num // shard_num
            min_disk = min([g["master"]["bk_disk"] for g in info["backend_group"]])
            cluster_max_disk = min_disk * group_num // shard_num

            info.update(
                # 分片大小, MB -> byte
                maxmemory=int(int(cluster_maxmemory) * 1024 * 1024),
                # 磁盘大小，单位是GB
                max_disk=int(cluster_max_disk),
                # 机器组数
                group_num=group_num,
                # 分片数
                shard_num=shard_num,
            )
        next_flow.save(update_fields=["details"])


class ClusterValidateMixin(object):
    """全局校验cluster状态"""

    @staticmethod
    def check_cluster_phase(cluster_id):

        if not isinstance(cluster_id, int):
            return cluster_id

        try:
            cluster = Cluster.objects.get(pk=cluster_id)
            if cluster.phase != ClusterPhase.ONLINE:
                raise serializers.ValidationError(_("集群{}已被禁用，请先启用!").format(cluster.immute_domain))
        except Cluster.DoesNotExist:
            raise serializers.ValidationError(_("集群{}不存在.").format(cluster_id))

        return cluster_id

    def validate_cluster_id(self, cluster_id):
        return self.check_cluster_phase(cluster_id)

    def validate_src_cluster(self, cluster_id):
        return self.check_cluster_phase(cluster_id)

    def validate_dst_cluster(self, cluster_id):
        return self.check_cluster_phase(cluster_id)
