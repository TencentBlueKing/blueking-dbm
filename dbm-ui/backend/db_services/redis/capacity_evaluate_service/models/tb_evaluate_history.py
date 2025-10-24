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
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CapacityEvaluateHistory(models.Model):
    """capacity evaluate history, 每次评估都会生成一条记录, 记录当前的评估结果"""

    """ 1. 当前集群的容量信息. 2. 本次请求的简要信息. 3 其它相关请求的简要信息. 4. 本次评估结果"""

    id = models.AutoField(primary_key=True, verbose_name=_("ID"))
    # 当前集群的容量信息
    bk_biz_id = models.IntegerField(default=0, verbose_name=_("Business ID"))
    bk_biz_name = models.CharField(max_length=64, default="", verbose_name=_("Business Name"))
    cluster_id = models.IntegerField(default=0, verbose_name=_("Cluster ID"))
    cluster_domain = models.CharField(max_length=64, default="", verbose_name=_("Cluster Domain"))
    cluster_type = models.CharField(max_length=256, default="", verbose_name=_("Cluster Type"))
    free_size_mb = models.IntegerField(default=0, verbose_name=_("Free Size MB"))
    total_size_mb = models.IntegerField(default=0, verbose_name=_("Total Size MB"))
    proxy_count = models.IntegerField(default=0, verbose_name=_("Proxy Count"))
    proxy_qps_k = models.IntegerField(default=0, verbose_name=_("Proxy QPS K"))
    evaluate_method = models.CharField(max_length=64, default="", blank=True, verbose_name=_("Evaluate Method"))
    evaluate_time = models.DateTimeField(default=timezone.now, verbose_name=_("Evaluate Time"))
    time_elapsed_ms = models.IntegerField(default=0, verbose_name=_("Evaluate cost time ms"))
    # 本次评估的简要信息
    action_id = models.CharField(max_length=128, default="", verbose_name=_("Action ID"))
    action_name = models.CharField(max_length=128, default="", verbose_name=_("Action Name"))
    action_type = models.CharField(max_length=64, default="", verbose_name=_("Action Type"))
    req_qps_k = models.IntegerField(default=0, verbose_name=_("Req QPS K"))
    req_capacity_m = models.IntegerField(default=0, verbose_name=_("Req Capacity M"))
    req_flags_json = models.CharField(max_length=1024, default="", verbose_name=_("Req Flags JSON"))
    # 相关评估记录的简要信息
    req_qps_k_total = models.IntegerField(default=0, verbose_name=_("Req QPS K Total"))
    req_capacity_m_total = models.IntegerField(default=0, verbose_name=_("Req Capacity M Total"))
    not_finished_records_json = models.CharField(
        max_length=4096, default="", verbose_name=_("Not Finished Records JSON")
    )
    # 本次评估结果
    is_force = models.IntegerField(default=0, null=True, verbose_name=_("Is Force"))
    action_user = models.CharField(max_length=64, default="", blank=True, null=True, verbose_name=_("Action User"))
    approved_user = models.CharField(max_length=64, default="", blank=True, null=True, verbose_name=_("Approved User"))
    approved_status = models.CharField(max_length=64, default="", verbose_name=_("Approved Status"))
    approved_time = models.DateTimeField(default=timezone.now, blank=True, null=True, verbose_name=_("Approved Time"))
    approved_comment = models.CharField(max_length=2048, default="", blank=True, verbose_name=_("Approved Comment"))

    class Meta:
        """meta"""

        db_table = "tb_capacity_evaluate_history"
        verbose_name = _("Capacity Evaluate History")
        verbose_name_plural = _("Capacity Evaluate Histories")
        unique_together = [("cluster_id", "evaluate_time")]
        ordering = ["-evaluate_time"]
        indexes = [
            models.Index(fields=["cluster_id", "evaluate_time"]),
        ]

    def __data__(self):
        return {
            "bk_biz_id": self.bk_biz_id,
            "bk_biz_name": self.bk_biz_name,
            "cluster_id": self.cluster_id,
            "cluster_domain": self.cluster_domain,
            "cluster_type": self.cluster_type,
            "free_size_mb": self.free_size_mb,
            "total_size_mb": self.total_size_mb,
            "proxy_count": self.proxy_count,
            "proxy_qps_k": self.proxy_qps_k,
            "evaluate_method": self.evaluate_method,
            "evaluate_time": self.evaluate_time,
            "time_elapsed_ms": self.time_elapsed_ms,
            "action_id": self.action_id,
            "action_name": self.action_name,
            "action_type": self.action_type,
            "req_qps_k": self.req_qps_k,
            "req_capacity_m": self.req_capacity_m,
            "req_flags_json": self.req_flags_json,
            "req_qps_k_total": self.req_qps_k_total,
            "req_capacity_m_total": self.req_capacity_m_total,
            "not_finished_records_json": self.not_finished_records_json,
            "is_force": self.is_force,
            "action_user": self.action_user,
            "approved_user": self.approved_user,
            "approved_status": self.approved_status,
            "approved_time": self.approved_time,
            "approved_comment": self.approved_comment,
        }
