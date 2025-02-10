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
from backend.flow.engine.bamboo.scene.spider.append_deploy_ctl_flow import AppendDeployCTLFlow
from backend.flow.engine.bamboo.scene.spider.db_table_backup import TenDBClusterDBTableBackupFlow
from backend.flow.engine.bamboo.scene.spider.full_backup import TenDBClusterFullBackupFlow
from backend.flow.engine.bamboo.scene.spider.import_sqlfile_flow import ImportSQLFlow
from backend.flow.engine.bamboo.scene.spider.remote_local_slave_recover import TenDBRemoteSlaveLocalRecoverFlow
from backend.flow.engine.bamboo.scene.spider.remote_master_fail_over import RemoteMasterFailOverFlow
from backend.flow.engine.bamboo.scene.spider.remote_master_slave_migrate import TendbClusterMigrateRemoteFlow
from backend.flow.engine.bamboo.scene.spider.remote_master_slave_swtich import RemoteMasterSlaveSwitchFlow
from backend.flow.engine.bamboo.scene.spider.remote_slave_recover import TenDBRemoteSlaveRecoverFlow
from backend.flow.engine.bamboo.scene.spider.spider_add_mnt import TenDBClusterAddSpiderMNTFlow
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_checksum import SpiderChecksumFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_deploy import TenDBClusterApplyFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_destroy import TenDBClusterDestroyFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_disable_deploy import SpiderClusterDisableFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_enable_deploy import SpiderClusterEnableFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_flashback import TenDBClusterFlashbackFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_metadata_import_flow import SpiderClusterMetadataImportFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_rollback_flow import TenDBRollBackDataFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_standardize_flow import SpiderClusterStandardizeFlow
from backend.flow.engine.bamboo.scene.spider.spider_cluster_truncate_database import SpiderTruncateDatabaseFlow
from backend.flow.engine.bamboo.scene.spider.spider_partition import SpiderPartitionFlow
from backend.flow.engine.bamboo.scene.spider.spider_partition_cron import SpiderPartitionCronFlow
from backend.flow.engine.bamboo.scene.spider.spider_reduce_mnt import TenDBClusterReduceMNTFlow
from backend.flow.engine.bamboo.scene.spider.spider_reduce_nodes import TenDBClusterReduceNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_remotedb_rebalance_flow import TenDBRemoteRebalanceFlow
from backend.flow.engine.bamboo.scene.spider.spider_rename_database_flow import SpiderRenameDatabaseFlow
from backend.flow.engine.bamboo.scene.spider.spider_slave_cluster_deploy import TenDBSlaveClusterApplyFlow
from backend.flow.engine.bamboo.scene.spider.spider_slave_cluster_destroy import TenDBSlaveClusterDestroyFlow
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

    def spider_cluster_apply_no_slave(self):
        """
        部署tenDB cluster(spider cluster) 部署场景，没有remote slave 单节点中控节点
        """
        flow = TenDBClusterApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_cluster_no_slave()

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
        spider 表分区
        """
        flow = SpiderPartitionFlow(root_id=self.root_id, data=self.ticket_data)
        flow.spider_partition_flow()

    def spider_partition_cron(self):
        """
        spider 表分区定时任务
        """
        flow = SpiderPartitionCronFlow(root_id=self.root_id, data=self.ticket_data)
        flow.spider_partition_cron_flow()

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

    def tendb_cluster_remote_switch_scene(self):
        """
        remote端互切的场景
        """
        flow = RemoteMasterSlaveSwitchFlow(root_id=self.root_id, data=self.ticket_data)
        flow.remote_switch()

    def tendbcluster_remote_fail_over_scene(self):
        """
        remote端主故障切换的场景
        """
        flow = RemoteMasterFailOverFlow(root_id=self.root_id, data=self.ticket_data)
        flow.remote_fail_over()

    def tendb_cluster_remote_rebalance(self):
        """
        remote 节点扩缩容同步数据(重均衡)
        """
        flow = TenDBRemoteRebalanceFlow(root_id=self.root_id, ticket_data=self.ticket_data)
        flow.tendb_migrate()

    def tendb_cluster_remote_migrate(self):
        """
        remote 节点主从成对迁移
        """
        flow = TendbClusterMigrateRemoteFlow(root_id=self.root_id, ticket_data=self.ticket_data)
        flow.migrate_master_slave_flow()

    def tendb_cluster_remote_slave_recover(self):
        """
        remote 远程slave节点恢复
        """
        flow = TenDBRemoteSlaveRecoverFlow(root_id=self.root_id, ticket_data=self.ticket_data)
        flow.tendb_remote_slave_recover()

    def tendb_cluster_remote_local_recover(self):
        """
        remote 本地恢复
        """
        flow = TenDBRemoteSlaveLocalRecoverFlow(root_id=self.root_id, ticket_data=self.ticket_data)
        flow.tendb_remote_slave_local_recover()

    def tendb_cluster_rollback_data(self):
        """
        tendb cluster 定点回档
        """
        flow = TenDBRollBackDataFlow(root_id=self.root_id, ticket_data=self.ticket_data)
        flow.tendb_rollback_data()

    def destroy_tendb_slave_cluster(self):
        """
        tendb cluster 只读接入层下架
        """
        flow = TenDBSlaveClusterDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_slave_cluster()

    def reduce_spider_mnt_scene(self):
        """
        tendb cluster 运维节点下架
        """
        flow = TenDBClusterReduceMNTFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reduce_spider_mnt()

    def append_deploy_ctl_scene(self):
        """
        转移spider cluster 从Gcs到dbm 系统需要的操作
        """
        flow = AppendDeployCTLFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run()

    def tendbcluster_standardize_scene(self):
        flow = SpiderClusterStandardizeFlow(root_id=self.root_id, data=self.ticket_data)
        flow.standardize()

    def metadata_import_scene(self):
        flow = SpiderClusterMetadataImportFlow(root_id=self.root_id, data=self.ticket_data)
        flow.import_meta()
