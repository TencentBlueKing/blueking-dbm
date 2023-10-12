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

# allow all hosts
CORS_ORIGIN_ALLOW_ALL = True

# cookies will be allowed to be included in cross-site HTTP requests
CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "backend.bk_web.middleware.DisableCSRFCheckMiddleware",
) + MIDDLEWARE

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_NAME", "bk-dbm.sqlite3"),
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "django.request": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "django.server": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
