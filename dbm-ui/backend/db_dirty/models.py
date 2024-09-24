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
from datetime import datetime
from typing import Tuple

from django.db import models
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.forms import model_to_dict
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE
from backend.bk_web.models import AuditedModel
from backend.db_dirty.constants import MACHINE_EVENT__POOL_MAP, MachineEventType, PoolType
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str


class DirtyMachine(AuditedModel):
    """
    DBM主机池，包含：资源池，故障池，待回收池
    """

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
        non_host_fields = ["pool", "ticket", *AuditedModel.AUDITED_FIELDS]
        fields = [field.name for field in cls._meta.fields if field.name not in non_host_fields]
        return fields

    @classmethod
    def hosts_pool_transfer(cls, hosts, pool, operator="", ticket=None):
        """将机器转入主机池"""
        host_ids = [host["bk_host_id"] for host in hosts]
        handle_hosts = cls.objects.filter(bk_host_id__in=host_ids)
        now = datetime2str(datetime.now(timezone.utc))
        # 如果主机不存在，则证明第一次导入主机池，需要进行标准化
        if not handle_hosts.exists():
            hosts = ResourceHandler.standardized_resource_host(hosts)
            hosts = [{field: host.get(field) for field in cls.host_fields()} for host in hosts]
        else:
            hosts = [model_to_dict(host) for host in handle_hosts]

        # 主机转入主机池池
        # 资源池来源：旧主机下架，导入，故障池转移
        # 故障池来源：旧主机下架，资源池转移
        # 待回收来源：旧主机下架，故障池转移、资源池转移
        # 污点池来源：任务失败时，主机转入污点池
        # 因此这里判断主机不存在就创建，否则更新

        # 新机导入，录入主机池
        if pool == PoolType.Resource and not handle_hosts.exists():
            fields = {"pool": pool, "ticket": ticket, "creator": operator, "updater": operator}
            handle_hosts = [cls(**fields, **host) for host in hosts]
            cls.objects.bulk_create(handle_hosts)
        # 主机回收，删除主机记录
        elif pool == PoolType.Recycled:
            handle_hosts.delete()
        # 其他情况仅更新主机归属
        elif pool in [PoolType.Resource, PoolType.Recycle, PoolType.Fault]:
            handle_hosts.update(pool=pool, ticket=ticket, updater=operator, update_at=now)
        # 主机被使用，则pool为空(或者叫占用中...)
        elif not pool:
            handle_hosts.update(pool="", ticket=ticket, updater=operator, update_at=now)

        return hosts


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
    remark = models.CharField(help_text=_("备注"), default="", max_length=LEN_LONG)

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
                return False, _("仅新导入且无被申请、转移等使用事件的主机，可执行撤销导入")

        return True, ""

    @classmethod
    def host_event_trigger(cls, bk_biz_id, hosts, event, operator="", ticket=None, remark=""):
        """主机事件触发"""
        pool = MACHINE_EVENT__POOL_MAP.get(event)
        # 主机池流转
        hosts = DirtyMachine.hosts_pool_transfer(hosts, pool, operator, ticket)
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
                remark=remark,
            )
            for host in hosts
        ]
        MachineEvent.objects.bulk_create(events)

    @classmethod
    def fill_hosts_latest_event(cls, hosts: list):
        """获取主机最近一次主机事件"""
        bk_host_ids = [host["bk_host_id"] for host in hosts]

        # 使用窗口函数将最近的时间进行聚合。
        # TODO：当前版本不支持窗口函数过滤，Django 4.2+ 后貌似会支持
        host_events = MachineEvent.objects.filter(bk_host_id__in=bk_host_ids).annotate(
            row=Window(expression=RowNumber(), partition_by=[F("bk_host_id")], order_by=[F("update_at").desc()])
        )
        host_latest_event_map = {event.bk_host_id: model_to_dict(event) for event in host_events if event.row == 1}

        # 补充主机事件
        for host in hosts:
            host.update(latest_event=host_latest_event_map.get(host["bk_host_id"], {}))

        return host_latest_event_map
