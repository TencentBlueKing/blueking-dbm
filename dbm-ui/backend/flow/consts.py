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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

GenerateAndPublish = "GenerateAndPublish"
HOST = "host"
MASTER_HOST = "master_host"
REPL_HOST = "repl_host"
BACKEND_HOST = "backend_host"

# 默认DB moudle id
DEFAULT_DB_MODULE_ID = 0
DEFAULT_CONFIG_CONFIRM = 0

# 默认 ip
DEFAULT_IP = "127.0.0.1"

# zookeeper配置文件模板
ZK_CONF = "server.{i}={zk_ip}:2888:3888;2181"
ZK_PORT = ":2888:3888;2181"

DEFAULT_FACTOR = 3

# 默认Redis起始端口
DEFAULT_REDIS_START_PORT = 30000
# 切换时， 默认允许多久心跳
DEFAULT_MASTER_DIFF_TIME = 61
# 切换时， 允许多少秒丢失
DEFAULT_LAST_IO_SECOND_AGO = 100

# tendisplus默认kvstorecount
DEFAULT_TENDISPLUS_KVSTORECOUNT = 10

# 定义每个TenDB-Cluster集群最大spider-master/mnt角色的节点数量（暂定）
MAX_SPIDER_MASTER_COUNT = 37

# 定义每个TenDB-Cluster集群中每个node的内置账号名称
TDBCTL_USER = "tdbctl"

# 数据量大小单位
BYTE = 1
KB = 1 << 10
MB = 1 << 20
GB = 1 << 30
TB = 1 << 40
PB = 1 << 50

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
    "twemproxy_mon",
]

# twemproxy seg总数
DEFAULT_TWEMPROXY_SEG_TOTOL_NUM = 420000

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


class StateType(str, StructuredEnum):
    CREATED = EnumField("CREATED", _("创建态"))
    READY = EnumField("READY", _("准备态"))
    RUNNING = EnumField("RUNNING", _("运行态"))
    SUSPENDED = EnumField("SUSPENDED", _("暂停态"))
    BLOCKED = EnumField("BLOCKED", _("闭塞态"))
    FINISHED = EnumField("FINISHED", _("完成态"))
    FAILED = EnumField("FAILED", _("失败态"))
    REVOKED = EnumField("REVOKED", _("取消态"))


FAILED_STATES = [StateType.FAILED.value, StateType.REVOKED.value]
SUCCEED_STATES = [StateType.FINISHED]


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


class DbBackupRoleEnum(str, StructuredEnum):
    Master = EnumField("MASTER", _("MASTER"))
    Slave = EnumField("SLAVE", _("SLAVE"))


class MediumEnum(str, StructuredEnum):
    MySQL = EnumField("mysql", _("mysql"))
    Proxy = EnumField("mysql-proxy", _("mysql-proxy"))
    Redis = EnumField("redis", _("redis"))
    TendisPlus = EnumField("tendisplus", _("tendisplus"))
    TendisSsd = EnumField("tendisssd", _("tendisssd"))
    DbBackup = EnumField("dbbackup", _("dbbackup"))
    DBActuator = EnumField("actuator", _("actuator"))
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


class CloudServiceName(str, StructuredEnum):
    Nginx = EnumField("nginx", _("nginx服务"))
    DNS = EnumField("dns", _("dns服务"))
    DRS = EnumField("drs", _("drs服务"))
    DBHA = EnumField("dbha", _("dbha服务"))


class CloudServiceConfFileEnum(str, StructuredEnum):
    PullCrond = EnumField("pull-crond.conf", _("pull-crond.conf"))
    HA_GM = EnumField("ha-gm.conf", _("ha-gm.conf"))
    HA_AGENT = EnumField("ha-agent.conf", _("ha-agent.conf"))
    DRS_ENV = EnumField("drs.env", _("drs.env"))


class CloudDBHATypeEnum(str, StructuredEnum):
    GM = EnumField("gm", _("GM"))
    AGENT = EnumField("agent", _("AGENT"))
    MySQLMonitor = EnumField("mysql-monitor", _("mysql-monitor"))


CLOUD_SERVICE_SET_NAME = "cloud.service.set"
CLOUD_SSL_PATH = "cloud/ssl"
CLOUD_NGINX_DBM_DEFAULT_PORT = 80
CLOUD_NGINX_MANAGE_DEFAULT_HOST = 8080


class CloudServiceModuleName(str, StructuredEnum):
    Nginx = EnumField("nginx.service.module", _("nginx服务模块"))
    DNS = EnumField("dns.service.module", _("dns服务模块"))
    DRS = EnumField("drs.service.module", _("drs服务模块"))
    DBHA = EnumField("dbha.service.module", _("dbha服务模块"))


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


