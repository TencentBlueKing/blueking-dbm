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
from django.urls import include
from django.urls import re_path as url
from iam.contrib.django.dispatcher import DjangoBasicResourceApiDispatcher
from rest_framework.routers import DefaultRouter

from backend import env
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.permission import Permission
from backend.iam_app.views.account_provider import (
    MongoDBAccountResourceProvider,
    MySQLAccountResourceProvider,
    SQLServerAccountResourceProvider,
    TendbClusterAccountResourceProvider,
)
from backend.iam_app.views.biz_dbtype_provider import BizDBTypeResourceProvider
from backend.iam_app.views.biz_provider import BusinessResourceProvider
from backend.iam_app.views.cluster_provider import (
    DorisClusterResourceProvider,
    EsClusterResourceProvider,
    HdfsClusterResourceProvider,
    K8sGreptimedbClusterResourceProvider,
    K8sMilvusClusterResourceProvider,
    K8sQdrantClusterResourceProvider,
    K8sRisingwaveClusterResourceProvider,
    K8sSurrealClusterResourceProvider,
    K8sVictoriametricsClusterResourceProvider,
    KafkaClusterResourceProvider,
    MongoDBClusterResourceProvider,
    MySQLResourceProvider,
    PulsarClusterResourceProvider,
    RedisClusterResourceProvider,
    SQLServerClusterResourceProvider,
    TendbClusterResourceProvider,
)
from backend.iam_app.views.dbtype_provider import DBTypeResourceProvider
from backend.iam_app.views.dumper_config_provider import DumperSubscribeConfigResourceProvider
from backend.iam_app.views.flow_provider import FlowResourceProvider
from backend.iam_app.views.monitor_policy_provider import MonitorPolicyResourceProvider
from backend.iam_app.views.notify_group_provider import NotifyGroupResourceProvider
from backend.iam_app.views.openarea_config_provider import OpenareaConfigResourceProvider
from backend.iam_app.views.ticket_provider import TicketResourceProvider
from backend.iam_app.views.v4.dispatcher import IAMV4ResourceApiDispatcher
from backend.iam_app.views.views import IAMViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"", IAMViewSet, basename="iam")

resource_providers = {
    r"flow": FlowResourceProvider(),
    r"ticket": TicketResourceProvider(),
    r"dbtype": DBTypeResourceProvider(),
    r"openarea_config": OpenareaConfigResourceProvider(),
    r"dumper_subscribe_config": DumperSubscribeConfigResourceProvider(),
    r"mysql": MySQLResourceProvider(),
    r"tendbcluster": TendbClusterResourceProvider(),
    r"redis": RedisClusterResourceProvider(),
    # TODO: 暂时屏蔽对influxdb的鉴权
    # r"influxdb": InfluxDBInstanceResourceProvider(),
    r"es": EsClusterResourceProvider(),
    r"hdfs": HdfsClusterResourceProvider(),
    r"kafka": KafkaClusterResourceProvider(),
    r"pulsar": PulsarClusterResourceProvider(),
    r"doris": DorisClusterResourceProvider(),
    r"mongodb": MongoDBClusterResourceProvider(),
    r"sqlserver": SQLServerClusterResourceProvider(),
    r"mysql_account": MySQLAccountResourceProvider(),
    r"tendbcluster_account": TendbClusterAccountResourceProvider(),
    r"sqlserver_account": SQLServerAccountResourceProvider(),
    r"mongodb_account": MongoDBAccountResourceProvider(),
    r"monitor_policy": MonitorPolicyResourceProvider(),
    r"notify_group": NotifyGroupResourceProvider(),
    r"k8s_surrealdb": K8sSurrealClusterResourceProvider(),
    r"k8s_victoriametrics": K8sVictoriametricsClusterResourceProvider(),
    r"k8s_risingwave": K8sRisingwaveClusterResourceProvider(),
    r"k8s_milvus": K8sMilvusClusterResourceProvider(),
    r"k8s_qdrant": K8sQdrantClusterResourceProvider(),
    r"k8s_greptimedb": K8sGreptimedbClusterResourceProvider(),
}

dispatcher = DjangoBasicResourceApiDispatcher(Permission.get_iam_client(), env.BK_IAM_SYSTEM_ID)
v4_dispatcher = IAMV4ResourceApiDispatcher(env.BK_IAM_SYSTEM_ID)
for resource_type, resource_provider in resource_providers.items():
    dispatcher.register(resource_type, resource_provider)
    # 未同步到V4的资源不会被IAM回调
    if not ResourceEnum.get_resource_by_id(resource_type).iamv4_disable:
        v4_dispatcher.register(resource_type, resource_provider)

# 业务在V3是cmdb的跨系统资源，只有V4才需要dbm自己提供回调
v4_dispatcher.register(r"biz", BusinessResourceProvider())
# 业务DB类型是V4专有的合成资源，用于表达「业务 + DB类型」的双维度管控
v4_dispatcher.register(r"biz_dbtype", BizDBTypeResourceProvider())


urlpatterns = [
    url(r"^", include(router.urls)),
    url(r"^resource/$", dispatcher.as_view([login_exempt])),
    url(r"^v4/resource/$", v4_dispatcher.as_view([login_exempt])),
]
