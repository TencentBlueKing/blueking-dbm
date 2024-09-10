package dtsJob

import (
	"fmt"
	"runtime/debug"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask/factory"
	"dbm-services/redis/redis-dts/pkg/dtsTask/tendispluslightning"
	"dbm-services/redis/redis-dts/pkg/osPerf"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
	"dbm-services/redis/redis-dts/pkg/txycos"

	"github.com/dustin/go-humanize"
	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"github.com/tencentyun/cos-go-sdk-v5"
	"go.uber.org/zap"
)

// TendisplusLightningJob tendis lightning job
type TendisplusLightningJob struct {
	BkCloudID int64  `json:"bk_cloud_id"`
	ServerIP  string `json:"serverIP"`
	ZoneName  string `json:"zoneName"`
	logger    *zap.Logger
	wg        *sync.WaitGroup
	cosWorker *txycos.TxyCosWoker
}

// NewTendisplusLightningJob new
func NewTendisplusLightningJob(bkCloudID int64, serverIP, zoneName string,
	logger *zap.Logger, wg *sync.WaitGroup) (job *TendisplusLightningJob) {
	var err error
	job = &TendisplusLightningJob{
		BkCloudID: bkCloudID,
		ServerIP:  serverIP,
		ZoneName:  zoneName,
		logger:    logger,
		wg:        wg,
	}
	job.cosWorker, err = txycos.NewTxyCosWoker(job.logger)
	if err != nil {
		panic(err)
	}
	return
}

// GetRatioN_LocalDisk 最大使用是本地磁盘的几分之一
func (job *TendisplusLightningJob) GetRatioN_LocalDisk() (ratioNOfLocalDisk uint64) {
	ratioNOfLocalDisk = viper.GetUint64("maxLocalDiskDataSizeRatioNLightning")
	if ratioNOfLocalDisk == 0 {
		ratioNOfLocalDisk = 4
	}
	return
}

// IsDataMigrationExceedingDiskLimit 检查迁移中数据量是否超过本地磁盘限制
func (job *TendisplusLightningJob) IsDataMigrationExceedingDiskLimit() (ok bool,
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
		msg = fmt.Sprintf("%s 磁盘使用率大于50%%,磁盘路径:%s,使用率:%d%%,stop accept tendisplus lightning dts task",
			job.ServerIP, myDisk01.DirName, myDisk01.UsageRatio)
		job.logger.Info(msg)
		return
	}
	lightningMigratingTasks, lightningMigratingDataSize, err := tendisdb.LightningDtsSvrMigratingTasks(
		job.BkCloudID, job.ServerIP, constvar.LightningMigratingTasksType, job.logger)
	if err != nil && gorm.IsRecordNotFoundError(err) == false {
		return false, 0, err
	}
	// '我'正在迁移中的数据量大于 本地磁盘的 1/ratioNOfLocalDisk, 则不继续给自己分配迁移任务
	if lightningMigratingDataSize > myDisk01.TotalSize/ratioNOfLocalDisk {
		msg = fmt.Sprintf(
			"正在迁移中的tendisplus lightning task 数据量:%s > 本地磁盘的1/%d:%s,本地磁盘大小:%s,stop accept tendisplus lightning dts task",
			humanize.Bytes(lightningMigratingDataSize),
			ratioNOfLocalDisk,
			humanize.Bytes(myDisk01.TotalSize/ratioNOfLocalDisk),
			humanize.Bytes(myDisk01.TotalSize))
		job.logger.Info(msg)
		return false, 0, nil
	}
	allowedMigrationDataSize = int64(myDisk01.TotalSize/ratioNOfLocalDisk - lightningMigratingDataSize)
	if allowedMigrationDataSize < 10*constvar.GiByte { // less than 10GB
		msg = fmt.Sprintf(
			"本地磁盘可用于迁移的空间:%s,tendisplus lightning 迁移中的数据量:%s,剩余可迁移数据量:%s < 10GB,stop accept tendisplus lightning dts task",
			humanize.Bytes(myDisk01.TotalSize/ratioNOfLocalDisk),
			humanize.Bytes(lightningMigratingDataSize),
			humanize.Bytes(uint64(allowedMigrationDataSize)))
		job.logger.Info(msg)
		return false, allowedMigrationDataSize, nil
	}
	// 如果'我'上面还有2个及以上task等待做 lightningCosFileDownload,则不继续认领
	todoBackupTasks := []*tendisdb.TbTendisplusLightningTask{}
	for _, task01 := range lightningMigratingTasks {
		task02 := task01
		if task02.TaskType == constvar.TendisplusLightningCosFileDownload && task02.Status == 0 {
			todoBackupTasks = append(todoBackupTasks, task02)
		}
	}
	if len(todoBackupTasks) >= 2 {
		job.logger.Info(fmt.Sprintf(
			"tendisplus lightning 正在等待 lightningCosFileDownload 的task数量:%d>=2,stop accept tendisplus lightning dts task",
			len(todoBackupTasks)))
		return false, allowedMigrationDataSize, nil
	}
	return true, allowedMigrationDataSize, nil
}

