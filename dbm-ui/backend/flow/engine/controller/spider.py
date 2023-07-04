"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.spider.import_sqlfile_flow import ImportSQLFlow
from backend.flow.engine.bamboo.scene.spider.spider_add_mnt import TenDBClusterAddSpiderMNTFlow
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_checksum import SpiderChecksumFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_db_table_backup import TenDBClusterDBTableBackupFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_deploy import TenDBClusterApplyFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_destroy import TenDBClusterDestroyFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_disable_deploy import SpiderClusterDisableFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_enable_deploy import SpiderClusterEnableFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_flashback import TenDBClusterFlashbackFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_full_backup import TenDBClusterFullBackupFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_truncate_database import SpiderTruncateDatabaseFlow
from backend.flow.engine.bamboo.scene.spider.spider_partition import SpiderPartitionFlow
from backend.flow.engine.bamboo.scene.spider.spider_reduce_nodes import TenDBClusterReduceNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_rename_database_flow import SpiderRenameDatabaseFlow
from backend.flow.engine.bamboo.scene.spider.spider_slave_cluster_deploy import TenDBSlaveClusterApplyFlow
from backend.flow.engine.controller.base import BaseController


class SpiderController(BaseController):
    """
    spider相关调用
    """

    def spider_cluster_apply_scene(self):
        """
        部署tenDB cluster(spider cluster) 部署场景
        """
        flow = TenDBClusterApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_cluster()

    def spider_cluster_destroy_scene(self):
        """
        下架tenDB cluster(spider cluster) 部署场景
        """
        flow = TenDBClusterDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_cluster()

    def add_spider_mnt_scene(self):
        flow = TenDBClusterAddSpiderMNTFlow(root_id=self.root_id, data=self.ticket_data)
        flow.add_spider_mnt()

    def spider_checksum(self):
        """
        mysql 数据校验
        """
        flow = SpiderChecksumFlow(root_id=self.root_id, data=self.ticket_data)
        flow.spider_checksum_flow()

    def spider_partition(self):
        """
        mysql 表分区
        """
        flow = SpiderPartitionFlow(root_id=self.root_id, data=self.ticket_data)
        flow.spider_partition_flow()

    def spider_cluster_disable_scene(self):
        """
        禁用spider集群场景
        """
        flow = SpiderClusterDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_spider_cluster_flow()

    def spider_cluster_enable_scene(self):
        """
        启用spider集群场景
        """
        flow = SpiderClusterEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_spider_cluster_flow()

    def spider_slave_cluster_apply_scene(self):
        """
        调用tenDB slave cluster(spider slave cluster) 部署场景
        """
        flow = TenDBSlaveClusterApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_slave_cluster()

    def rename_database(self):
        flow = SpiderRenameDatabaseFlow(
            root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBCluster.value
        )
        flow.rename_database()

    def spider_semantic_check_scene(self):
        """
        spider语义测试场景
        """
        flow = ImportSQLFlow(root_id=self.root_id, data=self.ticket_data)
        flow.sql_semantic_check_flow()

    def spider_sql_import_scene(self):
        flow = ImportSQLFlow(root_id=self.root_id, data=self.ticket_data)
        flow.import_sqlfile_flow()

    def truncate_database(self):
        flow = SpiderTruncateDatabaseFlow(
            root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBCluster.value
        )
        flow.truncate_database()

    def database_table_backup(self):
        flow = TenDBClusterDBTableBackupFlow(root_id=self.root_id, data=self.ticket_data)
        flow.backup_flow()

    def add_spider_nodes_scene(self):
        """
        扩容接入层的场景
        """
        flow = TenDBClusterAddNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.add_spider_nodes()

    def full_backup(self):
        flow = TenDBClusterFullBackupFlow(root_id=self.root_id, data=self.ticket_data)
        flow.full_backup_flow()

    def reduce_spider_nodes_scene(self):
        """
        缩容接入层的场景
        """
        flow = TenDBClusterReduceNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reduce_spider_nodes()

    def flashback(self):
        flow = TenDBClusterFlashbackFlow(
            root_id=self.root_id, data=self.ticket_data, cluster_type=ClusterType.TenDBCluster.value
        )
        flow.flashback()
