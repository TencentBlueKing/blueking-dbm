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
import humanize
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.common.constants import REDIS_PROXY_MIN, RedisRole
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, RedisBasePauseParamBuilder
from backend.ticket.constants import TicketType


class RedisClusterApplyDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    proxy_port = serializers.IntegerField(help_text=_("集群端口"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    city_name = serializers.SerializerMethodField(help_text=_("城市名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    db_version = serializers.CharField(help_text=_("版本号"))
    cap_key = serializers.CharField(help_text=_("申请容量"), required=False, allow_blank=True, allow_null=True)
    cap_spec = serializers.SerializerMethodField(help_text=_("申请容量详情"), required=False)

    cluster_name = serializers.CharField(help_text=_("集群ID（英文数字及下划线）"))
    cluster_alias = serializers.CharField(help_text=_("集群别名（一般为中文别名）"), required=False, allow_blank=True)

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

        # 集群名校验
        bk_biz_id = self.context["bk_biz_id"]
        CommonValidate.validate_duplicate_cluster_name(bk_biz_id, attrs["cluster_type"], attrs["cluster_name"])

        # 仅校验手工选择主机的情况
        if attrs["ip_source"] != IpSource.MANUAL_INPUT:
            return attrs

        role__nodes_map = attrs["nodes"]
        master_nodes = set([i["bk_host_id"] for i in role__nodes_map.get(RedisRole.MASTER.value)])
        slave_nodes = set([i["bk_host_id"] for i in role__nodes_map.get(RedisRole.SLAVE.value)])
        proxy_nodes = set([i["bk_host_id"] for i in role__nodes_map.get(RedisRole.PROXY.value)])
        all_nodes = [*master_nodes, *slave_nodes, *proxy_nodes]

        # 集群元数据检查
        exist_nodes = Machine.objects.filter(bk_host_id__in=all_nodes)
        if exist_nodes.exists():
            exist_hosts = ",".join((exist_nodes.values_list("ip", flat=True)))
            raise serializers.ValidationError(_("主机【{}】已经被注册到了集群元数据，请检查").format(exist_hosts))

        # 空闲机校验
        hosts_not_in_idle_pool = CommonValidate.validate_hosts_from_idle_pool(bk_biz_id, all_nodes)
        if hosts_not_in_idle_pool:
            host_id_to_ips = {
                h["bk_host_id"]: h["ip"] for __, role_hosts in role__nodes_map.items() for h in role_hosts
            }
            hosts_not_in_idle_pool = {host_id_to_ips[h] for h in hosts_not_in_idle_pool}
            raise serializers.ValidationError(_("主机{}不在空闲机池，请保证所选的主机均来自空闲机").format(hosts_not_in_idle_pool))

        # TODO: master&slave 规格检查: cpu/mem/disk...
        if master_nodes & slave_nodes:
            raise serializers.ValidationError(_("master和slave中存在重复节点"))

        if master_nodes & proxy_nodes:
            raise serializers.ValidationError(_("master和proxy中存在重复节点"))

        if slave_nodes & proxy_nodes:
            raise serializers.ValidationError(_("slave和proxy中存在重复节点"))

        # 节点数检查
        if not (len(master_nodes) and len(master_nodes) == len(slave_nodes)):
            raise serializers.ValidationError(_("至少提供1台master节点和1台slave节点，且master与slave节点数要保持一致"))

        if len(proxy_nodes) < REDIS_PROXY_MIN:
            raise serializers.ValidationError(_("proxy至少提供2台机器"))

        return attrs


class RedisClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controllers = {
        ClusterType.TendisTwemproxyRedisInstance: RedisController.redis_cluster_apply_scene,
        ClusterType.TendisPredixyTendisplusCluster: RedisController.tendisplus_apply_scene,
        ClusterType.TwemproxyTendisSSDInstance: RedisController.redis_cluster_apply_scene,
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
            "redis_pwd": "JWe5UeSUAAvcpcY3",
            "ticket_type": "REDIS_CLUSTER_APPLY",
            "proxy_pwd": "6Lenke4rWl6VU8lj",
            "uid": 342
        }
        """
        # 生成随机密码，长度16位，英文大小写+数字
        proxy_pwd = get_random_string(16)
        redis_pwd = get_random_string(16)
        ticket_type = self.ticket_data["cluster_type"]

        # 默认db数量
        DEFAULT_DATABASES = 2

        # 域名映射
        if ticket_type in [
            ClusterType.TwemproxyTendisSSDInstance,
        ]:
            domain_prefix = "ssd"
        elif ticket_type in [
            ClusterType.TendisTwemproxyTendisplusIns,
            ClusterType.TendisPredixyTendisplusCluster,
        ]:
            domain_prefix = "tendisplus"
        else:
            domain_prefix = "cache"

        domain_name = "{}.{}.{}.db".format(
            domain_prefix,
            self.ticket_data["cluster_name"],
            self.ticket_data["db_app_abbr"],
        )

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
                # redis密码
                "redis_pwd": redis_pwd,
            }
        )

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
                    "group_num": int(group_num),
                    # 分片数
                    "shard_num": int(shard_num),
                }
            )


class RedisApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
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


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_APPLY)
class RedisClusterApplyFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterApplyDetailSerializer
    inner_flow_builder = RedisClusterApplyFlowParamBuilder
    inner_flow_name = _("集群部署")
    resource_apply_builder = RedisApplyResourceParamBuilder
    pause_node_builder = RedisBasePauseParamBuilder

    @property
    def need_manual_confirm(self):
        return True

    @property
    def need_itsm(self):
        return True
