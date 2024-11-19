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
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.configuration.constants import SQLSERVER_ADMIN_USER
from backend.db_meta.enums import MachineType
from backend.db_services.version.constants import SqlserverVersion
from blue_krill.data_types.enum import EnumField, StructuredEnum

GenerateAndPublish = "GenerateAndPublish"
HOST = "host"
MASTER_HOST = "master_host"
REPL_HOST = "repl_host"
BACKEND_HOST = "backend_host"
DEPENDENCIES_PLUGINS = ["bkmonitorbeat", "bkunifylogbeat"]
BIGDATA_DEPEND_PLUGINS = ["bkmonitorbeat"]


# 默认flow缓存数据过期时间：7天
DEFAULT_FLOW_CACHE_EXPIRE_TIME = 7 * 24 * 60 * 60

# 默认DB moudle id
DEFAULT_DB_MODULE_ID = 0
DEFAULT_CONFIG_CONFIRM = 0

# 默认 ip
DEFAULT_IP = "127.0.0.1"

# zookeeper配置文件模板
ZK_CONF = "server.{i}={zk_ip}:2888:3888;{zk_ip}:2181"
ZK_PORT = ":2888:3888;.*2181"

DEFAULT_FACTOR = 3

# 默认Redis起始端口
DEFAULT_REDIS_START_PORT = 30000
# twemproxy admin port 默认增加值
DEFAULT_TWEMPROXY_ADMIN_PORT_EXTRA = 1000
# 默认Redis dbnum
DEFAULT_REDIS_DBNUM = 0
# 默认Redis databases
DEFAULT_REDIS_INSTANCE_DATABASES = 2
DEFAULT_REDIS_CLUSTER_DATABASES = 1

# 切换时， 默认允许多久心跳
DEFAULT_MASTER_DIFF_TIME = 61
# 切换时， 允许多少秒丢失
DEFAULT_LAST_IO_SECOND_AGO = 100

# 默认Riak端口
DEFAULT_RIAK_PORT = 8087

# 默认Sqlserver端口
DEFAULT_SQLSERVER_PORT = 48322

# 默认Sqlserver下发路径
DEFAULT_SQLSERVER_PATH = "d:\\install"

# window操作系统超级账号,标准运维调用
WINDOW_ADMIN_USER_FOR_CHECK = "Administrator"

# linux操作系统超级账号,标准运维调用
LINUX_ADMIN_USER_FOR_CHECK = "root"

# tendisplus默认kvstorecount
DEFAULT_TENDISPLUS_KVSTORECOUNT = 10

# 定义每个TenDB-Cluster集群最大spider-master/mnt角色的节点数量（暂定）
MAX_SPIDER_MASTER_COUNT = 37
# 定义每个TenDB-Cluster集群最小spider-master/slave角色的节点数量（暂定）
MIN_SPIDER_MASTER_COUNT = 2
MIN_SPIDER_SLAVE_COUNT = 1

TDBCTL_USER = "spider"

# 定义每个flow发起时的实例临时账号名称前缀
DBM_MYSQL_JOB_TMP_USER_PREFIX = "J_"
# 定义sqlserver专属的匹配临时账号的正则
DBM_JOB_TMP_USER_REGULAR = "J[_]%"
# 定义sqlserverJob超长超时时间
DBM_SQLSERVER_JOB_LONG_TIMEOUT = 24 * 3600

# 数据量大小单位
BYTE = 1
KB = 1 << 10
MB = 1 << 20
GB = 1 << 30
TB = 1 << 40
PB = 1 << 50

DEFAULT_JOB_TIMEOUT = 7200
LONG_JOB_TIMEOUT = 86400
BIGFILE_JOB_SCP_TIMEOUT = 86400

# 默认监听时间，1分钟
DEFAULT_MONITOR_TIME = 60000
# 默认监听排除请求命令
DEFAULT_REDIS_SYSTEM_CMDS = [
    "REPLCONF",
    "quit",
    "auth",
    "cmdstat",
    "ping",
    "ok",
    "cluster",
    "select",
    ":time",
    "dbmon",
    "command",
    "dbha:agent:",
    "info",
    "PSYNC",
    "twemproxy_mon",
    "readonly",
]

# twemproxy seg总数
DEFAULT_TWEMPROXY_SEG_TOTOL_NUM = 420000
# twemproxy seg 最小值
DEFAULT_TWEMPROXY_SEG_MIN_NUM = 0

# JOB任务状态
NOT_RUNNING = 1
RUNNING = 2
SUCCESS = 3
FAILED = 4
SKIPPED = 5
IGNORE_ERROR = 6
WAITING = 7
MANUAL_TERMINAL = 8
ABNORMAL_STATE = 9
BEING_FORCIBLY_TERMINATED = 10
SUCCESS_FORCIBLY_TERMINATED = 11
FAILED_FORCIBLY_TERMINATED = 12

SUCCESS_LIST = [SUCCESS, IGNORE_ERROR, SKIPPED, MANUAL_TERMINAL, SUCCESS_FORCIBLY_TERMINATED]
FAILED_LIST = [FAILED, ABNORMAL_STATE, FAILED_FORCIBLY_TERMINATED]
DBA_SYSTEM_USER = "mysql"
DBA_ROOT_USER = "root"

# ip port 分隔符，对应授权远程接口传入参数时使用的分隔符
AUTH_ADDRESS_DIVIDER = ":"

# ES默认部署的实例数
ES_DEFAULT_INSTANCE_NUM = 1

# DORIS默认部署的实例数
DORIS_DEFAULT_INSTANCE_NUM = 2

# MySQL 系统内置账号列表
MYSQL_SYS_USER = ["system user", "event_scheduler"]


class StateType(str, StructuredEnum):
    CREATED = EnumField("CREATED", _("创建态"))
    READY = EnumField("READY", _("准备态"))
    RUNNING = EnumField("RUNNING", _("运行态"))
    SUSPENDED = EnumField("SUSPENDED", _("暂停态"))
    BLOCKED = EnumField("BLOCKED", _("闭塞态"))
    FINISHED = EnumField("FINISHED", _("完成态"))
    FAILED = EnumField("FAILED", _("失败态"))
    REVOKED = EnumField("REVOKED", _("取消态"))
    EXPIRED = EnumField("EXPIRED", _("已过期"))


FAILED_STATES = [StateType.FAILED.value, StateType.REVOKED.value]
SUCCEED_STATES = [StateType.FINISHED]

# 备份系统文件TAG
BACKUP_TAG = (
    "REDIS_BINLOG,INCREMENT_BACKUP,REDIS_FULL,MYSQL_FULL_BACKUP,"
    "MSSQL_FULL_BACKUP,BINLOG,OSDATA,MONGO_INCR_BACKUP,LOG,ORACLE,OTHER,DBFILE"
)
# 备份系统默认用户
BACKUP_DEFAULT_OS_USER = "mysql"

# TBinlogDumper 默认安装端口
TBINLOGDUMPER_PORT = 27000

# 获取平台级别的账号密码的默认实例
DEFAULT_INSTANCE = {"ip": "0.0.0.0", "port": 0, "bk_cloud_id": 0}


class NameSpaceEnum(str, StructuredEnum):
    Common = EnumField("common", _("共用参数"))
    RedisCommon = EnumField("rediscomm", _("redis共用参数"))
    TenDBHA = EnumField("tendbha", _("TenDBHA"))
    RedisInstance = EnumField("RedisInstance", _("RedisCache 主从版"))
    TwemproxyRedisInstance = EnumField("TwemproxyRedisInstance", _("twemproxy + RedisInstance架构"))
    PredixyTendisplusCluster = EnumField("PredixyTendisplusCluster", _("predixy + tendisplus架构"))
    Es = EnumField("es", _("Es"))
    TenDB = EnumField("tendb", _("tendb"))
    Kafka = EnumField("kafka", _("Kafka"))
    Hdfs = EnumField("hdfs", _("Hdfs"))
    Pulsar = EnumField("pulsar", _("Pulsar"))
    Influxdb = EnumField("influxdb", _("Influxdb"))
    TenDBCluster = EnumField("tendbcluster", _("tendbcluster"))
    Riak = EnumField("riak", _("Riak"))
    MongoDBCommon = EnumField("mongodbcommon", _("mongodbcommon"))
    Doris = EnumField("doris", _("Doris"))
    Vm = EnumField("vm", _("Vm"))


class ConfigTypeEnum(str, StructuredEnum):
    InitUser = EnumField("init_user", _("初始化帐户"))
    MySQLAndUser = EnumField("mysql#user", _("实例和帐户"))
    OSConf = EnumField("osconf", _("系统配置"))
    DBConf = EnumField("dbconf", _("实例配置"))
    Config = EnumField("config", _("默认配置"))
    ProxyConf = EnumField("proxyconf", _("proxyconfig"))
    EsConf = EnumField("esconf", _("ES实例配置"))
    ActConf = EnumField("actconf", _("act配置"))
    SysConf = EnumField("sys", _("系统配置类型"))
    KafkaConf = EnumField("kafkaconf", _("Kafka实例配置"))
    HdfsConf = EnumField("hdfsconf", _("HDFS集群配置"))
    HdfsSite = EnumField("hdfs-site", _("HDFS实例hdfs-site配置"))
    CoreSite = EnumField("core-site", _("HDFS实例core-site配置"))
    HdfsInstall = EnumField("install", _("HDFS实例安装配置"))
    MongoD = EnumField("mongod", _("mongod配置"))
    MongoS = EnumField("mongos", _("mongos配置"))


