// Package constvar TODO
package constvar

import (
	"regexp"

	"github.com/spf13/viper"
)

// version
const (
	TendisDTSVersion = "v0.10"
)

// kibis of bits
const (
	Byte = 1 << (iota * 10)
	KiByte
	MiByte
	GiByte
	TiByte
	EiByte
)

const (
	// RedisMasterRole redis role master
	RedisMasterRole = "master"
	// RedisSlaveRole redis role slave
	RedisSlaveRole = "slave"

	// RedisNoneRole none role
	RedisNoneRole = "none"

	// MasterLinkStatusUP up status
	MasterLinkStatusUP = "up"
	// MasterLinkStatusDown down status
	MasterLinkStatusDown = "down"
)

// 环境类型
const (
	ProdENV   = "prod"   // 正式环境
	TestENV   = "test"   // 测试环境
	GlobalENV = "global" // 海外环境
)

// db类型
const (
	TendisTypeTendisSSDInsance  = "TendisSSDInstance"
	TendisTypeRedisInstance     = "RedisInstance"
	TendisTypeTendisplusInsance = "TendisplusInstance"
	UserTwemproxyType           = "user_twemproxy"
	UserRedisInstance           = "user_redis_instance"
	UnknownType                 = "unknown"
)

// redis-sync state
const (
	SyncOnlineState = "ONLINE"
)

// tendisplus replicate state
const (
	TendisplusReplSendbulk = "send_bulk"
	TendisplusReplOnline   = "online"
)

// IsProdEnv 是否是正式环境
func IsProdEnv() bool {
	return viper.GetString("ENV") == ProdENV
}

// IsTestEnv 是否是测试环境
func IsTestEnv() bool {
	return viper.GetString("ENV") == TestENV
}

// IsGlobalEnv 是否是海外环境
func IsGlobalEnv() bool {
	return viper.GetString("ENV") == GlobalENV
}

// tendisssd task type
const (
	TendisBackupTaskType    = "tendisBackup"
	BackupfileFetchTaskType = "backupfileFetch"
	TredisdumpTaskType      = "tendisdump"
	CmdsImporterTaskType    = "cmdsImporter"
	MakeSyncTaskType        = "makeSync"
	WatchOldSyncTaskType    = "WatchOldSync"
)

// redis cache task type
const (
	MakeCacheSyncTaskType  = "makeCacheSync"
	WatchCacheSyncTaskType = "watchCacheSync"
)

// tendisplus task type
const (
	TendisplusMakeSyncTaskType = "tendisplusMakeSync"
	// TendisplusSendBulkTaskType 将存量数据同步 与 增量数据同步分开,原因是 存量数据同步讲占用较多内存,增量不占用内存
	TendisplusSendBulkTaskType = "tendisplusSendBulk"
	TendisplusSendIncrTaskType = "tendisplusSendIncr"
)

// tendisplus lightning task type
const (
	TendisplusLightningCosFileDownload = "lightningCosFileDownload"
	TendisplusLightningFileSplit       = "lightningFileSplit"
	TendisplusLightningGenerateSst     = "lightningGenerateSst"
	TendisplusLightningScpSst          = "lightningScpSst"
	TendisplusLightningSlaveLoadSst    = "lightningSlaveLoadSst"
)

// tendisplus lightning tools
const (
	ToolLightningKVFileSplit  = "tendisplus_lightning_kvfile_split"
	ToolLightningSstGenerator = "tendisplus_lightning_sst_generator"
)

const (
	// ToolZstd tool
	ToolZstd = "zstd"
	// DbbakDir dir
	DbbakDir = "/data/dbbak/"
	// MysqlOSAccount os account
	MysqlOSAccount = "mysql"
)

/*
migrating tasks type
'迁移中' 是指那些正在占用资源 或者 即将占用资源 阶段, 资源主要指磁盘 or 内存
对tendiSSD来说,'迁移中'指处于[tendisBackup,backupfileFetch,tendisdump,cmdsImporter]中的task,不包含处于status=-1或 处于 makeSync 状态的task
不包含处于 status=-1 或 处于 makeSync 状态的task;
对tendisCache来说,'迁移中'指处于 'makeCacheSync'中的task,不包含处于 status=-1 或 处于 watchCacheSync 状态的task;
对tendisplus来说,'迁移中'指处于 'tendisplusMakeSync'、`tendisplusSendBulk`阶段的task,不包含 status=-1 或 处于 tendisplusSendIncr的task
*/
var (
	SSDMigratingTasksType = []string{
		TendisBackupTaskType,
		BackupfileFetchTaskType,
		TredisdumpTaskType,
		CmdsImporterTaskType,
	}
	CacheMigratingTasksType      = []string{MakeCacheSyncTaskType}
	TendisplusMigratingTasksType = []string{
		TendisplusMakeSyncTaskType,
		TendisplusSendBulkTaskType,
	}
	LightningMigratingTasksType = []string{
		TendisplusLightningCosFileDownload,
		TendisplusLightningFileSplit,
		TendisplusLightningGenerateSst,
		TendisplusLightningScpSst,
		// TendisplusLightningSlaveLoadSst
	}
)

