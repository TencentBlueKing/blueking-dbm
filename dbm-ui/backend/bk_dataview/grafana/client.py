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
import requests
from django.utils.crypto import get_random_string

from .provisioning import Datasource
from .settings import grafana_settings
from .utils import requests_curl_log

rpool = requests.Session()

API_HOST = (grafana_settings.HOST + grafana_settings.PREFIX).rstrip("/")


def get_user_by_login_or_email(username: str):
    url = f"{API_HOST}/api/users/lookup?loginOrEmail={username}"
    resp = rpool.get(url, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def create_user(username: str):
    url = f"{API_HOST}/api/admin/users/"
    # 使用proxy_auth验证, 密码随机
    password = get_random_string(12)
    data = {"name": username, "email": "", "login": username, "password": password}
    resp = rpool.post(url, json=data, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def get_organization_by_name(name: str):
    url = f"{API_HOST}/api/orgs/name/{name}"
    resp = rpool.get(url, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def get_organization_by_id(org_id: int):
    url = f"{API_HOST}/api/orgs/{org_id}"
    resp = rpool.get(url, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def create_organization(name: str):
    url = f"{API_HOST}/api/orgs/"
    data = {"name": name}
    resp = rpool.post(url, json=data, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def update_organization(name: str, org_id: int):
    url = f"{API_HOST}/api/orgs/{org_id}"
    data = {"name": name}
    resp = rpool.put(url, json=data, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def get_org_users(org_id: int):
    url = f"{API_HOST}/api/orgs/{org_id}/users"
    resp = rpool.get(url, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def add_user_to_org(org_id: int, username: str, role: str = "Viewer"):
    url = f"{API_HOST}/api/orgs/{org_id}/users"
    data = {"loginOrEmail": username, "role": role}
    resp = rpool.post(url, json=data, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def update_user_in_org(org_id: int, user_id: int, role: str = "Viewer"):
    """
    更新组织中的用户
    """
    url = f"{API_HOST}/api/orgs/{org_id}/users/{user_id}"
    data = {"role": role}
    resp = rpool.patch(url, json=data, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def get_datasource(org_id: int, name):
    """查询数据源"""
    url = f"{API_HOST}/api/datasources/name/{name}"
    headers = {"X-Grafana-Org-Id": str(org_id)}
    resp = rpool.get(url, headers=headers, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def get_datasource_id(org_id: int, name):
    """查询数据源"""
    url = f"{API_HOST}/api/datasources/id/{name}"
    headers = {"X-Grafana-Org-Id": str(org_id)}
    resp = rpool.get(url, headers=headers, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log})
    return resp


def create_datasource(org_id: int, ds: Datasource):
    """创建数据源"""
    url = f"{API_HOST}/api/datasources"
    headers = {"X-Grafana-Org-Id": str(org_id)}
    resp = rpool.post(
        url, json=ds.__dict__, headers=headers, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log}
    )
    return resp


def update_datasource(org_id: int, datsource_id: int, ds: Datasource):
    url = f"{API_HOST}/api/datasources/{datsource_id}"
    headers = {"X-Grafana-Org-Id": str(org_id)}
    resp = rpool.put(
        url, json=ds.__dict__, headers=headers, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log}
    )
    return resp


def update_dashboard(org_id: int, folder_id, dashboard):
    url = f"{API_HOST}/api/dashboards/db"
    data = {
        "dashboard": dashboard,
        "message": "provisioning dashboard",
        "overwrite": True,
        "folder_id": folder_id,
    }
    headers = {"X-Grafana-Org-Id": str(org_id)}
    resp = rpool.post(
        url, json=data, headers=headers, auth=grafana_settings.ADMIN, hooks={"response": requests_curl_log}
    )
    return resp


def create_folder():
    pass
