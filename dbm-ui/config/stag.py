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
from .default import *  # pylint: disable=wildcard-import

DEBUG = True

LOGGING = get_logging_config(os.path.join(BK_LOG_DIR, APP_CODE), "INFO")


# allow all hosts
CORS_ORIGIN_ALLOW_ALL = True

# cookies will be allowed to be included in cross-site HTTP requests
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = (
    "referer",
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-requested-with",
    "x-csrftoken",
    "HTTP_X_REQUESTED_WITH",
)

MIDDLEWARE += (
    "corsheaders.middleware.CorsMiddleware",
    "backend.bk_web.middleware.DisableCSRFCheckMiddleware",
    "pyinstrument.middleware.ProfilerMiddleware",
)
