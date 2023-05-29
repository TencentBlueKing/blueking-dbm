package dtsJob

import (
	"fmt"
	"runtime/debug"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/osPerf"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"

	"github.com/dustin/go-humanize"
	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// TendisSSDDtsJob tendis-ssd dts job
type TendisSSDDtsJob struct {
	DtsJobBase
}

// NewTendisSSDDtsJob new
func NewTendisSSDDtsJob(bkCloudID int64, serverIP, zoneName string,
	logger *zap.Logger, wg *sync.WaitGroup) (job *TendisSSDDtsJob) {
	job = &TendisSSDDtsJob{}
	job.DtsJobBase = *NewDtsJobBase(bkCloudID, serverIP, zoneName, logger, wg)
	return
}

// GetRatioN_LocalDisk 最大使用是本地磁盘的几分之一
func (job *TendisSSDDtsJob) GetRatioN_LocalDisk() (ratioNOfLocalDisk uint64) {
	ratioNOfLocalDisk = viper.GetUint64("maxLocalDiskDataSizeRatioNTendisSSD")
	if ratioNOfLocalDisk == 0 {
		ratioNOfLocalDisk = 12
	}
	return
}

// IsDataMigrationExceedingDiskLimit 检查迁移中数据量是否超过本地磁盘限制
func (job *TendisSSDDtsJob) IsDataMigrationExceedingDiskLimit() (ok bool,
	allowedMigrationDataSize int64, err error) {
	var myDisk01 osPerf.HostDiskUsage
	var msg string
	ratioNOfLocalDisk := job.GetRatioN_LocalDisk()
	myDisk01, err = osPerf.GetMyHostDisk()
	if err != nil {
		return
	}
	if myDisk01.UsageRatio > 50 {
		// 如果当前已使用磁盘大于50%,则不继续给自己分配迁移任务
		msg = fmt.Sprintf("%s 磁盘使用率大于50%%,磁盘路径:%s,使用率:%d%%,stop accept tendis_ssd dts task",
			job.ServerIP, myDisk01.DirName, myDisk01.UsageRatio)
		job.logger.Info(msg)
		return
	}
	ssdMigratingTasks, ssdMigratingDataSize, err := tendisdb.GetDtsSvrMigratingTasks(
		job.BkCloudID, job.ServerIP, constvar.TendisTypeTendisSSDInsance, constvar.SSDMigratingTasksType, job.logger)
	if err != nil && gorm.IsRecordNotFoundError(err) == false {
		return false, 0, err
	}
	// '我'正在迁移中的数据量大于 本地磁盘的 1/ratioNOfLocalDisk, 则不继续给自己分配迁移任务
	if ssdMigratingDataSize > myDisk01.TotalSize/ratioNOfLocalDisk {
		msg = fmt.Sprintf("正在迁移中的tendis_ssd task 数据量:%s > 本地磁盘的1/%d:%s,本地磁盘大小:%s,stop accept tendis_ssd dts task",
			humanize.Bytes(ssdMigratingDataSize),
			ratioNOfLocalDisk,
			humanize.Bytes(myDisk01.TotalSize/ratioNOfLocalDisk),
			humanize.Bytes(myDisk01.TotalSize))
		job.logger.Info(msg)
		return false, 0, nil
	}
	allowedMigrationDataSize = int64(myDisk01.TotalSize/ratioNOfLocalDisk - ssdMigratingDataSize)
	if allowedMigrationDataSize < 1*constvar.GiByte { // less than 1GB
		msg = fmt.Sprintf("本地磁盘可用于迁移的空间:%s,tendisssd迁移中的数据量:%s,剩余可迁移数据量:%s < 1GB,stop accept tendis_ssd dts task",
			humanize.Bytes(myDisk01.TotalSize/ratioNOfLocalDisk),
			humanize.Bytes(ssdMigratingDataSize),
			humanize.Bytes(uint64(allowedMigrationDataSize)))
		job.logger.Info(msg)
		return false, allowedMigrationDataSize, nil
	}
	// 如果'我'上面还有2个及以上task等待做 tendisBackup,则不继续认领
	todoBackupTasks := []*tendisdb.TbTendisDTSTask{}
	for _, task01 := range ssdMigratingTasks {
		task02 := task01
		if task02.TaskType == constvar.TendisBackupTaskType && task02.Status == 0 {
			todoBackupTasks = append(todoBackupTasks, task02)
		}
	}
	if len(todoBackupTasks) >= 2 {
		job.logger.Info(fmt.Sprintf("tendis_ssd正在等待tendisBackup的task数量:%d>=2,stop accept tendis_ssd dts task",
			len(todoBackupTasks)))
		return false, allowedMigrationDataSize, nil
	}
	return true, allowedMigrationDataSize, nil
}

// ClaimDtsJobs 认领tendis-ssd dts任务
func (job *TendisSSDDtsJob) ClaimDtsJobs() (err error) {
	var diskOk bool
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
		job.logger.Info(fmt.Sprintf("dts_server:%s start claim tendis_ssd dts jobs", job.ServerIP))
		// 如果dts_server在黑名单中,则不认领task
		if scrdbclient.IsMyselfInBlacklist(job.logger) {
			job.logger.Info(fmt.Sprintf("dts_server:%s in dts_server blacklist,stop accept tendis_ssd dts task", job.ServerIP))
			continue
		}
		diskOk, allowedMigrationDataSize, err = job.IsDataMigrationExceedingDiskLimit()
		if err != nil {
			continue
		}
		if !diskOk {
			continue
		}
		// 下面模块执行逻辑:
		// - GetLast30DaysToBeScheduledJobs 获取最近一个月待调度的Jobs(相同城市)
		// - 遍历Jobs
		// - GetJobToBeScheduledTasks 获取每个job中所有待调度的task
		// - 如果task 同时满足三个条件,则本节点 可调度该task:
		// 	 1. 数据量满足 <= availDiskSize, availDiskSize = 本机磁盘1/fractionalOfLocalDisk - 本机迁移中的(tasks)的dataSize
		// 	 2. task所在的srcIP, 其当前迁移中的tasksCnt + 1 <= srcIP可支持的最大并发数(task.src_ip_concurrency_limit决定)
		//   3. 其他dts_server没有在 尝试认领该task
		toScheduleJobs, err := tendisdb.GetLast30DaysToScheduleJobs(job.BkCloudID, allowedMigrationDataSize, job.ZoneName,
			constvar.TendisTypeTendisSSDInsance, job.logger)
		if err != nil {
			continue
		}
		if len(toScheduleJobs) == 0 {
			job.logger.Info(fmt.Sprintf(
				"tendis_ssd GetLast30DaysToScheduleJobs empty record,剩余可迁移的数据量:%s,ZoneName:%s,dbType:%s",
				humanize.Bytes(uint64(allowedMigrationDataSize)), job.ZoneName, constvar.TendisTypeTendisSSDInsance))
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
				srcSlaveConcurrOK, err = job.CheckSrcSlaveServerConcurrency(taskItem, constvar.SSDMigratingTasksType)
				if err != nil {
					break
				}
				if !srcSlaveConcurrOK {
					continue
				}
				// 尝试认领task
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
				if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.TendisBackupTaskType) {
					break
				}
			}
			if err != nil {
				// 执行下一个job的遍历
				continue
			}
			// 如果认领的task个数 超过 backup limit,则等待下一次调度
			if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.TendisBackupTaskType) {
				break
			}
		}
	}
}

// StartBgWorkers 拉起多个后台goroutine
func (job *TendisSSDDtsJob) StartBgWorkers() {
	// tendis_ssd
	// 监听以前的迁移中的task
	job.BgOldRunningSyncTaskWatcher(constvar.MakeSyncTaskType, constvar.TendisTypeTendisSSDInsance, 1)
	// 在tasks被认领后,后台负责执行task的worker
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TendisBackupTaskType, constvar.TendisTypeTendisSSDInsance)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.BackupfileFetchTaskType, constvar.TendisTypeTendisSSDInsance)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TredisdumpTaskType, constvar.TendisTypeTendisSSDInsance)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.CmdsImporterTaskType, constvar.TendisTypeTendisSSDInsance)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithoutLimit(constvar.MakeSyncTaskType, constvar.TendisTypeTendisSSDInsance)
	}()
	// 根据dts_server自身情况尝试认领 task
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.ClaimDtsJobs()
	}()
}
