package dtsJob

import (
	"fmt"
	"log"
	"runtime/debug"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask/factory"
	"dbm-services/redis/redis-dts/pkg/dtsTask/rediscache"
	"dbm-services/redis/redis-dts/pkg/dtsTask/tendisplus"
	"dbm-services/redis/redis-dts/pkg/dtsTask/tendisssd"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"

	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// DtsJober dts-job 接口
type DtsJober interface {
	StartBgWorkers()
	ClaimDtsJobs() (err error)
}

// DtsJobBase base class
type DtsJobBase struct {
	BkCloudID int64  `json:"bk_cloud_id"`
	ServerIP  string `json:"serverIP"`
	ZoneName  string `json:"zoneName"`
	logger    *zap.Logger
	wg        *sync.WaitGroup
}

// NewDtsJobBase new
func NewDtsJobBase(bkCloudID int64, serverIP, zoneName string, logger *zap.Logger, wg *sync.WaitGroup) *DtsJobBase {
	return &DtsJobBase{
		BkCloudID: bkCloudID,
		ServerIP:  serverIP,
		ZoneName:  zoneName,
		logger:    logger,
		wg:        wg,
	}
}

// GetTaskParallelLimit concurrency for task
func (job *DtsJobBase) GetTaskParallelLimit(taskType string) int {
	limit01 := viper.GetInt(taskType + "ParallelLimit")
	if limit01 == 0 {
		limit01 = 5 // 默认值5
	}
	return limit01
}

// BgDtsTaskRunnerWithConcurrency 执行子task,限制并发度,如backup、tredisdump等task任务
// 如拉起5个goroutine执行 backup tasks, 拉起 5个goroutine执行 tredisdump tasks
func (job *DtsJobBase) BgDtsTaskRunnerWithConcurrency(taskType, dbType string) {
	var err error
	wg := sync.WaitGroup{}
	genChan := make(chan *tendisdb.TbTendisDTSTask)
	limit := job.GetTaskParallelLimit(taskType)
	status := 0
	perTaskNum := 5

	for worker := 0; worker < limit; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			defer func() {
				if r := recover(); r != nil {
					job.logger.Error(string(debug.Stack()))
				}
			}()
			for oldRow := range genChan {
				// 可能在等待调度过程中row01数据已经改变,所以重新获取数据
				latestRow, err := tendisdb.GetTaskByID(oldRow.ID, job.logger)
				if err != nil {
					latestRow = oldRow
				}
				if latestRow == nil {
					job.logger.Warn(fmt.Sprintf("根据task_id:%d获取task row失败,taskRow:%v", oldRow.ID, latestRow))
					continue
				}
				if latestRow.Status != 0 || latestRow.TaskType != taskType {
					job.logger.Info(fmt.Sprintf("task_id:%d src_slave:%s:%d status=%d taskType=%s. 期待的taskType:%s 已经在运行中,不做任何处理",
						latestRow.ID, latestRow.SrcIP, latestRow.SrcPort, latestRow.Status, latestRow.TaskType, taskType))
					continue
				}
				task01 := factory.MyTaskFactory(latestRow)
				task01.Init() // 执行Init,成功则status=1,失败则status=-1
				task01.Execute()
			}
		}()
	}
	go func() {
		defer close(genChan)
		var toExecuteRows []*tendisdb.TbTendisDTSTask
		for {
			if !tendisdb.IsAllDtsTasksToForceKill(toExecuteRows) {
				// 如果所有dts tasks都是 ForceKillTaskTodo 状态,则大概率该dts job用户已强制终止, 无需sleep
				// 否则 sleep 10s
				time.Sleep(10 * time.Second)
			}
			toExecuteRows, err = tendisdb.GetLast30DaysToExecuteTasks(job.BkCloudID, job.ServerIP, taskType, dbType,
				status, perTaskNum, job.logger)
			if err != nil {
				continue
			}
			if len(toExecuteRows) == 0 {
				job.logger.Info(fmt.Sprintf("not found to be executed %q task,sleep 10s", taskType),
					zap.String("serverIP", job.ServerIP))
				continue
			}
			for _, row := range toExecuteRows {
				toDoRow := row
				// 将task放入channel,等待消费者goroutine真正处理
				genChan <- toDoRow
			}
		}
	}()
	wg.Wait()
}

