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
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum, DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate, SkipToRepresentationMixin
from backend.ticket.builders.common.constants import REDIS_PROXY_MIN, RedisRole
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, RedisBasePauseParamBuilder
from backend.ticket.constants import TicketType


class RedisClusterApplyDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    proxy_port = serializers.IntegerField(help_text=_("集群端口"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )
    city_name = serializers.SerializerMethodField(help_text=_("城市名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    db_version = serializers.CharField(help_text=_("版本号"))
    cap_key = serializers.CharField(help_text=_("申请容量"), required=False, allow_blank=True, allow_null=True)
    cap_spec = serializers.SerializerMethodField(help_text=_("申请容量详情"), required=False)

    cluster_name = serializers.CharField(help_text=_("集群ID（英文数字及下划线）"))
    cluster_alias = serializers.CharField(help_text=_("集群别名（一般为中文别名）"), required=False, allow_blank=True)
    proxy_pwd = serializers.CharField(help_text=_("proxy访问密码"), required=False)

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    nodes = serializers.JSONField(help_text=_("部署节点"), required=False)
    resource_spec = serializers.JSONField(help_text=_("proxy部署方案"), required=False)
    cluster_shard_num = serializers.IntegerField(help_text=_("集群分片数"), required=False)

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def get_cap_spec(self, obj):
        return obj.get("cap_key")

    def validate(self, attrs):
        """
        # 集群名校验 -> 参数统一的情况下，可考虑提取为公共校验
        # 主机校验
        1. 主机角色互斥
        2. master=slave数量为>=1
        3. proxy>=2
        """

        # 判断主机角色是否互斥
        super().validate(attrs)

        # predixyRedisCluster， tendisplus集群分片数至少>=3
        if attrs["cluster_shard_num"] < 3 and attrs["cluster_type"] in [
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
        ]:
            raise serializers.ValidationError(_("{}集群部署的集群分片数至少大于3").format(attrs["cluster_type"]))

        # 集群名校验
        bk_biz_id, ticket_type = self.context["bk_biz_id"], self.context["ticket_type"]
        CommonValidate.validate_duplicate_cluster_name(bk_biz_id, ticket_type, attrs["cluster_name"])

        # proxy密码校验，如果是用户输入，则必须满足密码强度
        if attrs.get("proxy_pwd"):
            verify_result = DBPasswordHandler.verify_password_strength(
                attrs["proxy_pwd"], echo=True, security_type=DBPrivSecurityType.REDIS_PASSWORD
            )
            attrs["proxy_pwd"] = verify_result["password"]
            if not verify_result["is_strength"]:
                raise serializers.ValidationError(_("密码强度不符合要求，请重新输入密码。"))

        # 仅校验手工选择主机的情况 TODO: 目前redis已经不支持手动部署
        if attrs["ip_source"] != IpSource.MANUAL_INPUT:
            return attrs

        role__nodes_map = attrs["nodes"]
        master_nodes = set([i["bk_host_id"] for i in role__nodes_map.get(RedisRole.MASTER.value)])
        slave_nodes = set([i["bk_host_id"] for i in role__nodes_map.get(RedisRole.SLAVE.value)])
        proxy_nodes = set([i["bk_host_id"] for i in role__nodes_map.get(RedisRole.PROXY.value)])
        all_nodes = [*master_nodes, *slave_nodes, *proxy_nodes]

        # 集群元数据检查
        CommonValidate.validate_hosts_not_in_db_meta(host_infos=[{"bk_host_id": host_id} for host_id in all_nodes])

        # 空闲机校验
        CommonValidate.validate_hosts_from_idle_pool(bk_biz_id, all_nodes)

        # 校验不存在重复节点
        if (master_nodes & slave_nodes) or (master_nodes & proxy_nodes) or (slave_nodes & proxy_nodes):
            raise serializers.ValidationError(_("master、slave、proxy中存在重复节点"))

        # 节点数检查
        if not (len(master_nodes) and len(master_nodes) == len(slave_nodes)):
            raise serializers.ValidationError(_("至少提供1台master节点和1台slave节点，且master与slave节点数要保持一致"))
        if len(proxy_nodes) < REDIS_PROXY_MIN and attrs["cluster_type"] != ClusterType.TendisRedisInstance:
            raise serializers.ValidationError(_("proxy至少提供2台机器"))

        return attrs


class RedisClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controllers = {
        # tendis-cache部署flow
        ClusterType.TendisTwemproxyRedisInstance: RedisController.twemproxy_cluster_apply_scene,
        # tendis-plus部署flow
        ClusterType.TendisPredixyTendisplusCluster: RedisController.predixy_cluster_apply_scene,
        # tendis-ssd部署flow
        ClusterType.TwemproxyTendisSSDInstance: RedisController.twemproxy_cluster_apply_scene,
        # redis-cluster部署flow
        ClusterType.TendisPredixyRedisCluster: RedisController.predixy_cluster_apply_scene,
    }

    def build_controller_info(self) -> dict:
        """重写build_controller_info方法，实现多种相似架构复用一个ticket_type，通过cluster_type来映射"""
        controller = self.controllers.get(self.ticket_data["cluster_type"])
        return {
            "func_name": controller.__name__,
            "class_name": controller.__qualname__.split(".")[0],
            "module": controller.__module__,
        }

    def format_ticket_data(self):
        """
        {
            "db_app_abbr": "blueking",
            "bk_biz_id": 2005000002,
            "bk_cloud_id": 0,
            "proxy_port": 50000,
            "city": "深圳",
            "city_code": "深圳",
            "cluster_alias": "测试集群",
            "cluster_name": "test1",
            "cluster_type": "TwemproxyRedisInstance",
            "created_by": "admin",
            "databases": 2,
            "db_version": "Redis-6",
            "domain_name": "cache.twemproxyredisinstance.test1.blueking.db",
            "ip_source": "manual_input",
            "cap_key": "tendis_cache:30:12",
            "maxmemory": 2684354560,
            "shard_num": 12,
            "group_num": 1,
            "nodes": {
                "master": [
                    {
                        "bk_cloud_id": 0,
                        "ip": "127.0.94.37"
                    }
                ],
                "proxy": [
                    {
                        "bk_cloud_id": 0,
                        "ip": "127.0.67.56"
                    }
                ],
                "slave": [
                    {
                        "bk_cloud_id": 0,
                        "ip": "127.0.0.1"
                    }
                ]
            },
            "redis_pwd": "xxxxxxx",
            "ticket_type": "REDIS_CLUSTER_APPLY",
            "proxy_pwd": "xxxxxxx",
            "uid": 342
        }
        """
        # 生成随机密码，密码强度符合平台密码策略
        proxy_admin_pwd = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.REDIS_PASSWORD)
        redis_pwd = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.REDIS_PASSWORD)
        # proxy访问密码优先以用户为准
        proxy_pwd = self.ticket_data.get("proxy_pwd") or DBPasswordHandler.get_random_password(
            security_type=DBPrivSecurityType.REDIS_PASSWORD
        )
        # 如果部署类型是RedisCluster、Tendisplus，则后端密码和proxy密码相同，以proxy为准
        ticket_type = self.ticket_data["cluster_type"]
        if ticket_type in [ClusterType.TendisPredixyRedisCluster, ClusterType.TendisPredixyTendisplusCluster]:
            redis_pwd = proxy_pwd

        # 默认db数量
        DEFAULT_DATABASES = 2

        # 域名映射
        if ticket_type == ClusterType.TwemproxyTendisSSDInstance:
            domain_prefix = "ssd"
        elif ticket_type == ClusterType.TendisPredixyRedisCluster:
            domain_prefix = "rediscluster"
        elif ticket_type == ClusterType.TendisTwemproxyRedisInstance:
            domain_prefix = "cache"
        elif ticket_type in [ClusterType.TendisTwemproxyTendisplusIns, ClusterType.TendisPredixyTendisplusCluster]:
            domain_prefix = "tendisplus"
        domain_name = "{}.{}.{}.db".format(
            domain_prefix,
            self.ticket_data["cluster_name"],
            self.ticket_data["db_app_abbr"],
        )
        # 校验域名是否合法
        CommonValidate._validate_domain_valid(domain_name)

        self.ticket_data.update(
            {
                "ip_source": self.ticket_data["ip_source"],
                "city": self.ticket_data["city_code"],
                # 库数量，集群申请给默认值2就好
                "databases": DEFAULT_DATABASES,
                # 域名
                "domain_name": domain_name,
                # proxy密码
                "proxy_pwd": proxy_pwd,
                # proxy管理密码
                "proxy_admin_pwd": proxy_admin_pwd,
                # redis密码
                "redis_pwd": redis_pwd,
            }
        )

        # TODO: 目前redis已经不支持手动部署
        if self.ticket_data["ip_source"] == IpSource.MANUAL_INPUT:
            # 如果是手动部署，根据前端传入的cap_key需充maxmemory, max_disk等参数
            cap_key = self.ticket_data["cap_key"]
            # total_memory, maxmemory, total_disk, max_disk, shard_num, group_num = cap_key.split(":")
            __, maxmemory, __, max_disk, shard_num, group_num = cap_key.split(":")
            self.ticket_data.update(
                {
                    # 分片大小, MB -> byte
                    "maxmemory": int(int(maxmemory) * 1024 * 1024),
                    #  单位GB
                    "max_disk": int(max_disk),
                    # 机器组数
                    "group_num": int(len(self.ticket_data["nodes"]["master"])),
                    # 分片数
                    "shard_num": int(shard_num),
                }
            )


class RedisApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        # 在跨机房亲和性要求下，接入层proxy的亲和性要求至少分布在2个机房
        self.ticket_data["resource_spec"]["proxy"]["group_count"] = 2

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        group_num = self.ticket_data["resource_spec"]["backend_group"]["count"]
        shard_num = self.ticket_data["cluster_shard_num"]

        min_mem = min([host["master"]["bk_mem"] for host in self.ticket_data["nodes"]["backend_group"]])
        cluster_maxmemory = min_mem * group_num // shard_num
        min_disk = min([host["master"]["bk_disk"] for host in self.ticket_data["nodes"]["backend_group"]])
        cluster_max_disk = min_disk * group_num // shard_num

        next_flow.details["ticket_data"].update(
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


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_APPLY, is_apply=True)
class RedisClusterApplyFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterApplyDetailSerializer
    inner_flow_builder = RedisClusterApplyFlowParamBuilder
    inner_flow_name = _("Redis 集群部署")
    resource_apply_builder = RedisApplyResourceParamBuilder
    pause_node_builder = RedisBasePauseParamBuilder
