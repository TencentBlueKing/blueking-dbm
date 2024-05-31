"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.conf.urls import url

from backend.flow.views.append_deploy_ctl import AppendDeployCTLView
from backend.flow.views.client_set_dns_server import ClientSetDnsServerSceneApiView
from backend.flow.views.cloud_dbha_apply import CloudDBHAApplySceneApiView
from backend.flow.views.cloud_dns_bind_apply import CloudDNSApplySceneApiView
from backend.flow.views.cloud_drs_apply import CloudDRSApplySceneApiView
from backend.flow.views.cloud_nginx_apply import CloudNginxApplySceneApiView, CloudNginxReplaceSceneApiView
from backend.flow.views.cloud_redis_dts_server_apply import (
    CloudRedisDTSServerApplySceneApiView,
    CloudRedisDTSServerReduceSceneApiView,
)
from backend.flow.views.doris_apply import InstallDorisSceneApiView
from backend.flow.views.doris_destroy import DestroyDorisSceneApiView
from backend.flow.views.doris_disable import DisableDorisSceneApiView
from backend.flow.views.doris_enable import EnableDorisSceneApiView
from backend.flow.views.doris_reboot import RebootDorisSceneApiView
from backend.flow.views.doris_scale_up import ScaleUpDorisSceneApiView
from backend.flow.views.es_apply import InstallEsSceneApiView
from backend.flow.views.es_destroy import DestroyEsSceneApiView
from backend.flow.views.es_disable import DisableEsSceneApiView
from backend.flow.views.es_enable import EnableEsSceneApiView
from backend.flow.views.es_reboot import RebootEsSceneApiView
from backend.flow.views.es_replace import ReplaceEsSceneApiView
from backend.flow.views.es_scale_up import ScaleUpEsSceneApiView
from backend.flow.views.es_shrink import ShrinkEsSceneApiView
from backend.flow.views.hdfs_apply import InstallHdfsSceneApiView
from backend.flow.views.hdfs_destroy import DestroyHdfsSceneApiView
from backend.flow.views.hdfs_disable import DisableHdfsSceneApiView
from backend.flow.views.hdfs_enable import EnableHdfsSceneApiView
from backend.flow.views.hdfs_reboot import RebootHdfsSceneApiView
from backend.flow.views.hdfs_replace import ReplaceHdfsSceneApiView
from backend.flow.views.hdfs_scale_up import ScaleUpHdfsSceneApiView
from backend.flow.views.hdfs_shrink import ShrinkHdfsSceneApiView
from backend.flow.views.import_resource_init import ImportResourceInitStepApiView
from backend.flow.views.import_sqlfile import ImportSQLFileSceneApiView
from backend.flow.views.influxdb_apply import InstallInfluxdbSceneApiView
from backend.flow.views.influxdb_destroy import DestroyInfluxdbSceneApiView
from backend.flow.views.influxdb_disable import DisableInfluxdbSceneApiView
from backend.flow.views.influxdb_enable import EnableInfluxdbSceneApiView
from backend.flow.views.influxdb_reboot import RebootInfluxdbSceneApiView
from backend.flow.views.influxdb_replace import ReplaceInfluxdbSceneApiView
from backend.flow.views.kafka_apply import InstallKafkaSceneApiView
from backend.flow.views.kafka_destroy import DestroyKafkaSceneApiView
from backend.flow.views.kafka_disable import DisableKafkaSceneApiView
from backend.flow.views.kafka_enable import EnableKafkaSceneApiView
from backend.flow.views.kafka_reboot import RebootKafkaSceneApiView
from backend.flow.views.kafka_replace import ReplaceKafkaSceneApiView
from backend.flow.views.kafka_scale_up import ScaleUpKafkaSceneApiView
from backend.flow.views.kafka_shrink import ShrinkKafkaSceneApiView
from backend.flow.views.migrate_views.es_fake_apply import FakeInstallEsSceneApiView
from backend.flow.views.migrate_views.hdfs_fake_apply import FakeInstallHdfsSceneApiView
from backend.flow.views.migrate_views.influxdb_fake_apply import FakeInstallInfluxdbSceneApiView
from backend.flow.views.migrate_views.kafka_fake_apply import FakeInstallKafkaSceneApiView
from backend.flow.views.migrate_views.pulsar_fake_apply import FakeInstallPulsarSceneApiView
from backend.flow.views.migrate_views.redis_migrate import (
    RedisClusterMigrateCompair,
    RedisClusterMigrateLoad,
    RedisClusterMigratePrecheck,
)
from backend.flow.views.migrate_views.riak_migrate import RiakClusterMigrateApiView
from backend.flow.views.mongodb_scene import (
    ClusterInstallApiView,
    MongoBackupApiView,
    MongoDBCreateUserView,
    MongoDBDeInstallView,
    MongoDBDeleteUserView,
    MongoDBDisableClusterView,
    MongoDBEnableClusterView,
    MongoDBExecScriptView,
    MongoDBIncreaseMongoSView,
    MongoDBIncreaseNodeView,
    MongoDBInstanceRestartView,
    MongoDBReduceMongoSView,
    MongoDBReduceNodeView,
    MongoDBReplaceView,
    MongoDBScaleView,
    MongoFakeInstallApiView,
    MultiReplicasetInstallApiView,
)
from backend.flow.views.mysql_add_slave import AddMysqlSlaveSceneApiView
from backend.flow.views.mysql_add_slave_remote import AddMysqlSlaveRemoteSceneApiView
from backend.flow.views.mysql_checksum import MysqlChecksumSceneApiView
from backend.flow.views.mysql_edit_config import MysqlEditConfigSceneApiView
from backend.flow.views.mysql_flashback import MysqlFlashbackSceneApiView
from backend.flow.views.mysql_ha_apply import InstallMySQLHASceneApiView
from backend.flow.views.mysql_ha_db_table_backup import MySQLHADBTableBackup
from backend.flow.views.mysql_ha_destroy import (
    DestroyMySQLHASceneApiView,
    DisableMySQLHASceneApiView,
    EnableMySQLHASceneApiView,
)
from backend.flow.views.mysql_ha_full_backup import MySQLHAFullBackup
from backend.flow.views.mysql_ha_master_fail_over import MySQLHAMasterFailOverApiView
from backend.flow.views.mysql_ha_rename_database import MySQLHARenameDatabaseView
from backend.flow.views.mysql_ha_switch import MySQLHASwitchSceneApiView
from backend.flow.views.mysql_ha_truncate_data import MySQLHATruncateDataView
from backend.flow.views.mysql_migrate_cluster import MigrateMysqlClusterSceneApiView
from backend.flow.views.mysql_migrate_cluster_remote import MysqlMigrateRemoteSceneApiView
from backend.flow.views.mysql_open_area import MysqlOpenAreaSceneApiView
from backend.flow.views.mysql_partition import MysqlPartitionSceneApiView
from backend.flow.views.mysql_proxy_add import AddMySQLProxySceneApiView
from backend.flow.views.mysql_proxy_switch import SwitchMySQLProxySceneApiView
from backend.flow.views.mysql_proxy_upgrade import UpgradeMySQLProxySceneApiView
from backend.flow.views.mysql_pt_table_sync import MySQLPtTableSyncApiView
from backend.flow.views.mysql_restore_local_remote import RestoreMysqlLocalRemoteSceneApiView
from backend.flow.views.mysql_restore_local_slave import RestoreMysqlLocalSlaveSceneApiView
from backend.flow.views.mysql_restore_slave import RestoreMysqlSlaveSceneApiView
from backend.flow.views.mysql_restore_slave_remote import RestoreMysqlSlaveRemoteSceneApiView
from backend.flow.views.mysql_rollback_data import MysqlRollbackDataSceneApiView
from backend.flow.views.mysql_single_apply import InstallMySQLSingleSceneApiView
from backend.flow.views.mysql_single_destroy import (
    DestroyMySQLSingleSceneApiView,
    DisableMySQLSingleSceneApiView,
    EnableMySQLSingleSceneApiView,
)
from backend.flow.views.mysql_single_rename_database import MySQLSingleRenameDatabaseView
from backend.flow.views.mysql_single_truncate_data import MySQLSingleTruncateDataView
from backend.flow.views.mysql_upgrade import UpgradeMySQLSceneApiView
from backend.flow.views.name_service import (
    ClbCreateSceneApiView,
    ClbDeleteSceneApiView,
    DomainBindClbIpSceneApiView,
    DomainUnBindClbIpSceneApiView,
    PolarisCreateSceneApiView,
    PolarisDeleteSceneApiView,
)
from backend.flow.views.pulsar_apply import InstallPulsarSceneApiView
from backend.flow.views.pulsar_destroy import DestroyPulsarSceneApiView
from backend.flow.views.pulsar_disable import DisablePulsarSceneApiView
from backend.flow.views.pulsar_enable import EnablePulsarSceneApiView
from backend.flow.views.pulsar_reboot import RebootPulsarSceneApiView
from backend.flow.views.pulsar_replace import ReplacePulsarSceneApiView
from backend.flow.views.pulsar_scale_up import ScaleUpPulsarSceneApiView
from backend.flow.views.redis_cluster import (
    InstallPredixyClusterSceneApiView,
    InstallRedisInstanceSceneApiView,
    InstallTwemproxyClusterSceneApiView,
    RedisAddDtsServerSceneApiView,
    RedisBackendScaleSceneApiView,
    RedisClusterAddSlaveApiView,
    RedisClusterBackupSceneApiView,
    RedisClusterDataCheckRepairApiView,
    RedisClusterDataCopySceneApiView,
    RedisClusterOpenCloseSceneApiView,
    RedisClusterProxysUpgradeApiView,
    RedisClusterShardNumUpdateSceneApiView,
    RedisClusterShutdownSceneApiView,
    RedisClusterTypeUpdateSceneApiView,
    RedisClusterVersionUpdateOnlineApiView,
    RedisDataStructureSceneApiView,
    RedisDataStructureTaskDeleteSceneApiView,
    RedisFlushDataSceneApiView,
    RedisInsShutdownSceneApiView,
    RedisProxyScaleSceneApiView,
    RedisRemoveDtsServerSceneApiView,
    RedisSlotsMigrateForContractionSceneApiView,
    RedisSlotsMigrateForExpansionSceneApiView,
    RedisSlotsMigrateForHotkeySceneApiView,
    SingleProxyShutdownSceneApiView,
)
from backend.flow.views.redis_keys import RedisKeysDeleteSceneApiView, RedisKeysExtractSceneApiView
from backend.flow.views.redis_scene import (
    RedisClusterCompleteReplaceSceneApiView,
    RedisClusterMSSwitchSceneApiView,
    RedisClusterReinstallDbmonSceneApiView,
    RedisInstallDbmonSceneApiView,
)
from backend.flow.views.riak_apply import RiakApplySceneApiView
from backend.flow.views.riak_destroy import RiakClusterDestroyApiView
from backend.flow.views.riak_disable import RiakClusterDisableApiView
from backend.flow.views.riak_enable import RiakClusterEnableApiView
from backend.flow.views.riak_reboot import RiakRebootApiView
from backend.flow.views.riak_scale_in import RiakClusterScaleInApiView
from backend.flow.views.riak_scale_out import RiakClusterScaleOutApiView
from backend.flow.views.spider_add_mnt import AddSpiderMNTSceneApiView
from backend.flow.views.spider_add_nodes import AddSpiderNodesSceneApiView
from backend.flow.views.spider_checksum import SpiderChecksumSceneApiView
from backend.flow.views.spider_cluster_apply import InstallSpiderClusterSceneApiView
from backend.flow.views.spider_cluster_database_table_backup import TenDBClusterDatabaseTableBackupView
from backend.flow.views.spider_cluster_destroy import (
    DestroySpiderClusterSceneApiView,
    DisableSpiderSceneApiView,
    EnableSpiderSceneApiView,
)
from backend.flow.views.spider_cluster_flashback import TenDBClusterFlashbackView
from backend.flow.views.spider_cluster_full_backup import TenDBClusterFullBackupView
from backend.flow.views.spider_cluster_rename_database import TenDBClusterRenameDatabaseView
from backend.flow.views.spider_cluster_truncate_database import TenDBClusterTruncateDatabaseView
from backend.flow.views.spider_partition import SpiderPartitionSceneApiView
from backend.flow.views.spider_reduce_mnt import ReduceSpiderMNTSceneApiView
from backend.flow.views.spider_reduce_nodes import ReduceSpiderNodesSceneApiView
from backend.flow.views.spider_semantic_check import SpiderSemanticCheckSceneApiView
from backend.flow.views.spider_slave_apply import InstallSpiderSlaveClusterSceneApiView
from backend.flow.views.spider_slave_destroy import DestroySpiderSlaveClusterSceneApiView
from backend.flow.views.spider_sql_import import SpiderSqlImportSceneApiView
from backend.flow.views.sql_semantic_check import SqlSemanticCheckSceneApiView
from backend.flow.views.sqlserver import (
    SqlserverAddSlaveSceneApiView,
    SqlserverBackupDBSSceneApiView,
    SqlserverCleanDBSSceneApiView,
    SqlserverDataConstructSceneApiView,
    SqlserverDBBuildSyncSceneApiView,
    SqlserverDestroySceneApiView,
    SqlserverDisableSceneApiView,
    SqlserverEnableSceneApiView,
    SqlserverFullDtsSceneApiView,
    SqlserverHAApplySceneApiView,
    SqlserverHAFailOverSceneApiView,
    SqlserverHASwitchSceneApiView,
    SqlserverIncrDtsSceneApiView,
    SqlserverRebuildInLocalSceneApiView,
    SqlserverRebuildInNewSlaveSceneApiView,
    SqlserverRenameDBSSceneApiView,
    SqlserverResetSceneApiView,
    SqlserverSingleApplySceneApiView,
    SqlserverSQLFileExecuteSceneApiView,
)
from backend.flow.views.tbinlogdumper_add import (
    DisableTBinlogDumperSceneApiView,
    EnableTBinlogDumperSceneApiView,
    InstallTBinlogDumperSceneApiView,
)
from backend.flow.views.tbinlogdumper_reduce import ReduceTBinlogDumperSceneApiView
from backend.flow.views.tbinlogdumper_switch import SwitchTBinlogDumperSceneApiView
from backend.flow.views.tendb_cluster_remote_fail_over import RemoteFailOverSceneApiView
from backend.flow.views.tendb_cluster_remote_local_recover import RemoteLocalRecoverSceneApiView
from backend.flow.views.tendb_cluster_remote_migrate import RemoteMigrateSceneApiView
from backend.flow.views.tendb_cluster_remote_rebalance import RemoteRebalanceSceneApiView
from backend.flow.views.tendb_cluster_remote_slave_recover import RemoteSlaveRecoverSceneApiView
from backend.flow.views.tendb_cluster_remote_switch import RemoteSwitchSceneApiView
from backend.flow.views.tendb_cluster_rollback_data import TendbClusterRollbackDataSceneApiView
from backend.flow.views.tendb_ha_standardize import TenDBHAStandardizeView