class ConfigFileEnum(str, StructuredEnum):
    OS = EnumField("os", _("系统"))
    Twemproxy = EnumField("Twemproxy-latest", _("twemproxy config file"))
    Predixy = EnumField("Predixy-latest", _("predixy config file"))
    Redis = EnumField("redis", _("redis config file"))
    FullBackup = EnumField("fullbackup", _("全备配置"))
    BinlogBackup = EnumField("binlogbackup", _("增备配置"))
    Heartbeat = EnumField("heartbeat", _("心跳配置"))
    Monitor = EnumField("monitor", _("监控配置"))
    Base = EnumField("base", _("基本配置"))
    HotKey = EnumField("hotkey", _("热key配置"))
    BigKey = EnumField("bigkey", _("大key配置"))
    DefaultConf = EnumField("defaultconf", _("默认配置"))
    OsConf = EnumField("osconf", _("os配置"))
    MaxMemorySet = EnumField("maxmemory_set", _("maxmemory配置"))


class DbBackupRoleEnum(str, StructuredEnum):
    Master = EnumField("MASTER", _("MASTER"))
    Slave = EnumField("SLAVE", _("SLAVE"))


class MediumEnum(str, StructuredEnum):
    MySQL = EnumField("mysql", _("mysql"))
    MySQLProxy = EnumField("mysql-proxy", _("mysql-proxy"))
    Redis = EnumField("redis", _("redis"))
    TendisPlus = EnumField("tendisplus", _("tendisplus"))
    TendisSsd = EnumField("tendisssd", _("tendisssd"))
    DbBackup = EnumField("dbbackup", _("dbbackup"))
    DbBackupTXSQL = EnumField("dbbackup-txsql", _("dbbackup-txsql"))
    DBActuator = EnumField("actuator", _("actuator"))
    Exporter = EnumField("exporter", _("exporter"))
    Latest = EnumField("latest", _("最新版本"))
    Twemproxy = EnumField("twemproxy", _("twemproxy"))
    Predixy = EnumField("predixy", _("predixy"))
    RedisTools = EnumField("tools", _("redis_tools"))
    Es = EnumField("es", _("es"))
    Kafka = EnumField("kafka", _("kafka"))
    Hdfs = EnumField("hdfs", _("hdfs"))
    Pulsar = EnumField("pulsar", _("pulsar"))
    Influxdb = EnumField("influxdb", _("influxdb"))
    DbMon = EnumField("dbmon", _("dbmon"))
    MySQLChecksum = EnumField("mysql-checksum", _("mysql-checksum"))
    MySQLRotateBinlog = EnumField("rotate-binlog", _("Binlog 滚动备份工具"))
    MySQLToolKit = EnumField("dba-toolkit", _("DBA 工具集"))
    MySQLCrond = EnumField("mysql-crond", _("mysql-crond"))
    MySQLMonitor = EnumField("mysql-monitor", _("MySQL 监控"))
    CloudNginx = EnumField("cloud-nginx", _("nginx 服务"))
    CloudDNSBind = EnumField("cloud-dns-bind", _("dns-bind 服务"))
    CloudDNSPullCrond = EnumField("cloud-dns-pullcrond", _("dns-pull-crond服务"))
    CloudDBHA = EnumField("cloud-dbha", _("cloud-dbha服务"))
    CloudDRS = EnumField("cloud-drs", _("cloud-drs服务"))
    CloudDRSTymsqlParse = EnumField("cloud-drs-tmysqlparse", _("cloud-drs-tmysqlparse服务"))
    Spider = EnumField("spider", _("spider节点名称"))
    tdbCtl = EnumField("tdbctl", _("spider中控节点名称"))
    Riak = EnumField("riak", _("riak"))
    RiakMonitor = EnumField("riak-monitor", _("riak-monitor"))
    RedisDts = EnumField("redis-dts", _("redis-dts"))
    RedisModules = EnumField("redis-modules", _("redis-modules"))
    TBinlogDumper = EnumField("tbinlogdumper", _("tbinlogdumper实例"))
    Sqlserver = EnumField("sqlserver", _("sqlserver实例"))
    MongoDB = EnumField("mongodb", _("mongodb"))
    MongoToolKit = EnumField("mongo-toolkit", _("Mongo 工具集"))
    MongoMonitor = EnumField("mongo-monitor", _("Mongo 监控"))
    DBTools = EnumField("dbtools", _("工具包"))
    Doris = EnumField("doris", _("doris"))
    Vm = EnumField("vm", _("vm"))


class CloudServiceName(str, StructuredEnum):
    Nginx = EnumField("nginx", _("nginx服务"))
    DNS = EnumField("dns", _("dns服务"))
    DRS = EnumField("drs", _("drs服务"))
    DBHA = EnumField("dbha", _("dbha服务"))
    RedisDTS = EnumField("redis_dts", _("redis 数据传输服务"))


class CloudServiceConfFileEnum(str, StructuredEnum):
    PullCrond = EnumField("pull-crond.conf", _("pull-crond.conf"))
    HA_GM = EnumField("ha-gm.conf", _("ha-gm.conf"))
    HA_AGENT = EnumField("ha-agent.conf", _("ha-agent.conf"))
    DRS_ENV = EnumField("drs.env", _("drs.env"))


class CloudDBHATypeEnum(str, StructuredEnum):
    GM = EnumField("gm", _("GM"))
    AGENT = EnumField("agent", _("AGENT"))
    MySQLMonitor = EnumField("mysql-monitor", _("mysql-monitor"))


CLOUD_SSL_PATH = "cloud/ssl"
CLOUD_NGINX_DBM_DEFAULT_PORT = 80
CLOUD_NGINX_MANAGE_DEFAULT_HOST = 8080


class CloudServiceModuleName(str, StructuredEnum):
    Nginx = EnumField("nginx.service.module", _("nginx服务模块"))
    DNS = EnumField("dns.service.module", _("dns服务模块"))
    DRS = EnumField("drs.service.module", _("drs服务模块"))
    DBHA = EnumField("dbha.service.module", _("dbha服务模块"))
    RedisDTS = EnumField("redis_dts.service.module", _("redis_dts服务模块"))


class MediumFileTypeEnum(int, StructuredEnum):
    Server = EnumField(1, _("服务器文件"))
    Repo = EnumField(3, _("蓝盾制品库"))


class RDMSApplyEnum(str, StructuredEnum):
    MySQL = EnumField("MySQL", _("MySQL"))
    Version = EnumField("v1", _("V1"))


class DBActuatorTypeEnum(str, StructuredEnum):
    Default = EnumField("", "")
    MySQL = EnumField("mysql", _("mysql"))
    Proxy = EnumField("proxy", _("proxy"))
    Redis = EnumField("redis", _("redis"))
    Tendis = EnumField("tendis", _("tendis"))
    Tendisplus = EnumField("tendisplus", _("tendisplus"))
    TendisSSD = EnumField("tendisssd", _("tendisssd"))
    Twemproxy = EnumField("twemproxy", _("twemproxy"))
    Predixy = EnumField("predixy", _("predixy"))
    Es = EnumField("es", _("es"))
    Kafka = EnumField("kafka", _("kafka"))
    Hdfs = EnumField("hdfs", _("hdfs"))
    Pulsar = EnumField("pulsar", _("pulsar"))
    Influxdb = EnumField("influxdb", _("influxdb"))
    Bkdbmon = EnumField("bkdbmon", _("bkdbmon"))
    Download = EnumField("download", _("download"))
    Spider = EnumField("spider", _("spider"))
    SpiderCtl = EnumField("spiderctl", _("spiderctl"))
    Riak = EnumField("riak", _("riak"))
    TBinlogDumper = EnumField("tbinlogdumper", _("tbinlogdumper"))
    Sqlserver = EnumField("sqlserver", _("sqlserer"))
    Sqlserver_check = EnumField("check", _("sqlserer_check"))
    Doris = EnumField("doris", _("doris"))
    Vm = EnumField("vm", _("vm"))


