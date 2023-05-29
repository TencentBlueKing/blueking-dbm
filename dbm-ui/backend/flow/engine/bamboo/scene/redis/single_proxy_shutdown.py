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
import logging.config
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class SingleProxyShutdownFlow(object):
    """
    孤立redis节点下架流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_slave_instance_ip_ports(bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        ip_ports = defaultdict(list)
        for slave in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE):
            ip_ports[slave.machine.ip].append(slave.port)

        return dict(ip_ports)

    @staticmethod
    def __get_domain(bk_biz_id: int, cluster_id: int) -> str:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        return cluster.immute_domain

    def single_proxy_shutdown_flow(self):
        pass