func (job *TendisplusLightningJob) updateTasksCosFileSize(taskRows []*tendisdb.TbTendisplusLightningTask) (
	anyRowUpdate bool, err error) {
	var cosRet *cos.BucketGetResult
	var rowFatherTask tendispluslightning.LightningFatherTask
	var msg string
	anyRowUpdate = false
	for _, row := range taskRows {
		taskRow := row
		job.logger.Info(fmt.Sprintf("start updateTasksCosFileSize ticket_id:%d dst_cluster:%s task_id:%s",
			taskRow.TicketID, taskRow.DstCluster, taskRow.TaskId))
		// 如果没有设置过,则默认为 0
		if taskRow.CosFileSize != 0 {
			job.logger.Info(fmt.Sprintf("ticket_id:%d dst_cluster:%s task_id:%s cos_file_size:%d skip.....",
				taskRow.TicketID, taskRow.DstCluster, taskRow.TaskId, taskRow.CosFileSize))
			continue
		}
		if taskRow.CosKey == "" {
			job.logger.Info(fmt.Sprintf("ticket_id:%d dst_cluster:%s task_id:%s cos_key:%s skip.....",
				taskRow.TicketID, taskRow.DstCluster, taskRow.TaskId, taskRow.CosKey))
			continue
		}
		rowFatherTask = tendispluslightning.NewLightningFatherTask(taskRow)
		rowFatherTask.Logger = job.logger
		cosRet, err = job.cosWorker.GetFileList(taskRow.CosKey, 100)
		if err != nil {
			// 更新数据库
			msg += err.Error() + "\n"
			rowFatherTask.SetMessage(err.Error())
			rowFatherTask.SetStatus(-1)
			rowFatherTask.UpdateRow()
			continue
		}
		if len(cosRet.Contents) == 0 {
			// 更新数据库
			err = fmt.Errorf("cos key:%s file.Contents empty records", taskRow.CosKey)
			msg += err.Error() + "\n"
			rowFatherTask.SetMessage(err.Error())
			rowFatherTask.SetStatus(-1)
			rowFatherTask.UpdateRow()
			continue
		}
		job.logger.Info(fmt.Sprintf("ticket_id:%d dst_cluster:%s task_id:%s start update cosFileSize:%d ...",
			taskRow.TicketID, taskRow.DstCluster, taskRow.TaskId, cosRet.Contents[0].Size))
		anyRowUpdate = true
		rowFatherTask.SetMessage("update fileSize ok")
		rowFatherTask.SetCosFileSize(cosRet.Contents[0].Size)
		rowFatherTask.SetStatus(0)
		rowFatherTask.UpdateRow()
	}
	if msg != "" {
		err = fmt.Errorf(msg)
		return
	}
	return
}

