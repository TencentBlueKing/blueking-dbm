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
from backend.flow.engine.bamboo.scene.common.disk_benchmark_flow import BaselineDiskBenchmarkFlow
from backend.flow.engine.controller.base import BaseController


class DbmAiAgentController(BaseController):
    """
    dbm_aiagent 模块的场景流程控制器
    """

    def disk_benchmark_flow(self):
        """
        BaselineDisk 性能基线采集流程
        多机并发 + 每机内多盘串行, 机器层走 SOPs 空闲检查, actuator 层走 DB 进程黑名单检查
        """
        flow = BaselineDiskBenchmarkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run_flow()
