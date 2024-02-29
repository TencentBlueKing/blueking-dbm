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

from blueapps.account.decorators import login_exempt
from django.conf.urls import include, url
from iam.contrib.django.dispatcher import DjangoBasicResourceApiDispatcher
from rest_framework.routers import DefaultRouter

from backend import env
from backend.iam_app.handlers.permission import Permission
from backend.iam_app.views.cluster_provider import (
    EsClusterResourceProvider,
    HdfsClusterResourceProvider,
    KafkaClusterResourceProvider,
    MongoDBClusterResourceProvider,
    MySQLResourceProvider,
    PulsarClusterResourceProvider,
    RedisClusterResourceProvider,
    TendbClusterResourceProvider,
)
from backend.iam_app.views.dbtype_provider import DBTypeResourceProvider
from backend.iam_app.views.dumper_config_provider import DumperSubscribeConfigResourceProvider
from backend.iam_app.views.duty_rule_provider import DutyRuleResourceProvider
from backend.iam_app.views.flow_provider import FlowResourceProvider
from backend.iam_app.views.instance_provider import InfluxDBInstanceResourceProvider
from backend.iam_app.views.monitor_policy_provider import MonitorPolicyResourceProvider
from backend.iam_app.views.openarea_config_provider import OpenareaConfigResourceProvider
from backend.iam_app.views.views import IAMViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"", IAMViewSet, basename="iam")

dispatcher = DjangoBasicResourceApiDispatcher(Permission.get_iam_client(), env.BK_IAM_SYSTEM_ID)
dispatcher.register(r"flow", FlowResourceProvider())
dispatcher.register(r"mysql", MySQLResourceProvider())
dispatcher.register(r"tendbcluster", TendbClusterResourceProvider())
dispatcher.register(r"redis", RedisClusterResourceProvider())
dispatcher.register(r"influxdb", InfluxDBInstanceResourceProvider())
dispatcher.register(r"es", EsClusterResourceProvider())
dispatcher.register(r"hdfs", HdfsClusterResourceProvider())
dispatcher.register(r"kafka", KafkaClusterResourceProvider())
dispatcher.register(r"pulsar", PulsarClusterResourceProvider())
dispatcher.register(r"dbtype", DBTypeResourceProvider())
dispatcher.register(r"mongodb", MongoDBClusterResourceProvider())
dispatcher.register(r"monitor_policy", MonitorPolicyResourceProvider())
dispatcher.register(r"duty_rule", DutyRuleResourceProvider())
dispatcher.register(r"openarea_config", OpenareaConfigResourceProvider())
dispatcher.register(r"dumper_subscribe_config", DumperSubscribeConfigResourceProvider())

urlpatterns = [url(r"^", include(router.urls)), url(r"^resource/$", dispatcher.as_view([login_exempt]))]
