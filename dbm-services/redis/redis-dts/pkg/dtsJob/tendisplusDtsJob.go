package dtsJob

import (
	"fmt"
	"math"
	"runtime/debug"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/osPerf"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"

	"github.com/dustin/go-humanize"
	"github.com/jinzhu/gorm"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// TendisplusDtsJob tendisplus dts job
type TendisplusDtsJob struct {
	DtsJobBase
}

// NewTendisplusDtsJob new
func NewTendisplusDtsJob(bkCloudID int64, serverIP, zoneName string,
	logger *zap.Logger, wg *sync.WaitGroup) (job *TendisplusDtsJob) {
	job = &TendisplusDtsJob{}
	job.DtsJobBase = *NewDtsJobBase(bkCloudID, serverIP, zoneName, logger, wg)
	return
}

// GetMemSizePerKvStoreSync 每个tendisplus kvstore的redis-sync占用的内存
func (job *TendisplusDtsJob) GetMemSizePerKvStoreSync() uint64 {
	memSizeStr := viper.GetString("memSizePerTendisplusKvStoreSync")
	if memSizeStr == "" {
		memSizeStr = "500MiB"
	}
	memSize, _ := humanize.ParseBytes(memSizeStr)
	if memSize <= 0 {
		memSize = 500 * constvar.MiByte
	}
	return memSize
}

// IsDataMigrationExceedingMemLimit 内存是否满足继续认领dts task
// 1. 内存已使用 50%+ 不认领;
// 2. 可用内存小于3GB不认领;
// 3. 每个tendisplus kvstore迁移时预计使用500MB内存,如果评估kvstore迁移使用内存数超过 50%,不认领
// 4. 如果等待迁移的kvstore>=2,不认领
func (job *TendisplusDtsJob) IsDataMigrationExceedingMemLimit() (ok bool, availMemSizeMigration int64, err error) {
	var memInfo *mem.VirtualMemoryStat
	var tendisplusMigratingTasks []*tendisdb.TbTendisDTSTask
	var kvstoreMigratingMemUsed uint64
	var msg string
	memInfo, err = osPerf.GetHostsMemInfo(job.logger)
	if memInfo.UsedPercent > 50 {
		msg = fmt.Sprintf("本机已使用内存%.2f%% > 50%%,stop accept tendisplus dts task", memInfo.UsedPercent)
		job.logger.Info(msg)
		return false, 0, nil
	}
	if memInfo.Available < 3*constvar.GiByte {
		msg = fmt.Sprintf("本机可用内存%s<3GB,stop accept tendisplus dts task", humanize.Bytes(memInfo.Available))
		job.logger.Info(msg)
		return false, 0, nil
	}
	tendisplusMigratingTasks, _, err = tendisdb.GetDtsSvrMigratingTasks(
		job.BkCloudID, job.ServerIP, constvar.TendisTypeTendisplusInsance, constvar.TendisplusMigratingTasksType, job.logger,
	)
	if err != nil && gorm.IsRecordNotFoundError(err) == false {
		return
	}
	// 如果迁移中的tasks数,评估其内存已超过系统内存 50%,返回false
	kvstoreMigratingMemUsed = uint64(len(tendisplusMigratingTasks)) * job.GetMemSizePerKvStoreSync()
	if kvstoreMigratingMemUsed > memInfo.Total*50/100 {
		msg = fmt.Sprintf("本机迁移中kvstore数:%d,评估使用内存:%s,stop accept tendisplus dts task",
			len(tendisplusMigratingTasks),
			humanize.Bytes(kvstoreMigratingMemUsed))
		job.logger.Info(msg)
		return false, 0, nil
	}
	availMemSizeMigration = int64(memInfo.Total*50/100 - kvstoreMigratingMemUsed)
	// 如果'我'上面还有2个以上task等待做 tendisplusStartSync,则不继续认领
	todoTaskCnt := 0
	for _, task01 := range tendisplusMigratingTasks {
		task02 := task01
		if task02.TaskType == constvar.TendisplusMakeSyncTaskType && task02.Status == 0 {
			todoTaskCnt++
		}
	}
	if todoTaskCnt >= 2 {
		job.logger.Info(fmt.Sprintf("tendisplus正在等待tendisplusMakeSync的task数量:%d>=2,stop accept tendisplus dts task",
			todoTaskCnt))
		return false, availMemSizeMigration, nil
	}
	return true, availMemSizeMigration, nil
}

// TryAcceptTasks 上锁,尝试认领任务
func (job *TendisplusDtsJob) TryAcceptTasks(taskRows []*tendisdb.TbTendisDTSTask) (succ bool, err error) {
	var lockOK bool
	scrCli, err := scrdbclient.NewClient(viper.GetString("serviceName"), job.logger)
	if err != nil {
		return false, err
	}
	// 获取锁,尝试认领该task
	lockOK, err = scrCli.DtsLockKey(taskRows[0].TaskLockKey(), job.ServerIP, 120)
	if err != nil {
		return false, err
	}
	if !lockOK {
		// 已经有其他dtsserver在尝试认领该task,遍历下一个task
		job.logger.Info(fmt.Sprintf(
			`billId:%d srcCluster:%s dstCluster:%s srcRedis:%s#%d 已经有其他dts_server在调度,放弃调度`,
			taskRows[0].BillID, taskRows[0].SrcCluster,
			taskRows[0].DstCluster, taskRows[0].SrcIP, taskRows[0].SrcPort))
		return false, nil
	}
	job.logger.Info(fmt.Sprintf("myself:%s get task dts lock ok,key:%s", job.ServerIP, taskRows[0].TaskLockKey()))
	// 尝试认领task成功
	job.logger.Info(fmt.Sprintf(
		`myself:%s 认领task,下一步开始迁移,billID:%d srcCluster:%s dstCluster:%s srcRedis:%s#%d`,
		job.ServerIP, taskRows[0].BillID, taskRows[0].SrcCluster,
		taskRows[0].DstCluster, taskRows[0].SrcIP, taskRows[0].SrcPort))
	taskIDs := make([]int64, 0, len(taskRows))
	for _, tmpTask := range taskRows {
		task := tmpTask
		taskIDs = append(taskIDs, task.ID)
	}
	taskRows[0].DtsServer = job.ServerIP
	taskRows[0].TaskType = job.getFirstTaskType(taskRows[0])
	taskRows[0].Status = 0
	colToVal, err := taskRows[0].GetColToValByFields([]string{"DtsServer", "TaskType", "Status"}, job.logger)
	if err != nil {
		return false, err
	}
	_, err = tendisdb.UpdateDtsTaskRows(taskIDs, colToVal, job.logger)
	if err != nil {
		return false, err
	}
	return true, nil
}

// TasksGroupBySlaveAddr 按照slaveAddr分组
func (job *TendisplusDtsJob) TasksGroupBySlaveAddr(taskRows []*tendisdb.TbTendisDTSTask) (
	slaveAddrToTasks map[string][]*tendisdb.TbTendisDTSTask, err error) {
	slaveAddrToTasks = make(map[string][]*tendisdb.TbTendisDTSTask)
	var slaveAddr string
	var ok bool
	for _, tmpRow := range taskRows {
		row := tmpRow
		slaveAddr = fmt.Sprintf("%d|%s|%s|%s|%d", row.BillID, row.SrcCluster, row.DstCluster, row.SrcIP, row.SrcPort)
		if _, ok = slaveAddrToTasks[slaveAddr]; !ok {
			slaveAddrToTasks[slaveAddr] = []*tendisdb.TbTendisDTSTask{}
		}
		slaveAddrToTasks[slaveAddr] = append(slaveAddrToTasks[slaveAddr], row)
	}
	return
}

// ClaimDtsJobs 认领tendisplus dts任务
func (job *TendisplusDtsJob) ClaimDtsJobs() (err error) {
	var memOK bool
	var availMemSizeMigration int64
	var toScheduleTasks []*tendisdb.TbTendisDTSTask
	var slaveAddrToTasks map[string][]*tendisdb.TbTendisDTSTask
	var srcSlaveConcurrOK bool
	var acceptOk bool
	// 在迁移tendisplus时,其本身数据量不影响,所以用MAX_INT64值
	var maxInt64 int64 = math.MaxInt64
	succClaimTaskCnt := 0
	defer func() {
		if r := recover(); r != nil {
			job.logger.Error(string(debug.Stack()))
		}
	}()
	for {
		time.Sleep(1 * time.Minute)
		job.logger.Info(fmt.Sprintf("dts_server:%s start claim tendisplus dts jobs", job.ServerIP))
		// 如果dts_server在黑名单中,则不认领task
		if scrdbclient.IsMyselfInBlacklist(job.logger) {
			job.logger.Info(fmt.Sprintf("dts_server:%s in dts_server blacklist,stop accept tendisplus dts task", job.ServerIP))
			continue
		}
		memOK, availMemSizeMigration, err = job.IsDataMigrationExceedingMemLimit()
		if err != nil {
			continue
		}
		if err != nil {
			continue
		}
		if !memOK {
			continue
		}
		toScheduleJobs, err := tendisdb.GetLast30DaysToScheduleJobs(job.BkCloudID, maxInt64, job.ZoneName,
			constvar.TendisTypeTendisplusInsance, job.logger)
		if err != nil {
			continue
		}
		if len(toScheduleJobs) == 0 {
			job.logger.Info(fmt.Sprintf(
				"tendisplus GetLast30DaysToScheduleJobs empty record,ZoneName:%s,dbType:%s",
				job.ZoneName, constvar.TendisTypeTendisplusInsance))
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
			slaveAddrToTasks, err = job.TasksGroupBySlaveAddr(toScheduleTasks)
			if err != nil {
				continue
			}
			for _, taskRows := range slaveAddrToTasks {
				if availMemSizeMigration < 1*constvar.GiByte {
					// 如果可用内存小于1GB,则不再继续
					break
				}
				// 检查源slave机器是否还能新增迁移task
				srcSlaveConcurrOK, err = job.CheckSrcSlaveServerConcurrency(taskRows[0], constvar.TendisplusMigratingTasksType)
				if err != nil {
					break
				}
				if !srcSlaveConcurrOK {
					continue
				}
				// 尝试认领task
				acceptOk, err = job.TryAcceptTasks(taskRows)
				if err != nil {
					continue
				}
				if !acceptOk {
					continue
				}
				// 减去预估将使用掉的内存
				availMemSizeMigration = availMemSizeMigration - int64(len(taskRows))*int64(job.GetMemSizePerKvStoreSync())
				succClaimTaskCnt++
				// 如果认领的task个数 超过 tendisplus_start_sync limit,则等待下一次调度
				if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.TendisplusMakeSyncTaskType) {
					break
				}
			}
			if err != nil {
				// 执行下一个job的遍历
				continue
			}
			// 如果认领的task个数 超过 tendisplus_start_sync limit,则等待下一次调度
			if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.TendisplusMakeSyncTaskType) {
				break
			}
		}
	}
}

// StartBgWorkers 拉起多个后台goroutine
func (job *TendisplusDtsJob) StartBgWorkers() {
	// tendisplus
	// 监听以前的迁移中的task
	job.BgOldRunningSyncTaskWatcher(constvar.TendisplusSendBulkTaskType, constvar.TendisTypeTendisplusInsance, 1)
	job.BgOldRunningSyncTaskWatcher(constvar.TendisplusSendIncrTaskType, constvar.TendisTypeTendisplusInsance, 1)
	// 在tasks被认领后,后台负责执行task的worker
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithoutLimit(constvar.TendisplusMakeSyncTaskType, constvar.TendisTypeTendisplusInsance)
	}()
	// 根据dts_server自身情况尝试认领 task
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.ClaimDtsJobs()
	}()
}
