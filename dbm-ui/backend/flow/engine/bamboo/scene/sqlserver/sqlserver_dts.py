"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow


class SqlserverDTSFlow(BaseFlow):
    """
    构建sqlserver数据迁移服务流程的抽象类
    兼容跨云区域的场景支持
    """

    def run_flow(self):
        """
        定义集群数据迁移服务的流程
        流程逻辑：
        """
