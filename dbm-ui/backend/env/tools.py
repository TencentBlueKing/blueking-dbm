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


def get_csrf_trusted_origins():
    from . import BK_SAAS_HOST, CSRF_TRUSTED_ORIGINS

    # 优先使用 CSRF_TRUSTED_ORIGINS 配置，否则解析访问地址的二级域名进行信任
    if CSRF_TRUSTED_ORIGINS:
        return CSRF_TRUSTED_ORIGINS
    if BK_SAAS_HOST:
        from urllib.parse import urlparse

        secondary_domain = urlparse(BK_SAAS_HOST).hostname.split(".", 1)[1]
        return [f"https://*.{secondary_domain}", f"http://*.{secondary_domain}"]

    print("Warning: If need, Please provide CSRF_TRUSTED_ORIGINS")
    return []