class DBActuatorActionEnum(str, StructuredEnum):
    Sysinit = EnumField("sysinit", _("sysinit"))
    Deploy = EnumField("deploy", _("deploy"))
    AppendDeploy = EnumField("append-deploy", _("append-deploy"))
    ImportSchemaToTdbctl = EnumField("import-schema-to-tdbctl", _("import-schema-to-tdbctl"))
    CheckTdbctlWithSpiderSchema = EnumField("check-tdbctl-with-spider-schema", _("icheck-tdbctl-with-spider-schema"))
    GetBackupFile = EnumField("find-local-backup", _("find-local-backup"))
    RestoreSlave = EnumField("restore-dr", _("restore-dr"))
    RecoverBinlog = EnumField("recover-binlog", _("recover-binlog"))
    GrantRepl = EnumField("grant-repl", _("grant-repl"))
    ChangeMaster = EnumField("change-master", _("change-master"))
    SetBackend = EnumField("set-backend", _("set-backend"))
    UnInstall = EnumField("uninstall", _("uninstall"))
    DeployDbbackup = EnumField("deploy-dbbackup", _("deploy-dbbackup"))
    InstallMonitor = EnumField("install-monitor", _("install-monitor"))
    SenmanticDumpSchema = EnumField("semantic-dumpschema", _("semantic-dumpschema"))
    ImportSQLFile = EnumField("import-sqlfile", _("import-sqlfile"))
    CloneClientGrant = EnumField("clone-client-grant", _("clone-client-grant"))
    CloneProxyUser = EnumField("clone-proxy-user", _("clone-proxy-user"))
    ClearCrontab = EnumField("clear-crontab", _("clear-crontab"))
    SemanticCheck = EnumField("semantic-check", _("semantic-check"))
    SemanticDumpSchema = EnumField("semantic-dumpschema", _("semantic-dumpschema"))
    MysqlDumpData = EnumField("dump", _("dump"))
    # TruncateDataBackupNaTable = EnumField("backup-truncate-database", _("backup-truncate-database"))
    RestartProxy = EnumField("restart", _("restart"))
    CleanMysql = EnumField("clean-mysql", _("clean-mysql"))
    DataBaseTableBackup = EnumField("backup-database-table", _("backup-database-table"))
    SetBackendTowardSlave = EnumField("set-backend-toward-slave", _("set-backend-toward-slave"))
    Checksum = EnumField("pt-table-checksum", _("pt-table-checksum"))
    Partition = EnumField("import-partitionsql", _("执行分区"))
    IbsRecver = EnumField("ibs-recover", _("ibs-recover"))
    PtTableSync = EnumField("pt-table-sync", _("数据修复指令"))
    FlashBackBinlog = EnumField("flashback-binlog", _("flashback-binlog"))
    FullBackup = EnumField("full-backup", _("full-backup"))
    DeployMySQLChecksum = EnumField("install-checksum", _("install-checksum"))
    MysqlEditConfig = EnumField("mycnf-change", _("mycnf-change"))
    DeployMysqlBinlogRotate = EnumField("deploy-mysql-rotatebinlog", _("安装mysql-rotatebinlog程序"))
    DeployDBAToolkit = EnumField("install-dbatoolkit", _("安装dba-toolkit程序"))
    DeployMySQLCrond = EnumField("deploy-mysql-crond", _("deploy-mysql-crond"))
    MysqlClearSurroundingConfig = EnumField("clear-inst-config", _("mysql实例的周边配置清理"))
    SpiderInitClusterRouting = EnumField("init-cluster-routing", _("初始化spider集群节点关系"))
    SpiderAddTmpNode = EnumField("add-tmp-spider", _("添加spider临时节点"))
    RestartSpider = EnumField("restart-spider", _("restart-spider"))
    AddSlaveClusterRouting = EnumField("add-slave-cluster-routing", _("添加spider-slave集群的相关路由信息"))
    MySQLBackupDemand = EnumField("backup-demand", _("mysql备份请求"))
    TenDBClusterBackendSwitch = EnumField("cluster-backend-switch", _("TenDBCluster集群做后端切换"))
    TenDBClusterMigrateCutOver = EnumField("cluster-backend-migrate-cutover", _("TenDBCluster集群做后端的成对迁移"))
    DumpSchema = EnumField("dumpschema", _("为TBinlogDumper实例导出导入源表结构"))
    OsCmd = EnumField("oscmd-run", _("执行os命令"))
    MysqlOpenAreaDumpSchema = EnumField("open_area_dumpschema", _("Mysql开区导出库表结构"))
    MysqlOpenAreaImportSchema = EnumField("open_area_importschema", _("Mysql开区导入库表结构"))
    MysqlOpenAreaDumpData = EnumField("open_area_dumpdata", _("Mysql开区导出库表数据"))
    MysqlOpenAreaImportData = EnumField("open_area_importdata", _("Mysql开区导入库表数据"))
    EnableTokudb = EnumField("enable-tokudb-engine", _("MySQL实例安装tokudb引擎"))
    StandardizeMySQLInstance = EnumField("standardize-mysql", _("标准化MySQL实例"))
    StandardizeTenDBHAProxy = EnumField("standardize-proxy", _("标准化Proxy实例"))
    Upgrade = EnumField("upgrade", _("本地升级"))
    MysqlDataMigrateDump = EnumField("mysql_data_migrate_dump", _("Mysql数据迁移导出库"))
    MysqlDataMigrateImport = EnumField("mysql_data_migrate_import", _("Mysql数据迁移导入库"))
    MysqlChangeMycnf = EnumField("mycnf-change", _("修改MySQL配置"))
    CreateStageViaCtl = EnumField("create-stage-via-ctl", _("TenDBCluster 清档在中控建立备份库表"))
    TruncatePreDropStageOnRemote = EnumField("truncate-pre-drop-stage-on-remote", _("TenDBCluster 清档在remote预清理备份库"))
    TruncateOnMySQL = EnumField("truncate-on-mysql", _("MySQL执行清档"))
    TruncateOnCtl = EnumField("truncate-on-ctl", _("中控执行清档"))
    RenameOnMySQL = EnumField("rename-on-mysql", _("MySQL执行DB重命名"))
    TruncateCheckDBsInUsing = EnumField("truncate-dbs-in-using", _("清档检查库表是否在用"))
    RenameCheckDBsInUsing = EnumField("rename-dbs-in-using", _("重命名检查库表是否在用"))
    CreateToDBViaCtl = EnumField("create-to-db-via-ctl", _("重命名在中控建立目标库"))
    RenamePreDropToOnRemote = EnumField("rename-pre-drop-to-on-remote", _("TenDBCluster 重命名在remote预清理目标库"))
    RenameDropFromViaCtl = EnumField("rename-drop-from-via-ctl", _("TenDBCluster 重命名在中控删除源库"))
    PushMySQLCrondConfig = EnumField("push-mysql-crond-config", _("推送mysql-crond配置"))
    PushMySQLMonitorConfig = EnumField("push-mysql-monitor-config", _("推送mysql-monitor配置"))
    PushChecksumConfig = EnumField("push-checksum-config", _("推送mysql-table-checksum配置"))
    PushNewDbBackupConfig = EnumField("push-new-db-backup-config", _("推送备份配置"))
    PushMySQLRotatebinlogConfig = EnumField("push-mysql-rotatebinlog-config", _("推送rotatebinlog配置"))
    ChangeServerId = EnumField("change-server-id", _("change-server-id"))


class RedisActuatorActionEnum(str, StructuredEnum):
    Sysinit = EnumField("sysinit", _("sysinit"))
    Install = EnumField("install", _("install"))
    REPLICA_BATCH = EnumField("replica_batch", _("replica_batch"))
    Replicaof = EnumField("replicaof", _("replicaof"))
    LocalReDoDR = EnumField("local_redo_dr", _("local_redo_dr"))
    CLUSTER_MEET = EnumField("clustermeet_slotsassign", _("clustermeet_slotsassign"))
    KEYS_PATTERN = EnumField("keyspattern", _("keyspattern"))
    KEYS_DELETE_REGEX = EnumField("keysdelete_regex", _("keysdelete_regex"))
    KEYS_DELETE_FILES = EnumField("keysdelete_files", _("keysdelete_files"))
    Backup = EnumField("backup", _("backup"))
    FlushData = EnumField("flush_data", _("flush_data"))
    Shutdown = EnumField("shutdown", _("shutdown"))
    Open = EnumField("open", _("open"))
    Close = EnumField("close", _("close"))
    Operate = EnumField("operate", _("operate"))
    Capturer = EnumField("capturer", _("capturer"))
    ChangePwd = EnumField("change_password", _("change_password"))
    KillConn = EnumField("kill_conn", _("kill_conn"))
    SyncParam = EnumField("param_sync", _("param_sync"))
    CheckSync = EnumField("sync_check", _("sync_check"))
    SwitchBackends = EnumField("switch", _("switch"))
    ClusterForget = EnumField("cluster_forget", _("cluster_forget"))
    DR_RESTORE = EnumField("dr_restore", _("dr_restore"))
    CheckProxysMd5 = EnumField("check_backends", _("check_backends"))
    DTS_DATACHECK = EnumField("dts_datacheck", _("dts_datacheck"))
    DTS_DATAREPAIR = EnumField("dts_datarepair", _("dts_datarepair"))
    DTS_ONLINE_SWITCH = EnumField("dts_online_switch", _("dts_online_switch"))
    ADD_DTS_SERVER = EnumField("add_dts_server", _("add_dts_server"))
    REMOVE_DTS_SERVER = EnumField("remove_dts_server", _("remove_dts_server"))
    DATA_STRUCTURE = EnumField("data_structure", _("data_structure"))
    CLUSTER_MEET_CHECK = EnumField("clustermeet_checkfinish", _("clustermeet_checkfinish"))
    VERSION_UPDATE = EnumField("version_update", _("version_update"))
    PROXY_VERSION_UPGRADE = EnumField("proxy_version_upgrade", _("proxy_version_upgrade"))
    CLUSTER_FAILOVER = EnumField("cluster_failover", _("cluster_failover"))
    SLOTS_MIGRATE = EnumField("migrate_slots", _("migrate_slots"))
    REUPLOAD_OLD_BACKUP_RECORDS = EnumField("reupload_old_backup_records", _("reupload_old_backup_records"))
    PREDIXY_CONFIG_SERVERS_REWRITE = EnumField("predixy_config_servers_rewrite", _("predixy_config_servers_rewrite"))
    MAXMEMORY_DYNAMICALLY_SET = EnumField("maxmemory_dynamically_set", _("maxmemory_dynamically_set"))
    CLIENT_CONNS_KILL = EnumField("client_conns_kill", _("client_conns_kill"))
    CONFIG_SET = EnumField("config_set", _("config_set"))
    LOAD_MODULES = EnumField("load_modules", _("load_modules"))
    PREDIXY_ADD_MODULES_CMDS = EnumField("predixy_add_modules_cmds", _("predixy_add_modules_cmds"))
    RESHAPE = EnumField("reshape", _("reshape"))
    CLUSTER_RESET_FLUSH_MEET = EnumField("cluster_reset_flush_meet", _("cluster_reset_flush_meet"))
    REPLICAS_FORCE_RESYNC = EnumField("replicas_force_resync", _("replicas_force_resync"))


