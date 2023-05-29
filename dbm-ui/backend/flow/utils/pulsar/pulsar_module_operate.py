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
from typing import Union

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.consts import ConfigTypeEnum, NameSpaceEnum, PulsarRoleEnum
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from backend.flow.utils.pulsar.consts import (
    PULSAR_BOOKKEEPER_METRICS_PORT,
    PULSAR_BROKER_METRICS_PORT,
    PULSAR_ZOOKEEPER_METRICS_PORT,
)


class PulsarCCTopoOperator(CCTopoOperator):
    db_type = DBType.Pulsar.value

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance]) -> dict:
        """
        生成自定义标签，即CommonInstanceLabels 不满足的标签
        Pulsar监控端口写入标签
        """
        custom_labels = dict()
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.bk_biz_id),
                "level_name": LevelName.APP,
                "level_value": str(self.bk_biz_id),
                "conf_file": self.clusters[0].major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": NameSpaceEnum.Pulsar,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        if ins.instance_role == InstanceRole.PULSAR_BROKER:
            custom_labels["metrics_port"] = data["content"][PulsarRoleEnum.Broker].get(
                "webServicePort", PULSAR_BROKER_METRICS_PORT
            )
        elif ins.instance_role == InstanceRole.PULSAR_BOOKKEEPER:
            custom_labels["metrics_port"] = data["content"][PulsarRoleEnum.BookKeeper].get(
                "prometheusStatsHttpPort", PULSAR_BOOKKEEPER_METRICS_PORT
            )
        elif ins.instance_role == InstanceRole.PULSAR_ZOOKEEPER:
            custom_labels["metrics_port"] = data["content"][PulsarRoleEnum.ZooKeeper].get(
                "metricsProvider.httpPort", PULSAR_ZOOKEEPER_METRICS_PORT
            )
        return custom_labels
