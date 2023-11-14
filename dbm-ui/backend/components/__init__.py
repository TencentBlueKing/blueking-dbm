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

from django.apps import AppConfig

from .bklog.client import BKLogApi
from .bkmonitorv3.client import BKMonitorV3Api
from .cc.client import CCApi
from .cmsi.client import CmsiApi
from .db_name_service.client import NameServiceApi
from .db_remote_service.client import DRSApi
from .dbconfig.client import DBConfigApi
from .dns.client import DnsApi
from .itsm.client import ItsmApi
from .job.client import JobApi
from .mysql_priv_manager.client import MySQLPrivManagerApi
from .usermanage.client import UserManagerApi

"""
API 统一调用模块，使用方式，举例
>>> from backend.api import CCApi
>>> CCApi.search_business({})
"""


__all__ = [
    "CCApi",
    "JobApi",
    "ItsmApi",
    "UserManagerApi",
    "CmsiApi",
    "BKLogApi",
    "DBConfigApi",
    "DnsApi",
    "MySQLPrivManagerApi",
    "DRSApi",
    "BKMonitorV3Api",
    "NameServiceApi",
]


class ApiConfig(AppConfig):
    name = "backend.api"
    verbose_name = "ESB_API"

    def ready(self):
        pass


default_app_config = "backend.api.ApiConfig"
