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

from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.views import BaseProxyPassViewSet

from ...exceptions import ProxyPassBaseException
from .serializers import CreateClusterSerializer, DeleteClusterSerializer, UpdateClusterSerializer


class K8sClusterApiProxyPassViewSet(BaseProxyPassViewSet):
    """
    k8s容器化接口的透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]创建集群"),
        request_body=CreateClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=CreateClusterSerializer, url_path="k8s/cluster/create")
    def create_cluster(self, request):
        """创建集群和集群入口"""
        params = self.params_validate(self.get_serializer_class())
        params["creator"] = params.pop("operator", "system")

        # 创建集群
        cluster, cluster_created = Cluster.objects.get_or_create(
            name=params["name"],
            cluster_type=params["cluster_type"],
            bk_biz_id=params["bk_biz_id"],
            defaults=params,
        )

        if not cluster_created:
            raise ProxyPassBaseException(_("集群已存在，创建失败"))

        return Response(cluster.to_dict())

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]删除集群"),
        request_body=DeleteClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DeleteClusterSerializer, url_path="k8s/cluster/delete")
    def delete_cluster(self, request):
        """删除集群和对应的入口"""
        params = self.params_validate(self.get_serializer_class())
        cluster_type = params["cluster_type"]
        name = params["name"]
        bk_biz_id = params["bk_biz_id"]

        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, name=name, cluster_type=cluster_type)
        # 删除所有entry
        cluster.clusterentry_set.all().update(forward_to=None)
        cluster.clusterentry_set.all().delete()
        # 删除集群
        cluster.delete()

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]更新集群"),
        request_body=UpdateClusterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateClusterSerializer, url_path="k8s/cluster/update")
    def update_cluster(self, request):
        """更新集群和入口"""
        params = self.params_validate(self.get_serializer_class())
        params["updater"] = params.pop("operator", "system")

        cluster_type = params["cluster_type"]
        name = params["name"]
        bk_biz_id = params["bk_biz_id"]
        cluster_entry_type = params.pop("cluster_entry_type")

        cluster = Cluster.objects.get(name=name, cluster_type=cluster_type, bk_biz_id=bk_biz_id)
        # 更新集群字段
        cluster.__dict__.update(**params)
        cluster.save()
        # 更新集群入口，目前认为k8s cluster一个集群只有一个入口
        ClusterEntry.objects.update_or_create(
            cluster=cluster, defaults={"cluster_entry_type": cluster_entry_type, "entry": params["immute_domain"]}
        )

        return Response(cluster.to_dict())
