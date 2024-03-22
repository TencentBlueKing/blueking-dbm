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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import AppCache, Cluster
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class TenDBClusterAppendDeployCTLDetailSerializer(TendbBaseOperateDetailSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"))
    use_stream = serializers.BooleanField(help_text=_("是否使用mydumper流式备份迁移"), required=False, default=False)
    drop_before = serializers.BooleanField(help_text=_("导入到tdbctl前,是否先删除"), required=False, default=False)
    threads = serializers.IntegerField(help_text=_("mydumper 并发"), required=False, default=0)
    use_mydumper = serializers.BooleanField(help_text=_("是否使用mydumper,myloader迁移"), required=False, default=True)

    def validate(self, attrs):
        self.__validate_cluster(attrs=attrs)
        return attrs

    def __validate_cluster(self, attrs):
        app_obj = AppCache.objects.get(bk_biz_id=attrs["bk_biz_id"])

        for cluster_obj in Cluster.objects.filter(pk__in=attrs["cluster_ids"]).all():
            if cluster_obj.bk_biz_id != attrs["bk_biz_id"]:
                raise serializers.ValidationError(
                    _("{} 不是 [{}]{} 的集群".format(cluster_obj.immute_domain, app_obj.bk_biz_id, app_obj.db_app_abbr))
                )

            if cluster_obj.cluster_type != ClusterType.TenDBCluster.value:
                raise serializers.ValidationError(
                    _("{} 不是 {} 集群".format(cluster_obj.immute_domain, ClusterType.TenDBCluster.value))
                )

            self.__validate_cluster_spider_master_count(cluster_obj=cluster_obj)
            self.__validate_cluster_remote_count(cluster_obj=cluster_obj)

    @staticmethod
    def __validate_cluster_spider_master_count(cluster_obj: Cluster):
        if (
            cluster_obj.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
            ).count()
            < 2
        ):
            raise serializers.ValidationError(_("{} spider master 数量不足 2 个".format(cluster_obj.immute_domain)))

    @staticmethod
    def __validate_cluster_remote_count(cluster_obj: Cluster):
        if cluster_obj.storageinstance_set.count() < 1:
            raise serializers.ValidationError(_("{} remote 数量异常".format(cluster_obj.immute_domain)))


class TenDBClusterAppendDeployCTLFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.append_deploy_ctl_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_APPEND_DEPLOY_CTL)
class TenDBClusterAppendDeployCTLFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBClusterAppendDeployCTLDetailSerializer
    # serializer = TenDBClusterAppendCTLSerializer  # TenDBClusterAppendDeployCTLDetailSerializer
    inner_flow_builder = TenDBClusterAppendDeployCTLFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 追加部署中控")
    retry_type = FlowRetryType.MANUAL_RETRY
