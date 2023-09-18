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
import logging

from celery import shared_task

from .. import env

logger = logging.getLogger("celery")


@shared_task
def update_app_policy(bk_biz_id, notify_group_id, db_type=None):
    """TODO: 业务监控策略刷新
    当业务运维配置了业务dba时，可调用该task立即下发策略更新
    notify_group_id: 新建的业务告警组
    """

    now = datetime.datetime.now()
    logger.warning("[db_monitor] update_app_policy start: %s", now)
