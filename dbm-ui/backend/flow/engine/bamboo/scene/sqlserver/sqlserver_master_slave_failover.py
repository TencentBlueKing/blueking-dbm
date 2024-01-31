"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_master_slave_switch import SqlserverSwitchFlow


class SqlserverFailOverFlow(SqlserverSwitchFlow):
    """
    构建Sqlserver执行数据库强制切换的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        # 开启强制模式
        self.data["force"] = True
        super().run_flow()