class MongoDBActuatorActionEnum(str, StructuredEnum):
    OsInit = EnumField("os_mongo_init", _("os_mongo_init"))
    mongoDInstall = EnumField("mongod_install", _("mongod_install"))
    mongoSInstall = EnumField("mongos_install", _("mongos_install"))
    InitReplicaset = EnumField("init_replicaset", _("init_replicaset"))
    AddShardToCluster = EnumField("add_shard_to_cluster", _("add_shard_to_cluster"))
    AddUser = EnumField("add_user", _("add_user"))
    DeleteUser = EnumField("delete_user", _("delete_user"))
    MongoExecuteScript = EnumField("mongo_execute_script", _("mongo_execute_script"))
    Backup = EnumField("mongodb_backup", _("mongodb_backup"))
    RemoveNs = EnumField("mongodb_remove_ns", _("mongodb_remove_ns"))
    Restore = EnumField("mongodb_restore", _("mongodb_restore"))
    PitRestore = EnumField("mongodb_pitr_restore", _("mongodb_pitr_restore"))
    MongoRestart = EnumField("mongo_restart", _("mongo_restart"))
    MongoDReplace = EnumField("mongod_replace", _("mongod_replace"))
    MongoDeInstall = EnumField("mongo_deinstall", _("mongo_deinstall"))
    InstallDBMon = EnumField("install_dbmon", _("install_dbmon"))
    MongoStart = EnumField("mongo_start", _("mongo_start"))
    MongoHello = EnumField("mongodb_hello", _("mongodb_hello"))


class EsActuatorActionEnum(str, StructuredEnum):
    Init = EnumField("init", _("init"))
    DecompressPkg = EnumField("decompress_pkg", _("decompress_pkg"))
    InstallSupervisor = EnumField("install_supervisor", _("install_supervisor"))
    InstallMaster = EnumField("install_master", _("install_master"))
    InstallHot = EnumField("install_hot", _("install_hot"))
    InstallCold = EnumField("install_cold", _("install_cold"))
    InstallClient = EnumField("install_client", _("install_client"))
    InitGrant = EnumField("init_grant", _("init_grant"))
    InstallExporter = EnumField("install_exporter", _("install_exporter"))
    InstallKibana = EnumField("install_kibana", _("install_kibana"))
    InstallTelegraf = EnumField("install_telegraf", _("install_telegraf"))
    StartProcess = EnumField("start_process", _("start_process"))
    StopProcess = EnumField("stop_process", _("stop_process"))
    RestartProcess = EnumField("restart_process", _("restart_process"))
    CleanData = EnumField("clean_data", _("clean_data"))
    ExcludeNode = EnumField("exclude_node", _("exclude_node"))
    CheckShards = EnumField("check_shards", _("check_shards"))
    CheckConnections = EnumField("check_connections", _("check_connections"))
    CheckNodes = EnumField("check_nodes", _("check_nodes"))
    ReplaceMaster = EnumField("replace_master", _("replace_master"))
    GenCertificate = EnumField("gen_certificate", _("gen_certificate"))
    PackCertificate = EnumField("pack_certificate", _("pack_certificate"))


class KafkaActuatorActionEnum(str, StructuredEnum):
    initKafka = EnumField("init", _("init"))
    decompressKafkaPkg = EnumField("decompress_pkg", _("decompress_pkg"))
    installKafkaSupervisor = EnumField("install_supervisor", _("install_supervisor"))
    installZookeeper = EnumField("install_zookeeper", _("install_zookeeper"))
    initKafkaUser = EnumField("init_kafkaUser", _("init_kafkaUser"))
    installBroker = EnumField("install_broker", _("install_broker"))
    installManager = EnumField("install_manager", _("install_manager"))
    StartProcess = EnumField("start_process", _("start_process"))
    StopProcess = EnumField("stop_process", _("stop_process"))
    RestartProcess = EnumField("restart_process", _("restart_process"))
    CleanData = EnumField("clean_data", _("clean_data"))
    ReduceBroker = EnumField("reduce_broker", _("reduce_broker"))
    CheckReassign = EnumField("check_reassign", _("check_reassign"))
    ReconfigAdd = EnumField("reconfig_add", _("reconfig_add"))
    RestartBroker = EnumField("restart_broker", _("restart_broker"))
    ReconfigRemove = EnumField("reconfig_remove", _("reconfig_remove"))
    ReplaceBroker = EnumField("replace_broker", _("replace_broker"))


class InfluxdbActuatorActionEnum(str, StructuredEnum):
    init = EnumField("init", _("init"))
    decompressPkg = EnumField("decompress_pkg", _("decompress_pkg"))
    installSupervisor = EnumField("install_supervisor", _("install_supervisor"))
    installInfluxdb = EnumField("install_influxdb", _("install_influxdb"))
    InstallTelegraf = EnumField("install_telegraf", _("install_telegraf"))
    initUser = EnumField("init_user", _("init_user"))
    StartProcess = EnumField("start_process", _("start_process"))
    StopProcess = EnumField("stop_process", _("stop_process"))
    RestartProcess = EnumField("restart_process", _("restart_process"))
    CleanData = EnumField("clean_data", _("clean_data"))


class PulsarActuatorActionEnum(str, StructuredEnum):
    CheckBrokerConfig = EnumField("check_broker_config", _("check_broker_config"))
    CheckNamespaceConfig = EnumField("check_namespace_config", _("check_namespace_config"))
    CheckUnderReplicated = EnumField("check_under_replicated", _("check_under_replicated"))
    CheckLedgerMetadata = EnumField("check_ledger_metadata", _("check_ledger_metadata"))
    SetBookieReadOnly = EnumField("set_bookie_readonly", _("set_bookie_readonly"))
    DecommissionBookie = EnumField("decommission_bookie", _("decommission_bookie"))
    Init = EnumField("init", _("init"))
    DecompressPkg = EnumField("decompress_pkg", _("decompress_pkg"))
    InstallSupervisor = EnumField("install_supervisor", _("install_supervisor"))
    InstallZookeeper = EnumField("install_zookeeper", _("install_zookeeper"))
    InitCluster = EnumField("init_cluster", _("init_cluster"))
    InstallBookKeeper = EnumField("install_bookkeeper", _("install_bookkeeper"))
    InstallBroker = EnumField("install_broker", _("install_broker"))
    InstallManager = EnumField("install_pulsar_manager", _("install_pulsar_manager"))
    InitManager = EnumField("init_pulsar_manager", _("init_pulsar_manager"))
    StartProcess = EnumField("start_process", _("start_process"))
    StopProcess = EnumField("stop_process", _("stop_process"))
    RestartProcess = EnumField("restart_process", _("restart_process"))
    CleanData = EnumField("clean_data", _("clean_data"))
    AddHosts = EnumField("add_hosts", _("add_hosts"))
    ModifyHosts = EnumField("modify_hosts", _("modify_hosts"))


class RiakActuatorActionEnum(str, StructuredEnum):
    SysinitRiak = EnumField("sysinit-riak", _("sysinit-riak"))
    Deploy = EnumField("deploy", _("deploy"))
    GetConfig = EnumField("get-config", _("get-config"))
    JoinCluster = EnumField("join-cluster", _("join-cluster"))
    CommitClusterChange = EnumField("commit-cluster-change", _("commit-cluster-change"))
    InitBucketType = EnumField("init-bucket-type", _("init-bucket-type"))
    RemoveNode = EnumField("remove-node", _("remove-node"))
    Transfer = EnumField("transfer", _("transfer"))
    CheckConnections = EnumField("check-connections", _("check-connections"))
    InstallMonitor = EnumField("install-monitor", _("install-monitor"))
    DeployRiakCrond = EnumField("deploy-riak-crond", _("deploy-riak-crond"))
    ClearCrontab = EnumField("clear-crontab", _("clear-crontab"))
    UnInstall = EnumField("uninstall", _("uninstall"))
    Start = EnumField("start", _("start"))
    Restart = EnumField("restart", _("restart"))
    Stop = EnumField("stop", _("stop"))
    DeployMonitor = EnumField("deploy-monitor", _("deploy-monitor"))
    StartMonitor = EnumField("start-monitor", _("start-monitor"))
    StopMonitor = EnumField("stop-monitor", _("stop-monitor"))


