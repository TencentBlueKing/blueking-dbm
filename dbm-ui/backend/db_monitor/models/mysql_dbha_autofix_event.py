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
from typing import List, Union

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstancePhase, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.ticket.constants import TicketFlowStatus
from blue_krill.data_types.enum import EnumField, StructuredEnum

# class MySQLDBHAAutofixTicketStatus(str, StructuredEnum):
# MySQLDBHAAutofixTicketQueueStatus=models.TextChoices()


class MySQLDBHAAutofixTicketPriority(int, StructuredEnum):
    """
    调度优先级
    P1 最高
    同优先级的可以随意同时发起单据执行
    """

    P1 = EnumField(1, _("优先级一"))
    P2 = EnumField(2, _("优先级二"))
    # P999 = EnumField(999, _("默认优先级"))


# 在 TicketFlowStatus 补充的一个状态
# 专门给自愈用的
# python 搞不了 enum 继承, 就这么搞下算了
TicketQueueUncommitStatus = "UNCOMMIT"


class MySQLDBHAAutofixTicketStageQueue(AuditedModel):
    """
    这个文件里的两个 Model 很多重复字段
    理论上, 确实是可以合并到一张表里
    但实在不想这么搞, 状态机太复杂了, 而且事务竞争也特别难处理
    冗余吧, 无所谓了
    queue_uuid 代表唯一单据, 和 ticket_id 是一对一的关系
    而 queue_uuid 在这个表里是不唯一的
    这样做事为了方便优先级处理
    """

    ticket_id = models.BigIntegerField(default=0, help_text=_("单据 id"))
    status = models.CharField(
        max_length=128, choices=TicketFlowStatus.get_choices(), default=TicketQueueUncommitStatus
    )
    check_id = models.IntegerField(help_text=_("关联check_id"))
    cluster_id = models.IntegerField(help_text=_("关联集群id"))  # 数组的 json.dumps
    machine_type = models.CharField(max_length=64, help_text=_("机器类型"), choices=MachineType.get_choices())
    priority = models.IntegerField(
        help_text=_("单据优先级"),
        choices=MySQLDBHAAutofixTicketPriority.get_choices(),
        default=MySQLDBHAAutofixTicketPriority.P1,
    )
    # 字典的 json.dumps
    # 完整的单据参数, 直接 ticket.create 就可以
    # 相同 queue_uuid 的 ticket_param 肯定相同
    ticket_param = models.JSONField(help_text=_("单据参数"), default=dict)
    af_uuid = models.CharField(max_length=256, help_text=_("关联自愈调度uuid"))  # 没啥用, 单纯写着万一哪天要关联调度信息
    # 和 ticket id 是 1:1 的关系
    # 因为这个表的记录 insert 时其实没有单据
    # 但是同一个单又会 insert 多行, 所以预生成一个唯一 id
    # 相同的 queue_uuid 只发起一次单据
    queue_uuid = models.CharField(max_length=256, help_text=_("单据队列uuid"))

    class Meta:
        indexes = [models.Index(fields=["status", "cluster_id"])]


class MySQLDBHAEvent(AuditedModel):
    # 原始 event 部分
    bk_cloud_id = models.IntegerField(default=0)
    bk_biz_id = models.IntegerField(default=0)
    check_id = models.BigIntegerField(default=0)
    cluster_id = models.BigIntegerField(default=0)
    immute_domain = models.CharField(max_length=255, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
    instance_role = models.CharField(max_length=64, choices=InstanceRole.get_choices(), default="", null=True)
    ip = models.GenericIPAddressField(default="")
    port = models.IntegerField(default=0)
    new_master_host = models.GenericIPAddressField(default="", null=True)
    new_master_port = models.IntegerField(default=0, null=True)
    new_master_log_file = models.CharField(max_length=255, default="", null=True)
    new_master_log_pos = models.IntegerField(default=0, null=True)
    event_create_time = models.DateTimeField()
    # 自愈调度相关部分, 多个原始 event 可能对应同一个 ticket
    # ticket = models.ForeignKey(MySQLDBHAAutofixTicketStageQueue, on_delete=models.PROTECT, blank=True, null=True)
    # 只有未调度, 也就是 ticket__is_null == True 的 event 需要关注这个
    # validated == False 时会被放弃
    validated = models.BooleanField(null=True, blank=True, help_text=_("校验状态"), default=True)
    validate_memo = models.TextField(help_text=_("校验失败的说明"))
    # 区分不同的自愈local task
    # 不要把空字符串转义为 NULL, 不允许 NULL, 默认为空字符串
    # MySQL 区分对待了 NULL 和 "", 为了避免 where or, 所以明确的定义下
    af_uuid = models.CharField(max_length=256, help_text=_("自愈task的唯一id"), null=False, blank=False, default="")

    def __str__(self):
        return "[{}:{}] {} {} {}:{}".format(
            self.bk_cloud_id,
            self.bk_biz_id,
            self.immute_domain,
            self.machine_type,
            # self.instance_role,
            self.ip,
            self.port,
        )

    class Meta:
        indexes = [
            #     models.Index(fields=["inplace_ticket_status", "current_step", "inplace_ticket_id"]),
            #     models.Index(fields=["replace_ticket_status", "current_step", "replace_ticket_id"]),
            #     models.Index(fields=["inplace_ticket_id"]),
            models.Index(fields=["af_uuid", "event_create_time"]),
            #     # 为查询优化建的索引
            #     models.Index(fields=["current_step", "replace_ticket_id", "check_id", "ip"]),
            #     models.Index(fields=["current_step", "inplace_ticket_id", "check_id", "ip"]),
            #     models.Index(fields=["inplace_ticket_status", "current_step", "check_id"]),
            #     models.Index(fields=["replace_ticket_status", "current_step", "check_id"]),
        ]
        unique_together = [
            (
                "check_id",
                "ip",
                "port",
            )
        ]

    def failed_validate_it(self, reason: str):
        self.validated = False
        self.validate_memo = reason
        self.save(update_fields=["validated", "validate_memo"])

    def instance(self) -> Union[ProxyInstance, StorageInstance]:
        """
        从目前看来, 这个函数返回的只拿去做 exists 测试了
        甚至连 exists 都没调用
        仅仅利用 get 会抛出异常的特性来判断了实例存在性
        为了优化 db 查询, 先限定只查询 pk, 减少 django 生成的无意义 sql
        """
        cluster_obj = Cluster.objects.only("pk").get(
            pk=self.cluster_id,
            cluster_type=self.cluster_type,
            bk_cloud_id=self.bk_cloud_id,
            bk_biz_id=self.bk_biz_id,
        )

        q = Q(
            **{
                "machine__ip": self.ip,
                "port": self.port,
                "status": InstanceStatus.UNAVAILABLE,
                "phase": InstancePhase.ONLINE,
            }
        )
        if self.machine_type in [MachineType.PROXY, MachineType.SPIDER]:
            instance = cluster_obj.proxyinstance_set.only("pk").get(q)
        else:
            q &= Q(**{"instance_role__in": [InstanceRole.BACKEND_SLAVE, InstanceRole.REMOTE_SLAVE]})
            instance = cluster_obj.storageinstance_set.only("pk").get(q)

        return instance

    def dbas(self) -> List[str]:
        if self.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
            db_type = DBType.MySQL
        else:
            db_type = DBType.TenDBCluster

        return DBAdministrator.get_biz_db_type_admins(bk_biz_id=self.bk_biz_id, db_type=db_type)