// Tredisdump 结果文件格式
const (
	TredisdumpRespFormat = "resp"
	TredisdumpCmdFormat  = "aof"
)

// Tredisdump 结果文件匹配模式
const (
	TredisdumpListGlobMatch   = "*_list_*"
	TredisdumpListRegMatch    = `^[0-9]+_list_[0-9]+$`
	TredisdumpOutputGlobMatch = "*_output_*"
	TredisdumpExpireGlobMatch = "*_expire_*"
	TredisdumpDelGlobMatch    = "*_del_*"
)

// ListKeyFileReg TODO
var ListKeyFileReg = regexp.MustCompile(TredisdumpListRegMatch)

// redis-sync 操作状态
const (
	// RedisSyncPauseTodo TODO
	// pause,'SYNCADMIN stop'
	RedisSyncPauseTodo = "SyncPauseTodo"
	RedisSyncPauseFail = "SyncPauseFail"
	RedisSyncPauseSucc = "SyncPauseSucc"

	// RedisSyncResumeTodo TODO
	// resume,'SYNCADMIN start'
	RedisSyncResumeTodo = "SyncResumeTodo"
	RedisSyncResumeFail = "SyncResumeFail"
	RedisSyncResumeSucc = "SyncResumeSucc"

	// RedisSyncUpgradeTodo TODO
	// upgrade,upgrade redis-sync binary
	RedisSyncUpgradeTodo = "SyncUpgradeTodo"
	RedisSyncUpgradeFail = "SyncUpgradeFail"
	RedisSyncUpgradeSucc = "SyncUpgradeSucc"

	// RedisSyncStopTodo TODO
	// Stop,kill redis-sync proccess
	RedisSyncStopTodo = "SyncStopTodo"
	RedisSyncStopFail = "SyncStopFail"
	RedisSyncStopSucc = "SyncStopSucc"

	// RedisForceKillTaskTodo kill migrate task
	RedisForceKillTaskTodo    = "ForceKillTaskTodo"
	RedisForceKillTaskFail    = "ForceKillTaskFail"
	RedisForceKillTaskSuccess = "ForceKillTaskSucc"

	// ReSyncFromSpecTimeTodo TODO
	// resyunc from specific time
	ReSyncFromSpecTimeTodo = "ReSyncFromSpecTimeTodo"
	ReSyncFromSpecTimeFail = "ReSyncFromSpecTimeFail"
	ReSyncFromSpecTimeSucc = "ReSyncFromSpecTimeSucc"
)

// 可以忽略错误类型
const (
	WrongTypeOperationErr = "WRONGTYPE Operation"
)

