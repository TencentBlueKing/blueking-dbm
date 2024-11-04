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
from typing import Dict

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum, DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate, SkipToRepresentationMixin
from backend.ticket.builders.redis.base import BaseRedisInstanceTicketFlowBuilder
from backend.ticket.constants import TicketType


class RedisInstanceApplyDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    class InstanceInfoSerializer(serializers.Serializer):
        cluster_name = serializers.CharField(help_text=_("集群ID（英文数字及下划线）"))
        databases = serializers.IntegerField(help_text=_("db数量"))
        backend_group = serializers.JSONField(help_text=_("追加部署的主机信息"), required=False)

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(help_text=_("城市代码"), required=False)
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )

    port = serializers.IntegerField(help_text=_("集群端口"), required=False)
    redis_pwd = serializers.CharField(help_text=_("访问密码"), required=False)
    db_version = serializers.CharField(help_text=_("版本号"), required=False)
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    infos = serializers.ListSerializer(help_text=_("集群信息"), child=InstanceInfoSerializer())

    resource_spec = serializers.JSONField(help_text=_("proxy部署方案"), required=False)
    ip_source = serializers.CharField(help_text=_("主机来源"), required=False, default=IpSource.RESOURCE_POOL)
    append_apply = serializers.BooleanField(help_text=_("是否是追加部署"))

    city_name = serializers.SerializerMethodField(help_text=_("城市名"))

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def validate(self, attrs):
        # 集群名校验
        bk_biz_id, ticket_type = self.context["bk_biz_id"], self.context["ticket_type"]
        for info in attrs["infos"]:
            CommonValidate.validate_duplicate_cluster_name(bk_biz_id, ticket_type, info["cluster_name"])

        # 新部署机器组数要整除集群数
        if not attrs["append_apply"]:
            machine_group = attrs["resource_spec"]["backend_group"]["count"]
            cluster_num = len(attrs["infos"])
            if cluster_num % machine_group:
                raise serializers.ValidationError(_("请保证机器组数{}能整除集群数{}").format(machine_group, cluster_num))

        return attrs


class RedisInstanceApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_instance_apply_scene

    def format_common_cluster_info(self):
        """补充部署redis主从集群通用信息"""
        for info in self.ticket_data["infos"]:
            # 生成随机密码，密码强度符合平台密码策略
            redis_pwd = self.ticket_data.get("redis_pwd") or DBPasswordHandler.get_random_password(
                security_type=DBPrivSecurityType.REDIS_PASSWORD
            )
            # 域名生成规则：ins.{cluster_name}.{db_app_abbr}.db
            domain_name = "ins.{}.{}.db".format(info["cluster_name"], self.ticket_data["db_app_abbr"])
            # 校验域名是否合法
            CommonValidate._validate_domain_valid(domain_name)
            # 在info里，补充每个主从集群的部署信息
            info.update(
                disaster_tolerance_level=self.ticket_data.get("disaster_tolerance_level"),
                city=self.ticket_data.get("city_code"),
                city_code=self.ticket_data.get("city_code"),
                db_version=self.ticket_data.get("db_version"),
                domain_name=domain_name,
                cluster_alias=info["cluster_name"],
                redis_pwd=redis_pwd,
            )

    def format_append_cluster_info(self):
        """补充追加集群的信息"""
        master_host_ids = [info["backend_group"]["master"]["bk_host_id"] for info in self.ticket_data["infos"]]
        storages = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(machine__in=master_host_ids)
        )

        master_host__cluster: Dict[int, Cluster] = {}
        master_host__machine: Dict[int, Machine] = {}
        master_host__max_port: Dict[int, int] = {}
        # 获取主机IP与集群，主机和起始端口的映射
        for inst in storages:
            master_host__machine[inst.machine.bk_host_id] = inst.machine
            master_host__cluster[inst.machine.bk_host_id] = inst.cluster.all()[0]
            if inst.machine.bk_host_id not in master_host__max_port:
                max_port = max(inst.machine.storageinstance_set.values_list("port", flat=True))
                master_host__max_port[inst.machine.bk_host_id] = max_port

        for info in self.ticket_data["infos"]:
            master_host = info["backend_group"]["master"]["bk_host_id"]
            # 更新起始端口+1
            master_host__max_port[master_host] += 1
            # 获取集群
            cluster = master_host__cluster[master_host]
            # 更新追加集群的部署信息
            info.update(
                city=cluster.region,
                city_code=cluster.region,
                disaster_tolerance_level=cluster.disaster_tolerance_level,
                port=master_host__max_port[master_host],
                db_version=cluster.major_version,
                resource_spec=master_host__machine[master_host].spec_config,
                # 追加部署的maxmemory为0，后续由周边程序分配
                maxmemory=0,
            )

    def format_ticket_data(self):
        self.format_common_cluster_info()
        if self.ticket_data["append_apply"]:
            self.format_append_cluster_info()


class RedisInstanceApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format_apply_cluster_info(self, ticket_data):
        """补充部署集群的信息"""
        cluster_num, machine_group = len(ticket_data["infos"]), len(ticket_data["nodes"]["backend_group"])
        for index, info in enumerate(ticket_data["infos"]):
            backend_group = ticket_data["nodes"]["backend_group"][index % machine_group]
            info.update(
                backend_group=backend_group,
                # 在同一台机器部署的实例端口号要递增
                port=ticket_data["port"] + (index // machine_group),
                db_version=ticket_data["db_version"],
                resource_spec=ticket_data["resource_spec"]["master"],
                # maxmemory = 机器内存 * 0.9 / 单机实例数 * 1024 * 1024 (MB --> 字节)
                maxmemory=int(1024 * 1024 * backend_group["master"]["bk_mem"] * 0.9 / (cluster_num / machine_group)),
            )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        self.format_apply_cluster_info(next_flow.details["ticket_data"])
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.REDIS_INS_APPLY, is_apply=True, iam=ActionEnum.REDIS_CLUSTER_APPLY)
class RedisClusterApplyFlowBuilder(BaseRedisInstanceTicketFlowBuilder):
    serializer = RedisInstanceApplyDetailSerializer
    inner_flow_builder = RedisInstanceApplyFlowParamBuilder
    inner_flow_name = _("Redis 主从部署")
    resource_apply_builder = RedisInstanceApplyResourceParamBuilder
