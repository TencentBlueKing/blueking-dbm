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
from itertools import chain

from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.components import BKMonitorV3Api
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.exceptions import SubscriptionMetricException
from backend.db_monitor.serializers import (
    DeleteMonitorSubscribeSerializer,
    ListMonitorSubscribeSerializer,
    SaveMonitorSubscribeSerializer,
)
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, ResourceActionPermission, get_request_key_id

SWAGGER_TAG = _("监控订阅")


def inst_getter(request, view):
    domains = [c["cluster_domain"] for c in get_request_key_id(request, "clusters")]
    cluster_ids = list(Cluster.objects.filter(immute_domain__in=domains).values_list("id", flat=True))
    return cluster_ids


class MonitorSubscribeViewSet(SystemViewSet):
    """告警订阅视图集"""

    default_permission_class = [DBManagePermission()]
    action_permission_map = {
        (
            "list_subscribe",
            "get_subscribe_metrics",
            "delete_subscribe",
        ): [],
        ("save_subscribe",): [
            ResourceActionPermission([ActionEnum.REDIS_SUBSCRIBE_MONITOR], ResourceEnum.REDIS, inst_getter)
        ],
    }

    @common_swagger_auto_schema(
        operation_summary=_("保存告警订阅"),
        request_body=SaveMonitorSubscribeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=SaveMonitorSubscribeSerializer)
    def save_subscribe(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        username = request.user.username
        bk_biz_id = env.DBA_APP_BK_BIZ_ID

        # 获取用户已有的告警订阅
        subscribes = BKMonitorV3Api.list_full_subscribe(bk_biz_id, username)

        # 暂定用户告警订阅不超过500条
        if len(subscribes) + len(data["clusters"]) > 500:
            raise SubscriptionMetricException(_("用户告警订阅不允许超过500条"))

        # 获得该类型对外提供的指标信息
        metric_config = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_SUBSCRIBE_METRIC, default={})
        subscriptions = []

        # 查询集群信息
        cluster_domains = [cluster["cluster_domain"] for cluster in data["clusters"]]
        clusters = Cluster.objects.filter(immute_domain__in=cluster_domains).values("id", "immute_domain", "bk_biz_id")
        cluster_biz_map = {c["immute_domain"]: c["bk_biz_id"] for c in clusters}

        # 获取集群与订阅的关系
        cluster_subscribe_map = {}
        for sub in subscribes:
            conditions_map = {c["field"]: c["value"] for c in sub["conditions"]}
            cluster_subscribe_map[conditions_map["tags.cluster_domain"][0]] = sub

        for subscribe_cluster in data["clusters"]:
            cluster_type, domain = subscribe_cluster["cluster_type"], subscribe_cluster["cluster_domain"]

            metric_list = [m["id"] for m in metric_config.get(cluster_type, [])]
            metric_list = list(chain.from_iterable(x if isinstance(x, list) else [x] for x in metric_list))
            if not metric_list:
                raise SubscriptionMetricException(_("该集群类型[{}]没有配置订阅指标").format(cluster_type))

            # 保存/更新告警组
            sub_id = cluster_subscribe_map.get(domain, {}).get("id")
            # 业务、集群域名，每个集群一条告警订阅
            params = {
                "sub_username": username,
                "conditions": [
                    {"field": "tags.cluster_domain", "value": [domain], "method": "eq", "condition": "and"},
                    {"field": "tags.appid", "value": [cluster_biz_map[domain]], "method": "eq", "condition": "and"},
                    {"field": "alert.severity", "value": data["alert_level"], "method": "eq", "condition": "and"},
                    {"field": "alert.metric", "value": metric_list, "method": "include", "condition": "and"},
                ],
                "notice_ways": data["notice_ways"],
                "is_enable": True,
                # 固定为follower，表示为关注人
                "user_type": "follower",
                "bk_biz_id": bk_biz_id,
            }
            # 如果已有订阅，则更新
            if sub_id:
                params.update(id=sub_id)
            subscriptions.append(params)

        resp = BKMonitorV3Api.bulk_save_subscribe(params={"bk_biz_id": bk_biz_id, "subscriptions": subscriptions})
        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("告警订阅列表"),
        query_serializer=ListMonitorSubscribeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], serializer_class=ListMonitorSubscribeSerializer)
    def list_subscribe(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        data.update(sub_username=request.user.username, bk_biz_id=env.DBA_APP_BK_BIZ_ID)

        # 获取用户全量的告警订阅
        subscribe_data = BKMonitorV3Api.list_full_subscribe(env.DBA_APP_BK_BIZ_ID, request.user.username)

        # 获取订阅的集群信息
        domains = []
        for info in subscribe_data:
            field_map = {c["field"]: c["value"] for c in info["conditions"]}
            domains.extend(field_map["tags.cluster_domain"])

        clusters = Cluster.objects.filter(immute_domain__in=domains).values(
            "id", "name", "immute_domain", "cluster_type"
        )
        cluster_map = {c["immute_domain"]: c for c in clusters}

        # 补充订阅策略的集群、业务、告警级别信息
        subscribe_exist_infos = []
        for info in subscribe_data:
            field_map = {c["field"]: c["value"] for c in info["conditions"]}
            cluster = cluster_map.get(field_map["tags.cluster_domain"][0], {})
            # 忽略不存在的集群订阅信息
            if not cluster:
                continue
            info.update(
                bk_biz_id=field_map["tags.appid"][0],
                master_domain=field_map["tags.cluster_domain"][0],
                cluster_name=cluster["name"],
                cluster_id=cluster["id"],
                cluster_type=cluster["cluster_type"],
                db_type=ClusterType.cluster_type_to_db_type(cluster["cluster_type"]),
                alert_severity=field_map["alert.severity"],
            )
            subscribe_exist_infos.append(info)

        # 格式化分页参数
        data = {"count": len(subscribe_exist_infos), "results": subscribe_exist_infos}
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("告警订阅删除"),
        request_body=DeleteMonitorSubscribeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=DeleteMonitorSubscribeSerializer)
    def delete_subscribe(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        resp = BKMonitorV3Api.bulk_delete_subscribe({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "ids": data["ids"]})
        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("获取告警订阅指标"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_subscribe_metrics(self, request, *args, **kwargs):
        metric_config = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_SUBSCRIBE_METRIC, default={})
        return Response(metric_config)
