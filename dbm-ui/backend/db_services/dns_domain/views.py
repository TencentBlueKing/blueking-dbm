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
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dns_domain.handlers import DnsDomainHandler
from backend.db_services.dns_domain.serializers import (
    DnsDomainAuditExportSerializer,
    DnsDomainAuditSerializer,
    DnsDomainCreateSerializer,
    DnsDomainDeleteSerializer,
    DnsDomainDetailSerializer,
    DnsDomainListSerializer,
    DnsDomainUpdateSerializer,
)
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import IAMPermission, ResourceActionPermission, get_request_key_id

SWAGGER_TAG = [_("域名服务")]


class DnsAuditPermission(IAMPermission):
    """本域日志需要该域名的 dns_manage。全局日志无 dns_audit_view 时返回 IAM 无权限数据。"""

    def __init__(self):
        super().__init__(actions=[])

    def has_permission(self, request, view):
        scope = get_request_key_id(request, "scope", default="domain")
        if scope == "global":
            self.actions = [ActionEnum.DNS_AUDIT_VIEW]
            self.resources = []
            return super().has_permission(request, view)
        domain = get_request_key_id(request, "domain")
        if not domain:
            return False
        self.actions = [ActionEnum.DNS_MANAGE]
        self.resources = [[ResourceEnum.DNS_DOMAIN.create_instance(domain)]]
        return super().has_permission(request, view)


def _domain_ids(request, view):
    domain = get_request_key_id(request, "domain")
    return [domain] if domain else []


class DnsDomainViewSet(viewsets.SystemViewSet):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.action != "service_status" and not env.DNS_DOMAIN_SERVICE_ENABLED:
            raise NotFound(_("当前环境未开放域名服务"))

    def _get_custom_permissions(self):
        domain_manage = ResourceActionPermission(
            [ActionEnum.DNS_MANAGE], ResourceEnum.DNS_DOMAIN, instance_ids_getter=_domain_ids
        )
        return {
            "service_status": [],
            "list_domains": [],
            "retrieve_domain": [domain_manage],
            "create_domain": [ResourceActionPermission([ActionEnum.DNS_DOMAIN_CREATE])],
            "update_domain": [domain_manage],
            "delete_domain": [domain_manage],
            "list_audits": [DnsAuditPermission()],
            "export_audits": [DnsAuditPermission()],
        }.get(self.action, self.get_default_permission_class())

    def _handler(self) -> DnsDomainHandler:
        return DnsDomainHandler(username=self.request.user.username, request=self.request)

    @common_swagger_auto_schema(operation_summary=_("域名服务是否开放"), tags=SWAGGER_TAG)
    @action(methods=["GET"], detail=False, url_path="enabled")
    def service_status(self, request, *args, **kwargs):
        return Response({"enabled": env.DNS_DOMAIN_SERVICE_ENABLED})

    @common_swagger_auto_schema(
        operation_summary=_("域名列表"), query_serializer=DnsDomainListSerializer(), tags=SWAGGER_TAG
    )
    @action(methods=["GET"], detail=False, url_path="domains", serializer_class=DnsDomainListSerializer)
    def list_domains(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self._handler().list_domains(data))

    @common_swagger_auto_schema(
        operation_summary=_("域名详情"), query_serializer=DnsDomainDetailSerializer(), tags=SWAGGER_TAG
    )
    @action(methods=["GET"], detail=False, url_path="domains/detail", serializer_class=DnsDomainDetailSerializer)
    def retrieve_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self._handler().retrieve_domain(data["domain"]))

    @common_swagger_auto_schema(operation_summary=_("新建自主维护域名"), tags=SWAGGER_TAG)
    @action(methods=["POST"], detail=False, url_path="domains/create", serializer_class=DnsDomainCreateSerializer)
    def create_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self._handler().create_domain(data))

    @common_swagger_auto_schema(operation_summary=_("保存自主维护域名"), tags=SWAGGER_TAG)
    @action(methods=["POST"], detail=False, url_path="domains/update", serializer_class=DnsDomainUpdateSerializer)
    def update_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self._handler().update_domain(data))

    @common_swagger_auto_schema(operation_summary=_("删除自主维护域名"), tags=SWAGGER_TAG)
    @action(methods=["POST"], detail=False, url_path="domains/delete", serializer_class=DnsDomainDeleteSerializer)
    def delete_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self._handler().delete_domain(data))

    @common_swagger_auto_schema(
        operation_summary=_("域名操作日志"), query_serializer=DnsDomainAuditSerializer(), tags=SWAGGER_TAG
    )
    @action(methods=["GET"], detail=False, url_path="audits", serializer_class=DnsDomainAuditSerializer)
    def list_audits(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self._handler().list_audits(data))

    @common_swagger_auto_schema(
        operation_summary=_("导出域名操作日志"), query_serializer=DnsDomainAuditExportSerializer(), tags=SWAGGER_TAG
    )
    @action(methods=["GET"], detail=False, url_path="audits/export", serializer_class=DnsDomainAuditExportSerializer)
    def export_audits(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return self._handler().export_audits(data)