urlpatterns = [
    #  redis api url begin
    url(r"^scene/install_redis_cache_cluster_apply$", InstallTwemproxyClusterSceneApiView.as_view()),
    url(r"^scene/install_redis_ssd_cluster_apply$", InstallTwemproxyClusterSceneApiView.as_view()),
    url(r"^scene/install_tendisplus_cluster_apply$", InstallPredixyClusterSceneApiView.as_view()),
    url(r"^scene/install_redis_cluster_apply$", InstallPredixyClusterSceneApiView.as_view()),
    url(r"^scene/install_redis_instance_apply$", InstallRedisInstanceSceneApiView.as_view()),
    url(r"^scene/redis_keys_extract$", RedisKeysExtractSceneApiView.as_view()),
    url(r"^scene/redis_keys_delete$", RedisKeysDeleteSceneApiView.as_view()),
    url(r"^scene/redis_backup$", RedisClusterBackupSceneApiView.as_view()),
    url(r"^scene/redis_open_close$", RedisClusterOpenCloseSceneApiView.as_view()),
    url(r"^scene/redis_shutdown$", RedisClusterShutdownSceneApiView.as_view()),
    url(r"^scene/redis_flush_data$", RedisFlushDataSceneApiView.as_view()),
    url(r"^scene/redis_proxy_scale$", RedisProxyScaleSceneApiView.as_view()),
    url(r"^scene/redis_backend_scale$", RedisBackendScaleSceneApiView.as_view()),
    url(r"^scene/redis_ins_shutdown$", RedisInsShutdownSceneApiView.as_view()),
    url(r"^scene/single_proxy_shutdown$", SingleProxyShutdownSceneApiView.as_view()),
    url(r"^scene/cutoff/redis_cluster$", RedisClusterCompleteReplaceSceneApiView.as_view()),
    url(r"^scene/switch/redis_cluster$", RedisClusterMSSwitchSceneApiView.as_view()),
    url(r"^scene/install/dbmon$", RedisInstallDbmonSceneApiView.as_view()),
    url(r"^scene/redis_clusters_reinstall_dbmon$", RedisClusterReinstallDbmonSceneApiView.as_view()),
    url(r"^scene/redis_cluster_data_copy$", RedisClusterDataCopySceneApiView.as_view()),
    url(r"^scene/redis_cluster_shard_num_update$", RedisClusterShardNumUpdateSceneApiView.as_view()),
    url(r"^scene/redis_cluster_type_update$", RedisClusterTypeUpdateSceneApiView.as_view()),
    url(r"^scene/redis_cluster_data_check_repair$", RedisClusterDataCheckRepairApiView.as_view()),
    url(r"^scene/redis_add_dts_server$", RedisAddDtsServerSceneApiView.as_view()),
    url(r"^scene/redis_remove_dts_server$", RedisRemoveDtsServerSceneApiView.as_view()),
    url(r"^scene/redis_data_structure$", RedisDataStructureSceneApiView.as_view()),
    url(r"^scene/redis_data_structure_task_delete$", RedisDataStructureTaskDeleteSceneApiView.as_view()),
    url(r"^scene/redis_cluster_add_slave$", RedisClusterAddSlaveApiView.as_view()),
    url(r"^scene/redis_migrate_precheck$", RedisClusterMigratePrecheck.as_view()),
    url(r"^scene/redis_migrate_load$", RedisClusterMigrateLoad.as_view()),
    url(r"^scene/redis_migrate_compair$", RedisClusterMigrateCompair.as_view()),
    url(r"^scene/redis_cluster_version_update_online$", RedisClusterVersionUpdateOnlineApiView.as_view()),
    url(r"^scene/redis_cluster_proxys_upgrade$", RedisClusterProxysUpgradeApiView.as_view()),
    url(r"^scene/redis_slots_migrate_for_expansion$", RedisSlotsMigrateForExpansionSceneApiView.as_view()),
    url(r"^scene/redis_slots_migrate_for_contraction$", RedisSlotsMigrateForContractionSceneApiView.as_view()),
    url(r"^scene/redis_slots_migrate_for_hotkey$", RedisSlotsMigrateForHotkeySceneApiView.as_view()),
    # redis api url end
    # dns api
    url(r"^scene/client_set_dns_server$", ClientSetDnsServerSceneApiView.as_view()),
    # name_service start
    # name_service clb
    url(r"^scene/nameservice_clb_create$", ClbCreateSceneApiView.as_view()),
    url(r"^scene/nameservice_clb_delete$", ClbDeleteSceneApiView.as_view()),
    url(r"^scene/nameservice_domain_bind_clb_ip$", DomainBindClbIpSceneApiView.as_view()),
    url(r"^scene/nameservice_domain_unbind_clb_ip$", DomainUnBindClbIpSceneApiView.as_view()),
    # name_service polaris
    url(r"^scene/nameservice_polaris_create$", PolarisCreateSceneApiView.as_view()),
    url(r"^scene/nameservice_polaris_delete$", PolarisDeleteSceneApiView.as_view()),
    # name_service end
    # mongodb start
    url(r"^scene/multi_replicaset_create$", MultiReplicasetInstallApiView.as_view()),
    url(r"^scene/cluster_create$", ClusterInstallApiView.as_view()),
    url(r"^scene/mongo_backup$", MongoBackupApiView.as_view()),
    url(r"^scene/install_rs_fake$", MongoFakeInstallApiView.as_view()),
    url(r"^scene/multi_cluster_create_user$", MongoDBCreateUserView.as_view()),
    url(r"^scene/multi_cluster_delete_user$", MongoDBDeleteUserView.as_view()),
    url(r"^scene/multi_cluster_exec_script$", MongoDBExecScriptView.as_view()),
    url(r"^scene/multi_instance_restart$", MongoDBInstanceRestartView.as_view()),
    url(r"^scene/multi_hosts_replace$", MongoDBReplaceView.as_view()),
    url(r"^scene/multi_cluster_increase_mongos$", MongoDBIncreaseMongoSView.as_view()),
    url(r"^scene/multi_cluster_reduce_mongos$", MongoDBReduceMongoSView.as_view()),
    url(r"^scene/cluster_deinstall$", MongoDBDeInstallView.as_view()),
    url(r"^scene/cluster_scale$", MongoDBScaleView.as_view()),
    url(r"^scene/multi_cluster_increase_node$", MongoDBIncreaseNodeView.as_view()),
    url(r"^scene/multi_cluster_reduce_node$", MongoDBReduceNodeView.as_view()),
    url(r"^scene/multi_cluster_enable$", MongoDBEnableClusterView.as_view()),
    url(r"^scene/multi_cluster_disable$", MongoDBDisableClusterView.as_view()),
    # mongodb end
    # mysql upgrade
    url(r"^scene/upgrade_mysql_proxy$", UpgradeMySQLProxySceneApiView.as_view()),
    url(r"^scene/upgrade_mysql$", UpgradeMySQLSceneApiView.as_view()),
    # mysql
    url(r"^scene/install_mysql_apply$", InstallMySQLSingleSceneApiView.as_view()),
    url(r"^scene/install_mysql_ha_apply$", InstallMySQLHASceneApiView.as_view()),
    url(r"^scene/destroy_mysql_ha$", DestroyMySQLHASceneApiView.as_view()),
    url(r"^scene/destroy_mysql_single$", DestroyMySQLSingleSceneApiView.as_view()),
    url(r"^scene/disable_mysql_single$", DisableMySQLSingleSceneApiView.as_view()),
    url(r"^scene/enable_mysql_single$", EnableMySQLSingleSceneApiView.as_view()),
    # url(r'^scene/reduce_mysql_proxy$', ReduceMySQLProxySceneApiView.as_view()),
    url(r"^scene/mysql_checksum$", MysqlChecksumSceneApiView.as_view()),
    url(r"^scene/mysql_partition$", MysqlPartitionSceneApiView.as_view()),
    url(r"^scene/spider_partition$", SpiderPartitionSceneApiView.as_view()),
    url(r"^scene/tendbha_truncate_data$", MySQLHATruncateDataView.as_view()),
    url(r"^scene/import_sqlfile$", ImportSQLFileSceneApiView.as_view()),
    url(r"^scene/switch_mysql_proxy$", SwitchMySQLProxySceneApiView.as_view()),
    url(r"^scene/add_mysql_proxy$", AddMySQLProxySceneApiView.as_view()),
    url(r"^scene/install_influxdb$", InstallInfluxdbSceneApiView.as_view()),
    url(r"^scene/enable_influxdb$", EnableInfluxdbSceneApiView.as_view()),
    url(r"^scene/disable_influxdb$", DisableInfluxdbSceneApiView.as_view()),
    url(r"^scene/destroy_influxdb$", DestroyInfluxdbSceneApiView.as_view()),
    url(r"^scene/reboot_influxdb$", RebootInfluxdbSceneApiView.as_view()),
    url(r"^scene/replace_influxdb$", ReplaceInfluxdbSceneApiView.as_view()),
    url(r"^scene/fake_install_influxdb$", FakeInstallInfluxdbSceneApiView.as_view()),
    url(r"^scene/install_kafka$", InstallKafkaSceneApiView.as_view()),
    url(r"^scene/fake_install_kafka$", FakeInstallKafkaSceneApiView.as_view()),
    url(r"^scene/scale_up_kafka$", ScaleUpKafkaSceneApiView.as_view()),
    url(r"^scene/enable_kafka$", EnableKafkaSceneApiView.as_view()),
    url(r"^scene/disable_kafka$", DisableKafkaSceneApiView.as_view()),
    url(r"^scene/destroy_kafka$", DestroyKafkaSceneApiView.as_view()),
    url(r"^scene/shrink_kafka$", ShrinkKafkaSceneApiView.as_view()),
    url(r"^scene/replace_kafka$", ReplaceKafkaSceneApiView.as_view()),
    url(r"^scene/reboot_kafka$", RebootKafkaSceneApiView.as_view()),
    url(r"^scene/install_es$", InstallEsSceneApiView.as_view()),
    url(r"^scene/fake_install_es$", FakeInstallEsSceneApiView.as_view()),
    url(r"^scene/scale_up_es$", ScaleUpEsSceneApiView.as_view()),
    url(r"^scene/shrink_es$", ShrinkEsSceneApiView.as_view()),
    url(r"^scene/enable_es$", EnableEsSceneApiView.as_view()),
    url(r"^scene/disable_es$", DisableEsSceneApiView.as_view()),
    url(r"^scene/destroy_es$", DestroyEsSceneApiView.as_view()),
    url(r"^scene/reboot_es$", RebootEsSceneApiView.as_view()),
    url(r"^scene/replace_es$", ReplaceEsSceneApiView.as_view()),
    url(r"^scene/redis_keys_delete$", RedisKeysDeleteSceneApiView.as_view()),
    url(r"^scene/sql_semantic_check$", SqlSemanticCheckSceneApiView.as_view()),
    url(r"^scene/tendbha_rename_database", MySQLHARenameDatabaseView.as_view()),
    url(r"^scene/redis_backup$", RedisClusterBackupSceneApiView.as_view()),
    url(r"^scene/tendbha_db_table_backup", MySQLHADBTableBackup.as_view()),
    url(r"^scene/install_hdfs$", InstallHdfsSceneApiView.as_view()),
    url(r"^scene/tendbha_truncate_data$", MySQLHATruncateDataView),
    url(r"^scene/import_sqlfile$", ImportSQLFileSceneApiView.as_view()),
    url(r"^scene/switch_mysql_proxy$", SwitchMySQLProxySceneApiView.as_view()),
    url(r"^scene/add_mysql_proxy$", AddMySQLProxySceneApiView.as_view()),
    url(r"^scene/restore_slave$", RestoreMysqlSlaveSceneApiView.as_view()),
    url(r"^scene/add_slave$", AddMysqlSlaveSceneApiView.as_view()),
    url(r"^scene/restore_local_slave$", RestoreMysqlLocalSlaveSceneApiView.as_view()),
    # 从节点数据恢复(接入备份系统)
    url(r"^scene/restore_slave_remote$", RestoreMysqlSlaveRemoteSceneApiView.as_view()),
    url(r"^scene/add_slave_remote$", AddMysqlSlaveRemoteSceneApiView.as_view()),
    url(r"^scene/restore_local_slave_remote$", RestoreMysqlLocalRemoteSceneApiView.as_view()),
    url(r"^scene/migrate_cluster_remote$", MysqlMigrateRemoteSceneApiView.as_view()),
    url(r"^scene/migrate_cluster$", MigrateMysqlClusterSceneApiView.as_view()),
    url(r"^scene/mysql_rollback_data", MysqlRollbackDataSceneApiView.as_view()),
    url(r"^scene/install_es$", InstallEsSceneApiView.as_view()),
    url(r"^scene/redis_keys_delete$", RedisKeysDeleteSceneApiView.as_view()),
    url(r"^scene/disable_mysql_ha$", DisableMySQLHASceneApiView.as_view()),
    url(r"^scene/enable_mysql_ha$", EnableMySQLHASceneApiView.as_view()),
    url(r"^scene/scale_up_hdfs$", ScaleUpHdfsSceneApiView.as_view()),
    url(r"^scene/enable_hdfs$", EnableHdfsSceneApiView.as_view()),
    url(r"^scene/disable_hdfs$", DisableHdfsSceneApiView.as_view()),
    url(r"^scene/destroy_hdfs$", DestroyHdfsSceneApiView.as_view()),
    url(r"^scene/shrink_hdfs$", ShrinkHdfsSceneApiView.as_view()),
    url(r"^scene/reboot_hdfs$", RebootHdfsSceneApiView.as_view()),
    url(r"^scene/replace_hdfs$", ReplaceHdfsSceneApiView.as_view()),
    url(r"^scene/fake_install_hdfs$", FakeInstallHdfsSceneApiView.as_view()),
    url(r"^scene/switch_mysql_ha$", MySQLHASwitchSceneApiView.as_view()),
    url(r"^scene/master_ha_master_fail_over$", MySQLHAMasterFailOverApiView.as_view()),
    url(r"^scene/master_pt_table_sync$", MySQLPtTableSyncApiView.as_view()),
    url(r"^scene/mysql_flashback", MysqlFlashbackSceneApiView.as_view()),
    url(r"scene/tendbha_full_backup", MySQLHAFullBackup.as_view()),
    url(r"^scene/mysql_edit_config", MysqlEditConfigSceneApiView.as_view()),
    url(r"^scene/dns_apply$", CloudDNSApplySceneApiView.as_view()),
    url(r"^scene/dbha_apply$", CloudDBHAApplySceneApiView.as_view()),
    url(r"^scene/nginx_apply$", CloudNginxApplySceneApiView.as_view()),
    url(r"^scene/nginx_replace$", CloudNginxReplaceSceneApiView.as_view()),
    url(r"^scene/drs_apply$", CloudDRSApplySceneApiView.as_view()),
    url(r"^scene/redis_dts_server_apply$", CloudRedisDTSServerApplySceneApiView.as_view()),
    url(r"^scene/redis_dts_server_reduce$", CloudRedisDTSServerReduceSceneApiView.as_view()),
    url(r"^scene/install_pulsar$", InstallPulsarSceneApiView.as_view()),
    url(r"^scene/scale_up_pulsar$", ScaleUpPulsarSceneApiView.as_view()),
    url(r"^scene/enable_pulsar$", EnablePulsarSceneApiView.as_view()),
    url(r"^scene/disable_pulsar$", DisablePulsarSceneApiView.as_view()),
    url(r"^scene/destroy_pulsar$", DestroyPulsarSceneApiView.as_view()),
    url(r"^scene/reboot_pulsar$", RebootPulsarSceneApiView.as_view()),
    url(r"^scene/replace_pulsar$", ReplacePulsarSceneApiView.as_view()),
    url(r"^scene/fake_install_pulsar$", FakeInstallPulsarSceneApiView.as_view()),
    url(r"^scene/import_resource_init$", ImportResourceInitStepApiView.as_view()),
    # spider
    url(r"^scene/add_spider_mnt$", AddSpiderMNTSceneApiView.as_view()),
    url(r"^scene/install_tendb_cluster$", InstallSpiderClusterSceneApiView.as_view()),
    url(r"^scene/destroy_tendb_cluster$", DestroySpiderClusterSceneApiView.as_view()),
    url(r"^scene/spider_checksum$", SpiderChecksumSceneApiView.as_view()),
    url(r"^scene/disable_spider_cluster$", DisableSpiderSceneApiView.as_view()),
    url(r"^scene/enable_spider_cluster$", EnableSpiderSceneApiView.as_view()),
    url(r"^scene/install_tendb_slave_cluster$", InstallSpiderSlaveClusterSceneApiView.as_view()),
    url(r"^scene/spider_semantic_check$", SpiderSemanticCheckSceneApiView.as_view()),
    url(r"^scene/spider_sql_import$", SpiderSqlImportSceneApiView.as_view()),
    # tendbsingle 清档
    url(r"^scene/tendbsingle_truncate_data$", MySQLSingleTruncateDataView.as_view()),
    # tendbsingle db重命名
    url(r"^scene/tendbsingle_rename_database$", MySQLSingleRenameDatabaseView.as_view()),
    # tendbcluster db重命名
    url(r"^scene/tendbcluster_rename_database$", TenDBClusterRenameDatabaseView.as_view()),
    # tendbcluster 清档
    url(r"^scene/tendbcluster_truncate_data$", TenDBClusterTruncateDatabaseView.as_view()),
    # tendbcluster 库表备份
    url(r"^scene/tendbcluster_database_table_backup$", TenDBClusterDatabaseTableBackupView.as_view()),
    # spider 添加
    url(r"^scene/add_spider_nodes$", AddSpiderNodesSceneApiView.as_view()),
    url(r"^scene/tendbcluster_full_backup$", TenDBClusterFullBackupView.as_view()),
    # spider 减少
    url(r"^scene/reduce_spider_nodes$", ReduceSpiderNodesSceneApiView.as_view()),
    # riak
    url(r"^scene/riak_cluster_apply$", RiakApplySceneApiView.as_view()),
    url(r"^scene/tendbcluster_flashback$", TenDBClusterFlashbackView.as_view()),
    url(r"^scene/riak_cluster_scale_out$", RiakClusterScaleOutApiView.as_view()),
    url(r"^scene/riak_cluster_scale_in$", RiakClusterScaleInApiView.as_view()),
    url(r"^scene/riak_cluster_destroy$", RiakClusterDestroyApiView.as_view()),
    url(r"^scene/riak_cluster_enable$", RiakClusterEnableApiView.as_view()),
    url(r"^scene/riak_cluster_disable$", RiakClusterDisableApiView.as_view()),
    url(r"^scene/riak_reboot$", RiakRebootApiView.as_view()),
    url(r"^scene/riak_cluster_migrate$", RiakClusterMigrateApiView.as_view()),
    # tendbcluster 切换类
    url(r"^scene/tendb_cluster_remote_switch$", RemoteSwitchSceneApiView.as_view()),
    url(r"^scene/tendb_cluster_remote_fail_over$", RemoteFailOverSceneApiView.as_view()),
    # remote 节点扩缩容
    url(r"^scene/tendb_cluster_remote_rebalance$", RemoteRebalanceSceneApiView.as_view()),
    url(r"^scene/tendb_cluster_remote_migrate$", RemoteMigrateSceneApiView.as_view()),
    url(r"^scene/tendb_cluster_rollback_data$", TendbClusterRollbackDataSceneApiView.as_view()),
    url("^scene/destroy_tendb_slave_cluster$", DestroySpiderSlaveClusterSceneApiView.as_view()),
    url("^scene/reduce_spider_mnt$", ReduceSpiderMNTSceneApiView.as_view()),
    url(r"^scene/tendb_cluster_remote_slave_recover$", RemoteSlaveRecoverSceneApiView.as_view()),
    url(r"^scene/tendb_cluster_remote_local_recover$", RemoteLocalRecoverSceneApiView.as_view()),
    # tbinlogdumper
    url("^scene/install_tbinlogumper$", InstallTBinlogDumperSceneApiView.as_view()),
    url("^scene/reduce_tbinlogumper$", ReduceTBinlogDumperSceneApiView.as_view()),
    url("^scene/switch_tbinlogumper$", SwitchTBinlogDumperSceneApiView.as_view()),
    url("^scene/enable_tbinlogumper$", EnableTBinlogDumperSceneApiView.as_view()),
    url("^scene/disable_tbinlogumper$", DisableTBinlogDumperSceneApiView.as_view()),
    url("^scene/tendbha_standardize$", TenDBHAStandardizeView.as_view()),
    url("^scene/mysql_open_area$", MysqlOpenAreaSceneApiView.as_view()),
    # migrate
    url("^scene/append_deploy_ctl$", AppendDeployCTLView.as_view()),
    # sqlserver
    url("^scene/sqlserver_single_apply$", SqlserverSingleApplySceneApiView.as_view()),
    url("^scene/sqlserver_ha_apply$", SqlserverHAApplySceneApiView.as_view()),
    url("^scene/sqlserver_sql_file_execute$", SqlserverSQLFileExecuteSceneApiView.as_view()),
    url("^scene/sqlserver_backup_dbs$", SqlserverBackupDBSSceneApiView.as_view()),
    url("^scene/sqlserver_rename_dbs$", SqlserverRenameDBSSceneApiView.as_view()),
    url("^scene/sqlserver_clean_dbs$", SqlserverCleanDBSSceneApiView.as_view()),
    url("^scene/sqlserver_ha_switch$", SqlserverHASwitchSceneApiView.as_view()),
    url("^scene/sqlserver_ha_fail_over$", SqlserverHAFailOverSceneApiView.as_view()),
    url("^scene/sqlserver_build_db_sync$", SqlserverDBBuildSyncSceneApiView.as_view()),
    url("^scene/sqlserver_cluster_disable$", SqlserverDisableSceneApiView.as_view()),
    url("^scene/sqlserver_cluster_enable$", SqlserverEnableSceneApiView.as_view()),
    url("^scene/sqlserver_cluster_reset$", SqlserverResetSceneApiView.as_view()),
    url("^scene/sqlserver_cluster_destroy$", SqlserverDestroySceneApiView.as_view()),
    url("^scene/sqlserver_add_slave$", SqlserverAddSlaveSceneApiView.as_view()),
    url("^scene/sqlserver_rebuild_in_local$", SqlserverRebuildInLocalSceneApiView.as_view()),
    url("^scene/sqlserver_rebuild_in_new_slave$", SqlserverRebuildInNewSlaveSceneApiView.as_view()),
    url("^scene/sqlserver_full_dts$", SqlserverFullDtsSceneApiView.as_view()),
    url("^scene/sqlserver_incr_dts$", SqlserverIncrDtsSceneApiView.as_view()),
    url("^scene/sqlserver_data_construct$", SqlserverDataConstructSceneApiView.as_view()),
    # doris
    url(r"^scene/install_doris$", InstallDorisSceneApiView.as_view()),
    url(r"^scene/scale_up_doris$", ScaleUpDorisSceneApiView.as_view()),
    url(r"^scene/enable_doris$", EnableDorisSceneApiView.as_view()),
    url(r"^scene/disable_doris$", DisableDorisSceneApiView.as_view()),
    url(r"^scene/destroy_doris$", DestroyDorisSceneApiView.as_view()),
    url(r"^scene/reboot_doris$", RebootDorisSceneApiView.as_view()),
]
