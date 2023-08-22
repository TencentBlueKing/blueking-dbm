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

import logging

from backend.configuration.constants import DBType
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator

logger = logging.getLogger("flow")


class RedisCCTopoOperator(CCTopoOperator):
    db_type = DBType.Redis.value

    def init_instances_service(self, machine_type, instances=None):
        """
        Redis  转移实例到对应的集群模块下，并判断是否需要添加服务实例
        """
        if instances:
            first_instance = instances[0]
        if first_instance.cluster.first() is None:
            logger.warning("属于构造场景的临时节点，没有集群归属信息，不需要创建服务实例")
            # 属于构造场景的临时节点，没有集群归属信息，不需要创建服务实例
            return
        # 创建 CMDB 服务实例
        super(RedisCCTopoOperator, self).init_instances_service(machine_type, instances)