// ClaimDtsJobs 认领tendisplus lightning dts任务
func (job *TendisplusLightningJob) ClaimDtsJobs() (err error) {
	var diskOk bool
	var allowedMigrationDataSize int64
	var toScheduleTasks []*tendisdb.TbTendisplusLightningTask
	var acceptOk bool
	succClaimTaskCnt := 0
	defer func() {
		if r := recover(); r != nil {
			job.logger.Error(string(debug.Stack()))
		}
	}()
	for {
		time.Sleep(1 * time.Minute)
		job.logger.Info(fmt.Sprintf("dts_server:%s start claim tendisplus lightning dts jobs", job.ServerIP))
		// 如果dts_server在黑名单中,则不认领task
		if scrdbclient.IsMyselfInBlacklist(job.logger) {
			job.logger.Info(
				fmt.Sprintf("dts_server:%s in dts_server blacklist,stop accept tendisplus lightning dts task",
					job.ServerIP))
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
		// - LightningLast30DaysToScheduleJobs 获取最近一个月待调度的Jobs(相同城市)
		// - 遍历Jobs
		// - lightningJobToScheduleTasks 获取每个job中所有待调度的task
		// - 如果task 同时满足条件,则本节点 可调度该task:
		// 	 1. 数据量满足 <= availDiskSize, availDiskSize = 本机磁盘1/fractionalOfLocalDisk - 本机迁移中的(tasks)的dataSize
		//   2. 其他dts_server没有在 尝试认领该task
		toScheduleJobs, err := tendisdb.LightningLast30DaysToScheduleJobs(job.BkCloudID, allowedMigrationDataSize,
			job.ZoneName, job.logger)
		if err != nil {
			continue
		}
		if len(toScheduleJobs) == 0 {
			job.logger.Info(fmt.Sprintf(
				"tendisplus lightningLast30DaysToScheduleJobs empty record,剩余可迁移的数据量:%s,ZoneName:%s",
				humanize.Bytes(uint64(allowedMigrationDataSize)), job.ZoneName))
			continue
		}
		succClaimTaskCnt = 0
		anyRowUpdate := false
		for _, tmpJob := range toScheduleJobs {
			jobItem := tmpJob
			toScheduleTasks, err = tendisdb.LightningJobToScheduleTasks(
				jobItem.TicketID, jobItem.DstCluster, job.logger)
			if err != nil {
				// 执行下一个Job的遍历
				continue
			}
			if len(toScheduleTasks) == 0 {

				continue
			}
			// 如果'我'更新了任何task的cosFileSize,则不再继续这个job对应task等认领和执行
			anyRowUpdate, err = job.updateTasksCosFileSize(toScheduleTasks)
			if err != nil {
				continue
			}
			if anyRowUpdate {
				continue
			}
			for _, tmpTask := range toScheduleTasks {
				taskItem := tmpTask
				if allowedMigrationDataSize < 10*constvar.GiByte {
					// 如果可用空间小于10GB,则不再继续
					break
				}
				if taskItem.CosFileSize > allowedMigrationDataSize {
					// 数据量过大,遍历job的下一个task
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
				allowedMigrationDataSize = allowedMigrationDataSize - taskItem.CosFileSize
				succClaimTaskCnt++
				// 如果认领的task个数 超过 backup limit,则等待下一次调度
				if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.TendisplusLightningCosFileDownload) {
					break
				}
			}
			if err != nil {
				// 执行下一个job的遍历
				continue
			}
			// 如果认领的task个数 超过 cosfiledownload limit,则等待下一次调度
			if succClaimTaskCnt > job.GetTaskParallelLimit(constvar.TendisplusLightningCosFileDownload) {
				break
			}
		}
	}
}

func (job *TendisplusLightningJob) getFirstTaskType() (taskType string) {
	return constvar.TendisplusLightningCosFileDownload
}

// GetTaskParallelLimit concurrency for task
func (job *TendisplusLightningJob) GetTaskParallelLimit(taskType string) int {
	limit := viper.GetInt(taskType + "ParallelLimit")
	if limit == 0 {
		limit = 5 // 默认值5
	}
	return limit
}

// TryAcceptTask 上锁,尝试认领任务
func (job *TendisplusLightningJob) TryAcceptTask(taskRow *tendisdb.TbTendisplusLightningTask) (succ bool, err error) {
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
			`taskId:%s ticketID:%d dstCluster:%s  已经有其他dts_server在调度,放弃调度`,
			taskRow.TaskId, taskRow.TicketID, taskRow.DstCluster))
		return false, nil
	}
	job.logger.Info(fmt.Sprintf("myself:%s get task dts lock ok,key:%s", job.ServerIP, taskRow.TaskLockKey()))
	// 尝试认领task成功
	job.logger.Info(fmt.Sprintf(
		`myself:%s 认领task,下一步开始迁移,taskId:%s ticketID:%d dstCluster:%s`,
		job.ServerIP, taskRow.TaskId, taskRow.TicketID, taskRow.DstCluster))
	taskRow.DtsServer = job.ServerIP
	taskRow.TaskType = job.getFirstTaskType()
	taskRow.Status = 0
	taskRow.UpdateFieldsValues([]string{"DtsServer", "TaskType", "Status"}, job.logger)
	return true, nil
}

