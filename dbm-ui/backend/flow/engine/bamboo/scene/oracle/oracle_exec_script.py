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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.oracle.oracle_actuator_job import OracleExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.oracle.send_media import OracleExecSendMediaOperationComponent
from backend.flow.utils.oracle.oracle_exec_script_dataclass import ExecuteScriptActKwargs

from .sub_task.cluster_execute_script import cluster_execute_script

logger = logging.getLogger("flow")


class OracleExecuteScriptFlow(object):
    """oracle执行脚本flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.data = data
        self.get_kwargs = ExecuteScriptActKwargs()
        self.get_kwargs.payload = data

    def multi_oracle_execute_script_flow(self):
        """
        oracle 执行脚本流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 获取集群信息
        self.get_kwargs.get_db_info_by_cluster_id()

        # 介质下发
        kwargs = self.get_kwargs.get_send_media_kwargs()
        pipeline.add_act(
            act_name=_("Oracle-介质下发"), act_component_code=OracleExecSendMediaOperationComponent.code, kwargs=kwargs
        )

        # 创建原子任务执行目录
        kwargs = self.get_kwargs.get_create_dir_kwargs()
        pipeline.add_act(
            act_name=_("Oracle-创建原子任务执行目录"), act_component_code=OracleExecuteDBActuatorJobComponent.code, kwargs=kwargs
        )

        # 机器初始化
        kwargs = self.get_kwargs.get_os_init_kwargs()
        pipeline.add_act(
            act_name=_("Oracle-机器初始化"), act_component_code=OracleExecuteDBActuatorJobComponent.code, kwargs=kwargs
        )

        # 分发sql文件
        kwargs = self.get_kwargs.get_send_sql_kwargs()
        pipeline.add_act(
            act_name=_("Oracle-sql文件下发"), act_component_code=OracleExecSendMediaOperationComponent.code, kwargs=kwargs
        )

        # 执行脚本并行
        sub_pipelines = []
        for cluster in self.get_kwargs.db_info:
            sub_pipline = cluster_execute_script(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                info=cluster,
            )
            sub_pipelines.append(sub_pipline)
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
