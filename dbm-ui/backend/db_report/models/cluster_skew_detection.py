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


class ClusterSkewDetection(models.Model):
    """
    是个 doris 表
    这里的定义只是用来读写
    migrate 不让 django 管理
    """

    dt = models.DateField()
    detect_time = models.DateTimeField(primary_key=True)
    cluster_domain = models.CharField(max_length=256)
    metric_name = models.CharField(max_length=64)
    instance_role = models.CharField(max_length=64)
    node = models.CharField(max_length=128)
    value = models.DecimalField(max_digits=18, decimal_places=2)
    mean_value = models.DecimalField(max_digits=18, decimal_places=2)
    pct_deviation = models.DecimalField(max_digits=18, decimal_places=2)
    abs_deviation = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        managed = False
        db_table = "cluster_skew_detection"
