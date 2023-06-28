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
import operator
from functools import reduce
from typing import Dict, List, Union

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend import constants
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import (
    AccessLayer,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import Cluster, ClusterEntry
from backend.ticket.constants import InstanceType
from backend.ticket.models import InstanceOperateRecord

from ...constants import DEFAULT_TIME_ZONE, IP_PORT_DIVIDER
from .machine import Machine


class InstanceMixin(object):
    """
    封装实例的状态查询的相关方法
    """

    def __str__(self):
        return self.ip_port

    @property
    def simple_desc(self):
        return {
            "name": self.name,
            "ip": self.machine.ip,
            "port": self.port,
            "instance": "{}{}{}".format(self.machine.ip, IP_PORT_DIVIDER, self.port),
            "status": self.status,
            "phase": getattr(self, "phase", None),
            "bk_instance_id": self.bk_instance_id,
            "bk_host_id": self.machine.bk_host_id,
            "bk_cloud_id": self.machine.bk_cloud_id,
            "bk_biz_id": self.bk_biz_id,
        }

    @property
    def ip_port(self):
        return f"{self.machine.ip}{constants.IP_PORT_DIVIDER}{self.port}"

    @property
    def instance_type(self):
        raise NotImplementedError()

    def is_locked(self):
        return InstanceOperateRecord.objects.has_locked_operations(instance_id=self.id)

    def can_access(self) -> (bool, str):
        if self.is_locked():
            return False, _("实例结构和状态变更中，请稍后!")

        if self.status != InstanceStatus.RUNNING:
            return False, _("实例运行状态异常，请检查!")

        return True, ""

    def to_cluster_dict(self, cluster):
        return {
            "ip": self.machine.ip,
            "role": self.instance_role,
            "cluster": cluster.extra_desc,
            "spec": self.machine.spec_config,
        }

    @classmethod
    def find_insts_by_addresses(cls, addresses: List[Union[str, Dict]], divider: str = IP_PORT_DIVIDER):
        """通过实例的ip:port查询实例"""

        if not addresses:
            return None

        if isinstance(addresses[0], str):
            ip_port_list = [address.split(divider) for address in addresses]
        elif isinstance(addresses[0], dict):
            if addresses[0].get("address", None):
                ip_port_list = [address["address"].split(divider) for address in addresses]
            else:
                ip_port_list = [(address["ip"], address["port"]) for address in addresses]
        else:
            return None

        address_filters = reduce(
            operator.or_, [Q(machine__ip=ip_port[0], port=ip_port[1]) for ip_port in ip_port_list]
        )
        return cls.objects.select_related("machine").filter(address_filters)

    @classmethod
    def filter_by_ips(cls, bk_biz_id: int, ips: List[str]):
        """通过ip列表反查实例列表"""
        grouped_instances = []
        unique_ip_roles = set()
        for inst in cls.objects.select_related("machine").filter(bk_biz_id=bk_biz_id, machine__ip__in=ips):
            ip_role = ":".join([inst.machine.ip, inst.instance_role])
            if ip_role in unique_ip_roles:
                continue

            unique_ip_roles.add(ip_role)
            for cluster in inst.cluster.all():
                grouped_instances.append(inst.to_cluster_dict(cluster))

        return grouped_instances


class StorageInstance(InstanceMixin, AuditedModel):
    version = models.CharField(max_length=64, default="", help_text=_("版本号"))
    port = models.PositiveIntegerField(default=0)
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT)

    db_module_id = models.IntegerField(default=0)
    bk_biz_id = models.IntegerField(default=0)
    cluster = models.ManyToManyField(Cluster, blank=True)

    access_layer = models.CharField(max_length=64, choices=AccessLayer.get_choices(), default="")
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
    instance_role = models.CharField(max_length=64, choices=InstanceRole.get_choices(), default="")
    instance_inner_role = models.CharField(max_length=64, choices=InstanceInnerRole.get_choices(), default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    status = models.CharField(max_length=64, choices=InstanceStatus.get_choices(), default="")
    phase = models.CharField(max_length=64, choices=InstancePhase.get_choices(), default=InstancePhase.ONLINE.value)
    bind_entry = models.ManyToManyField(ClusterEntry, blank=True)
    name = models.CharField(max_length=255, default="")
    time_zone = models.CharField(max_length=16, default=DEFAULT_TIME_ZONE, help_text=_("实例所在的时区"))
    bk_instance_id = models.BigIntegerField(default=0, help_text=_("对应在cc的服务实例的id"))
    is_stand_by = models.BooleanField(default=True, help_text=_("多 slave 的备选标志"))

    class Meta:
        unique_together = (
            "machine",
            "port",
        )
        ordering = ("-create_at",)

    @classmethod
    def get_instance_id_ip_port_map(cls, instance_id: List[int]) -> Dict[int, str]:
        """查询实例 ID 和 IP:PORT 的映射关系"""
        instances = cls.objects.select_related("machine").filter(id__in=instance_id)
        return {instance.id: instance.ip_port for instance in instances}

    @property
    def instance_type(self):
        return InstanceType.STORAGE.value

    @classmethod
    def find_storage_instance_by_addresses(cls, addresses: List[Union[str, Dict]]):
        """通过实例的ip查询实例"""

        if not addresses:
            return None

        address_filters = reduce(operator.or_, [Q(machine__ip=address) for address in addresses])
        return cls.objects.select_related("machine").filter(address_filters)


class ProxyInstance(InstanceMixin, AuditedModel):
    version = models.CharField(max_length=64, default="", help_text=_("版本号"))
    port = models.PositiveIntegerField(default=0)
    admin_port = models.PositiveIntegerField(default=0)
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT)

    db_module_id = models.IntegerField(default=0)
    bk_biz_id = models.IntegerField(default=0)
    cluster = models.ManyToManyField(Cluster, blank=True)

    access_layer = models.CharField(max_length=64, choices=AccessLayer.get_choices(), default="")
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")

    storageinstance = models.ManyToManyField(StorageInstance, blank=True)

    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    status = models.CharField(max_length=64, choices=InstanceStatus.get_choices(), default="")
    bind_entry = models.ManyToManyField(ClusterEntry, blank=True)
    name = models.CharField(max_length=255, default="")
    time_zone = models.CharField(max_length=16, default=DEFAULT_TIME_ZONE, help_text=_("实例所在的时区"))
    bk_instance_id = models.BigIntegerField(default=0, help_text=_("对应在cc的服务实例的id"))

    class Meta:
        unique_together = (
            "machine",
            "port",
        )
        ordering = ("-create_at",)

    @property
    def instance_role(self):
        return InstanceType.PROXY.value

    @property
    def instance_type(self):
        return InstanceType.PROXY.value
