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
from django.db.models import QuerySet

from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.register import register_resource_decorator


@register_resource_decorator()
class SqlserverListRetrieveResource(query.ListRetrieveResource):
    """查看 sqlserver 架构的资源"""

    db_sync_mode_map = {}

    @classmethod
    def _filter_cluster_hook(
        cls,
        bk_biz_id,
        cluster_queryset: QuerySet,
        proxy_queryset: QuerySet,
        storage_queryset: QuerySet,
        limit: int,
        offset: int,
        **kwargs,
    ) -> query.ResourceList:
        # 获取集群与主从模式的映射
        cls.db_sync_mode_map = {
            mode.cluster_id: mode.sync_mode
            for mode in SqlserverClusterSyncMode.objects.filter(cluster_id__in=cluster_queryset)
        }
        cluster_infos = super()._filter_cluster_hook(
            bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit, offset
        )
        return cluster_infos