// BgDtsTaskRunnerWithoutLimit 执行子task,不限制并发度,执行makeSync、watchCacheSync 等增量同步不能限制并发度
func (job *DtsJobBase) BgDtsTaskRunnerWithoutLimit(taskType, dbType string) {
	wg := sync.WaitGroup{}
	genChan := make(chan *tendisdb.TbTendisDTSTask)
	status := 0
	perTaskNum := 5
	var err error

	wg.Add(1)
	go func() {
		// 消费者:处理task
		defer wg.Done()
		defer func() {
			if r := recover(); r != nil {
				job.logger.Error(string(debug.Stack()))
			}
		}()
		for row01 := range genChan {
			rowItem := row01
			wg.Add(1)
			go func(rowData *tendisdb.TbTendisDTSTask) {
				defer wg.Done()
				defer func() {
					if r := recover(); r != nil {
						job.logger.Error(string(debug.Stack()))
					}
				}()
				task01 := factory.MyTaskFactory(rowData)
				task01.Init()
				task01.Execute()
			}(rowItem)
		}
	}()
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer close(genChan)
		var toExecuteRows []*tendisdb.TbTendisDTSTask
		for {
			// 生产者: 获取task
			// 如果所有dts tasks都是 ForceKillTaskTodo 状态,则大概率该dts job用户已强制终止, 无需sleep
			// 否则 sleep 10s
			if !tendisdb.IsAllDtsTasksToForceKill(toExecuteRows) {
				time.Sleep(10 * time.Second)
			}
			toExecuteRows, err = tendisdb.GetLast30DaysToExecuteTasks(job.BkCloudID, job.ServerIP, taskType, dbType,
				status, perTaskNum, job.logger)
			if err != nil {
				continue
			}
			if len(toExecuteRows) == 0 {
				job.logger.Info(fmt.Sprintf("not found to be executed %q task,sleep 10s", taskType),
					zap.String("serverIP", job.ServerIP))
				continue
			}
			for _, row := range toExecuteRows {
				toDoRow := row
				// 将task放入channel,等待消费者goroutine真正处理
				genChan <- toDoRow
			}
		}
	}()
	wg.Wait()
}

// BgOldRunningSyncTaskWatcher 目的:
// 很多时候 redis-sync 已经拉起,状态为runnig(taskrow.status==1 taskrow.taskType="makeSync")
// 而此时我们需要暂停 dbm-services/redis/redis-dts 升级 dbm-services/redis/redis-dts的介质
// 再次拉起后, 以前(taskrow.status==1 taskrow.taskType="makeSync")的task其相关状态依然需要我们不断watch
// 注意: 该函数只在 dbm-services/redis/redis-dts 被拉起时执行,启动goroutine监听属于当前dts_server的属于running状态的tasks
// 对于后续新增的 (taskrow.status==1 taskrow.taskType="makeSync")的task,不归该函数处理
func (job *DtsJobBase) BgOldRunningSyncTaskWatcher(taskType, dbType string, status int) {
	limit := 100000
	oldSyncTasks, err := tendisdb.GetLast30DaysToExecuteTasks(job.BkCloudID, job.ServerIP, taskType, dbType, status, limit,
		job.logger)
	if err != nil {
		return
	}
	if len(oldSyncTasks) == 0 {
		job.logger.Info(fmt.Sprintf("DTSserver:%s not found oldRunningSyncTasks", job.ServerIP))
		return
	}
	job.logger.Info(fmt.Sprintf("DTSserver:%s found %d oldRunningSyncTasks", job.ServerIP, len(oldSyncTasks)))
	for _, taskRow01 := range oldSyncTasks {
		taskRowItem := taskRow01
		go func(taskRow *tendisdb.TbTendisDTSTask) {
			defer func() {
				if r := recover(); r != nil {
					job.logger.Error(string(debug.Stack()))
				}
			}()
			if taskRow.TaskType == constvar.MakeSyncTaskType {
				watcherTask := tendisssd.NewWatchOldSync(taskRow)
				watcherTask.Init()
				watcherTask.Execute()
			} else if taskRow.TaskType == constvar.WatchCacheSyncTaskType {
				watcherTask := rediscache.NewWatchCacheSyncTask(taskRow)
				watcherTask.Init()
				watcherTask.Execute()
			} else if taskRow.TaskType == constvar.TendisplusSendBulkTaskType ||
				taskRow.TaskType == constvar.TendisplusSendIncrTaskType {
				watcherTask := tendisplus.NewWatchSyncTask(taskRow)
				watcherTask.Init()
				watcherTask.Execute()
			}
		}(taskRowItem)
	}
}

