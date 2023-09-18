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
from backend.configuration.constants import DBType
from backend.db_meta.enums import MachineType
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator


class EsCCTopoOperator(CCTopoOperator):
    db_type = DBType.Es.value

    def init_instances_service(self, machine_type, instances=None):
        """
        ES 只需要给集群的 一个 datanode 添加一个服务实例，下发一个采集器即可
        否则会导致聚合数据重复
        """
        if machine_type != MachineType.ES_DATANODE.value:
            # 非 datanode，不创建服务实例
            return

        # machine_type==datanode, 只需一个服务实例
        self.init_unique_service(machine_type)
