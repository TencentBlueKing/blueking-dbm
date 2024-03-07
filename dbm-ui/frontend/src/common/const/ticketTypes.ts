/**
 * 服务单据类型(与后端字段对应)
 */
export enum TicketTypes {
  MYSQL_SINGLE_APPLY = 'MYSQL_SINGLE_APPLY',
  MYSQL_HA_APPLY = 'MYSQL_HA_APPLY',
  MYSQL_EXCEL_AUTHORIZE_RULES = 'MYSQL_EXCEL_AUTHORIZE_RULES',
  MYSQL_AUTHORIZE_RULES = 'MYSQL_AUTHORIZE_RULES',
  MYSQL_HA_DISABLE = 'MYSQL_HA_DISABLE',
  MYSQL_HA_ENABLE = 'MYSQL_HA_ENABLE',
  MYSQL_HA_DESTROY = 'MYSQL_HA_DESTROY',
  MYSQL_SINGLE_DISABLE = 'MYSQL_SINGLE_DISABLE',
  MYSQL_SINGLE_ENABLE = 'MYSQL_SINGLE_ENABLE',
  MYSQL_SINGLE_DESTROY = 'MYSQL_SINGLE_DESTROY',
  MYSQL_INSTANCE_CLONE_RULES = 'MYSQL_INSTANCE_CLONE_RULES',
  MYSQL_CLIENT_CLONE_RULES = 'MYSQL_CLIENT_CLONE_RULES',
  MYSQL_RESTORE_LOCAL_SLAVE = 'MYSQL_RESTORE_LOCAL_SLAVE',
  MYSQL_HA_RENAME_DATABASE = 'MYSQL_HA_RENAME_DATABASE',
  MYSQL_SINGLE_RENAME_DATABASE = 'MYSQL_SINGLE_RENAME_DATABASE',
  MYSQL_ADD_SLAVE = 'MYSQL_ADD_SLAVE',
  MYSQL_HA_TRUNCATE_DATA = 'MYSQL_HA_TRUNCATE_DATA',
  MYSQL_SINGLE_TRUNCATE_DATA = 'MYSQL_SINGLE_TRUNCATE_DATA',
  MYSQL_CHECKSUM = 'MYSQL_CHECKSUM',
  MYSQL_DATA_MIGRATE = 'MYSQL_DATA_MIGRATE',
  MYSQL_PROXY_SWITCH = 'MYSQL_PROXY_SWITCH',
  MYSQL_HA_DB_TABLE_BACKUP = 'MYSQL_HA_DB_TABLE_BACKUP',
  MYSQL_MIGRATE_CLUSTER = 'MYSQL_MIGRATE_CLUSTER',
  MYSQL_MASTER_SLAVE_SWITCH = 'MYSQL_MASTER_SLAVE_SWITCH',
  MYSQL_PROXY_ADD = 'MYSQL_PROXY_ADD',
  MYSQL_MASTER_FAIL_OVER = 'MYSQL_MASTER_FAIL_OVER',
  MYSQL_IMPORT_SQLFILE = 'MYSQL_IMPORT_SQLFILE',
  MYSQL_FORCE_IMPORT_SQLFILE = 'MYSQL_FORCE_IMPORT_SQLFILE',
  MYSQL_FLASHBACK = 'MYSQL_FLASHBACK',
  MYSQL_ROLLBACK_CLUSTER = 'MYSQL_ROLLBACK_CLUSTER',
  MYSQL_RESTORE_SLAVE = 'MYSQL_RESTORE_SLAVE',
  MYSQL_HA_FULL_BACKUP = 'MYSQL_HA_FULL_BACKUP',
  MYSQL_OPEN_AREA = 'MYSQL_OPEN_AREA', // 开区
  MYSQL_PARTITION = 'MYSQL_PARTITION',
  MYSQL_DUMP_DATA = 'MYSQL_DUMP_DATA', // mysql mysql 数据导出
  MYSQL_PROXY_UPGRADE = 'MYSQL_PROXY_UPGRADE', // MySQL Proxy 升级
  MYSQL_LOCAL_UPGRADE = 'MYSQL_LOCAL_UPGRADE', // MySQL 原地升级
  MYSQL_MIGRATE_UPGRADE = 'MYSQL_MIGRATE_UPGRADE', // MySQL 迁移升级
}
export enum TicketTypes {
  REDIS_CLUSTER_APPLY = 'REDIS_CLUSTER_APPLY',
  REDIS_KEYS_EXTRACT = 'REDIS_KEYS_EXTRACT',
  REDIS_KEYS_DELETE = 'REDIS_KEYS_DELETE',
  REDIS_BACKUP = 'REDIS_BACKUP',
  REDIS_PURGE = 'REDIS_PURGE',
  REDIS_DESTROY = 'REDIS_DESTROY',
  REDIS_PROXY_OPEN = 'REDIS_PROXY_OPEN',
  REDIS_PROXY_CLOSE = 'REDIS_PROXY_CLOSE',
  REDIS_PLUGIN_DNS_BIND_CLB = 'REDIS_PLUGIN_DNS_BIND_CLB',
  REDIS_PLUGIN_DNS_UNBIND_CLB = 'REDIS_PLUGIN_DNS_UNBIND_CLB',
  REDIS_PLUGIN_CREATE_CLB = 'REDIS_PLUGIN_CREATE_CLB',
  REDIS_PLUGIN_DELETE_CLB = 'REDIS_PLUGIN_DELETE_CLB',
  REDIS_PLUGIN_CREATE_POLARIS = 'REDIS_PLUGIN_CREATE_POLARIS',
  REDIS_PLUGIN_DELETE_POLARIS = 'REDIS_PLUGIN_DELETE_POLARIS',
  REDIS_CLUSTER_CUTOFF = 'REDIS_CLUSTER_CUTOFF', // redis 整机替换
  REDIS_PROXY_SCALE_UP = 'REDIS_PROXY_SCALE_UP', // redis 接入层扩容
  REDIS_PROXY_SCALE_DOWN = 'REDIS_PROXY_SCALE_DOWN', // redis 接入层缩容
  REDIS_SCALE_UPDOWN = 'REDIS_SCALE_UPDOWN', // redis 集群容量变更
  REDIS_SCALE_UP = 'REDIS_SCALE_UP', // redis 存储层扩容
  REDIS_SCALE_DOWN = 'REDIS_SCALE_DOWN', // redis 存储层缩容
  REDIS_MASTER_SLAVE_SWITCH = 'REDIS_MASTER_SLAVE_SWITCH', // redis 主故障切换
  REDIS_SLOTS_MIGRATE = 'REDIS_SLOTS_MIGRATE', // redis slots 迁移
  REDIS_DATA_STRUCTURE = 'REDIS_DATA_STRUCTURE', // redis 定点构造
  REDIS_DATA_STRUCTURE_TASK_DELETE = 'REDIS_DATA_STRUCTURE_TASK_DELETE', // redis 构造销毁
  REDIS_CLUSTER_ADD_SLAVE = 'REDIS_CLUSTER_ADD_SLAVE', // redis 新建从库
  REDIS_CLUSTER_DATA_COPY = 'REDIS_CLUSTER_DATA_COPY', // redis 数据复制
  REDIS_CLUSTER_SHARD_NUM_UPDATE = 'REDIS_CLUSTER_SHARD_NUM_UPDATE', // redis 集群分片变更
  REDIS_CLUSTER_TYPE_UPDATE = 'REDIS_CLUSTER_TYPE_UPDATE', // redis 集群类型变更
  REDIS_DATACOPY_CHECK_REPAIR = 'REDIS_DATACOPY_CHECK_REPAIR', // redis 数据校验与修复
  REDIS_CLUSTER_ROLLBACK_DATA_COPY = 'REDIS_CLUSTER_ROLLBACK_DATA_COPY', // redis 数据回写
  REDIS_VERSION_UPDATE_ONLINE = 'REDIS_VERSION_UPDATE_ONLINE', // redis 版本升级
  REDIS_INS_APPLY = 'REDIS_INS_APPLY', // redis 主从集群部署
  REDIS_INSTANCE_PROXY_OPEN = 'REDIS_INSTANCE_PROXY_OPEN', // redis 主从集群启用
  REDIS_INSTANCE_PROXY_CLOSE = 'REDIS_INSTANCE_PROXY_CLOSE', // redis 主从集群禁用
  REDIS_INSTANCE_DESTROY = 'REDIS_INSTANCE_DESTROY', // redis 主从集群删除
}
export enum TicketTypes {
  TENDBCLUSTER_APPLY = 'TENDBCLUSTER_APPLY',
  TENDBCLUSTER_DISABLE = 'TENDBCLUSTER_DISABLE', // spider 集群禁用
  TENDBCLUSTER_ENABLE = 'TENDBCLUSTER_ENABLE', // spider 集群启用
  TENDBCLUSTER_DESTROY = 'TENDBCLUSTER_DESTROY', // spider 集群下架
  TENDBCLUSTER_SPIDER_SLAVE_DESTROY = 'TENDBCLUSTER_SPIDER_SLAVE_DESTROY', // spider 只读集群下架
  TENDBCLUSTER_SPIDER_REDUCE_MNT = 'TENDBCLUSTER_SPIDER_REDUCE_MNT', // spider 运维节点下架
  TENDBCLUSTER_SPIDER_ADD_NODES = 'TENDBCLUSTER_SPIDER_ADD_NODES', // Spider扩容接入层
  TENDBCLUSTER_SPIDER_REDUCE_NODES = 'TENDBCLUSTER_SPIDER_REDUCE_NODES', // Spider缩容接入层
  TENDBCLUSTER_SPIDER_SLAVE_APPLY = 'TENDBCLUSTER_SPIDER_SLAVE_APPLY', // Spider 部署只读接入层
  TENDBCLUSTER_SPIDER_MNT_APPLY = 'TENDBCLUSTER_SPIDER_MNT_APPLY', // Spider 添加运维节点
  TENDBCLUSTER_MASTER_SLAVE_SWITCH = 'TENDBCLUSTER_MASTER_SLAVE_SWITCH', // Spider remote 主从切换
  TENDBCLUSTER_RENAME_DATABASE = 'TENDBCLUSTER_RENAME_DATABASE', // Spider Tendbcluster 重命名
  TENDBCLUSTER_MASTER_FAIL_OVER = 'TENDBCLUSTER_MASTER_FAIL_OVER', // Spider remote主故障切换
  TENDBCLUSTER_DB_TABLE_BACKUP = 'TENDBCLUSTER_DB_TABLE_BACKUP', // Spider TenDBCluster 库表备份
  TENDBCLUSTER_FULL_BACKUP = 'TENDBCLUSTER_FULL_BACKUP', // Spider TenDBCluster 全备单据
  TENDBCLUSTER_NODE_REBALANCE = 'TENDBCLUSTER_NODE_REBALANCE', // Spider 集群remote节点扩缩容
  TENDBCLUSTER_ROLLBACK_CLUSTER = 'TENDBCLUSTER_ROLLBACK_CLUSTER', // Spider 定点回档
  TENDBCLUSTER_FLASHBACK = 'TENDBCLUSTER_FLASHBACK', // Spider 闪回
  TENDBCLUSTER_TRUNCATE_DATABASE = 'TENDBCLUSTER_TRUNCATE_DATABASE', // Spider tendbcluster 清档
  TENDBCLUSTER_SPIDER_MNT_DESTROY = 'TENDBCLUSTER_SPIDER_MNT_DESTROY', // Spider 运维节点下架
  TENDBCLUSTER_CHECKSUM = 'TENDBCLUSTER_CHECKSUM', // Spider checksum
  TENDBCLUSTER_CLIENT_CLONE_RULES = 'TENDBCLUSTER_CLIENT_CLONE_RULES', // Spider 客户端权限克隆
  TENDBCLUSTER_INSTANCE_CLONE_RULES = 'TENDBCLUSTER_INSTANCE_CLONE_RULES', // Spider DB 实例权限克隆
  TENDBCLUSTER_AUTHORIZE_RULES = 'TENDBCLUSTER_AUTHORIZE_RULES',
  TENDBCLUSTER_EXCEL_AUTHORIZE_RULES = 'TENDBCLUSTER_EXCEL_AUTHORIZE_RULES',
  TENDBCLUSTER_PARTITION = 'TENDBCLUSTER_PARTITION', // Spider 分区管理
  TENDBCLUSTER_IMPORT_SQLFILE = 'TENDBCLUSTER_IMPORT_SQLFILE', // Spider SQL变更执行
  TENDBCLUSTER_FORCE_IMPORT_SQLFILE = 'TENDBCLUSTER_FORCE_IMPORT_SQLFILE', // Spider SQL变更执行
  TENDBCLUSTER_OPEN_AREA = 'TENDBCLUSTER_OPEN_AREA', // Spider 开区
  TENDBCLUSTER_MIGRATE_CLUSTER = 'TENDBCLUSTER_MIGRATE_CLUSTER', // spider 迁移主从
  TENDBCLUSTER_RESTORE_LOCAL_SLAVE = 'TENDBCLUSTER_RESTORE_LOCAL_SLAVE', // spider 重建从库-原地重建
  TENDBCLUSTER_RESTORE_SLAVE = 'TENDBCLUSTER_RESTORE_SLAVE', // spider 重建从库-新机重建
  TENDBCLUSTER_DUMP_DATA = 'TENDBCLUSTER_DUMP_DATA', // spider 数据导出
  TENDBCLUSTER_SEMANTIC_CHECK = 'TENDBCLUSTER_SEMANTIC_CHECK', // spider 模拟执行
}
export enum TicketTypes {
  MONGODB_DISABLE = 'MONGODB_DISABLE', // mongodb禁用
  MONGODB_INSTANCE_RELOAD = 'MONGODB_INSTANCE_RELOAD', // mongodb重启
  MONGODB_SHARD_APPLY = 'MONGODB_SHARD_APPLY', // MongoDB 分片式集群部署申请
  MONGODB_REPLICASET_APPLY = 'MONGODB_REPLICASET_APPLY', // MongoDB 副本集部署申请
  MONGODB_ENABLE = 'MONGODB_ENABLE', // MongoDB 集群启用
  MONGODB_DESTROY = 'MONGODB_DESTROY', // MongoDB 集群删除
  MONGODB_SCALE_UPDOWN = 'MONGODB_SCALE_UPDOWN', // MongoDB 分片式集群单个容量变更
  MONGODB_AUTHORIZE = 'MONGODB_AUTHORIZE', // MongoDB 集群授权
  MONGODB_EXCEL_AUTHORIZE = 'MONGODB_EXCEL_AUTHORIZE', // MongoDB 导入授权
  MONGODB_AUTHORIZE_RULES = 'MONGODB_AUTHORIZE_RULES', // MongoDB 集群授权
  MONGODB_EXCEL_AUTHORIZE_RULES = 'MONGODB_EXCEL_AUTHORIZE_RULES', // MongoDB 导入授权
  MONGODB_EXEC_SCRIPT_APPLY = 'MONGODB_EXEC_SCRIPT_APPLY', // mongo 变更脚本执行
  MONGODB_ADD_SHARD_NODES = 'MONGODB_ADD_SHARD_NODES', // mongo 扩容 shard 节点数
  MONGODB_REDUCE_SHARD_NODES = 'MONGODB_REDUCE_SHARD_NODES', // mongo 缩容 shard 节点数
  MONGODB_ADD_MONGOS = 'MONGODB_ADD_MONGOS', // mongo 扩容接入层
  MONGODB_REDUCE_MONGOS = 'MONGODB_REDUCE_MONGOS', // mongo 缩容接入层
  MONGODB_CUTOFF = 'MONGODB_CUTOFF', // mongo 整机替换
  MONGODB_FULL_BACKUP = 'MONGODB_FULL_BACKUP', // mongo 全库备份
  MONGODB_REMOVE_NS = 'MONGODB_REMOVE_NS', // mongo 清档
  MONGODB_BACKUP = 'MONGODB_BACKUP', // mongo 库表备份
  MONGODB_RESTORE = 'MONGODB_RESTORE', // mongo 定点构造
  MONGODB_TEMPORARY_DESTROY = 'MONGODB_TEMPORARY_DESTROY', // mongo 临时集群销毁
}
export enum TicketTypes {
  SQLSERVER_SINGLE_APPLY = 'SQLSERVER_SINGLE_APPLY', // sqlserver单节点部署
  SQLSERVER_HA_APPLY = 'SQLSERVER_HA_APPLY', // sqlserver主从部署
  SQLSERVER_DISABLE = 'SQLSERVER_DISABLE', // sqlserver 禁用
  SQLSERVER_ENABLE = 'SQLSERVER_ENABLE', // sqlserver 启用
  SQLSERVER_DESTROY = 'SQLSERVER_DESTROY', // sqlserver 删除
  SQLSERVER_AUTHORIZE_RULES = 'SQLSERVER_AUTHORIZE_RULES', // sqlserver 集群授权
  SQLSERVER_EXCEL_AUTHORIZE_RULES = 'SQLSERVER_EXCEL_AUTHORIZE_RULES', // sqlserver 导入授权
  SQLSERVER_RESET = 'SQLSERVER_RESET', // sqlserver 集群重置
  SQLSERVER_BACKUP_DBS = 'SQLSERVER_BACKUP_DBS', // sqlserver 数据库备份
  SQLSERVER_DBRENAME = 'SQLSERVER_DBRENAME', // sqlserver 数据库重命名
  SQLSERVER_DATA_MIGRATE = 'SQLSERVER_DATA_MIGRATE', // sqlserver 数据迁移
  SQLSERVER_CLEAR_DBS = 'SQLSERVER_CLEAR_DBS', // sqlserver 清档
  SQLSERVER_MASTER_FAIL_OVER = 'SQLSERVER_MASTER_FAIL_OVER', // sqlserver 主故障切换
  SQLSERVER_MASTER_SLAVE_SWITCH = 'SQLSERVER_MASTER_SLAVE_SWITCH', // sqlserver 主从切换
  SQLSERVER_ROLLBACK = 'SQLSERVER_ROLLBACK', // sqlserver 定点回档
  SQLSERVER_ADD_SLAVE = 'SQLSERVER_ADD_SLAVE', // sqlserver 增加从库'
  SQLSERVER_RESTORE_SLAVE = 'SQLSERVER_RESTORE_SLAVE', // sqlserver 重建从库_新机重建
  SQLSERVER_RESTORE_LOCAL_SLAVE = 'SQLSERVER_RESTORE_LOCAL_SLAVE', // sqlserver 重建从库_原地重建
  SQLSERVER_IMPORT_SQLFILE = 'SQLSERVER_IMPORT_SQLFILE', // sqlserver SQL变更执行'
  SQLSERVER_FULL_MIGRATE = 'SQLSERVER_FULL_MIGRATE', // sqlserver 全量迁移
  SQLSERVER_INCR_MIGRATE = 'SQLSERVER_INCR_MIGRATE', // sqlserver 增量迁移
  SQLSERVER_BUILD_DB_SYNC = 'SQLSERVER_BUILD_DB_SYNC', // DB建立同步
}

