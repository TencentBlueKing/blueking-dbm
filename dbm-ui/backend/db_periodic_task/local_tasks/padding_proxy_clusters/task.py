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
from celery.schedules import crontab

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task


@register_periodic_task(run_every=crontab(minute="*"))
def update_padding_proxy_clusters():
    """
    有些db机器部署了业务进程的老业务, 还有新增集群的需求
    以前padding proxy是录入的域名
    搞个task动态更新下
    """
    padding_proxy_bk_biz_ids = SystemSettings.get_setting_value(SystemSettingsEnum.PADDING_PROXY_APPS.value)

    padding_proxy_clusters = SystemSettings.get_setting_value(SystemSettingsEnum.PADDING_PROXY_CLUSTER_LIST.value)
    for bk_biz_id in padding_proxy_bk_biz_ids:
        for c in Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBHA):
            if c.immute_domain not in padding_proxy_clusters:
                padding_proxy_clusters.append(c.immute_domain)

    SystemSettings.objects.filter(key=SystemSettingsEnum.PADDING_PROXY_CLUSTER_LIST).update(
        value=padding_proxy_clusters
    )
