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
from typing import Tuple

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_MIDDLE
from backend.bk_web.models import AuditedModel
from backend.db_dirty.constants import MACHINE_EVENT__POOL_MAP, MachineEventType, PoolType
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.ticket.models import Ticket


class DirtyMachine(AuditedModel):
    """
    机器池：污点池，故障池，待回收池
    """

    bk_biz_id = models.IntegerField(default=0, help_text=_("业务ID"))
    bk_host_id = models.PositiveBigIntegerField(primary_key=True, default=0, help_text=_("主机ID"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("主机云区域"))
    ip = models.CharField(max_length=LEN_MIDDLE, help_text=_("主机IP"))
    city = models.CharField(max_length=LEN_MIDDLE, default="", blank=True, null=True, help_text=_("城市"))
    sub_zone = models.CharField(max_length=LEN_MIDDLE, default="", blank=True, null=True, help_text=_("园区"))
    rack_id = models.CharField(max_length=LEN_MIDDLE, default="", blank=True, null=True, help_text=_("机架"))
    device_class = models.CharField(max_length=LEN_MIDDLE, default="", blank=True, null=True, help_text=_("机型"))
    os_name = models.CharField(max_length=LEN_MIDDLE, default="", blank=True, null=True, help_text=_("操作系统"))
    bk_cpu = models.IntegerField(default=0, help_text=_("cpu"))
    bk_mem = models.IntegerField(default=0, help_text=_("内存"))
    bk_disk = models.IntegerField(default=0, help_text=_("磁盘"))

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, help_text=_("关联单据"), null=True, blank=True)

    pool = models.CharField(help_text=_("池类型"), max_length=LEN_MIDDLE, choices=PoolType.get_choices())

    class Meta:
        verbose_name = verbose_name_plural = _("污点池机器(DirtyMachine)")

    @classmethod
    def host_fields(cls):
        non_host_fields = ["bk_biz_id", "pool", "ticket", *AuditedModel.AUDITED_FIELDS]
        fields = [field.name for field in cls._meta.fields if field.name not in non_host_fields]
        return fields

    @classmethod
    def hosts_pool_transfer(cls, bk_biz_id, hosts, pool, operator="", ticket=None):
        """将机器转入主机池"""
        hosts = [{field: host.get(field) for field in cls.host_fields()} for host in hosts]
        host_ids = [host["bk_host_id"] for host in hosts]

        # 主机转入污点/故障池，说明第一次被纳管到池
        # 待回收会从故障池、资源池转移
        # 因此这里判断主机不存在就创建，否则更新
        if pool in [PoolType.Fault, PoolType.Dirty, PoolType.Recycle]:
            handle_hosts = cls.objects.filter(bk_host_id__in=host_ids)
            if handle_hosts.count() == len(host_ids):
                handle_hosts.update(pool=pool, ticket=ticket)
            else:
                handle_hosts = [
                    cls(bk_biz_id=bk_biz_id, pool=pool, ticket=ticket, creator=operator, updater=operator, **host)
                    for host in hosts
                ]
                cls.objects.bulk_create(handle_hosts)
        # 回收机器只能从待回收转移，删除池纳管记录
        # 重导入回资源池，删除池纳管记录
        elif pool in [PoolType.Recycled, PoolType.Resource]:
            cls.objects.filter(bk_host_id__in=host_ids).delete()


class MachineEvent(AuditedModel):
    """
    机器事件，主要记录机器的流转记录
    """

    bk_biz_id = models.IntegerField(default=0, help_text=_("业务ID"))
    ip = models.CharField(max_length=LEN_MIDDLE, help_text=_("主机IP"))
    bk_host_id = models.PositiveBigIntegerField(help_text=_("主机ID"))
    event = models.CharField(help_text=_("事件类型"), max_length=LEN_MIDDLE, choices=MachineEventType.get_choices())
    to = models.CharField(
        help_text=_("资源流向"), max_length=LEN_MIDDLE, choices=PoolType.get_choices(), null=True, blank=True
    )
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, help_text=_("关联单据"), null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = _("机器事件记录")

    @classmethod
    def hosts_can_return(cls, bk_host_ids) -> Tuple[bool, str]:
        """判断机器是否能退回"""
        host_events = cls.objects.filter(bk_host_id__in=bk_host_ids).order_by("id")

        grouped_events = defaultdict(list)
        for event in host_events:
            grouped_events[event.bk_host_id].append(event)

        # 如果最近一次的机器事件非导入，则无法退回
        for host_id, events in grouped_events.items():
            if events and events[-1].event != MachineEventType.ImportResource:
                return False, _("主机经历过流转事件: {}".format(MachineEventType.get_choice_label(events[-1].event)))

        return True, ""

    @classmethod
    def host_event_trigger(cls, bk_biz_id, hosts, event, operator="", ticket=None, standard=False):
        """主机事件触发"""
        pool = MACHINE_EVENT__POOL_MAP.get(event)
        # 如果主机非标准话，则查询cc
        if not standard:
            hosts = ResourceHandler.standardized_resource_host(hosts)
        # 主机池流转
        if pool:
            DirtyMachine.hosts_pool_transfer(bk_biz_id, hosts, pool, operator, ticket)
        # 流转污点池不记录主机事件
        if event == MachineEventType.ToDirty:
            return
        # 事件记录
        events = [
            MachineEvent(
                bk_biz_id=bk_biz_id,
                ip=host["ip"],
                bk_host_id=host["bk_host_id"],
                event=event,
                to=pool,
                ticket=ticket,
                creator=operator,
                updater=operator,
            )
            for host in hosts
        ]
        MachineEvent.objects.bulk_create(events)
