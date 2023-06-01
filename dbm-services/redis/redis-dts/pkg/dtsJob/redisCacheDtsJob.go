package dtsJob

import (
	"fmt"
	"runtime/debug"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"

	"github.com/dustin/go-humanize"
	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// RedisCacheDtsJob redis-cache dts job
type RedisCacheDtsJob struct {
	DtsJobBase
}

// NewRedisCacheDtsJob new
func NewRedisCacheDtsJob(bkCloudID int64, serverIP, zoneName string,
	logger *zap.Logger, wg *sync.WaitGroup) (job *RedisCacheDtsJob) {
	job = &RedisCacheDtsJob{}
	job.DtsJobBase = *NewDtsJobBase(bkCloudID, serverIP, zoneName, logger, wg)
	return
}

// GetMaxMigrationCacheDataSizePerDtsServer 单台dts_server允许的迁移中的最大Cache数据量,单位byte
func (job *RedisCacheDtsJob) GetMaxMigrationCacheDataSizePerDtsServer() uint64 {
	dataSizeStr := viper.GetString("maxCacheDataSizePerDtsServer")
	if dataSizeStr == "" {
		dataSizeStr = "256GiB"
	}
	maxCacheDataSizePerDtsServer, err := humanize.ParseBytes(dataSizeStr)
	if err != nil {
		job.logger.Error(fmt.Sprintf("'maxCacheDataSizePerDtsServer' in config fail is %s,ParseBytes fail,err:%v",
			dataSizeStr, err))
		maxCacheDataSizePerDtsServer = 256 * constvar.GiByte
	}
	if maxCacheDataSizePerDtsServer > 256*constvar.GiByte {
		maxCacheDataSizePerDtsServer = 256 * constvar.GiByte
	}
	return maxCacheDataSizePerDtsServer
}

// IsDataMigrationExceedingMemLimit 检查迁移中redis_cache数据量是否超过 单台dts_server限制
func (job *RedisCacheDtsJob) IsDataMigrationExceedingMemLimit() (ok bool, allowedMigrationDataSize int64, err error) {
	maxMigrationCacheSize := job.GetMaxMigrationCacheDataSizePerDtsServer()
	var cacheMigratingTasks []*tendisdb.TbTendisDTSTask
	var cacheMigratingDataSize uint64
	var msg string
	cacheMigratingTasks, cacheMigratingDataSize, err = tendisdb.GetDtsSvrMigratingTasks(
		job.BkCloudID, job.ServerIP, constvar.TendisTypeRedisInstance,
		constvar.CacheMigratingTasksType, job.logger)
	if err != nil && gorm.IsRecordNotFoundError(err) == false {
		return
	}
	// '我'正在迁移中的数据量大于 dstMaxMigratingCacheSize, 则不继续给自己分配迁移任务
	if cacheMigratingDataSize > maxMigrationCacheSize {
		msg = fmt.Sprintf("正在迁移中的tendis_cache task 数据量:%s > 单机限制:%s,,stop accept redis_cache dts task",
			humanize.Bytes(cacheMigratingDataSize),
			humanize.Bytes(maxMigrationCacheSize))
		job.logger.Info(msg)
		return false, 0, nil
	}
	allowedMigrationDataSize = int64(maxMigrationCacheSize - cacheMigratingDataSize)
	// 如果'我'上面还有2个以上task等待做 makeCacheSync,则不继续认领
	todoTasks := []*tendisdb.TbTendisDTSTask{}
	for _, task01 := range cacheMigratingTasks {
		task02 := task01
		if task02.TaskType == constvar.MakeCacheSyncTaskType && task02.Status == 0 {
			todoTasks = append(todoTasks, task02)
		}
	}
	if len(todoTasks) >= 2 {
		job.logger.Info(fmt.Sprintf("redis_cache正在等待MakeCacheSync的task数量:%d>=2,stop accept redis_cache dts task",
			len(todoTasks)))
		return false, allowedMigrationDataSize, nil
	}
	return true, allowedMigrationDataSize, nil
}

// ClaimDtsJobs 认领redis-cache任务
func (job *RedisCacheDtsJob) ClaimDtsJobs() (err error) {
	var memOk bool
	var allowedMigrationDataSize int64
	var toScheduleTasks []*tendisdb.TbTendisDTSTask
	var srcSlaveConcurrOK bool
	var acceptOk bool
	succClaimTaskCnt := 0
	defer func() {
		if r := recover(); r != nil {
			job.logger.Error(string(debug.Stack()))
		}
	}()
	for {
		time.Sleep(1 * time.Minute)
		job.logger.Info(fmt.Sprintf("dts_server:%s start claim redisCache dts jobs", job.ServerIP))
		// 如果dts_server在黑名单中,则不认领task
		if scrdbclient.IsMyselfInBlacklist(job.logger) {
			job.logger.Info(fmt.Sprintf(
				"dts_server:%s in dts_server blacklist,stop accept redis_cache dts task",
				job.ServerIP),
			)
			continue
		}
		memOk, allowedMigrationDataSize, err = job.IsDataMigrationExceedingMemLimit()
		if err != nil {
			continue
		}
		if !memOk {
			continue
		}
		/*
			下面模块执行逻辑:
			1. GetLast30DaysToBeScheduledJobs 获取最近一个月待调度的tendis_cache Jobs(相同城市)
			2. 遍历Jobs
			3. GetJobToBeScheduledTasks 获取job中所有待调度的task
			   如果task 同时满足三个条件,则本节点 可调度该task:
			   a. 数据量满足 <= myAvailScheduleSize,
			   	  allowedMigrationDataSize = maxCacheDataSizePerDtsServer - 本机迁移中的(tendis_cache tasks)的dataSize
			   b. task所在的srcIP, 其当前迁移中的tasksCnt + 1 <= srcIP可支持的最大并发数(task.src_ip_concurrency_limit决定)
			   c. 其他dtsserver没有在 尝试认领该task
		*/
		toScheduleJobs, err := tendisdb.GetLast30DaysToScheduleJobs(job.BkCloudID,
			allowedMigrationDataSize, job.ZoneName,
			constvar.TendisTypeRedisInstance, job.logger)
		if err != nil {
			continue
		}
		if len(toScheduleJobs) == 0 {
			job.logger.Info(fmt.Sprintf(
				"redis_cache GetLast30DaysToScheduleJobs empty record,剩余可迁移的数据量:%s,ZoneName:%s,dbType:%s",
				humanize.Bytes(uint64(allowedMigrationDataSize)),
				job.ZoneName, constvar.TendisTypeRedisInstance))
			continue
		}
		succClaimTaskCnt = 0
		for _, tmpJob := range toScheduleJobs {
			jobItem := tmpJob
			toScheduleTasks, err = tendisdb.GetJobToScheduleTasks(
				jobItem.BillID, jobItem.SrcCluster, jobItem.DstCluster, job.logger)
			if err != nil {
				// 执行下一个Job的遍历
				continue
			}
			if len(toScheduleTasks) == 0 {
				continue
			}
			for _, tmpTask := range toScheduleTasks {
				taskItem := tmpTask
				if allowedMigrationDataSize < 1*constvar.GiByte {
					// 如果可用空间小于1GB,则不再继续
					break
				}
				if taskItem.SrcDbSize > allowedMigrationDataSize {
					// 数据量过大,遍历job的下一个task
					continue
				}
				// 检查源slave机器是否还能新增迁移task
				srcSlaveConcurrOK, err = job.CheckSrcSlaveServerConcurrency(taskItem, constvar.CacheMigratingTasksType)
				if err != nil {
					break
				}
				if !srcSlaveConcurrOK {
					continue
				}
				// 尝试认领task成功
				acceptOk, err = job.TryAcceptTask(taskItem)
				if err != nil {
					continue
				}
				if !acceptOk {
					continue
				}
				allowedMigrationDataSize = allowedMigrationDataSize - taskItem.SrcDbSize
				succClaimTaskCnt++
				// 如果认领的task个数 超过 backup limit,则等待下一次调度
				if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.MakeCacheSyncTaskType) {
					break
				}
			}
			if err != nil {
				// 执行下一个job的遍历
				continue
			}
			// 如果认领的task个数 超过 backup limit,则等待下一次调度
			if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.MakeCacheSyncTaskType) {
				break
			}
		}
	}
}

// StartBgWorkers 拉起多个后台goroutine
func (job *RedisCacheDtsJob) StartBgWorkers() {
	// redis_cache
	// 监听以前的迁移中的task
	job.BgOldRunningSyncTaskWatcher(constvar.WatchCacheSyncTaskType, constvar.TendisTypeRedisInstance, 1)
	// 在tasks被认领后,后台负责执行task的worker
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.MakeCacheSyncTaskType, constvar.TendisTypeRedisInstance)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithoutLimit(constvar.WatchCacheSyncTaskType, constvar.TendisTypeRedisInstance)
	}()
	// 根据dts_server自身情况尝试认领 task
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.ClaimDtsJobs()
	}()
}
