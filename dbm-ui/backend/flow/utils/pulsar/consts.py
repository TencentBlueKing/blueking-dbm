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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

PULSAR_KEY_PATH_LIST_ZOOKEEPER = ["/data/pulsarenv/zookeeper/my-secret.key"]
PULSAR_KEY_PATH_LIST_BROKER = ["/data/pulsarenv/broker/my-secret.key"]
PULSAR_AUTH_CONF_TARGET_PATH = "/data/pulsarenv/broker/"


class PulsarConfigEnum(str, StructuredEnum):
    NumPartitions = EnumField("broker.defaultNumPartitions", _("broker默认分区数"))
    ClientAuthenticationParameters = EnumField("broker.brokerClientAuthenticationParameters", _("broker认证配置"))
    EnsembleSize = EnumField("broker.managedLedgerDefaultEnsembleSize", _("默认bookie池大小"))
    WriteQuorum = EnumField("broker.managedLedgerDefaultWriteQuorum", _("写入副本数"))
    AckQuorum = EnumField("broker.managedLedgerDefaultAckQuorum", _("确认写入副本数"))
    RetentionTime = EnumField("broker.defaultRetentionTimeInMinutes", _("数据保留时间，单位为分钟"))
    Port = EnumField("port", _("broker服务端口"))
    ManagerUserName = EnumField("username", _("访问Pulsar Manager账户名"))
    ManagerPassword = EnumField("password", _("访问Pulsar Manager密码"))


PULSAR_ZOOKEEPER_SERVICE_PORT = 2181
PULSAR_BOOKKEEPER_SERVICE_PORT = 3181
PULSAR_ZOOKEEPER_METRICS_PORT = 6000
PULSAR_BOOKKEEPER_METRICS_PORT = 8000
PULSAR_BROKER_METRICS_PORT = 7000
PULSAR_MANAGER_WEB_PORT = 7750

PULSAR_ROLE_ALL = "all"