// remote services' name
const (
	DtsRemoteTendisxk8s = "dtsRemoteTendisxk8s"
	// K8sIsDtsSvrInBlacklistURL TODO
	// tendisk8s mico service
	K8sIsDtsSvrInBlacklistURL         = "/tendisxk8s/cluster/tendis-dts/is-dts-server-in-blacklist"
	K8sDtsLockKeyURL                  = "/tendisxk8s/cluster/tendis-dts/dts-lock-key"
	K8sDtsUnlockKeyURL                = "/tendisxk8s/cluster/tendis-dts/dts-unlock-key"
	K8sGetDtsJobURL                   = "/tendisxk8s/cluster/tendis-dts/get-dts-job"
	K8sDtsServerMigratingTasksURL     = "/tendisxk8s/cluster/tendis-dts/get-dts-server-migrating-tasks"
	K8sDtsServerMaxSyncPortURL        = "/tendisxk8s/cluster/tendis-dts/get-dts-server-max-sync-port"
	K8sDtsLast30DaysToExecuteTasksURL = "/tendisxk8s/cluster/tendis-dts/get-dts-last-30days-to-execute-tasks"
	K8sDtsLast30DaysToScheduleJobsURL = "/tendisxk8s/cluster/tendis-dts/get-dts-last-30days-to-schedule-jobs"
	K8sDtsJobToScheduleTasksURL       = "/tendisxk8s/cluster/tendis-dts/get-dts-job-to-schedule-tasks"
	K8sDtsJobSrcIPRunningTasksURL     = "/tendisxk8s/cluster/tendis-dts/get-dts-job-srcip-running-tasks"
	K8sDtsTaskRowByIDURL              = "/tendisxk8s/cluster/tendis-dts/get-dts-task-row-by-id"
	K8sDtsUpdateTaskRowsURL           = "/tendisxk8s/cluster/tendis-dts/update-dts-task-rows"

	BkDbm                             = "bkDbm"
	DbmIsDtsSvrInBlacklistURL         = "/apis/proxypass/redis_dts/is_dtsserver_in_blacklist/"
	DbmDtsLockKeyURL                  = "/apis/proxypass/redis_dts/distribute_trylock/"
	DbmDtsUnlockKeyURL                = "/apis/proxypass/redis_dts/distribute_unlock/"
	DbmGetDtsJobURL                   = "/apis/proxypass/redis_dts/job_detail/"
	DbmDtsServerMigratingTasksURL     = "/apis/proxypass/redis_dts/dts_server_migrating_tasks/"
	DbmDtsServerMaxSyncPortURL        = "/apis/proxypass/redis_dts/dts_server_max_sync_port/"
	DbmDtsLast30DaysToExecuteTasksURL = "/apis/proxypass/redis_dts/last_30_days_to_exec_tasks/"
	DbmDtsLast30DaysToScheduleJobsURL = "/apis/proxypass/redis_dts/last_30_days_to_schedule_jobs/"
	DbmDtsJobToScheduleTasksURL       = "/apis/proxypass/redis_dts/job_to_schedule_tasks/"
	DbmDtsJobSrcIPRunningTasksURL     = "/apis/proxypass/redis_dts/job_src_ip_running_tasks/"
	DbmDtsTaskRowByIDURL              = "/apis/proxypass/redis_dts/task_by_task_id/"
	DbmDtsUpdateTaskRowsURL           = "/apis/proxypass/redis_dts/tasks_update/"

	DbmJobApiFastExecuteScriptURL        = "/apis/proxypass/jobapi/fast_execute_script/"
	DbmJobApiGetJobInstanceStatusURL     = "/apis/proxypass/jobapi/get_job_instance_status/"
	DbmJobApiBatchGetJobInstanceIPLogURL = "/apis/proxypass/jobapi/batch_get_job_instance_ip_log/"
	DbmJobApiTransferFileURL             = "/apis/proxypass/jobapi/fast_transfer_file/"

	// DbmLightningDtsServerMigratingTasksURL TODO
	// tendisplus Lightning api
	DbmLightningDtsServerMigratingTasksURL  = "/apis/proxypass/tendisplus_lightning/dts_server_migrating_tasks/"
	DbmLightningLast30DaysToExecuteTasksURL = "/apis/proxypass/tendisplus_lightning/last_30_days_to_exec_tasks/"
	DbmLightningLast30DaysToScheduleJobsURL = "/apis/proxypass/tendisplus_lightning/last_30_days_to_schedule_jobs/"
	DbmLightningJobToScheduleTasksURL       = "/apis/proxypass/tendisplus_lightning/job_to_schedule_tasks/"
	DbmLightningJobDetailURL                = "/apis/proxypass/tendisplus_lightning/job_detail/"
	DbmLightningTaskRowByIDURL              = "/apis/proxypass/tendisplus_lightning/task_by_task_id/"
	DbmLightningUpdateTaskRowsURL           = "/apis/proxypass/tendisplus_lightning/tasks_update/"
)

// ZonenameTransform 城市转换
func ZonenameTransform(zoneName string) string {
	switch zoneName {
	case "苏州":
		return "上海"
	case "昆山":
		return "上海"
	case "扬州":
		return "南京"
	case "仪征":
		return "南京"
	case "清远":
		return "广州"
	default:
		return zoneName
	}
}

// dts write_mode
const (
	// WriteModeDeleteAndWriteToRedis 先删除同名redis key, 再执行写入(如:del $key + hset $key)
	WriteModeDeleteAndWriteToRedis = "delete_and_write_to_redis"
	// WriteModeKeepAndAppendToRedis 保留同名redis key,追加写入(如hset $key)
	WriteModeKeepAndAppendToRedis = "keep_and_append_to_redis"
	// WriteModeFlushallAndWriteToRedis 先清空目标集群所有数据,在写入(如flushall + hset $key)
	WriteModeFlushallAndWriteToRedis = "flushall_and_write_to_redis"
)

// dts copy type
const (
	// CopyTypeOneAppDiffCluster 同业务不同集群
	CopyTypeOneAppDiffCluster = "one_app_diff_cluster"
	// CopyTypeDiffAppDiffCluster 不同业务不同集群
	CopyTypeDiffAppDiffCluster = "diff_app_diff_cluster"
	// CopyTypeCopyToOtherSystem 业务内至第三方
	CopyTypeCopyToOtherSystem = "copy_to_other_system"
	// CopyTypeUserBuiltToDBM_built_to_dbm 自建集群至业务内
	CopyTypeUserBuiltToDBM_built_to_dbm = "user_built_to_dbm"
	// CopyTypeCopyFromRollbackInstance 构造实例至业务内
	CopyTypeCopyFromRollbackInstance = "copy_from_rollback_instance"
)
