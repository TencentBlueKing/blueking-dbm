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

from backend.ticket.constants import TicketType

SWAGGER_TAG = _("污点池")

# 涉及到部署的单据，机器都有可能成为污点机器
APPLY_TICKET_TYPE = [
    # MySQL
    TicketType.MYSQL_SINGLE_APPLY,
    TicketType.MYSQL_HA_APPLY,
    TicketType.MYSQL_RESTORE_SLAVE,
    TicketType.MYSQL_MIGRATE_CLUSTER,
    TicketType.MYSQL_PROXY_ADD,
    TicketType.MYSQL_PROXY_SWITCH,
    TicketType.MYSQL_ROLLBACK_CLUSTER,
    # Spider
    TicketType.TENDB_CLUSTER_APPLY,
    # Redis
    TicketType.REDIS_SINGLE_APPLY,
    TicketType.REDIS_CLUSTER_APPLY,
    TicketType.REDIS_SCALE_UP,
    TicketType.REDIS_CLUSTER_CUTOFF,
    TicketType.PROXY_SCALE_UP,
    TicketType.REDIS_DATA_STRUCTURE,
    # 大数据
    TicketType.KAFKA_APPLY,
    TicketType.KAFKA_SCALE_UP,
    TicketType.KAFKA_REPLACE,
    TicketType.HDFS_APPLY,
    TicketType.HDFS_SCALE_UP,
    TicketType.HDFS_REPLACE,
    TicketType.ES_APPLY,
    TicketType.ES_SCALE_UP,
    TicketType.ES_REPLACE,
    TicketType.PULSAR_APPLY,
    TicketType.PULSAR_SCALE_UP,
    TicketType.PULSAR_REPLACE,
    TicketType.INFLUXDB_APPLY,
    TicketType.INFLUXDB_REPLACE,
    # RIAK
    TicketType.RIAK_CLUSTER_APPLY,
    TicketType.RIAK_CLUSTER_SCALE_OUT,
]
