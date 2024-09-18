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

from iam import IAM as BaseIAM
from iam.api.client import Client as IAMClient
from iam.api.http import http_get, http_post, http_put


class Client(IAMClient):
    """补充一些额外的api请求"""

    # 创建用户组
    def create_user_groups(self, system_id, grade_manager_id, data):
        path = "/api/v2/open/management/systems/{system_id}/grade_managers/{grade_manager_id}/groups/".format(
            system_id=system_id, grade_manager_id=grade_manager_id
        )
        ok, message, data = self._call_iam_api(http_post, path, data)
        return ok, message, data

    # 用户组授权
    def grant_user_group_actions(self, system_id, group_id, data):
        path = "/api/v2/open/management/systems/{system_id}/groups/{group_id}/policies".format(
            system_id=system_id, group_id=group_id
        )
        ok, message, data = self._call_iam_api(http_post, path, data)
        return ok, message, data

    # 添加用户组成员
    def add_user_group_members(self, system_id, group_id, data):
        path = "/api/v2/open/management/systems/{system_id}/groups/{group_id}/members".format(
            system_id=system_id, group_id=group_id
        )
        ok, message, data = self._call_iam_api(http_post, path, data)
        return ok, message, data

    # 查询用户组
    def query_user_groups(self, system_id, grade_manager_id, data):
        path = "/api/v2/open/management/systems/{system_id}/grade_managers/{grade_manager_id}/groups".format(
            system_id=system_id, grade_manager_id=grade_manager_id
        )
        ok, message, data = self._call_iam_api(http_get, path, data)
        return ok, message, data

    # 更新用户组名字和描述
    def update_user_groups(self, system_id, group_id, data):
        path = "/api/v2/open/management/systems/{system_id}/groups/{group_id}/".format(
            system_id=system_id, group_id=group_id
        )
        ok, message, data = self._call_iam_api(http_put, path, data)
        return ok, message, data


class IAM(BaseIAM):
    def __init__(
        self, app_code, app_secret, bk_iam_host=None, bk_paas_host=None, bk_apigateway_url=None, api_version="v2"
    ):
        super().__init__(app_code, app_secret, bk_iam_host, bk_paas_host, bk_apigateway_url, api_version)
        self._client = Client(app_code, app_secret, bk_iam_host, bk_paas_host, bk_apigateway_url)
