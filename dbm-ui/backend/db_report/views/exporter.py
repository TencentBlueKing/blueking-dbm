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

import logging

from django.db.models import Count
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import StorageInstance
from backend.db_report.enums import SWAGGER_TAG
from backend.iam_app.dataclass import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

logger = logging.getLogger("root")


class ClusterExporterUpViewSet(SystemViewSet):

    default_permission_class = [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])]

    @common_swagger_auto_schema(
        operation_summary=_("获取redis集群的exporter数与分片数不一致的报表"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False)
    def get_redis_exporter_mismatch(self, request):
        """获取redis集群的exporter数与分片数不一致的报表"""
        # 获取exporter数与集群的映射
        from backend.db_periodic_task.local_tasks.db_meta.sync_cluster_stat import query_cluster_exporter_up

        exporter_map = query_cluster_exporter_up(DBType.Redis, "dbm_redis_exporter")
        # 获取元数据的集群分片映射
        redis_masters = StorageInstance.objects.filter(instance_role=InstanceRole.REDIS_MASTER)
        shard_map = {
            item["cluster__immute_domain"]: item["total"]
            for item in redis_masters.values("cluster__immute_domain").annotate(total=Count("id"))
        }
        # 过滤exporter与元数据不一致的集群
        mismatch_clusters = [
            {"domain": domain, "shard": shard, "exporter_up": exporter_map.get(domain, 0)}
            for domain, shard in shard_map.items()
            if shard != exporter_map.get(domain, 0)
        ]
        return Response(mismatch_clusters)
