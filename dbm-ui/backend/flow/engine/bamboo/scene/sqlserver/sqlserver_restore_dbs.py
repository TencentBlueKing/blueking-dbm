"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow


class SqlserverRestoreDBSFlow(BaseFlow):
    """
    构建sqlserver数据定点构造的抽象类
    兼容跨云区域的场景支持
    """

    def run_flow(self):
        """
        定义集群定点构造的流程，支持备份文件恢复和定点恢复
        流程逻辑：
        1: 下发执行器到目标master实例
        2: 下载文件到目标master机器指定目录
        3: 恢复指定全量备份文件
        4：恢复指点增量备份文件 （可选）
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
