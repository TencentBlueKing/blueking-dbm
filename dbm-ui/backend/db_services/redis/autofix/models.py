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
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL, LEN_XX_LONG
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from blue_krill.data_types.enum import EnumField, StructuredEnum

from .enums import AutofixStatus


class RedisAutofixCtl(AuditedModel):
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域 ID"), db_index=True)
    bk_biz_id = models.IntegerField(verbose_name=_("业务 ID"), db_index=True)
    ctl_name = models.CharField(verbose_name=_("模块名"), max_length=LEN_NORMAL)
    ctl_value = models.CharField(verbose_name=_("取值范围"), max_length=LEN_NORMAL)

    class Meta:
        db_table = "tb_tendis_autofix_ctl"


class RedisAutofixCore(AuditedModel):
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域ID"))
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"))
    cluster_id = models.IntegerField(verbose_name=_("集群ID"))
    cluster_type = models.CharField(verbose_name=_("集群类型"), choices=ClusterType.get_choices(), max_length=LEN_NORMAL)
    immute_domain = models.CharField(verbose_name=_("集群主域名"), max_length=LEN_LONG)
    fault_machines = models.JSONField(verbose_name=_("故障机器"), max_length=LEN_XX_LONG)
    ticket_id = models.BigIntegerField(verbose_name=_("单据ID"), default=-1)
    deal_status = models.CharField(verbose_name=_("自愈状态"), choices=AutofixStatus.get_choices(), max_length=LEN_NORMAL)
    status_version = models.CharField(verbose_name=_("状态版本"), max_length=LEN_NORMAL)

    class Meta:
        db_table = "tb_tendis_autofix_core"
        index_together = [("cluster_id")]


class RedisIgnoreAutofix(AuditedModel):
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域ID"))
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"))
    cluster_id = models.IntegerField(verbose_name=_("集群ID"))
    cluster_type = models.CharField(verbose_name=_("集群类型"), choices=ClusterType.get_choices(), max_length=LEN_NORMAL)
    immute_domain = models.CharField(verbose_name=_("集群域名"), max_length=LEN_LONG)
    instance_type = models.CharField(verbose_name=_("实例类型"), max_length=LEN_NORMAL)
    cluster_ports = models.JSONField(verbose_name=_("实例列表"), max_length=LEN_LONG)
    bk_host_id = models.IntegerField(verbose_name=_("机器ID"))
    ip = models.GenericIPAddressField(verbose_name=_("机器IP"))
    switch_ports = models.JSONField(verbose_name=_("切换端口"), max_length=LEN_LONG)
    sw_min_id = models.IntegerField(verbose_name=_("切换最小值"))
    sw_max_id = models.IntegerField(verbose_name=_("切换最大值"))
    sw_result = models.JSONField(verbose_name=_("切换结果"), max_length=LEN_LONG)
    ignore_msg = models.CharField(verbose_name=_("忽略类型"), max_length=LEN_NORMAL)

    class Meta:
        db_table = "tb_tendis_autofix_ignore"


class NodeUpdateTaskStatus(str, StructuredEnum):
    TODO = EnumField("todo", _("待处理"))
    CANCELED = EnumField("canceled", _("已取消"))
    FAILED = EnumField("failed", _("失败"))
    DOING = EnumField("doing", _("执行中"))
    SUCCESS = EnumField("success", _("成功"))


class TbRedisClusterNodesUpdateTask(models.Model):
    id = models.BigAutoField(primary_key=True)
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"), default=0)
    cluster_id = models.IntegerField(verbose_name=_("集群ID"), default=0)
    cluster_type = models.CharField(verbose_name=_("集群类型"), choices=ClusterType.get_choices(), max_length=LEN_NORMAL)
    immute_domain = models.CharField(verbose_name=_("集群域名"), max_length=LEN_LONG, default="")
    message = models.TextField(default="", verbose_name=_("信息"))
    status = models.CharField(
        verbose_name=_("任务状态"), max_length=LEN_NORMAL, choices=NodeUpdateTaskStatus.get_choices()
    )
    report_server_ip = models.GenericIPAddressField(verbose_name=_("上报IP"), default="")
    report_server_port = models.IntegerField(verbose_name=_("上报端口"), default=0)
    report_nodes_data = models.TextField(default="", verbose_name=_("上报的nodes data"))
    report_time = models.DateTimeField(verbose_name=_("上报时间"), default="1970-01-01 08:00:01")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))

    class Meta:
        db_table = "tb_tendis_cluster_nodes_update_task"
        indexes = [
            models.Index(fields=["create_time"], name="idx_create_time"),
            models.Index(fields=["bk_biz_id", "create_time"], name="idx_biz_create_time"),
            models.Index(fields=["immute_domain", "create_time"], name="idx_domain_create_time"),
        ]
