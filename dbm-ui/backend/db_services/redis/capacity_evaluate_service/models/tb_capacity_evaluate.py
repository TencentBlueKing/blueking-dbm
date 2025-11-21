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
import datetime

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CapacityEvaluateRecord(models.Model):
    """capacity evaluate record"""

    action_id = models.CharField(max_length=128, default="", verbose_name=_("Action ID"))
    action_name = models.CharField(max_length=128, default="", verbose_name=_("Action Name"))
    action_type = models.CharField(max_length=64, default="", verbose_name=_("Action Type"))
    action_user = models.CharField(max_length=64, default="", blank=True, null=True, verbose_name=_("Action User"))
    bk_biz_id = models.IntegerField(default=0, verbose_name=_("Business ID"))
    bk_biz_name = models.CharField(max_length=64, default="", verbose_name=_("Business Name"))
    cluster_id = models.IntegerField(default=0, verbose_name=_("Cluster ID"))
    cluster_domain = models.CharField(max_length=64, default="", verbose_name=_("Cluster Domain"))
    cluster_type = models.CharField(max_length=256, default="", verbose_name=_("Cluster Type"))
    evaluate_method = models.CharField(max_length=64, default="", blank=True, verbose_name=_("Evaluate Method"))
    evaluate_time = models.DateTimeField(default=timezone.now, verbose_name=_("Evaluate Time"))
    start_time = models.DateTimeField(default=None, verbose_name=_("Start Time"))
    end_time = models.DateTimeField(default=None, verbose_name=_("End Time"))
    req_qps_k = models.IntegerField(default=0, verbose_name=_("Req QPS K"))
    req_capacity_m = models.IntegerField(default=0, verbose_name=_("Req Capacity M"))
    key_pattern = models.CharField(max_length=2048, default="", verbose_name=_("Key Pattern"))
    req_flag_no_big_key_with_a_lot_of_member = models.BooleanField(
        default=False, verbose_name=_("Req Flag No Big Key With A Lot Of Member")
    )
    req_flag_no_big_result = models.BooleanField(default=False, verbose_name=_("Req Flag No Big Result"))
    req_flag_no_big_value = models.BooleanField(default=False, verbose_name=_("Req Flag No Big Value"))
    req_flag_no_hot_key = models.BooleanField(default=False, verbose_name=_("Req Flag No Hot Key"))
    req_flag_no_use_dns = models.IntegerField(default=0, verbose_name=_("Req Flag No Use DNS"))
    is_force = models.IntegerField(default=0, null=True, verbose_name=_("Is Force"))
    last_approved_user = models.CharField(max_length=64, default="", verbose_name=_("Last Approved User"))
    last_approved_status = models.IntegerField(default=0, verbose_name=_("Last Approved Status"))
    last_approved_time = models.DateTimeField(default=timezone.now, verbose_name=_("Last Approved Time"))

    # 如果这个__data__ 改为__dict__ 会报错，因为__dict__ 被Model用了
    def __data__(self):
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "action_type": self.action_type,
            "bk_biz_id": self.bk_biz_id,
            "bk_biz_name": self.bk_biz_name,
            "cluster_id": self.cluster_id,
            "cluster_domain": self.cluster_domain,
            "cluster_type": self.cluster_type,
            "evaluate_time": self.evaluate_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "req_qps_k": self.req_qps_k,
            "req_capacity_m": self.req_capacity_m,
            "key_pattern": self.key_pattern,
            "req_flag_no_big_key_with_a_lot_of_member": self.req_flag_no_big_key_with_a_lot_of_member,
            "req_flag_no_big_result": self.req_flag_no_big_result,
            "req_flag_no_big_value": self.req_flag_no_big_value,
            "req_flag_no_hot_key": self.req_flag_no_hot_key,
            "req_flag_no_use_dns": self.req_flag_no_use_dns,
            "is_force": self.is_force,
            "action_user": self.action_user,
            "last_approved_user": self.last_approved_user,
            "last_approved_status": self.last_approved_status,
            "last_approved_time": self.last_approved_time,
        }

    class Meta:
        """meta"""

        db_table = "tb_capacity_evaluate_request"
        verbose_name = _("Capacity Evaluate Record")
        verbose_name_plural = _("Capacity Evaluate Records")
        unique_together = [("cluster_id", "action_id")]
        ordering = ["-start_time"]

    def get_run_stats(self, t: datetime.datetime):
        """获取运行状态"""
        if self.start_time.timestamp() > t.timestamp():
            return "not_start"
        if self.end_time.timestamp() < t.timestamp():
            return "end"
        return "running"

    def __str__(self):
        return f"CapacityEvaluateRecord(action_id={self.action_id}, action_name={self.action_name}"