// BgDtsTaskRunnerWithConcurrency 执行子task,限制并发度,如backup、tredisdump等task任务
// 如拉起5个goroutine执行 backup tasks, 拉起 5个goroutine执行 tredisdump tasks
func (job *TendisplusLightningJob) BgDtsTaskRunnerWithConcurrency(taskType string) {
	var err error
	wg := sync.WaitGroup{}
	genChan := make(chan *tendisdb.TbTendisplusLightningTask)
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
				latestRow, err := tendisdb.LightningTaskByID(oldRow.TaskId, job.logger)
				if err != nil {
					latestRow = oldRow
				}
				if latestRow == nil {
					job.logger.Warn(fmt.Sprintf("根据task_id:%s获取task row失败,taskRow:%v", oldRow.TaskId, latestRow))
					continue
				}
				if latestRow.Status != 0 || latestRow.TaskType != taskType {
					job.logger.Info(fmt.Sprintf("task_id:%s status=%d taskType=%s. 期待的taskType:%s 已经在运行中,不做任何处理",
						latestRow.TaskId, latestRow.Status, latestRow.TaskType, taskType))
					continue
				}
				task01 := factory.MyTendisplusLightningTaskFactory(latestRow)
				task01.Init() // 执行Init,成功则status=1,失败则status=-1
				task01.Execute()
			}
		}()
	}
	go func() {
		defer close(genChan)
		var toExecuteRows []*tendisdb.TbTendisplusLightningTask
		for {
			if !tendisdb.IsAllLightningTasksToForceKill(toExecuteRows) {
				// 如果所有dts tasks都是 ForceKillTaskTodo 状态,则大概率该dts job用户已强制终止, 无需sleep
				// 否则 sleep 10s
				time.Sleep(10 * time.Second)
			}
			toExecuteRows, err = tendisdb.LightningLast30DaysToExecuteTasks(job.BkCloudID, job.ServerIP, taskType,
				status, perTaskNum, job.logger)
			if err != nil {
				continue
			}
			if len(toExecuteRows) == 0 {
				job.logger.Info(fmt.Sprintf("serverIP:%s not found to be executed %s task,sleep 10s", job.ServerIP, taskType))
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

// StartBgWorkers 拉起多个后台goroutine
func (job *TendisplusLightningJob) StartBgWorkers() {
	// tendisplus lightning job
	// 在tasks被认领后,后台负责执行task的worker
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TendisplusLightningCosFileDownload)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TendisplusLightningFileSplit)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TendisplusLightningGenerateSst)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TendisplusLightningScpSst)
	}()
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.BgDtsTaskRunnerWithConcurrency(constvar.TendisplusLightningSlaveLoadSst)
	}()
	// 根据dts_server自身情况尝试认领 task
	go func() {
		job.wg.Add(1)
		defer job.wg.Done()
		job.ClaimDtsJobs()
	}()
}
