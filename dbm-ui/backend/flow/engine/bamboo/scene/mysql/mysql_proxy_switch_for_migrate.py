"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.flow.engine.bamboo.scene.mysql.mysql_proxy_switch_for_extend import ProxySwitchForExtendFlow


class ProxySwitchForMigrateFlow(ProxySwitchForExtendFlow):
    """
    构建mysql集群整体proxy实例拆分的流程类
    因为proxy实例拆分和proxy扩缩容的入参结构体、流程行为是一致的，所有这里完全复用proxy扩缩容流程
    """

    def switch_proxy_for_migrate_flow(self):
        """
        定义迁移proxy流程, 复用扩缩容proxy流程
        """
        self.switch_mysql_cluster_proxy_flow()
