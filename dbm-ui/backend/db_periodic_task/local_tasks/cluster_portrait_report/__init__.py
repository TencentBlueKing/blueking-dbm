# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告 —— 包入口。

模块职责：
    - 导出 celery beat 触发点 :func:`generate_cluster_portrait_report`（每日 0 点）
    - 导入各 db_type 画像 Task 触发 ``@register_dispatch_task`` 副作用，使其进入 dispatch registry，
      并被 :func:`generate_cluster_portrait_report` 自动纳入每日投递；导入顺序即轮转顺序
"""
from backend.db_periodic_task.local_tasks.cluster_portrait_report.mysql_portrait_task import MysqlPortraitReportTask
from backend.db_periodic_task.local_tasks.cluster_portrait_report.redis_portrait_task import RedisPortraitReportTask
from backend.db_periodic_task.local_tasks.cluster_portrait_report.task import generate_cluster_portrait_report

__all__ = ["generate_cluster_portrait_report", "MysqlPortraitReportTask", "RedisPortraitReportTask"]
