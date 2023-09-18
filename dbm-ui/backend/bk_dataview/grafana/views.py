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
from urllib import parse

import requests
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from backend.db_monitor.models import Dashboard as MonitorDash

from ...configuration.constants import BKM_DBM_TOKEN
from ...configuration.models import SystemSettings
from . import client
from .provisioning import Dashboard, Datasource
from .settings import grafana_settings
from .utils import requests_curl_log

rpool = requests.Session()

logger = logging.getLogger(__name__)

CACHE_HEADERS = ["Cache-Control", "Expires", "Pragma", "Last-Modified"]
# 缓存配置
_USER_CACHE = {}
_ORG_CACHE = {}
_ORG_CACHE_REVERSE = {}
_ORG_DASHBOARDS_CACHE = {}
_ORG_USERS = {}

DEFAULT_ORG_ID = 1
DEFAULT_ORG_NAME = "dbm"


class ForbiddenError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class ProxyBaseView(View):
    authentication_classes = grafana_settings.AUTHENTICATION_CLASSES
    permission_classes = grafana_settings.PERMISSION_CLASSES
    provisioning_classes = ()

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        self.handler = grafana_settings.BACKEND_CLASS()
        # Ensure that the incoming request is permitted
        self.perform_authentication(request)
        self.check_permissions(request)
        self.perform_provisioning(request)

    def perform_authentication(self, request):
        if len(self.authentication_classes) == 0:
            return

        for authentication_cls in self.authentication_classes:
            authentication = authentication_cls()
            user_auth_tuple = authentication.authenticate(request)
            if user_auth_tuple is None:
                continue

            # 中间件缺少LoginRequired，这里直接注入user
            request.user, _ = user_auth_tuple

            # 只要有一个满足, 创建用户
            self.provision_user(request, request.user.username)
            break
        else:
            raise UnauthorizedError()

    def check_permissions(self, request):
        """权限校验"""
        if len(self.permission_classes) == 0:
            return

        if not request.org_name:
            raise ForbiddenError()

        for permission_cls in self.permission_classes:
            permission = permission_cls()
            ok = permission.has_permission(request, self, request.org_name)
            if not ok:
                raise ForbiddenError(permission)

        # 全部通过, 创建org
        # logger.info("org_name: %s, user.username: %s", request.org_name, request.user.username)
        org_id = self.provision_org(request.org_name, request.user.username)

        return org_id

    def perform_provisioning(self, request):
        """默认的数据源, 面板注入"""
        if len(self.provisioning_classes) == 0:
            logger.warning("perform_provisioning: %s", len(self.provisioning_classes))
            return

        logger.warning("perform_provisioning: %s", self.provisioning_classes)
        org_name = request.org_name
        # 默认-1, 和 grafana保持一致
        org_id = _ORG_CACHE.get(org_name, -1)

        for provisioning_cls in self.provisioning_classes:
            provisioning = provisioning_cls()

            # 仅当db中配置了监控的token，才进行数据源初始化
            if SystemSettings.objects.filter(key=BKM_DBM_TOKEN).exists():
                # 注入数据源
                ds_list = []
                logger.info("create datasource monitor for grafana")
                for ds in provisioning.datasources(request, org_name, org_id):
                    if not isinstance(ds, Datasource):
                        raise ValueError("%s is not instance %s" % (type(ds), Datasource))
                    ds_list.append(ds)
                self.handler.handle_datasources(request, org_name, org_id, ds_list)
            else:
                logger.error("skip datasource init for grafana, please set BKM_DBM_TOKEN in database")

            # 注入面板
            for db in provisioning.dashboards(request, org_name, org_id):
                if not isinstance(db, Dashboard):
                    raise ValueError("%s is not instance %s" % (type(db), Dashboard))

                self.provision_dashboard(request, org_name, org_id, db)

    def provision_user(self, request, username: str):
        """注入用户"""
        if username in _USER_CACHE:
            return _USER_CACHE[username]

        resp = client.get_user_by_login_or_email(username)
        if resp.status_code == 200:
            _user = resp.json()
            _USER_CACHE[username] = _user
            return _user

        if resp.status_code == 404:
            resp = client.create_user(username)
            _user = resp.json()
            _USER_CACHE[username] = _user
            return _user

    def provision_org(self, org_name: str, username: str):
        """注入org"""
        if org_name in _ORG_CACHE:
            org_id = _ORG_CACHE[org_name]
        else:
            org_id = self._get_org_id(org_name)

        if username in _ORG_USERS.get(org_id, []):
            return org_id

        resp = client.get_org_users(org_id)
        _ORG_USERS[org_id] = set()
        for i in resp.json():
            _ORG_USERS[org_id].add(i["login"])
            if i["login"] == username:
                break
        else:
            resp = client.add_user_to_org(org_id, username)
            if resp.status_code != 200:
                logger.error("add_user_to_org(%s, %s)", org_id, username, resp.content)
                raise ForbiddenError()

        _ORG_USERS[org_id].add(username)
        _ORG_CACHE[org_name] = org_id
        _ORG_CACHE_REVERSE[org_id] = org_name
        return org_id

    def provision_dashboard(self, request, org_name: str, org_id: int, db: Dashboard):
        """注入面板"""
        _ORG_DASHBOARDS_CACHE.setdefault(org_name, {})

        if db.title in _ORG_DASHBOARDS_CACHE[org_name]:
            return

        resp = client.update_dashboard(org_id, 0, db.dashboard)
        if resp.status_code == 200:
            dash = resp.json()
            MonitorDash.objects.update_or_create(
                defaults={
                    "name": db.title,
                    "uid": dash["uid"],
                    "url": dash["url"],
                    "details": db.dashboard,
                },
                org_id=DEFAULT_ORG_ID,
                org_name=DEFAULT_ORG_NAME,
                cluster_type=db.dashboard["tags"][0],
            )
            _ORG_DASHBOARDS_CACHE[org_name][db.title] = resp.json()
            logger.info("provision dashboard success, %s", resp)
        else:
            logger.info("provision dashboard error, %s", resp.content)

    def _get_org_id(self, org_name):
        resp = client.get_organization_by_name(org_name)
        if resp.status_code == 200:
            _org = resp.json()
            return _org["id"]

        if resp.status_code == 404:
            # 暂时不用org做业务隔离，统一在默认org（id=1）的命名空间下
            # resp = client.create_organization(org_name)
            # _org = resp.json()
            # return _org["orgId"]
            client.update_organization(org_name, DEFAULT_ORG_ID)
            return DEFAULT_ORG_ID

    def _get_org_name_by_org_id(self, org_id: int) -> str:
        """
        根据org_id获取org_name
        """
        if org_id in _ORG_CACHE_REVERSE:
            return _ORG_CACHE_REVERSE[org_id]

        resp = client.get_organization_by_id(org_id)
        if resp.status_code != 200:
            logger.error(
                f"_get_org_name_by_org_id error, "
                f"org_id: {org_id} status_code: {resp.status_code}, content: {resp.content}"
            )
            raise Http404

        _org = resp.json()
        _ORG_CACHE_REVERSE[org_id] = _org["name"]
        return _org["name"]

    def get_request_headers(self, request):
        headers = {
            "Content-Type": request.META.get("CONTENT_TYPE", "text/html"),
            "X-WEBAUTH-USER": request.user.username,
        }

        org_id = _ORG_CACHE.get(request.org_name)
        if org_id:
            headers["X-Grafana-Org-Id"] = str(org_id)
        return headers

    def get_request_url(self, request):
        """获取后端的grafana url"""
        return grafana_settings.HOST + request.path

    def get_org_name(self, request, *args, **kwargs) -> str:
        """
        获取org_name，取值优先级如下:
        1. GET请求参数中的orgName
        2. 请求头中的x-grafana-org-id
        3. GET请求参数中的org_id
        """
        org_name = request.GET.get("orgName")
        if org_name:
            return org_name

        org_id = request.META.get("HTTP_X_GRAFANA_ORG_ID") or request.GET.get("orgId")
        if not org_id:
            logger.error("get_org_name fail, org_id not exists")
            raise Http404
        elif not str(org_id).isdigit():
            logger.error(f"get_org_name fail, org_id({org_id}) must be digit")
            raise Http404

        org_name = self._get_org_name_by_org_id(int(org_id))
        return org_name

    def _created_proxy_response(self, request):
        url = self.get_request_url(request)
        headers = self.get_request_headers(request)

        query_dict = request.GET.copy()
        query_dict.pop("orgId", None)
        query_dict.pop("orgName", None)

        # 需主动转换 QueryDict 为 dict, 否则对多个值的query只会获取一个值
        params = dict(query_dict)

        try:
            proxy_response = rpool.request(
                request.method,
                url,
                params=params,
                headers=headers,
                data=request.body,
                stream=True,
                hooks={"response": requests_curl_log},
            )
        except Exception as error:
            logger.exception(error)
            raise

        return proxy_response

    def get_django_response(self, proxy_response):
        """"""
        content_type = proxy_response.headers.get("Content-Type", "")

        content = self.update_response(proxy_response, proxy_response.content)

        response = HttpResponse(content, status=proxy_response.status_code, content_type=content_type)
        for header in CACHE_HEADERS:
            value = proxy_response.headers.get(header)
            if value:
                response[header] = value

        return response

    def update_response(self, response, content):
        # 管理员跳过代码注入
        skip_code_injection = self.request.user.is_superuser and "develop" in self.request.GET

        # 注入控制代码
        if "text/html" in response.headers.get("Content-Type", "") and not skip_code_injection:
            content = smart_str(content)
            for tag, code in grafana_settings.CODE_INJECTIONS.items():
                content = content.replace(tag, code)

        return content

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        org_name = self.get_org_name(request, *args, **kwargs)
        request.org_name = org_name

        try:
            self.initial(request, *args, **kwargs)
        except UnauthorizedError:
            _next = request.build_absolute_uri()
            _next_quoted = parse.quote(_next)
            return HttpResponseRedirect(settings.LOGIN_URL + "?c_url=" + _next_quoted)
        except Exception as err:
            logger.exception("initial request error, %s", err)
            raise Http404

        try:
            proxy_response = self._created_proxy_response(request)
        except Exception as err:
            logger.exception("proxy request error, %s", err)
            raise Http404

        response = self.get_django_response(proxy_response)
        return response


class StaticView(ProxyBaseView):
    """静态资源代理, 不做校验和资源注入"""

    authentication_classes = ()
    permission_classes = ()
    provisioning_classes = ()

    def get_org_name(self, request, *args, **kwargs) -> str:
        return ""


class ProxyView(ProxyBaseView):
    """代理访问"""

    authentication_classes = grafana_settings.AUTHENTICATION_CLASSES
    permission_classes = grafana_settings.PERMISSION_CLASSES
    provisioning_classes = ()


class SwitchOrgView(ProxyBaseView):
    """项目/业务切换"""

    authentication_classes = grafana_settings.AUTHENTICATION_CLASSES
    permission_classes = grafana_settings.PERMISSION_CLASSES
    provisioning_classes = grafana_settings.PROVISIONING_CLASSES

    def get_org_name(self, request, *args, **kwargs):
        org_name = request.GET.get("orgName")
        if not org_name:
            logger.error("get_org_name fail, org_name not exists")
            raise Http404
        return org_name

    def get_request_url(self, request):
        return grafana_settings.HOST + grafana_settings.PREFIX
