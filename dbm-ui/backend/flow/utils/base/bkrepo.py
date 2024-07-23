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
from django.conf import settings

from backend.db_proxy.models import DBCloudProxy
from backend.db_services.ipchooser.constants import DEFAULT_CLOUD


def get_bk_repo_url(bk_cloud_id: int) -> str:
    """
    根据云区域ID获取蓝鲸制品库地址
    :param bk_cloud_id: 云区域ID
    :return: 蓝鲸仓库地址
    """
    if bk_cloud_id == DEFAULT_CLOUD:
        return settings.BKREPO_ENDPOINT_URL
    else:
        nginx_ip = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last().internal_address
        return f"http://{nginx_ip}/apis/proxypass"