class DBActuatorActionEnum(str, StructuredEnum):
    Sysinit = EnumField("sysinit", _("sysinit"))
    Deploy = EnumField("deploy", _("deploy"))
    GetBackupFile = EnumField("find-local-backup", _("find-local-backup"))
    RestoreSlave = EnumField("restore-dr", _("restore-dr"))
    RecoverBinlog = EnumField("recover-binlog", _("recover-binlog"))
    GrantRepl = EnumField("grant-repl", _("grant-repl"))
    ChangeMaster = EnumField("change-master", _("change-master"))
    SetBackend = EnumField("set-backend", _("set-backend"))
    UnInstall = EnumField("uninstall", _("uninstall"))
    DeployDbbackup = EnumField("deploy-dbbackup", _("deploy-dbbackup"))
    InstallMonitor = EnumField("install-monitor", _("install-monitor"))
    DeployRotate = EnumField("deploy-rotate", _("deploy-rotate"))
    SenmanticDumpSchema = EnumField("semantic-dumpschema", _("semantic-dumpschema"))
    ImportSQLFile = EnumField("import-sqlfile", _("import-sqlfile"))
    CloneClientGrant = EnumField("clone-client-grant", _("clone-client-grant"))
    CloneProxyUser = EnumField("clone-proxy-user", _("clone-proxy-user"))
    ClearCrontab = EnumField("clear-crontab", _("clear-crontab"))
    SemanticCheck = EnumField("semantic-check", _("semantic-check"))
    SemanticDumpSchema = EnumField("semantic-dumpschema", _("semantic-dumpschema"))
    TruncateDataBackupNaTable = EnumField("backup-truncate-database", _("backup-truncate-database"))
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


class RedisActuatorActionEnum(str, StructuredEnum):
    Sysinit = EnumField("sysinit", _("sysinit"))
    Install = EnumField("install", _("install"))
    REPLICA_BATCH = EnumField("replica_batch", _("replica_batch"))
    Replicaof = EnumField("replicaof", _("replicaof"))
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
    KillConn = EnumField("kill_conn", _("kill_conn"))
    SyncParam = EnumField("param_sync", _("param_sync"))
    CheckSync = EnumField("sync_check", _("sync_check"))
    DTS_DATACHECK = EnumField("dts_datacheck", _("dts_datacheck"))
    DTS_DATAREPAIRE = EnumField("dts_datarepaire", _("dts_datarepaire"))


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
    JoinCluster = EnumField("join-cluster", _("join-cluster"))
    CommitClusterChange = EnumField("commit-cluster-change", _("commit-cluster-change"))
    InitBucketType = EnumField("init-bucket-type", _("init-bucket-type"))
    RemoveNode = EnumField("remove-node", _("remove-node"))
    InstallMonitor = EnumField("install-monitor", _("install-monitor"))
    DeployRiakCrond = EnumField("deploy-riak-crond", _("deploy-riak-crond"))
    ClearCrontab = EnumField("clear-crontab", _("clear-crontab"))
    UnInstall = EnumField("uninstall", _("uninstall"))


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


class ManagerOpType(str, StructuredEnum):
    CREATE = EnumField("create", _("create"))
    UPDATE = EnumField("update", _("update"))
    DELETE = EnumField("delete", _("delete"))


class ManagerServiceType(str, StructuredEnum):
    KIBANA = EnumField("kibana", _("kibana"))
    KAFKA_MANAGER = EnumField("kafka_manager", _("kafka_manager"))
    PULSAR_MANAGER = EnumField("pulsar_manager", _("pulsar_manager"))
    HA_PROXY = EnumField("ha_proxy", _("ha_proxy"))


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


class DBRoleEnum(str, StructuredEnum):
    Proxy = EnumField("proxy", _("proxy"))
    Master = EnumField("master", _("master"))
    Slave = EnumField("slave", _("slave"))


class LevelInfoEnum(str, StructuredEnum):
    TendataModuleDefault = EnumField("0", _("TendataModuleDefault"))


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


class MySQLBackupFileTagEnum(str, StructuredEnum):
    MYSQL_FULL_BACKUP = EnumField("MYSQL_FULL_BACKUP", _("全备-保留25天"))
    LONGDAY_DBFILE_3Y = EnumField("LONGDAY_DBFILE_3Y", _("长久存储-保留三年"))


class InstanceFuncAliasEnum(str, StructuredEnum):
    """
    定义实例对应的进程别名，用于注册服务实例
    """

    MYSQL_FUNC_ALIAS = EnumField("mysql", _("Mysql的进程名称"))
    MYSQL_PROXY_FUNC_ALIAS = EnumField("mysql-proxy", _("Mysql-proxy进程名称"))
    ES_FUNC_ALIAS = EnumField("java", _("ES的进程名称"))
    HDFS_NAME_NODE_FUNC_ALIAS = EnumField("java", _("HDFS-NameNode的进程名称"))
    HDFS_DATA_NODE_FUNC_ALIAS = EnumField("java", _("HDFS-DataNode的进程名称"))
    PULSAR_FUNC_ALIAS = EnumField("java", _("Pulsar的进程名称"))


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
    SYNC_SMS = EnumField("sms", _("sms"))


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


class PrivRole(str, StructuredEnum):
    """
    定义授权实例角色
    """

    SPIDER = EnumField("spider", _("spider"))
    TDBCTL = EnumField("tdbctl", _("tdbctl"))
    MYSQL = EnumField("mysql", _("mysql"))
