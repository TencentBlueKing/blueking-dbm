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
import base64
import logging
import os.path

from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from backend import env
from backend.components import JobApi
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import *  # pylint: disable=wildcard-import

logger = logging.getLogger("root")

SNIPPETS_DIR = os.path.join(os.path.dirname(settings.BASE_DIR), "scripts/snippets")


@swagger_auto_schema(name=_("drop_cluster - 方便调试，后面去掉"), methods=["GET"], auto_schema=None)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def drop_cluster(request, cluster_id):
    try:
        cluster = Cluster.objects.get(pk=cluster_id)

        if cluster.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBHA]:
            db_type = "mysql"
        elif cluster.cluster_type in [ClusterType.Es, ClusterType.Kafka, ClusterType.Hdfs]:
            db_type = cluster.cluster_type.lower()
        else:
            db_type = "redis"

        with open(os.path.join(SNIPPETS_DIR, f"uninstall_{db_type}.sh"), "r") as f:
            script_content = f.read()

        cluster_ips = set(
            list(cluster.storageinstance_set.values_list("machine__ip", flat=True))
            + list(cluster.proxyinstance_set.values_list("machine__ip", flat=True))
        )

        cluster.nosqlstoragesetdtl_set.all().delete()
        cluster.storageinstance_set.all().delete()
        cluster.proxyinstance_set.all().delete()
        cluster.clusterentry_set.all().delete()
        Machine.objects.filter(ip__in=cluster_ips).delete()
        cluster.delete()

        resp = JobApi.fast_execute_script(
            {
                "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
                "script_content": str(base64.b64encode(script_content.encode("utf-8")), "utf-8"),
                "task_name": _("清理集群"),
                "account_alias": "root",
                "script_language": 1,
                "target_server": {"ip_list": [{"bk_cloud_id": cluster.bk_cloud_id, "ip": ip} for ip in cluster_ips]},
            },
            raw=True,
        )
        return JsonResponse(resp)
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse(e)


@swagger_auto_schema(name=_("drop_my_cluster - 方便调试，后面去掉"), methods=["GET"], auto_schema=None)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def drop_my_cluster(request):
    try:
        username = request.query_params.get("username")
        NosqlStorageSetDtl.objects.all().delete()
        ProxyInstance.objects.filter(creator=username).delete()
        StorageInstance.objects.filter(creator=username).delete()
        Machine.objects.filter(creator=username).delete()
        ClusterEntry.objects.filter(creator=username).delete()
        Cluster.objects.filter(creator=username).delete()

        return JsonResponse({"message": "success"})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse(e)