export enum TicketTypes {
  ES_APPLY = 'ES_APPLY',
  ES_DISABLE = 'ES_DISABLE',
  ES_DESTROY = 'ES_DESTROY',
  ES_ENABLE = 'ES_ENABLE',
  ES_SCALE_UP = 'ES_SCALE_UP',
  ES_SHRINK = 'ES_SHRINK',
  ES_REPLACE = 'ES_REPLACE',
  ES_REBOOT = 'ES_REBOOT',
}
export enum TicketTypes {
  KAFKA_APPLY = 'KAFKA_APPLY',
  KAFKA_ENABLE = 'KAFKA_ENABLE',
  KAFKA_DISABLE = 'KAFKA_DISABLE',
  KAFKA_DESTROY = 'KAFKA_DESTROY',
  KAFKA_SCALE_UP = 'KAFKA_SCALE_UP',
  KAFKA_SHRINK = 'KAFKA_SHRINK',
  KAFKA_REPLACE = 'KAFKA_REPLACE',
  KAFKA_REBOOT = 'KAFKA_REBOOT',
}
export enum TicketTypes {
  HDFS_APPLY = 'HDFS_APPLY',
  HDFS_ENABLE = 'HDFS_ENABLE',
  HDFS_DISABLE = 'HDFS_DISABLE',
  HDFS_DESTROY = 'HDFS_DESTROY',
  HDFS_SCALE_UP = 'HDFS_SCALE_UP',
  HDFS_SHRINK = 'HDFS_SHRINK',
  HDFS_REPLACE = 'HDFS_REPLACE',
  HDFS_REBOOT = 'HDFS_REBOOT',
}
export enum TicketTypes {
  INFLUXDB_APPLY = 'INFLUXDB_APPLY',
  INFLUXDB_DISABLE = 'INFLUXDB_DISABLE',
  INFLUXDB_REBOOT = 'INFLUXDB_REBOOT',
  INFLUXDB_REPLACE = 'INFLUXDB_REPLACE',
  INFLUXDB_ENABLE = 'INFLUXDB_ENABLE',
  INFLUXDB_DESTROY = 'INFLUXDB_DESTROY',
}
export enum TicketTypes {
  PULSAR_APPLY = 'PULSAR_APPLY',
  PULSAR_REBOOT = 'PULSAR_REBOOT',
  PULSAR_ENABLE = 'PULSAR_ENABLE',
  PULSAR_DISABLE = 'PULSAR_DISABLE',
  PULSAR_DESTROY = 'PULSAR_DESTROY',
  PULSAR_REPLACE = 'PULSAR_REPLACE',
  PULSAR_SHRINK = 'PULSAR_SHRINK',
  PULSAR_SCALE_UP = 'PULSAR_SCALE_UP',
}
export enum TicketTypes {
  TBINLOGDUMPER_INSTALL = 'TBINLOGDUMPER_INSTALL', // dumper 新建订阅
  TBINLOGDUMPER_SWITCH_NODES = 'TBINLOGDUMPER_SWITCH_NODES', // dumper 节点迁移
  TBINLOGDUMPER_REDUCE_NODES = 'TBINLOGDUMPER_REDUCE_NODES', // dumper 节点下架
  TBINLOGDUMPER_ENABLE_NODES = 'TBINLOGDUMPER_ENABLE_NODES', // dumper 节点启动
  TBINLOGDUMPER_DISABLE_NODES = 'TBINLOGDUMPER_DISABLE_NODES', // dumper 节点禁用
}
export enum TicketTypes {
  RIAK_CLUSTER_APPLY = 'RIAK_CLUSTER_APPLY', // Riak 集群申请
  RIAK_CLUSTER_DESTROY = 'RIAK_CLUSTER_DESTROY', // Riak 集群删除
  RIAK_CLUSTER_DISABLE = 'RIAK_CLUSTER_DISABLE', // Riak 集群禁用
  RIAK_CLUSTER_ENABLE = 'RIAK_CLUSTER_ENABLE', // Riak 集群启用
  RIAK_CLUSTER_SCALE_OUT = 'RIAK_CLUSTER_SCALE_OUT', // Riak 集群扩容
  RIAK_CLUSTER_SCALE_IN = 'RIAK_CLUSTER_SCALE_IN', // Riak 集群缩容
  RIAK_CLUSTER_REBOOT = 'RIAK_CLUSTER_REBOOT', // Riak 节点重启
}
export enum TicketTypes {
  DORIS_APPLY = 'DORIS_APPLY', // Doris 集群申请
}

export type TicketTypesStrings = keyof typeof TicketTypes;
