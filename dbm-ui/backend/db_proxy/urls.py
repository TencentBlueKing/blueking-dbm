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

from rest_framework.routers import DefaultRouter

from backend.db_proxy.views.bkrepo.views import BKRepoProxyPassViewSet
from backend.db_proxy.views.db_meta.views import DBMetaApiProxyPassViewSet
from backend.db_proxy.views.db_remote_service.views import DRSApiProxyPassViewSet
from backend.db_proxy.views.dbconfig.views import DBConfigProxyPassViewSet
from backend.db_proxy.views.dns.views import DnsProxyPassViewSet
from backend.db_proxy.views.hadb.views import HADBProxyPassViewSet
from backend.db_proxy.views.jobapi.views import JobApiProxyPassViewSet
from backend.db_proxy.views.nameservice.views import NameServiceProxyPassViewSet
from backend.db_proxy.views.redis_dts.views import DtsApiProxyPassViewSet
from backend.db_proxy.views.views import JobCallBackViewSet

routers = DefaultRouter(trailing_slash=True)
routers.register(r"", DnsProxyPassViewSet, basename="dns")
routers.register(r"", DBConfigProxyPassViewSet, basename="bkconfig")
routers.register(r"", DBMetaApiProxyPassViewSet, basename="dbmeta")
routers.register(r"", NameServiceProxyPassViewSet, basename="nameservice")
routers.register(r"", DRSApiProxyPassViewSet, basename="drs")
routers.register(r"", HADBProxyPassViewSet, basename="hadb")
routers.register(r"", JobCallBackViewSet, basename="job_callback")
routers.register(r"", BKRepoProxyPassViewSet, basename="bkrepo")
routers.register(r"", DtsApiProxyPassViewSet, basename="redis_dts")
routers.register(r"", JobApiProxyPassViewSet, basename="jobapi")

urlpatterns = routers.urls
