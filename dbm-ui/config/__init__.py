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
import os
from pathlib import Path

import environ
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from blueapps.core.celery import celery_app

django_env = environ.Env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
environ.Env.read_env(os.path.join(BASE_DIR, os.getenv("ENV_FILE", "local.env")))

__all__ = ["celery_app", "RUN_VER", "APP_CODE", "SECRET_KEY", "BASE_DIR", "django_env"]

# app 基本信息默认设置，本地开发可以修改这里，预发布环境和正式环境会从环境变量自动获取
RUN_VER = "open"
APP_ID = ""
APP_TOKEN = ""
BK_PAAS_HOST = ""
BK_URL = BK_PAAS_HOST
APP_CODE = APP_ID = django_env("APP_ID", default=APP_ID)
SECRET_KEY = APP_TOKEN = django_env("APP_TOKEN", default=APP_TOKEN)
RUN_VER = django_env("RUN_VER", default=RUN_VER)


def get_env_or_raise(key):
    """Get an environment variable, if it does not exist, raise an exception"""
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            ('Environment variable "{}" not found, you must set this variable to run this application.').format(key)
        )
    return value
