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
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_report.report_basemodel import BaseReportABS


class KafkaZookeeperAffinityReport(BaseReportABS):
    """
    Kafka Zookeeper 亲和性巡检报告
    检查 Zookeeper 节点的机房亲和性和机架亲和性
    """

    domain = models.CharField(max_length=255, default="", verbose_name=_("集群域名"))
    app = models.CharField(max_length=100, verbose_name=_("业务名"))
    dba = models.JSONField(verbose_name=_("业务所属dba"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))

    # Zookeeper 节点信息
    zk_node_count = models.IntegerField(default=0, verbose_name=_("Zookeeper节点数量"))

    # 亲和性相关字段
    zk_idc_affinity = models.IntegerField(default=1, verbose_name=_("Zookeeper机房亲和度"))
    zk_rack_affinity = models.IntegerField(default=1, verbose_name=_("Zookeeper机架亲和度"))

    # 检查详情
    zk_idc_distribution = models.JSONField(default=dict, verbose_name=_("Zookeeper机房分布"))
    zk_rack_distribution = models.JSONField(default=dict, verbose_name=_("Zookeeper机架分布"))


class KafkaBrokerAffinityReport(BaseReportABS):
    """
    Kafka Broker 亲和性巡检报告
    检查 Broker 节点的机架亲和性
    """

    domain = models.CharField(max_length=255, default="", verbose_name=_("集群域名"))
    app = models.CharField(max_length=100, verbose_name=_("业务名"))
    dba = models.JSONField(verbose_name=_("业务所属dba"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))

    # Broker 节点信息
    broker_node_count = models.IntegerField(default=0, verbose_name=_("Broker节点数量"))

    # 亲和性相关字段
    broker_rack_affinity = models.IntegerField(default=1, verbose_name=_("Broker机架亲和度"))

    # 检查详情
    broker_rack_distribution = models.JSONField(default=dict, verbose_name=_("Broker机架分布"))