class SqlserverActuatorActionEnum(str, StructuredEnum):
    SysInit = EnumField("sysinit", _("机器初始化"))
    Deploy = EnumField("deploy", _("实例安装"))
    ExecSQLFiles = EnumField("ExecSQLFiles", _("SQL文件执行"))
    BackupDBS = EnumField("BackupDBS", _("备份数据库"))
    RenameDBS = EnumField("RenameDBS", _("备份数据库"))
    CleanDBS = EnumField("CleanDBS", _("数据库清档"))
    RestoreDBSForFull = EnumField("RestoreDBSForFull", _("恢复全量备份文件"))
    RestoreDBSForLog = EnumField("RestoreDBSForLog", _("恢复日志备份文件"))
    RoleSwitch = EnumField("RoleSwitch", _("集群角色互切"))
    CheckAbnormalDB = EnumField("CheckAbnormalDB", _("检查非正常的数据库信息"))
    CheckInstProcess = EnumField("CheckInstProcess", _("检查实例连接情况"))
    CloneLoginUsers = EnumField("CloneLoginUsers", _("实例间克隆用户"))
    CloneJobs = EnumField("CloneJobs", _("实例间克隆定时作业"))
    CloneLinkservers = EnumField("CloneLinkservers", _("实例间克隆linkservers"))
    BuildDBMirroring = EnumField("BuildDBMirroring", _("建立数据库的镜像库关系"))
    InitForAlwaysOn = EnumField("InitForAlwaysOn", _("为Always-on做别名初始化"))
    BuildAlwaysOn = EnumField("BuildAlwaysOn", _("建立Always-on通信"))
    AddDBSInAlwaysOn = EnumField("AddDBSInAlwaysOn", _("数据库加入到Always-on可用组"))
    Uninstall = EnumField("Uninstall", _("卸载sqlserver实例"))
    MoveBackupFile = EnumField("MoveBackupFile", _("判断备份文件是否存在，存在则移动"))
    InitSqlserverInstance = EnumField("InitSqlserverInstance", _("实例接入dbm系统初始化"))
    ClearConfig = EnumField("ClearConfig", _("清理实例周边配置。目前支持清理job、linkserver"))
    RemoteDr = EnumField("RemoteDr", _("将一些dr移除可用组"))
    Init = EnumField("init", _("部署后需要初始化实例的步骤"))


class DorisActuatorActionEnum(str, StructuredEnum):
    Init = EnumField("init", _("init"))
    DecompressPkg = EnumField("decompress_pkg", _("decompress_pkg"))
    InstallSupervisor = EnumField("install_supervisor", _("install_supervisor"))
    InstallDoris = EnumField("install_doris", _("install_doris"))
    RenderConfig = EnumField("render_config", _("render_config"))
    InitGrant = EnumField("init_grant", _("init_grant"))
    StartProcess = EnumField("start_process", _("start_process"))
    StartFeByHelper = EnumField("start_fe_by_helper", _("start_fe_by_helper"))
    StopProcess = EnumField("stop_process", _("stop_process"))
    RestartProcess = EnumField("restart_process", _("restart_process"))
    CleanData = EnumField("clean_data", _("clean_data"))
    UpdateMetadata = EnumField("update_metadata", _("update_metadata"))
    CheckDecommission = EnumField("check_decommission", _("check_decommission"))
    CheckProcessStart = EnumField("check_process_start", _("check_process_start"))


class RiakModuleId(int, StructuredEnum):
    """
    Riak模块id
    """

    mhs = EnumField(0, _("聊天历史记录"))
    legs = EnumField(1, _("用户战绩数据"))
    pp = EnumField(2, _("玩家按键快捷键信息"))
    test = EnumField(3, _("test"))
    mixed = EnumField(4, _("mixed"))


class JobStatusEnum(int, StructuredEnum):
    NOT_RUNNING = EnumField(1, _("NOT_RUNNING"))
    RUNNING = EnumField(2, _("RUNNING"))
    SUCCESS = EnumField(3, _("SUCCESS"))
    FAILED = EnumField(4, _("FAILED"))
    SKIPPED = EnumField(5, _("SKIPPED"))
    IGNORED = EnumField(6, _("IGNORED"))
    WAITING = EnumField(7, _("WAITING"))
    NORMAL = EnumField(8, _("NORMAL"))
    ABNORMAL = EnumField(9, _("ABNORMAL"))
    ForciblyTerminating = EnumField(10, _("步骤强制终止中"))
    ForciblyTerminatedSucceeded = EnumField(11, _("步骤强制终止成功"))


class PipelineStatus(str, StructuredEnum):
    READY = EnumField("READY", _("准备中"))
    RUNNING = EnumField("RUNNING", _("运行中"))
    FINISHED = EnumField("FINISHED", _("完成"))
    FAILED = EnumField("FAILED", _("失败"))


class InstanceStatus(str, StructuredEnum):
    RUNNING = EnumField("running", _("running"))
    AVAILABLE = EnumField("available", _("available"))
    UNAVAILABLE = EnumField("unavailable", _("unavailable"))
    LOCKED = EnumField("locked", _("locked"))


class ClusterStatus(str, StructuredEnum):
    REDIS_CLUSTER_NO = EnumField("no", _("cluster no"))
    REDIS_CLUSTER_YES = EnumField("yes", _("cluster yes"))


class DnsOpType(str, StructuredEnum):
    CREATE = EnumField("create", _("create"))
    CLUSTER_DELETE = EnumField("cluster_delete", _("cluster_delete"))
    RECYCLE_RECORD = EnumField("recycle_record", _("recycle_record"))
    UPDATE = EnumField("update", _("update"))
    SELECT = EnumField("select", _("select"))
    ADD_AND_DELETE = EnumField("add_and_delete", _("add_and_delete"))
    IP_DNS_RECORD_RECYCLE = EnumField("ip_dns_recycle_record", _("ip_dns对应记录回收"))


class ManagerOpType(str, StructuredEnum):
    CREATE = EnumField("create", _("create"))
    UPDATE = EnumField("update", _("update"))
    DELETE = EnumField("delete", _("delete"))


class ManagerServiceType(str, StructuredEnum):
    KIBANA = EnumField("kibana", _("kibana"))
    KAFKA_MANAGER = EnumField("kafka_manager", _("kafka_manager"))
    PULSAR_MANAGER = EnumField("pulsar_manager", _("pulsar_manager"))
    HA_PROXY = EnumField("ha_proxy", _("ha_proxy"))
    DORIS_WEB_UI = EnumField("doris_web_ui", _("doris_web_ui"))


class ManagerDefaultPort(int, StructuredEnum):
    KIBANA = EnumField(5601, _("KIBANA_PORT"))
    KAFKA_MANAGER = EnumField(9000, _("KAFKA_MANAGER_PORT"))


class AuthorizeStatus(int, StructuredEnum):
    RUNNING = EnumField(1, _("RUNNING"))
    SUCCESS = EnumField(0, _("SUCCESS"))
    FAILED = EnumField(2, _("FAILED"))


class DBConstNumEnum(int, StructuredEnum):
    PROXY_DEFAULT_NUM = EnumField(3, _("proxy默认实例个数"))
    REDIS_ROLE_NUM = EnumField(2, _("redis角色数"))


class ConfigDefaultEnum(list, StructuredEnum):
    DATA_DIRS = EnumField(["/data", "/data1"], _("DB安装目录"))


class DirEnum(str, StructuredEnum):
    GSE_DIR = EnumField("/usr/local/gse_bkte", _("gcs 安装路径"))
    REDIS_KEY_LIFE_DIR = EnumField("/data/dbbak/keylifecycle", _("key生命周期路径"))
    MONGO_RECOVER_DIR = EnumField("/data/dbbak/recover_mg", _("mongo恢复路径"))


class TruncateDataTypeEnum(str, StructuredEnum):
    TRUNCATE_TABLE = EnumField("truncate_table", _("truncate_table"))
    DROP_DATABASE = EnumField("drop_database", _("drop_database"))
    DROP_TABLE = EnumField("drop_table", _("drop_table"))


INFODBA_SCHEMA = "infodba_schema"
SYSTEM_DBS = ["mysql", "test", "db_infobase", "information_schema", "performance_schema", "sys", INFODBA_SCHEMA]
STAGE_DB_HEADER = "stage_truncate"
ROLLBACK_DB_TAIL = "rollback"

# 定义数据检验的常量
CHECKSUM_DB = "infodba_schema"
CHECKSUM_TABlE_PREFIX = "checksum_"

# 定义单据生成随机账号的前缀
ACCOUNT_PREFIX = "_temp_"

# sqlserver系统账号列表
SQLSERVER_SYSTEM_DBS = ["master", "msdb", "model", "tempdb", "Monitor"]

# sqlserver自定义系统库名
SQLSERVER_CUSTOM_SYS_DB = "Monitor"

# sqlserver的exporter账号名称
MSSQL_EXPORTER = "mssql_exporter"

# sqlserver的DBHA账号名称
MSSQL_DBHA = "mssql_dbha"

# sqlserver的DRS账号名称
MSSQL_DRS = "mssql_drs"

# sqlserver的用户登录admin账号名称
MSSQL_ADMIN = SQLSERVER_ADMIN_USER

# sqlserver自定义系统账号列表
SQLSERVER_CUSTOM_SYS_USER = [MSSQL_EXPORTER, MSSQL_ADMIN, MSSQL_DBHA, MSSQL_DRS, "sa"]

# window系统job账号
WINDOW_SYSTEM_JOB_USER = "system"

# tbinlogdumper连接kafka的global config的定义
TBINLOGDUMPER_KAFKA_GLOBAL_CONF = {
    "sasl.mechanisms": "SCRAM-SHA-512",
    "security.protocol": "SASL_PLAINTEXT",
    "sasl.username": "",
    "sasl.password": "",
    "queue.buffering.max.messages": "5000",
    "message.max.bytes": "10000000",
    "broker.version.fallback": "2.0.0",
}

# tbinlogdumper连接kafka的global config的定义
TBINLOGDUMPER_KAFKA_TOPIC_CONF = {"message.timeout.ms": "100000"}


class DBRoleEnum(str, StructuredEnum):
    Proxy = EnumField("proxy", _("proxy"))
    Master = EnumField("master", _("master"))
    Slave = EnumField("slave", _("slave"))