// IsMyselfInBlacklist 当前dts_server是否在黑名单中
func (job *DtsJobBase) IsMyselfInBlacklist() bool {
	scrCli, err := scrdbclient.NewClient(viper.GetString("serviceName"), job.logger)
	if err != nil {
		log.Fatal(err)
	}
	return scrCli.IsDtsServerInBlachList(job.ServerIP)
}

// CheckSrcSlaveServerConcurrency 检查源slave机器是否还能新增迁移task
// 如源slave机器上有20个redis,同时启动迁移是危险的,需做并发控制
func (job *DtsJobBase) CheckSrcSlaveServerConcurrency(taskRow *tendisdb.TbTendisDTSTask, taskTypes []string) (ok bool,
	err error) {

	var msg string
	srcSlaveRunningTasks, err := tendisdb.GetJobSrcIPRunningTasks(taskRow.BillID, taskRow.SrcCluster, taskRow.DstCluster,
		taskRow.SrcIP, taskTypes, job.logger)
	if (err != nil && gorm.IsRecordNotFoundError(err)) || len(srcSlaveRunningTasks) == 0 {
		// 该 srcSlave 上没有任何处于迁移中的task,满足对 srcSlave的并发度保护
		return true, nil
	} else if err != nil {
		return false, err
	}
	// 该srcSlave上有部分处于迁移中的task
	if len(srcSlaveRunningTasks)+1 > taskRow.SrcIPConcurrencyLimit {
		// srcSlave 当前迁移中的tasks数 + 1 > srcSlave可支持的最大并发数
		// 遍历下一个task
		msg = fmt.Sprintf("srcSlave:%s上正在运行的迁移任务数:%d,srcSlave允许的并发数:%d,so stop accept task",
			taskRow.SrcIP, len(srcSlaveRunningTasks), taskRow.SrcIPConcurrencyLimit)
		job.logger.Info(msg)
		return false, nil
	}
	// srcSlave 当前迁移中的tasks数 + 1 <= srcSlave可支持的最大并发数,满足对 srcSlave的并发度保护
	return true, nil
}

func (job *DtsJobBase) getFirstTaskType(taskRow *tendisdb.TbTendisDTSTask) (taskType string) {
	switch taskRow.SrcDbType {
	case constvar.TendisTypeTendisSSDInsance:
		return constvar.TendisBackupTaskType
	case constvar.TendisTypeRedisInstance:
		return constvar.MakeCacheSyncTaskType
	case constvar.TendisTypeTendisplusInsance:
		return constvar.TendisplusMakeSyncTaskType
	}
	return ""
}

// TryAcceptTask 上锁,尝试认领任务
func (job *DtsJobBase) TryAcceptTask(taskRow *tendisdb.TbTendisDTSTask) (succ bool, err error) {
	var lockOK bool
	scrCli, err := scrdbclient.NewClient(viper.GetString("serviceName"), job.logger)
	if err != nil {
		return false, err
	}
	// 获取锁,尝试认领该task
	lockOK, err = scrCli.DtsLockKey(taskRow.TaskLockKey(), job.ServerIP, 120)
	if err != nil {
		return false, err
	}
	if !lockOK {
		// 已经有其他dtsserver在尝试认领该task,遍历下一个task
		job.logger.Info(fmt.Sprintf(
			`taskId:%d srcCluster:%s dstCluster:%s srcRedis:%s#%d 已经有其他dts_server在调度,放弃调度`,
			taskRow.ID, taskRow.SrcCluster,
			taskRow.DstCluster, taskRow.SrcIP, taskRow.SrcPort))
		return false, nil
	}
	job.logger.Info(fmt.Sprintf("myself:%s get task dts lock ok,key:%s", job.ServerIP, taskRow.TaskLockKey()))
	// 尝试认领task成功
	job.logger.Info(fmt.Sprintf(
		`myself:%s 认领task,下一步开始迁移,taskId:%d srcCluster:%s dstCluster:%s srcRedis:%s#%d`,
		job.ServerIP, taskRow.ID, taskRow.SrcCluster,
		taskRow.DstCluster, taskRow.SrcIP, taskRow.SrcPort))
	taskRow.DtsServer = job.ServerIP
	taskRow.TaskType = job.getFirstTaskType(taskRow)
	taskRow.Status = 0
	taskRow.UpdateFieldsValues([]string{"DtsServer", "TaskType", "Status"}, job.logger)
	return true, nil
}
