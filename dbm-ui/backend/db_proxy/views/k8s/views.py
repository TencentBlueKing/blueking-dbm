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
from backend.components.dns.client import DnsApi
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.views import BaseProxyPassViewSet

from ...exceptions import ProxyPassBaseException
from .serializers import (
    CreateClusterSerializer,
    CreateDomainSerializer,
    DeleteClusterSerializer,
    DeleteDomainSerializer,
    GetDomainSerializer,
    UpdateClusterSerializer,
    UpdateClusterStatusSerializer,
    UpdateDomainSerializer,
)


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

    @staticmethod
    def _format_domain(domain_name: str) -> str:
        """保证域名末尾有 '.'"""
        return domain_name if domain_name.endswith(".") else f"{domain_name}."

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]创建域名"),
        request_body=CreateDomainSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=CreateDomainSerializer, url_path="k8s/domain/create")
    def create_domain(self, request):
        """
        为 k8s 集群创建 DNS 域名解析，并在 ClusterEntry 中记录
        instances 格式：["ip#port", ...]
        """
        params = self.params_validate(self.get_serializer_class())
        bk_biz_id = params["bk_biz_id"]
        bk_cloud_id = params["bk_cloud_id"]
        cluster_type = params["cluster_type"]
        name = params["name"]
        domain = params["domain"]
        instances = params["instances"]
        role = params["role"]

        cluster = Cluster.objects.get(name=name, cluster_type=cluster_type, bk_biz_id=bk_biz_id)

        # 调用 DnsApi 注册解析
        DnsApi.create_domain(
            {
                "app": str(bk_biz_id),
                "bk_cloud_id": bk_cloud_id,
                "domains": [{"domain_name": self._format_domain(domain), "instances": instances}],
            }
        )

        existing_entry = ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS, entry=domain).exists()
        if not existing_entry:
            # 写入 ClusterEntry
            ClusterEntry.objects.create(
                creator=params["operator"],
                cluster=cluster,
                cluster_entry_type=ClusterEntryType.DNS,
                entry=domain,
                role=role,
            )
        return Response({"domain": domain, "instances": instances})

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]删除域名"),
        request_body=DeleteDomainSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DeleteDomainSerializer, url_path="k8s/domain/delete")
    def delete_domain(self, request):
        """
        删除 k8s 集群的 DNS 域名解析，并删除 ClusterEntry 中对应记录
        """
        params = self.params_validate(self.get_serializer_class())
        bk_biz_id = params["bk_biz_id"]
        bk_cloud_id = params["bk_cloud_id"]
        cluster_type = params["cluster_type"]
        name = params["name"]
        domain = params["domain"]
        instances = params.get("instances", [])  # 新增：获取要删除的实例列表

        cluster = Cluster.objects.get(name=name, cluster_type=cluster_type, bk_biz_id=bk_biz_id)

        # 如果传入了要删除的实例列表，则只删除这些实例
        if instances:
            # 调用 DnsApi 删除特定实例
            DnsApi.delete_domain(
                {
                    "app": str(bk_biz_id),
                    "bk_cloud_id": bk_cloud_id,
                    "domains": [{"domain_name": self._format_domain(domain), "instances": instances}],
                }
            )
            return Response({"message": _("成功删除指定实例"), "deleted_instances": instances})

        # 如果没有传入实例列表，则保持原来的行为：删除整个域名
        entry = ClusterEntry.objects.filter(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=domain
        ).first()
        if not entry:
            raise ProxyPassBaseException(_("域名 {} 不存在，删除失败").format(domain))

        # 调用 DnsApi 删除解析
        DnsApi.delete_domain(
            {
                "app": str(bk_biz_id),
                "bk_cloud_id": bk_cloud_id,
                "domains": [{"domain_name": self._format_domain(domain)}],
            }
        )

        # 先解除 forward_to 引用，再删除
        entry.forward_from.all().update(forward_to=None)
        entry.delete()
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]更新域名"),
        request_body=UpdateDomainSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateDomainSerializer, url_path="k8s/domain/update")
    def update_domain(self, request):
        """
        更新 k8s 集群的 DNS 域名解析（替换某条 ip#port 映射）
        old_instance / new_instance 格式：ip#port
        """
        params = self.params_validate(self.get_serializer_class())
        bk_biz_id = params["bk_biz_id"]
        bk_cloud_id = params["bk_cloud_id"]
        cluster_type = params["cluster_type"]
        name = params["name"]
        domain = params["domain"]
        old_instance = params["old_instance"]
        new_instance = params["new_instance"]

        # 校验集群和域名存在
        cluster = Cluster.objects.get(name=name, cluster_type=cluster_type, bk_biz_id=bk_biz_id)
        if not ClusterEntry.objects.filter(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=domain
        ).exists():
            raise ProxyPassBaseException(_("域名 {} 不存在，更新失败").format(domain))

        # 调用 DnsApi 更新解析
        DnsApi.update_domain(
            {
                "app": str(bk_biz_id),
                "bk_cloud_id": bk_cloud_id,
                "domain_name": self._format_domain(domain),
                "instance": old_instance,
                "set": {"instance": new_instance},
            }
        )
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]查询域名"),
        request_body=GetDomainSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetDomainSerializer, url_path="k8s/domain/get")
    def get_domain(self, request):
        """
        查询 k8s 集群的 DNS 域名解析记录
        """
        params = self.params_validate(self.get_serializer_class())
        bk_biz_id = params["bk_biz_id"]
        bk_cloud_id = params["bk_cloud_id"]
        domain = params["domain"]

        res = DnsApi.get_domain(
            {
                "app": str(bk_biz_id),
                "bk_cloud_id": bk_cloud_id,
                "domain_name": self._format_domain(domain),
            }
        )
        return Response(res)

    @common_swagger_auto_schema(
        operation_summary=_("[k8s]集群状态更新"),
        request_body=UpdateClusterStatusSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=UpdateClusterStatusSerializer,
        url_path="k8s/domain/update_cluster_status",
    )
    def update_cluster_status(self, request):
        params = self.params_validate(self.get_serializer_class())
        cluster = Cluster.objects.filter(id=params["cluster_id"]).first()
        if not cluster:
            raise ProxyPassBaseException(_("集群id {} 不存在，更新失败").format(params["cluster_id"]))

        cluster.phase = params["phase"]
        cluster.status = params["status"]
        cluster.save()
        return Response()
