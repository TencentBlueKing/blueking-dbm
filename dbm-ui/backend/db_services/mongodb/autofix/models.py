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

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL, LEN_XX_LONG
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType

from .enums import MongoAutofixLogEvent, MongoAutofixStatus


class MongoAutofixCtl(AuditedModel):
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域 ID"), db_index=True)
    bk_biz_id = models.IntegerField(verbose_name=_("业务 ID"), db_index=True)
    ctl_name = models.CharField(verbose_name=_("控制项"), max_length=LEN_NORMAL)
    ctl_value = models.CharField(verbose_name=_("取值"), max_length=LEN_XX_LONG)

    class Meta:
        verbose_name = _("MongoDB自愈控制项")
        verbose_name_plural = _("MongoDB自愈控制项")
        db_table = "tb_mongodb_autofix_ctl"


class MongoAutofixCore(AuditedModel):
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域ID"))
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"))
    cluster_id = models.IntegerField(verbose_name=_("集群ID"), db_index=True)
    cluster_type = models.CharField(verbose_name=_("集群类型"), choices=ClusterType.get_choices(), max_length=LEN_NORMAL)
    immute_domain = models.CharField(verbose_name=_("集群主域名"), max_length=LEN_LONG)
    fault_machines = models.JSONField(verbose_name=_("故障机器"), max_length=LEN_XX_LONG)
    ip = models.GenericIPAddressField(verbose_name=_("故障IP"), db_index=True)
    bk_host_id = models.IntegerField(verbose_name=_("机器ID"), default=0)
    cluster_ids = models.JSONField(verbose_name=_("关联集群ID列表"), default=list)
    ports = models.JSONField(verbose_name=_("端口列表"), default=list)
    roles = models.JSONField(verbose_name=_("角色列表"), default=list)
    bk_city = models.CharField(verbose_name=_("城市"), max_length=LEN_NORMAL, blank=True, default="")
    bk_sub_zone_id = models.IntegerField(verbose_name=_("园区ID"), default=0)
    pre_ticket_id = models.BigIntegerField(verbose_name=_("PRE单据ID"), default=-1)
    ticket_id = models.BigIntegerField(verbose_name=_("修复/替换单据ID"), default=-1)
    confirm_result = models.CharField(verbose_name=_("确认结果"), max_length=LEN_NORMAL, blank=True, default="")
    deal_status = models.CharField(
        verbose_name=_("自愈状态"),
        choices=MongoAutofixStatus.get_choices(),
        max_length=LEN_NORMAL,
        db_index=True,
    )
    status_version = models.CharField(verbose_name=_("状态版本"), max_length=LEN_NORMAL)
    disk_rw_ok = models.IntegerField(verbose_name=_("磁盘读写是否正常"), null=True, blank=True, default=-1)
    detected_at = models.DateTimeField(verbose_name=_("发现时间"), null=True, blank=True)

    class Meta:
        verbose_name = _("MongoDB自愈待办 (tb_mongodb_autofix_core)")
        verbose_name_plural = _("MongoDB自愈待办 (tb_mongodb_autofix_core)")
        db_table = "tb_mongodb_autofix_core"


class MongoIgnoreAutofix(AuditedModel):
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域ID"))
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"))
    cluster_id = models.IntegerField(verbose_name=_("集群ID"))
    cluster_type = models.CharField(verbose_name=_("集群类型"), choices=ClusterType.get_choices(), max_length=LEN_NORMAL)
    immute_domain = models.CharField(verbose_name=_("集群域名"), max_length=LEN_LONG)
    bk_host_id = models.IntegerField(verbose_name=_("机器ID"))
    ip = models.GenericIPAddressField(verbose_name=_("机器IP"))
    ignore_msg = models.CharField(verbose_name=_("忽略原因"), max_length=LEN_NORMAL)
    extra = models.JSONField(verbose_name=_("扩展信息"), default=dict)

    class Meta:
        verbose_name = _("MongoDB自愈忽略记录")
        verbose_name_plural = _("MongoDB自愈忽略记录")
        db_table = "tb_mongodb_autofix_ignore"
        index_together = [("bk_biz_id", "ip")]


class MongoAutofixLog(AuditedModel):
    """自愈流水日志（追加写，按 core_id / ip 检索）。"""

    core_id = models.BigIntegerField(verbose_name=_("Core ID"), db_index=True, default=0)
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域ID"), default=0)
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"), db_index=True, default=0)
    cluster_id = models.IntegerField(verbose_name=_("集群ID"), db_index=True, default=0)
    immute_domain = models.CharField(verbose_name=_("集群域名"), max_length=LEN_LONG, blank=True, default="")
    ip = models.GenericIPAddressField(verbose_name=_("故障IP"), db_index=True, null=True, blank=True)
    bk_host_id = models.IntegerField(verbose_name=_("机器ID"), default=0)
    event = models.CharField(
        verbose_name=_("事件"),
        choices=MongoAutofixLogEvent.get_choices(),
        max_length=LEN_NORMAL,
        db_index=True,
    )
    deal_status = models.CharField(verbose_name=_("当时自愈状态"), max_length=LEN_NORMAL, blank=True, default="")
    confirm_result = models.CharField(verbose_name=_("确认结果"), max_length=LEN_NORMAL, blank=True, default="")
    pre_ticket_id = models.BigIntegerField(verbose_name=_("PRE单据ID"), default=-1)
    ticket_id = models.BigIntegerField(verbose_name=_("修复/替换单据ID"), default=-1)
    message = models.CharField(verbose_name=_("日志内容"), max_length=LEN_XX_LONG, blank=True, default="")
    context = models.JSONField(verbose_name=_("扩展上下文"), default=dict)

    class Meta:
        verbose_name = _("MongoDB自愈日志 (tb_mongodb_autofix_log)")
        verbose_name_plural = _("MongoDB自愈日志 (tb_mongodb_autofix_log)")
        db_table = "tb_mongodb_autofix_log"
        ordering = ("-id",)
        index_together = [("core_id", "event"), ("bk_biz_id", "ip")]
