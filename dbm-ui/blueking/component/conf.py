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
"""Django project settings
"""
from blueking.component.constants import BK_API_CONFIG

try:
    from django.conf import settings

    APP_CODE = settings.APP_CODE
    SECRET_KEY = settings.SECRET_KEY
    COMPONENT_SYSTEM_HOST = getattr(settings, 'BK_COMPONENT_API_URL', '')
    DEFAULT_BK_API_VER = getattr(settings, 'DEFAULT_BK_API_VER', 'v2')
    BK_API_COOKIES_PARAMS = getattr(settings, 'BK_API_COOKIES_PARAMS', {})

    RUN_VER = getattr(settings, 'RUN_VER', '')
    ENVIRONMENT = getattr(settings, 'ENVIRONMENT', '')
    RUN_VER_CONFIG = BK_API_CONFIG.get(RUN_VER, {})
    ENVIRONMENT_CONFIG = RUN_VER_CONFIG.get(ENVIRONMENT) or RUN_VER_CONFIG.get('default', {})
    COMPONENT_SYSTEM_HOST = COMPONENT_SYSTEM_HOST or ENVIRONMENT_CONFIG.get('bk_api_host', '')
    BK_API_COOKIES_PARAMS = BK_API_COOKIES_PARAMS or ENVIRONMENT_CONFIG.get('bk_api_cookies_params', {})
except Exception:  # pylint: disable=broad-except
    APP_CODE = ''
    SECRET_KEY = ''
    COMPONENT_SYSTEM_HOST = ''
    DEFAULT_BK_API_VER = 'v2'
    BK_API_COOKIES_PARAMS = {}

CLIENT_ENABLE_SIGNATURE = False
