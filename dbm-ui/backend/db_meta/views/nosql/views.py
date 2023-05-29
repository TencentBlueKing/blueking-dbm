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

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

from backend.db_meta import api
from backend.db_meta.enums import ClusterType

logger = logging.getLogger("root")

"""_summary_
    提供 数据迁移、场景化相关的接口服务
    1. 创建集群
    2. 查询数据 (根据IP查询)
"""


@swagger_auto_schema(
    methods=["get"],
    manual_parameters=[
        openapi.Parameter(
            name="bk_cloud_id",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_NUMBER,
        ),
        openapi.Parameter(
            name="bk_biz_id",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_NUMBER,
        ),
        openapi.Parameter(
            name="hosts",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING),
            collectionFormat="multi",
        ),
    ],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def instances(request: Request):
    try:
        return JsonResponse({"code": 0, "msg": "", "data": api.cluster.query_instances(**request.query_params)})
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        return JsonResponse({"code": 1, "msg": "{}".format(e), "data": ""})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def create_nosql_cluster(request: Request):
    """
    bk_biz_id: int,
    name: str, // set_name
    immute_domain: str,
    db_module_id: int,
    alias: str = "", // set_info
    major_version: str = "", // deploy_version
    creator: str = "",
    region: str = "", // region
    cluster_type: str = ClusterType.TendisTwemproxyRedisInstance.value

    twemproxy :
        proxies  [{"ip":"","port":""},{}]
        storages [{"shard":"0-1000","nodes":{"master":{"ip":"","port":1],"slave":{}}}, {}, {}]
    tendisSingle :
        storages [{"master":{"ip":"","port":""},"slave":{}},{}]
        slave_domain : ""
    mongoRepSet :
        storages :
            [{"role":"mongo_m1","ip":"xx","port":20000,"domain":""},
            {"role":"mongo_m2","ip":"xx","port":20000,"domain":""},
            {"role":"mongo_m3","ip":"xx","port":20000,"domain":""},
            {"role":"mongo_backup","ip":"xx","port":20000,"domain":""}]
    monogoCluster :
        proxies : [{},{}]
        configes: [{},{},{}]
        storages: [{"shard":"S1","nodes":[{"ip":,"port":,"role":},{},{}]},]
    """
    try:
        if request.data["cluster_type"] in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.TwemproxyTendisSSDInstance.value,
        ]:
            api.cluster.nosqlcomm.create_cluster.pkg_create_twemproxy_cluster(**request.data)
        elif request.data["cluster_type"] == ClusterType.TendisRedisInstance:
            api.cluster.tendissingle.pkg_create_single(**request.data)
        elif request.data["cluster_type"] == ClusterType.MongoReplicaSet:
            api.cluster.mongorepset.pkg_create_mongoset(**request.data)
        elif request.data["cluster_type"] == ClusterType.MongoShardedCluster:
            api.cluster.mongocluster.pkg_create_mongo_cluster(**request.data)
        else:
            return JsonResponse({"code": 1, "data": "", "msg": "unsupported {}".format(request.data["cluster_type"])})
        return JsonResponse({"code": 0, "data": "", "msg": ""})
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        return JsonResponse({"code": 1, "data": "", "msg": "{}".format(e)})
