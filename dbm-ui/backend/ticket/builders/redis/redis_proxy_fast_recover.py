from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import RedisFastRecoverEnum
from backend.db_meta.models import Machine, ProxyInstance
from backend.flow.engine.controller.redis import RedisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, RedisBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class RedisProxyFastRecoverDetailSerializer(RedisBaseOperateDetailSerializer):
    class ProxyItemSerializer(serializers.Serializer):
        """Proxy节点信息"""

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        proxy = serializers.ListSerializer(help_text=_("Proxy节点列表"), child=HostInfoSerializer())
        operate_type = serializers.ChoiceField(help_text=_("操作类型"), choices=RedisFastRecoverEnum.get_choices())
        restart_proxy = serializers.BooleanField(help_text=_("是否重启proxy实例"), default=False)

    infos = serializers.ListSerializer(help_text=_("Proxy节点信息"), child=ProxyItemSerializer())


class RedisProxyFastRecoverFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.cluster_proxy_fast_recovery

    def format_ticket_data(self):
        """通过proxy IP获取地域、园区和关联集群"""
        # 收集所有proxy IP
        proxy_ips = []
        for info in self.ticket_data["infos"]:
            for proxy in info["proxy"]:
                proxy_ips.append(proxy["ip"])

        # 查询Machine实例并构建IP到Machine的映射
        machines = Machine.objects.filter(ip__in=proxy_ips)
        machine_map = {machine.ip: machine for machine in machines}

        # 获取所有Machine的ProxyInstance实例
        machine_ids = [machine.bk_host_id for machine in machines]
        proxy_instances = ProxyInstance.objects.filter(machine_id__in=machine_ids).prefetch_related("cluster")

        # 构建Machine到关联Cluster的映射
        machine_cluster_map = {}
        for proxy_instance in proxy_instances:
            machine_id = proxy_instance.machine_id
            if machine_id not in machine_cluster_map:
                machine_cluster_map[machine_id] = []

            # 获取关联的所有Cluster的immute_domain
            for cluster in proxy_instance.cluster.all():
                machine_cluster_map[machine_id].append(cluster.immute_domain)

        # 遍历所有proxy，添加地域、园区和immute_domain
        for info in self.ticket_data["infos"]:
            for proxy in info["proxy"]:
                ip = proxy["ip"]
                machine = machine_map.get(ip)

                if machine:
                    city_name = machine.bk_city.bk_idc_city_name if machine.bk_city else ""
                    sub_zone = machine.bk_sub_zone or ""
                    immute_domains = list(set(machine_cluster_map.get(machine.bk_host_id, [])))

                    # 直接添加到proxy字典中
                    proxy["bk_idc_city_name"] = city_name
                    proxy["bk_sub_zone"] = sub_zone
                    proxy["immute_domains"] = immute_domains


@builders.BuilderFactory.register(TicketType.REDIS_PROXY_KICKOFF, iam=ActionEnum.REDIS_MANAGE)
class RedisProxyKickoffFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisProxyFastRecoverDetailSerializer
    inner_flow_builder = RedisProxyFastRecoverFlowParamBuilder
    inner_flow_name = _("Redis Proxy剔除")


@builders.BuilderFactory.register(TicketType.REDIS_PROXY_FIX, iam=ActionEnum.REDIS_MANAGE)
class RedisProxyFixFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisProxyFastRecoverDetailSerializer
    inner_flow_builder = RedisProxyFastRecoverFlowParamBuilder
    inner_flow_name = _("Redis Proxy修复")
