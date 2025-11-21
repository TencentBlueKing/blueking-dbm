"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.flow.consts import StateType

logger = logging.getLogger("root")


class ReportRecord(AuditedModel):
    """
    定义内存分析统计记录表，存储内存分析统计生成每一条分析报告信息
    """

    record_id = models.AutoField(help_text=_("主键id"), primary_key=True)
    ticket_id = models.PositiveIntegerField(default=0, help_text=_("关联的单据id"))
    root_id = models.CharField(max_length=64, default="", help_text=_("关联root_id"))
    bk_biz_id = models.IntegerField(default=0, help_text=_("关联的业务id"))
    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    immute_domain = models.CharField(max_length=255, default="")
    cluster_shard_num = models.IntegerField(default=0, help_text=_("集群分片数"))
    analyzed_shard_num = models.IntegerField(default=0, help_text=_("参与分析的分片数"))
    analysis_time = models.IntegerField(default=0, help_text=_("分析时长"))
    redis_version = models.CharField(max_length=255, default="", help_text=_("redis版本"))
    source_type = models.CharField(max_length=255, default="", help_text=_("数据来源类型"))  # rdb or aof or keyfile
    source_role = models.CharField(max_length=255, default="", help_text=_("rdb来源"))  # master or slave
    source_addr_list = models.JSONField(help_text=_("rdb来源地址列表"), blank=True, null=True, default=list)
    atime_available = models.BooleanField(default=False, help_text=_("atime可用性"))
    sampling_ratio = models.FloatField(default=0.1, help_text=_("采样比例, 0.1表示10%"))
    status = models.CharField(
        max_length=64, choices=StateType.get_choices(), default=StateType.CREATED, help_text=_("报告状态")
    )
    current_progress = models.CharField(max_length=255, default="", help_text=_("当前进度, 0-100"))
    exec_ip = models.CharField(max_length=255, default="", help_text=_("执行ip"))
    keystat_report_rows_num = models.IntegerField(help_text=_("内存分析统计报告行数据"), default=0)
    keystat_rank_rows_num = models.IntegerField(help_text=_("内存分析统计排行行数据"), default=0)

    class Meta:
        verbose_name = verbose_name_plural = _("内存分析统计记录表")
        indexes = [
            models.Index(fields=["bk_biz_id", "create_at"]),
        ]


class ReportProgress(models.Model):
    """
    定义内存分析统计进度记录表，存储内存分析统计生成每一条进度信息
    """

    id = models.AutoField(help_text=_("主键id"), primary_key=True)
    create_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    record_id = models.BigIntegerField(default=0, help_text=_("关联的记录id"))
    progress = models.CharField(max_length=255, default="", help_text=_("进度, 0-100"))
    detail = models.JSONField(help_text=_("进度详情"), blank=True, null=True, default=dict)

    class Meta:
        verbose_name = verbose_name_plural = _("内存分析统计进度记录表")
        indexes = [
            models.Index(fields=["record_id"]),
        ]


class ReportItem(models.Model):
    """
    定义内存分析统计详情记录表，存储内存分析统计生成每一条分析报告详情信息
    """

    id = models.AutoField(help_text=_("主键id"), primary_key=True)
    create_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    record_id = models.BigIntegerField(default=0, help_text=_("关联的记录id"))
    key_name = models.CharField(max_length=255, default="", help_text=_("key名称"))
    key_type = models.CharField(max_length=255, default="", help_text=_("key类型"))
    key_class = models.CharField(max_length=255, default="", help_text=_("key分类"))
    count = models.IntegerField(default=0, help_text=_("数量"))
    count_with_ttl = models.IntegerField(default=0, help_text=_("带TTL的数量"))
    member_max_count = models.IntegerField(default=0, help_text=_("成员最大数量"))
    avg_key_length = models.IntegerField(default=0, help_text=_("平均成员数量"))
    avg_ttl = models.IntegerField(default=0, help_text=_("平均TTL"))
    avg_ttl_human = models.CharField(max_length=255, default="", help_text=_("平均TTL人类化描述"))
    min_idletime_human = models.CharField(max_length=255, default="", help_text=_("最小空闲时间人类化描述"))
    so_min_idletime_human = models.CharField(max_length=255, default="", help_text=_("最小空闲时间人类化描述ForSo"))
    min_idletime = models.IntegerField(default=0, help_text=_("最小空闲时间"))
    min_idletime_show = models.CharField(max_length=255, default="", help_text=_("最近访问时间（带单位）"))
    avg_key_used_bytes = models.IntegerField(default=0, help_text=_("单key平均占用内存"))
    mem_used_bytes = models.IntegerField(default=0, help_text=_("内存使用量字节数"))
    mem_used_pct = models.FloatField(max_length=255, default=0, help_text=_("内存使用量字节数占比"))

    class Meta:
        verbose_name = verbose_name_plural = _("内存分析统计记录详情表")
        indexes = [
            models.Index(fields=["record_id"]),
        ]


class RankItem(models.Model):
    """
    定义内存分析统计排行详情记录表，存储内存分析统计生成每一条排行报告详情信息
    """

    id = models.AutoField(help_text=_("主键id"), primary_key=True)
    create_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    record_id = models.BigIntegerField(default=0, help_text=_("关联的记录id"))
    key_name = models.CharField(max_length=255, default="", help_text=_("key名称"))
    key_type = models.CharField(max_length=255, default="", help_text=_("key类型"))
    rank_value = models.IntegerField(default=0, help_text=_("排行值"))
    ttl = models.IntegerField(default=0, help_text=_("TTL"))
    ttl_human = models.CharField(max_length=255, default="", help_text=_("过期时间（带单位）"))
    atime = models.IntegerField(default=0, help_text=_("最后访问时间"))
    member = models.IntegerField(default=0, help_text=_("成员的数量"))
    member_len = models.IntegerField(default=0, help_text=_("成员的平均长度"))
    key_length = models.IntegerField(default=0, help_text=_("key的长度"))
    value_size = models.IntegerField(default=0, help_text=_("value的长度或者成员value的长度"))
    db = models.IntegerField(default=0, help_text=_("db"))
    memory_size = models.IntegerField(default=0, help_text=_("基础内存占用, 复合类型中是采样计算结果"))

    class Meta:
        verbose_name = verbose_name_plural = _("内存分析统计排行详情表")
        indexes = [
            models.Index(fields=["record_id"]),
        ]
