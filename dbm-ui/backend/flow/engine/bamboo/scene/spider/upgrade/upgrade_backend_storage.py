"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.spider.upgrade.local_upgrade import TenDBClusterStorageLocalUpgradeFlow
from backend.flow.engine.bamboo.scene.spider.upgrade.migrate_upgrade import TenDBClusterStorageMigrateUpgradeFlow


class UpgradeRemoteFlow(TenDBClusterStorageLocalUpgradeFlow, TenDBClusterStorageMigrateUpgradeFlow):
    """
    TenDBCluster 后端节点主从成对迁移
    """

    def __init__(self, root_id: str, data: dict):
        """
        初始化UpgradeRemoteFlow

        @param root_id: 任务流程定义的root_id
        @param data: 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = data
        self.ticket_data["is_check_process"] = data.get("is_check_process", True)
        self.ticket_data["is_verify_checksum"] = data.get("is_verify_checksum", True)
        # 默认检查延迟
        self.ticket_data["is_check_delay"] = True
        # 为TenDBClusterStorageMigrateUpgradeFlow父类设置必要属性
        self.uid = data.get("uid")
        self.bk_biz_id = data.get("bk_biz_id")
        self.created_by = data.get("created_by")
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def run(self):
        """
        执行tendbcluster存储层本地升级流程
        """
        if self.ticket_data.get("upgrade_local", False):
            self.local_upgrade()
        else:
            self.migrate_upgrade()