class LevelInfoEnum(str, StructuredEnum):
    TendataModuleDefault = EnumField("0", _("TendataModuleDefault"))
    RiakModuleDefault = EnumField("0", _("RiakModuleDefault"))


class ESRoleEnum(str, StructuredEnum):
    HOT = EnumField("hot", _("hot"))
    COLD = EnumField("cold", _("cold"))
    CLIENT = EnumField("client", _("client"))
    MASTER = EnumField("master", _("master"))


class OperateTypeEnum(str, StructuredEnum):
    DELETE_KEY_REGEX = EnumField("regex", _("redis key删除正则方式"))
    DELETE_KEY_FILES = EnumField("files", _("redis key删除文件方式"))


class SemanticInsOpType(str, StructuredEnum):
    GET = EnumField("get", _("get"))
    RELEASE = EnumField("release", _("release"))


class WriteContextOpType(str, StructuredEnum):
    REWRITE = EnumField("rewrite", _("覆盖写入上下文变量"))
    APPEND = EnumField("append", _("追加写入上下文变量"))


class HdfsDBActuatorActionEnum(str, StructuredEnum):
    InstallSupervisor = EnumField("install-supervisor", _("install-supervisor"))
    RenderConfig = EnumField("render-config", _("render-config"))
    InitSystemConfig = EnumField("init", _("init"))
    DecompressPackage = EnumField("decompress_pkg", _("decompress_pkg"))
    InstallZooKeeper = EnumField("install-zookeeper", _("install-zookeeper"))
    InstallJournalNode = EnumField("install-journalnode", _("install-journalnode"))
    InstallNn1 = EnumField("install-nn1", _("install-nn1"))
    InstallNn2 = EnumField("install-nn2", _("install-nn2"))
    InstallDataNode = EnumField("install-dn", _("install-dn"))
    InstallZKFC = EnumField("install-zkfc", _("install-zkfc"))
    InstallTelegraf = EnumField("install-telegraf", _("install-telegraf"))
    InstallHaproxy = EnumField("install-haproxy", _("install-haproxy"))
    UpdateHostMapping = EnumField("update-hosts", _("update-hosts"))
    StopProcess = EnumField("stop-process", _("stop-process"))
    StartStopComponent = EnumField("start-component", _("start-component"))
    CleanData = EnumField("clean-data", _("clean-data"))
    UpdateDfsHost = EnumField("dfs-host", _("dfs-host"))
    RefreshNodes = EnumField("refresh-nodes", "refresh-nodes")
    CheckDecommission = EnumField("check-decommission", "check-decommission")
    GenerateKey = EnumField("generate-key", "generate-key")
    WriteKey = EnumField("write-key", "write-key")
    RemoteCopyDir = EnumField("scp-dir", "scp-dir")
    CheckActive = EnumField("check-active", "check-active")
    UpdateZooKeeperConfig = EnumField("update-zk-conf", "update-zk-conf")


class HdfsRoleEnum(str, StructuredEnum):
    NameNode = EnumField("namenode", _("namenode"))
    DataNode = EnumField("datanode", _("datanode"))
    JournalNode = EnumField("journalnode", _("journalnode"))
    ZooKeeper = EnumField("zookeeper", _("zookeeper"))
    ZKFailController = EnumField("zkfc", _("zkfc"))


class PulsarRoleEnum(str, StructuredEnum):
    BookKeeper = EnumField("bookkeeper", _("bookkeeper"))
    Broker = EnumField("broker", _("broker"))
    ZooKeeper = EnumField("zookeeper", _("zookeeper"))
    # All = EnumField("all", _("all"))


class RedisBackupEnum(str, StructuredEnum):
    NORMAL_BACKUP = EnumField("normal_backup", _("常规备份"))
    FOREVER_BACKUP = EnumField("forever_backup", _("长期备份"))


class KafkaFlowEnum(str, StructuredEnum):
    KAFKA_REPLACE = EnumField("KAFKA_REPLACE", _("KAFKA_REPLACE"))
    KAFKA_SCALE_UP = EnumField("KAFKA_SCALE_UP", _("KAFKA_SCALE_UP"))


class InfluxdbFlowEnum(str, StructuredEnum):
    INFLUXDB_REPLACE = EnumField("INFLUXDB_REPLACE", _("INFLUXDB_REPLACE"))


class MySQLBackupTypeEnum(str, StructuredEnum):
    LOGICAL = EnumField("logical", _("逻辑备份"))
    PHYSICAL = EnumField("physical", _("物理备份"))


# 定义根据mysql大版本获取对应的db-backup-pkg-type
MysqlVersionToDBBackupForMap = {
    "MySQL-5.5": MediumEnum.DbBackupTXSQL if env.MYSQL_BACKUP_PKG_MAP_ENABLE else MediumEnum.DbBackup,
    "MySQL-5.6": MediumEnum.DbBackupTXSQL if env.MYSQL_BACKUP_PKG_MAP_ENABLE else MediumEnum.DbBackup,
    "MySQL-5.7": MediumEnum.DbBackupTXSQL if env.MYSQL_BACKUP_PKG_MAP_ENABLE else MediumEnum.DbBackup,
    "MySQL-8.0": MediumEnum.DbBackup,
    "TXSQL-8.0": MediumEnum.DbBackupTXSQL if env.MYSQL_BACKUP_PKG_MAP_ENABLE else MediumEnum.DbBackup,
    "MySQL-5.7-community": MediumEnum.DbBackup,
    "Spider-1": MediumEnum.DbBackup,
    "Spider-3": MediumEnum.DbBackup,
}


class MySQLBackupFileTagEnum(str, StructuredEnum):
    DBFILE1M = EnumField("DBFILE1M", _("备份1个月"))
    DBFILE6M = EnumField("DBFILE6M", _("备份6个月"))
    DBFILE1Y = EnumField("DBFILE1Y", _("备份1年"))
    DBFILE3Y = EnumField("DBFILE3Y", _("备份3年"))


class MongoDBBackupFileTagEnum(str, StructuredEnum):
    NORMAL_BACKUP = EnumField("normal_backup", _("常规备份(25天)"))
    HALF_YEAR_BACKUP = EnumField("half_year_backup", _("6个月"))
    A_YEAR_BACKUP = EnumField("a_year_backup", _("1年"))
    FOREVER_BACKUP = EnumField("forever_backup", _("长期备份(3年)"))


class InstanceFuncAliasEnum(str, StructuredEnum):
    """
    定义实例对应的进程别名，用于注册服务实例
    """

    MYSQL_FUNC_ALIAS = EnumField("mysql", _("Mysql的进程名称"))
    MYSQL_PROXY_FUNC_ALIAS = EnumField("mysql-proxy", _("Mysql-proxy进程名称"))
    REDIS_FUNC_ALIAS = EnumField("redis", _("Redis的进程名称"))
    MONGODB_FUNC_ALIAS = EnumField("mongodb", _("MONGODB的进程名称"))
    ES_FUNC_ALIAS = EnumField("java", _("ES的进程名称"))
    KAFKA_FUNC_ALIAS = EnumField("java", _("KAFKA的进程名称"))
    HDFS_NAME_NODE_FUNC_ALIAS = EnumField("java", _("HDFS-NameNode的进程名称"))
    HDFS_DATA_NODE_FUNC_ALIAS = EnumField("java", _("HDFS-DataNode的进程名称"))
    PULSAR_FUNC_ALIAS = EnumField("java", _("Pulsar的进程名称"))
    INFLUXDB_FUNC_ALIAS = EnumField("telegraf", _("InfluxDB 的进程名称"))
    RIAK_FUNC_ALIAS = EnumField("riak", _("Riak的进程名称"))


class RollbackType(str, StructuredEnum):
    """
    回滚类型
    """

    REMOTE_AND_TIME = EnumField("REMOTE_AND_TIME", _("远程备份+时间"))
    REMOTE_AND_BACKUPID = EnumField("REMOTE_AND_BACKUPID", _("远程备份+备份ID"))
    LOCAL_AND_TIME = EnumField("LOCAL_AND_TIME", _("本地备份+时间"))
    LOCAL_AND_BACKUPID = EnumField("LOCAL_AND_BACKUPID", _("本地备份+备份ID"))


class DataSyncSource(str, StructuredEnum):
    """
    定义触发数据修复单据来源
    """

    MANUAL = EnumField("manual", _("手动单据发起"))
    ROUTINE = EnumField("routine", _("例行校验单据发起"))


class SyncType(str, StructuredEnum):
    """数据同步类型"""

    SYNC_MS = EnumField("ms", _("ms"))
    SYNC_MMS = EnumField("mms", _("mms"))
    SYNC_SMS = EnumField("msms", _("msms"))


class SwitchType(str, StructuredEnum):
    """
    切换时是否需要,用户确认
    """

    SWITCH_WITH_CONFIRM = "user_confirm"
    SWITCH_WITHOUT_CONFIRM = "no_confirm"


class RedisSlotSep(str, StructuredEnum):
    """
    redis slot分隔符
    """

    SLOT_SEPARATOR = EnumField("-", _("redis slot分隔符"))
    IMPORTING_SEPARATOR = EnumField("-<-", _("redis slot导入分隔符"))
    MIGRATING_SEPARATOR = EnumField("->-", _("redis slot迁移分隔符"))


class RedisSlotNum(int, StructuredEnum):
    """
    redis slot数量
    """

    MIN_SLOT = EnumField(0, _("redis min slot"))
    MAX_SLOT = EnumField(16383, _("redis max slot"))
    TOTAL_SLOT = EnumField(16384, _("redis total slot"))


