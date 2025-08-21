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
from enum import IntFlag, auto
from typing import List

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from blue_krill.data_types.enum import EnumField, StructuredEnum


class MySQLAutofixTicketStatus(str, StructuredEnum):
    UNSUBMITTED = EnumField("UNSUBMITTED", _("未提交"))
    SKIPPED = EnumField("SKIPPED", _("跳过"))
    PENDING = EnumField("PENDING", _("等待中"))
    RUNNING = EnumField("RUNNING", _("执行中"))
    SUCCEEDED = EnumField("SUCCEEDED", _("成功"))
    FAILED = EnumField("FAILED", _("失败"))
    REVOKED = EnumField("REVOKED", _("撤销"))
    TERMINATED = EnumField("TERMINATED", _("终止"))
    # 多实例机器等待 dbha 上报所有实例的 dbha 事件超时
    # 由于自愈总是从 inplace 开始, 所以理论上只有 inplace ticket status 会有这个值
    # 超时后放弃自愈, inplace 和 replace 都不做了
    TIMEOUT = EnumField("TIMEOUT", _("等待超时"))


# class InplaceStatusFlag(IntFlag):
#     def flag_text(self) -> List[str]:
#         flag_str = self.__str__()[len(self.__class__.__name__) + 1 :]
#         return flag_str.split("|")
#
#     InplaceUnsubmitted = auto()
#     InplaceSkipped = auto()
#     InplacePending = auto()
#     InplaceSucceeded = auto()
#     InplaceFailed = auto()
#     InplaceRevoked = auto()
#     InplaceTerminated = auto()


class ReplaceStatusFlag(IntFlag):
    def flag_text(self) -> List[str]:
        flag_str = self.__str__()[len(self.__class__.__name__) + 1 :]
        return flag_str.split("|")

    ReplaceUnsubmitted = auto()
    ReplaceSkipped = auto()
    ReplacePending = auto()
    ReplaceSucceeded = auto()
    ReplaceFailed = auto()
    ReplaceRevoked = auto()
    ReplaceTerminated = auto()


# class FooFlag(IntFlag):


class MySQLDBHAAutofixTodo(AuditedModel):
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
    ticket_id = models.BigIntegerField(default=0, help_text=_("自愈单据"))
    status = models.CharField(
        max_length=64,
        choices=MySQLAutofixTicketStatus.get_choices(),
        default=MySQLAutofixTicketStatus.UNSUBMITTED.value,
    )

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
        # indexes = [
        #     models.Index(fields=["inplace_ticket_status", "current_step", "inplace_ticket_id"]),
        #     models.Index(fields=["replace_ticket_status", "current_step", "replace_ticket_id"]),
        #     models.Index(fields=["inplace_ticket_id"]),
        #     models.Index(fields=["replace_ticket_id"]),
        #     # 为查询优化建的索引
        #     models.Index(fields=["current_step", "replace_ticket_id", "check_id", "ip"]),
        #     models.Index(fields=["current_step", "inplace_ticket_id", "check_id", "ip"]),
        #     models.Index(fields=["inplace_ticket_status", "current_step", "check_id"]),
        #     models.Index(fields=["replace_ticket_status", "current_step", "check_id"]),
        # ]
        unique_together = [
            (
                "check_id",
                "ip",
                "port",
            )
        ]