class ClusterNodeFailStatus(str, StructuredEnum):
    """
    redis节点状态
    """

    PFAIL = EnumField("fail?", _("redis PFAIL state"))
    FAIL = EnumField("fail", _("redis fail state"))
    HANDSHAKE = EnumField("handshake", _("redis handshake state"))
    NOADDR = EnumField("noaddr", _("redis noaddr state"))
    NOFLAGS = EnumField("noflags", _("redis noflags state"))


class RedisRole(str, StructuredEnum):
    """
    redis节点角色
    """

    MASTER = EnumField("master", _("redis master role"))
    SLAVE = EnumField("slave", _("redis slave role"))
    UNKNOWN = EnumField("unknown", _("redis unknown role"))


class RedisLinkStatus(str, StructuredEnum):
    """
    redis节点连接状态
    """

    MASTER_LINK_STATUS_UP = EnumField("up", _("redis master link status up"))
    MASTER_LINK_STATUS_DOWN = EnumField("down", _("redis master link status down"))
    TENDISSSD_INCR_SYNC = EnumField("IncrSync", _("redis ssd incrSync state"))
    TENDISSSD_REPL_FOLLOW = EnumField("REPL_FOLLOW", _("redis ssd REPL_FOLLOW state"))
    CONNECTED = EnumField("connected", _("redis connected status"))
    DISCONNECTED = EnumField("disconnected", _("redis disconnected status"))


class RedisClusterState(str, StructuredEnum):
    """
    redis集群状态
    """

    OK = EnumField("ok", _("redis cluster state ok,all slots are covered. 通过 cluster info 命令获取"))
    FAIL = EnumField("fail", _("redis cluster state fail,not all slots are covered.通过 cluster info 命令获取"))


class RedisCapacityUpdateType(str, StructuredEnum):
    """
    redis容量变更类型
    """

    KEEP_CURRENT_MACHINES = EnumField("keep_current_machines", _("原地变更"))
    ALL_MACHINES_REPLACE = EnumField("all_machines_replace", _("全部机器替换"))


class RedisMaxmemoryConfigType(str, StructuredEnum):
    """
    redis maxmemory配置类型
    """

    BK_BIZ_ID_BLACKLIST = EnumField("bk_biz_id_blacklist", _("bk_biz_id黑名单"))
    CLUSTER_ID_BLACKLIST = EnumField("cluster_id_blacklist", _("cluster_id黑名单"))
    USED_MEMORY_CHANGE_THRESHOLD = EnumField("used_memory_change_threshold", _("used_memory变更阈值"))
    USED_MEMORY_CHANGE_PERCENT = EnumField("used_memory_change_percent", _("used_memory变更百分比"))


class KafkaRoleEnum(str, StructuredEnum):
    ZOOKEEPER = EnumField("zookeeper", _("zookeeper"))
    BROKER = EnumField("broker", _("broker"))


class PrivRole(str, StructuredEnum):
    """
    定义授权实例角色
    """

    SPIDER = EnumField("spider", _("spider"))
    TDBCTL = EnumField("tdbctl", _("tdbctl"))
    MYSQL = EnumField("mysql", _("mysql"))


class MysqlChangeMasterType(str, StructuredEnum):
    MASTERSTATUS = EnumField("MasterStatus", _("from show master status"))
    BACKUPFILE = EnumField("BackFile", _("from backup file"))


class TenDBBackUpLocation(str, StructuredEnum):
    """
    TendbCluster的库表备份位置
    """

    REMOTE = EnumField("remote", _("remote"))
    SPIDER_MNT = EnumField("spider_mnt", _("spider_mnt"))


class TBinlogDumperAddType(str, StructuredEnum):
    """
    TBinlogDumper添加类型
    """

    FULL_SYNC = EnumField("full_sync", _("全量同步"))
    INCR_SYNC = EnumField("incr_sync", _("增量同步"))


class DorisRoleEnum(str, StructuredEnum):
    HOT = EnumField("hot", _("hot"))
    COLD = EnumField("cold", _("cold"))
    FOLLOWER = EnumField("follower", _("follower"))
    OBSERVER = EnumField("observer", _("observer"))


# 定义根据不同的MachineType获取对应的PrivRole
MachinePrivRoleMap = {
    MachineType.REMOTE: PrivRole.MYSQL.value,
    MachineType.BACKEND: PrivRole.MYSQL.value,
    MachineType.SINGLE: PrivRole.MYSQL.value,
    MachineType.SPIDER: PrivRole.SPIDER.value,
}


class UserName(str, StructuredEnum):
    """
    定义密码服务的用户名称
    """

    ADMIN = EnumField("ADMIN", _("root实例账号"))
    BACKUP = EnumField("dba_bak_all_sel", _("备份实例账号"))
    MONITOR = EnumField("MONITOR", _("监控实例账号"))
    MONITOR_ACCESS_ALL = EnumField("MONITOR_ALL", _("监控实例账号"))
    OS_MYSQL = EnumField("mysql", _("MYSQL系统账号"))
    REPL = EnumField("repl", _("MYSQL实例同步账号"))
    YW = EnumField("yw", _("MYSQL实例只读账号"))
    PROXY = EnumField("proxy", _("PROXY实例账号"))
    REDIS_DEFAULT = EnumField("default", _("REDIS默认账号"))
    HDFS_DEFAULT = EnumField("root", _("HDFS默认账号"))
    PARTITION_YW = EnumField("partition_yw", _("分区实例账号"))


class MySQLPrivComponent(str, StructuredEnum):
    """
    定义密码服务的用户component类型
    """

    MYSQL = EnumField("mysql", _("mysql"))
    PROXY = EnumField("proxy", _("proxy"))
    TBINLOGDUMPER = EnumField("tbinlogdumper", _("tbinlogdumper"))
    REDIS = EnumField("redis", _("redis"))
    REDIS_PROXY = EnumField("redis_proxy", _("redis_proxy"))
    REDIS_PROXY_ADMIN = EnumField("redis_proxy_admin", _("redis_proxy_admin"))
    ES_FAKE_USER = EnumField("es_user", _("es_user"))
    KAFKA_FAKE_USER = EnumField("kafka_user", _("kafka_user"))
    INFLUXDB_FAKE_USER = EnumField("influxdb_user", _("influxdb_user"))
    HDFS_FAKE_USER = EnumField("hdfs_user", _("hdfs_user"))
    PULSAR_FAKE_USER = EnumField("pulsar_user", _("pulsar_user"))
    DORIS_FAKE_USER = EnumField("doris_user", _("doris_user"))
    VM_FAKE_USER = EnumField("vm_user", _("vm_user"))


class RequestResultCode(int, StructuredEnum):
    """
    请求结果code状态
    """

    Success = EnumField(0, _("success"))


class MongoDBPasswordRule(str, StructuredEnum):
    """
    mongodb密码规则名
    """

    RULE = EnumField("mongodb_password", _("MongoDB密码规则"))


class MongoDBClusterRole(str, StructuredEnum):
    """
    mongodb cluster role
    """

    ConfigSvr = EnumField("configsvr", _("configsvr"))
    ShardSvr = EnumField("shardsvr", _("shardsvr"))
    Mongos = EnumField("mongos", _("mongos"))
    Replicaset = EnumField("replicaset", _("replicaset"))


class MongoDBTotalCache(float, StructuredEnum):
    """
    cache占机器内存的百分比
    """

    Cache_Percent = EnumField(0.65, _("cache_percent"))


class MongoDBDomainPrefix(str, StructuredEnum):
    """
    mongodb domain Prefix
    """

    MONGOS = EnumField("mongos", _("mongos"))
    M1 = EnumField("m1", _("m1"))
    M2 = EnumField("m2", _("m2"))
    M3 = EnumField("m3", _("m3"))
    M4 = EnumField("m4", _("m4"))
    M5 = EnumField("m5", _("m5"))
    M6 = EnumField("m6", _("m6"))
    M7 = EnumField("m7", _("m7"))
    M8 = EnumField("m8", _("m8"))
    M9 = EnumField("m9", _("m9"))
    M10 = EnumField("m10", _("m10"))
    BACKUP = EnumField("backup", _("backup"))


class TBinlogDumperProtocolType(str, StructuredEnum):
    """
    定义tbinlogdumper的对端协议
    """

    KAFKA = EnumField("KAFKA", _("KAFKA"))
    L5_AGENT = EnumField("L5_AGENT", _("L5_AGENT"))
    TCP_IP = EnumField("TCP/IP", _("TCP/IP"))


class SqlserverUserName(str, StructuredEnum):
    """
    定义Sqlserver密码服务的用户名称
    """

    MSSQL = EnumField("mssql", _("mssql系统账号"))
    SQLSERVER = EnumField("sqlserver", _("sqlserver系统账号，进程启动"))
    SA = EnumField("sa", _("sa实例账号"))


class SqlserverComponent(str, StructuredEnum):
    """
    定义sqlserver的密码component
    """

    SQLSERVER = EnumField("sqlserver", _("sqlserver"))


class SqlserverSysVersion(str, StructuredEnum):
    """
    定义Sqlserver支持操作系统版本名称
    """

    Windows_Server_2008 = EnumField("WindowsServer2008", _("2008服务器版"))
    Windows_Server_2012 = EnumField("WindowsServer2012", _("2012服务器版"))
    Windows_Server_2016 = EnumField("WindowsServer2016", _("2016服务器版"))
    Windows_Server_2019 = EnumField("WindowsServer2019", _("2019服务器版"))
    Windows_Server_2022 = EnumField("WindowsServer2022", _("2022服务器版"))


# mssql各版本的操作系统版本支持
MssqlSystemVersionSupportMap = {
    SqlserverVersion.MSSQL_Enterprise_2022: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
    ],
    SqlserverVersion.MSSQL_Enterprise_2019: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
    ],
    SqlserverVersion.MSSQL_Enterprise_2017: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
        SqlserverSysVersion.Windows_Server_2012,
    ],
    SqlserverVersion.MSSQL_Enterprise_2016: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
        SqlserverSysVersion.Windows_Server_2012,
    ],
    SqlserverVersion.MSSQL_Enterprise_2014: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
        SqlserverSysVersion.Windows_Server_2012,
        SqlserverSysVersion.Windows_Server_2008,
    ],
    SqlserverVersion.MSSQL_Enterprise_2012: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
        SqlserverSysVersion.Windows_Server_2012,
        SqlserverSysVersion.Windows_Server_2008,
    ],
    SqlserverVersion.MSSQL_Enterprise_2008: [
        SqlserverSysVersion.Windows_Server_2022,
        SqlserverSysVersion.Windows_Server_2019,
        SqlserverSysVersion.Windows_Server_2016,
        SqlserverSysVersion.Windows_Server_2012,
        SqlserverSysVersion.Windows_Server_2008,
    ],
}


class SqlserverCharSet(str, StructuredEnum):
    """
    目前支持的Sqlserver的字符集
    """

    Chinese_PRC_CI_AS = EnumField("Chinese_PRC_CI_AS", _("Chinese_PRC_CI_AS"))
    Latin1_General_100_CI_AS = EnumField("Latin1_General_100_CI_AS", _("Latin1_General_100_CI_AS"))
    GBK_CharSet = EnumField("GBK", _("GBK"))


# sqlserver sqlcmd 文件输入格式编码对应的编号
SQlCmdFileFormatNOMap = {"GBK": 936}


class SqlserverSyncMode(str, StructuredEnum):
    """
    定义Sqlserver 数据库同步模式
    """

    MIRRORING = EnumField("mirroring", _("镜像同步"))
    ALWAYS_ON = EnumField("always_on", _("Always_on同步"))


# 各个同步模式定义的编号
SqlserverSyncModeMaps = {
    SqlserverSyncMode.MIRRORING: 1,
    SqlserverSyncMode.ALWAYS_ON: 2,
}

# 无同步模式的编号
NoSync = 3


class SqlserverCleanMode(str, StructuredEnum):
    """
    Sqlserver清档模式
    """

    CLEAN_TABLES = EnumField("clean_tables", _("清理表数据"))
    DROP_TABLES = EnumField("drop_tables", _("删除表"))
    DROP_DBS = EnumField("drop_dbs", _("删除库"))


class SqlserverBackupMode(str, StructuredEnum):
    """
    Sqlserver备份触发模式
    """

    FULL_BACKUP = EnumField("full_backup", _("全量备份"))
    LOG_BACKUP = EnumField("log_backup", _("增量备份"))


class SqlserverBackupJobExecMode(str, StructuredEnum):
    """
    Sqlserver例行备份操作方式
    """

    ENABLE = EnumField(1, _("启动"))
    DISABLE = EnumField(0, _("关闭"))


class SqlserverRestoreMode(str, StructuredEnum):
    """
    Sqlserver 恢复类型
    """

    FULL = EnumField("D", _("选择全量备份恢复"))
    LOG = EnumField("L", _("选择日志备份恢复"))


class SqlserverLoginExecMode(str, StructuredEnum):
    """
    Sqlserver账号操作方式
    """

    ENABLE = EnumField("enable", _("启动"))
    DISABLE = EnumField("disable", _("关闭"))
    DROP = EnumField("drop", _("删除"))


class SqlserverDtsMode(str, StructuredEnum):
    """
    Sqlserver数据迁移模式
    """

    FULL = EnumField("full", _("完整备份迁移(一次性)"))
    INCR = EnumField("incr", _("增量备份迁移(持续的)"))


class SqlserverRestoreDBStatus(str, StructuredEnum):
    """
    Sqlserver 执行恢复后db的状态
    """

    NORECOVERY = EnumField("NORECOVERY", "NORECOVERY")
    RECOVERY = EnumField("RECOVERY", "RECOVERY")


class MongoDBClusterDefaultPort(int, StructuredEnum):
    """mongodb cluster默认端口"""

    CONFIG_PORT = EnumField(28021, _("config_port"))
    SHARD_START_PORT = EnumField(27001, _("shard_start_port"))


class MongoDBManagerUser(str, StructuredEnum):
    """mongodb 管理用户"""

    DbaUser = EnumField("dba", _("dba"))
    AppDbaUser = EnumField("appdba", _("appdba"))
    MonitorUser = EnumField("monitor", _("monitor"))
    AppMonitorUser = EnumField("appmonitor", _("appmonitor"))


class MongoDBUserPrivileges(str, StructuredEnum):
    """mongodb 用户权限"""

    RootRole = EnumField("root", _("root"))
    BackupRole = EnumField("backup", _("backup"))
    ClusterMonitorRole = EnumField("clusterMonitor", _("clusterMonitor"))
    ReadAnyDatabaseRole = EnumField("readAnyDatabase", _("readAnyDatabase"))
    HostManagerRole = EnumField("hostManager", _("hostManager"))
    ReadWriteRole = EnumField("readWrite", _("readWrite"))
    UserAdminAnyDatabaseRole = EnumField("userAdminAnyDatabase", _("userAdminAnyDatabase"))
    DbAdminAnyDatabaseRole = EnumField("dbAdminAnyDatabase", _("dbAdminAnyDatabase"))
    ReadWriteAnyDatabaseRole = EnumField("readWriteAnyDatabase", _("readWriteAnyDatabase"))
    ClusterAdminRole = EnumField("clusterAdmin", _("clusterAdmin"))


class MongoDBTask(str, StructuredEnum):
    """mongodb 任务"""

    MongoDBInitSet = EnumField("mongodb_init_set", _("mongodb_init_set"))
    MongoDBExtraUserCreate = EnumField("mongodb_extra_user_create", _("mongodb_extra_user_create"))


class MongoDBInstanceType(str, StructuredEnum):
    """mongodb 实例类型"""

    MongoD = EnumField("mongod", _("mongod"))
    MongoS = EnumField("mongos", _("mongos"))


class MongoDBDefaultAuthDB(str, StructuredEnum):
    """mongodb 默认验证db"""

    AuthDB = EnumField("admin", _("admin"))


class MongoDBShardType(str, StructuredEnum):
    """mongodb shard类型"""

    MongoShardSvr = EnumField("shardsvr", _("shardsvr"))
    MongoConfigSvr = EnumField("configsvr", _("configsvr"))


class MongoDBDropType(str, StructuredEnum):
    """
    定义mongodb清档的删除方式
    """

    DROP_COLLECTION = EnumField("drop_collection", _("直接删除表"))
    RENAME_COLLECTION = EnumField("rename_collection", _("将表暂时重命名"))


class MongoShardedClusterBackupType(str, StructuredEnum):
    """
    定义mongodb分片集群备份方式
    """

    MONGOS = EnumField("mongos", _("mongos"))
    SHARD = EnumField("shard", _("shard"))


class MongoOplogSizePercent(float, StructuredEnum):
    """
    oplog默认占机器磁盘的百分比
    """

    Oplog_Percent = EnumField(0.15, _("cache_percent"))


class SqlserverBackupFileTagEnum(str, StructuredEnum):
    DBFILE1M = EnumField("DBFILE1M", _("全备-保留1个月"))
    DBFILE6M = EnumField("DBFILE6M", _("全备-保留6个月"))
    DBFILE1Y = EnumField("DBFILE1Y", _("全备-保留1年"))
    DBFILE3Y = EnumField("DBFILE3Y", _("全备-保留3年"))
    INCREMENT_BACKUP = EnumField("INCREMENT_BACKUP", _("增量备份-保留15天"))


class VmActuatorActionEnum(str, StructuredEnum):
    """
    定义vm dbactuator
    """

    Init = EnumField("init", _("init"))
    DecompressPkg = EnumField("decompress_pkg", _("decompress_pkg"))
    InstallSupervisor = EnumField("install_supervisor", _("install_supervisor"))
    InstallVmStorage = EnumField("install_vmstorage", _("install_vmstorage"))
    InstallVmInsert = EnumField("install_vminsert", _("install_vminsert"))
    InstallVmSelect = EnumField("install_vmselect", _("install_vmselect"))
    InstallVmAuth = EnumField("install_vmauth", _("install_vmauth"))
    StartProcess = EnumField("start_process", _("start_process"))
    StopProcess = EnumField("stop_process", _("stop_process"))
    RestartProcess = EnumField("restart_process", _("restart_process"))
    CleanData = EnumField("clean_data", _("clean_data"))
    ReloadVmSelect = EnumField("reload_vmselect", _("reload_vmselect"))
    ReloadVmInsert = EnumField("reload_vminsert", _("reload_vminsert"))


class VmRoleEnum(str, StructuredEnum):
    """
    定义vm角色
    """

    VMAUTH = EnumField("vmauth", _("vmauth"))
    VMINSERT = EnumField("vminsert", _("vminsert"))
    VMSELECT = EnumField("vmselect", _("vmselect"))
    VMSTORAGE = EnumField("vmstorage", _("vmstorage"))
