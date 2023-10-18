package tendisssd

import (
	"context"
	"encoding/base64"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask"
	"dbm-services/redis/redis-dts/util"

	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

const (
	// SyncSubOffset TODO
	SyncSubOffset = 100000
)

// MakeSyncTask  启动redis-sync
type MakeSyncTask struct {
	dtsTask.FatherTask
	RedisCliTool  string `json:"redisCliTool"`
	RedisSyncTool string `json:"redisSyncTool"`
	SyncLogFile   string `json:"syncLogFile"`
	SyncConfFile  string `json:"syncConfFile"`
	SrcADDR       string `json:"srcAddr"`
	SrcPassword   string `json:"srcPassword"`
	DstADDR       string `json:"dstAddr"`
	DstPassword   string `json:"dstPassword"`
	LastSeq       uint64 `json:"lastSeq"`
	Runid         string `json:"runnid"`
	syncSeqSave   dtsTask.ISaveSyncSeq
}

// TaskType task类型
func (task *MakeSyncTask) TaskType() string {
	return constvar.MakeSyncTaskType
}

// NextTask 下一个task类型
func (task *MakeSyncTask) NextTask() string {
	return ""
}

// NewMakeSyncTask 新建一个 redis-sync启动task
func NewMakeSyncTask(row *tendisdb.TbTendisDTSTask) *MakeSyncTask {
	return &MakeSyncTask{
		FatherTask: dtsTask.NewFatherTask(row),
	}
}

// PreClear 关闭以前生成的redis-sync
func (task *MakeSyncTask) PreClear() {
	if task.Err != nil {
		return
	}
	if task.RowData.SyncerPort == 0 {
		return
	}
	defer func() {
		// clear old sync config file and log file
		syncDir := task.MkSyncDirIfNotExists()
		if task.Err != nil {
			return
		}
		rmCmd := fmt.Sprintf("cd %s && rm -rf *-taskid%d-*.log *-taskid%d-*.conf", syncDir, task.RowData.ID, task.RowData.ID)
		task.Logger.Info(fmt.Sprintf("tendisplus makeSync preClear execute:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 10*time.Second, task.Logger)

	}()

	task.RedisSyncStop()
	return
}

// Execute 执行启动redis-sync
func (task *MakeSyncTask) Execute() {
	var err error
	if task.Err != nil {
		return
	}

	defer func() {
		if task.Err != nil {
			task.SetStatus(-1)
			task.SetMessage(task.Err.Error())
			task.UpdateRow()
		}
	}()
	task.SetStatus(1)
	task.UpdateDbAndLogLocal("开始创建sync关系")

	_, task.Err = util.IsFileExistsInCurrDir("tendisssd-sync-template.conf")
	if task.Err != nil {
		task.Logger.Error(task.Err.Error())
		return
	}

	redisClient, err := util.IsToolExecutableInCurrDir("redis-cli")
	if err != nil {
		task.Err = err
		return
	}
	task.RedisCliTool = redisClient

	task.SetSyncSeqSaveInterface()
	if task.Err != nil {
		return
	}

	srcPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.SrcPassword)
	dstPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.DstPassword)

	task.SrcADDR = fmt.Sprintf("%s:%d", task.RowData.SrcIP, task.RowData.SrcPort)
	task.SrcPassword = string(srcPasswd)
	task.DstADDR = task.RowData.DstCluster
	task.DstPassword = string(dstPasswd)

	isSyncOK := task.IsSyncStateOK()
	if isSyncOK {
		// 同步状态本来就是ok的,直接watcht redis-sync即可
		task.Logger.Info(fmt.Sprintf("redis:%s 同步状态ok,开始watch...", task.SrcADDR))
		task.WatchSync()
		return
	}

	task.GetMyRedisSyncTool(true)
	if task.Err != nil {
		return
	}

	lastSeq := task.GetLastSyncSeq(SyncSubOffset)
	if task.Err != nil {
		return
	}
	task.Logger.Info(fmt.Sprintf("lastSeq=>%s", lastSeq.String()))

	task.PreClear()
	if task.Err != nil {
		return
	}
	task.LastSeq = lastSeq.Seq
	task.Runid = lastSeq.RunID

	// before start redis-sync, we must confirm binlog is ok
	task.ConfirmSrcRedisBinlogOK(task.LastSeq)
	if task.Err != nil {
		return
	}

	task.RedisSyncStart(true)
	if task.Err != nil {
		return
	}

	task.UpdateDbAndLogLocal("redis-sync 启动成功,pid:%d", task.RowData.SyncerPid)

	task.WatchSync()
	return
}

// MkSyncDirIfNotExists TODO
// create sync directory if not exists
func (task *MakeSyncTask) MkSyncDirIfNotExists() (syncDir string) {
	task.Err = task.InitTaskDir()
	if task.Err != nil {
		return
	}
	syncDir = filepath.Join(task.TaskDir, "syncs")
	task.Err = util.MkDirIfNotExists(syncDir)
	if task.Err != nil {
		return
	}
	return
}

// SetSyncSeqSaveInterface TODO
// set syncSeqSave interface
func (task *MakeSyncTask) SetSyncSeqSaveInterface() {
	syncDir := task.MkSyncDirIfNotExists()
	if task.Err != nil {
		return
	}
	syncRuntimeSeqFile := filepath.Join(syncDir, "sync-runtime-pos.txt")
	task.syncSeqSave, task.Err = dtsTask.NewSaveSyncSeqToFile(syncRuntimeSeqFile, task.Logger)
	return
}

// GetLastSyncSeq 获取最后一条sync seq
// - 先从 task.syncSeqSave 中获取得到 savedLastSeq;
// (task.syncSeqSave中保存的seq结果是redis-sync info Tendis-SSD得到,仅表示redis-sync接收到的binlog,
//
//	并非dstRedis实际已执行的binlog, redis-sync最多保存10w条，故从 task.syncSeqSave中得到的savedLastSeq需要减去一个偏移)
//
// - 在从 full backup 中获取 bakSeq;
// - 比较 savedLastSeq 与 bakSeq, 较大者即为我们需要的 lastSeq
func (task *MakeSyncTask) GetLastSyncSeq(subOffset uint64) (lastSeq dtsTask.SyncSeqItem) {
	var err error
	var savedLastSeq dtsTask.SyncSeqItem
	if task.syncSeqSave.HaveOldSyncSeq() == true {
		savedLastSeq, err = task.syncSeqSave.GetLastSyncSeq()
		if err != nil {
			task.Err = err
			return
		}
		task.Logger.Info("GetLastSyncSeq before sub offset", zap.Any("savedLastSeq", savedLastSeq))
		savedLastSeq.Seq = savedLastSeq.Seq - subOffset
		task.Logger.Info("GetLastSyncSeq after sub offset", zap.Any("savedLastSeq", savedLastSeq))
	}
	bakSeq := task.GetSyncSeqFromFullBackup()
	if task.Err != nil {
		return
	}
	// tendis slave将发送 lastSeq - 1 + 1=lastSeq 及其以后的binlog给redis-sync
	// 因此这里必须lastSeq-1,否则将缺少lastSeq对应的命令
	bakSeq.Seq = bakSeq.Seq - 1

	// 两者取较大值
	if savedLastSeq.RunID != "" && savedLastSeq.Seq > bakSeq.Seq {
		lastSeq = savedLastSeq
	} else {
		lastSeq = *bakSeq
	}

	task.Logger.Info("GetLastSyncSeq finally result", zap.Any("lastSeq", lastSeq))
	return
}

// GetSpecificTimeSyncSeq 获取某个时间点(精确到分钟)第一条sync seq
// - 先从 task.syncSeqSave 中获取得到 savedSpecTimeSeq;
// (task.syncSeqSave中保存的seq结果是redis-sync info Tendis-SSD得到,仅表示redis-sync接收到的binlog,
//
//	并非dstRedis实际已执行的binlog, redis-sync最多保存10w条，故从 task.syncSeqSave中得到的 savedSpecTimeSeq 需要减去一个偏移)
//
// - 在从 full backup 中获取 bakSeq;
// - 比较 savedSpecTimeSeq 与 bakSeq, 较大者即为我们需要的 lastSeq
func (task *MakeSyncTask) GetSpecificTimeSyncSeq(time01 time.Time, subOffset uint64) (lastSeq dtsTask.SyncSeqItem) {
	var err error
	var savedSpecTimeSeq dtsTask.SyncSeqItem
	if task.syncSeqSave.HaveOldSyncSeq() == true {
		savedSpecTimeSeq, err = task.syncSeqSave.GetSpecificTimeSyncSeq(time01)
		if err != nil && util.IsNotFoundErr(err) == false {
			task.Err = err
			return
		}
		if err == nil {
			task.Logger.Info("GetSpecificTimeSyncSeq before sub offset", zap.Any("savedSpecTimeSeq", savedSpecTimeSeq))
			savedSpecTimeSeq.Seq = savedSpecTimeSeq.Seq - subOffset
			task.Logger.Info("GetSpecificTimeSyncSeq after sub offset", zap.Any("savedSpecTimeSeq", savedSpecTimeSeq))
		} else if err != nil && util.IsNotFoundErr(err) == true {
			// reset err
			err = nil
		}
	}
	bakSeq := task.GetSyncSeqFromFullBackup()
	if task.Err != nil {
		return
	}
	// tendis slave将发送 lastSeq - 1 + 1=lastSeq 及其以后的binlog给redis-sync
	// 因此这里必须lastSeq-1,否则将缺少lastSeq对应的命令
	bakSeq.Seq = bakSeq.Seq - 1

	// 两者取较大值
	if savedSpecTimeSeq.RunID != "" && savedSpecTimeSeq.Seq > bakSeq.Seq {
		lastSeq = savedSpecTimeSeq
	} else {
		lastSeq = *bakSeq
	}

	task.Logger.Info("GetSpecificTimeSyncSeq finally result", zap.Any("lastSeq", lastSeq))
	return
}

// GetMyRedisSyncTool Get [latest] redis-sync binary
func (task *MakeSyncTask) GetMyRedisSyncTool(fetchLatest bool) {
	task.GetRedisSyncClientFromLocal()
	return
}

// GetRedisSyncClientFromLocal 本地获取redis-sync
func (task *MakeSyncTask) GetRedisSyncClientFromLocal() {
	currentPath, err := util.CurrentExecutePath()
	if err != nil {
		task.Err = err
		task.Logger.Error(err.Error())
		return
	}
	syncClient := filepath.Join(currentPath, "redis-sync")
	_, err = os.Stat(syncClient)
	if err != nil && os.IsNotExist(err) == true {
		task.Err = fmt.Errorf("%s not exists,err:%v", syncClient, err)
		task.Logger.Error(task.Err.Error())
		return
	} else if err != nil && os.IsPermission(err) == true {
		err = os.Chmod(syncClient, 0774)
		if err != nil {
			task.Err = fmt.Errorf("%s os.Chmod 0774 fail,err:%v", syncClient, err)
			task.Logger.Error(task.Err.Error())
			return
		}
	}
	task.Logger.Info(fmt.Sprintf("%s is ok", syncClient))
	task.RedisSyncTool = syncClient
}

// getMySyncPort 获取redis-sync port, 10000<=port<20000
func (task *MakeSyncTask) getMySyncPort(initSyncPort int) {
	taskTypes := []string{}
	var syncerPort int
	taskTypes = append(taskTypes, constvar.MakeSyncTaskType)
	if initSyncPort <= 0 {
		initSyncPort = 10000
		localIP, _ := util.GetLocalIP()
		dtsSvrMaxSyncPortTask, err := tendisdb.GetDtsSvrMaxSyncPort(task.RowData.BkCloudID, localIP,
			constvar.TendisTypeTendisSSDInsance, taskTypes, task.Logger)
		if (err != nil && gorm.IsRecordNotFoundError(err)) || dtsSvrMaxSyncPortTask == nil {
			initSyncPort = 10000
		} else if err != nil {
			task.Err = err
			return
		} else {
			if dtsSvrMaxSyncPortTask.SyncerPort >= 10000 {
				initSyncPort = dtsSvrMaxSyncPortTask.SyncerPort + 1
			}
		}
	}
	if initSyncPort > 20000 {
		initSyncPort = 10000
	}
	syncerPort, task.Err = util.GetANotUsePort("127.0.0.1", initSyncPort, 1)
	if task.Err != nil {
		task.Logger.Error(task.Err.Error())
		return
	}
	task.SetSyncerPort(syncerPort)

	return
}

// WatchSync 监听redis-sync,binlog-lag与last-key等信息
func (task *MakeSyncTask) WatchSync() {
	// ssd slave中slave-log-keep-count是否减少到1800w
	// (redis-sync同步落后10分钟以内,则将slave-log-keep-count修改为1200w)
	slaveLogCountDecr := false

	jobRows, err := tendisdb.GetTendisDTSJob(task.RowData.BillID, task.RowData.SrcCluster,
		task.RowData.DstCluster, task.Logger)
	if err != nil {
		task.Err = err
		return
	}

	lastSeqAndTime := dtsTask.SyncSeqItem{}
	for {
		time.Sleep(10 * time.Second)

		task.RefreshRowData()
		if task.Err != nil {
			return
		}
		if task.RowData.KillSyncer == 1 ||
			task.RowData.SyncOperate == constvar.RedisSyncStopTodo ||
			task.RowData.SyncOperate == constvar.RedisForceKillTaskTodo { // stop redis-sync

			succ := constvar.RedisSyncStopSucc
			fail := constvar.RedisSyncStopFail
			if task.RowData.SyncOperate == constvar.RedisForceKillTaskTodo {
				succ = constvar.RedisForceKillTaskSuccess
				fail = constvar.RedisForceKillTaskFail
			}
			task.Logger.Info(fmt.Sprintf("start execute %q ...", task.RowData.SyncOperate))
			task.RedisSyncStop()
			if task.Err == nil {
				task.RestoreSrcSSDKeepCount() // 恢复 src ssd slave-log-keep-count值
				task.SetSyncOperate(succ)
				task.SetStatus(2)
				task.UpdateDbAndLogLocal("redis-sync:%d终止成功", task.RowData.SyncerPid)
				task.Err = nil
			} else {
				task.SetSyncOperate(fail)
			}
			task.Logger.Info(fmt.Sprintf("end %q ...", task.RowData.SyncOperate))
			return
		}
		// pause and resume redis-sync
		if task.RowData.SyncOperate == constvar.RedisSyncPauseTodo {
			task.Logger.Info(fmt.Sprintf("start execute %q ...", task.RowData.SyncOperate))
			task.PauseAndResumeSync()
			task.Logger.Info(fmt.Sprintf("end %q ...", task.RowData.SyncOperate))
			if task.Err != nil {
				return
			}
			continue
		}
		// upgrade redis-sync
		if task.RowData.SyncOperate == constvar.RedisSyncUpgradeTodo {
			task.Logger.Info(fmt.Sprintf("start execute %q ...", task.RowData.SyncOperate))
			task.UpgradeSyncMedia()
			if task.Err != nil {
				return
			}
			task.SetSyncOperate(constvar.RedisSyncUpgradeSucc)
			task.UpdateDbAndLogLocal(constvar.RedisSyncUpgradeSucc + "...")

			task.Logger.Info(fmt.Sprintf("end %q ...", task.RowData.SyncOperate))
			continue
		}
		// resync from specific time
		if task.RowData.SyncOperate == constvar.ReSyncFromSpecTimeTodo {
			task.Logger.Info(fmt.Sprintf("start execute %q ...", task.RowData.SyncOperate))
			task.ReSyncFromSpecTime(task.RowData.ResyncFromTime.Time)
			if task.Err != nil {
				return
			}
			task.SetSyncOperate(constvar.ReSyncFromSpecTimeSucc)
			task.UpdateDbAndLogLocal(constvar.ReSyncFromSpecTimeSucc + "...")

			task.Logger.Info(fmt.Sprintf("end %q ...", task.RowData.SyncOperate))
			continue
		}
		syncInfoMap := task.RedisSyncInfo("tendis-ssd")
		if task.Err != nil {
			return
		}
		binlogLag, _ := strconv.ParseInt(syncInfoMap["tendis_binlog_lag"], 10, 64)
		if binlogLag < 0 { // 说明 redis-sync没有正常运行
			task.SetTendisBinlogLag(binlogLag)
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal("redis-sync 同步异常,binlog延迟:%d", binlogLag)
			continue
		}
		tendisIP := syncInfoMap["tendis-ssd_ip"]
		tendisPort := syncInfoMap["tendis_port"]
		if tendisIP != task.RowData.SrcIP || tendisPort != strconv.Itoa(task.RowData.SrcPort) {
			task.Err = fmt.Errorf("redis-sync:%s#%d 同步redis:%s#%s的binlog 不等于 %s#%d,同步源redis不对?",
				"127.0.0.1", task.RowData.SyncerPort,
				tendisIP, tendisPort,
				task.RowData.SrcIP, task.RowData.SrcPort)
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			return
		}
		if binlogLag < 600 && slaveLogCountDecr == false {
			// 如果redis-sync同步延迟在600s以内,则修改srcSlave slave-log-keep-count=1200w,避免告警
			task.ChangeSrcSSDKeepCount(1200 * 10000)
			if task.Err != nil {
				return
			}
			slaveLogCountDecr = true
		}
		lastKey, _ := syncInfoMap["tendis_last_key"]
		task.SetTendisBinlogLag(binlogLag)
		task.SetMessage("binlog延迟:%d秒,lastKey:%s", binlogLag, lastKey)
		task.SetStatus(1)
		task.UpdateRow()

		nowSeq := dtsTask.SyncSeqItem{}
		nowSeq.Time.Time = time.Now().Local()
		nowSeq.RunID = syncInfoMap["tendis_run_id"]
		nowSeq.Seq, _ = strconv.ParseUint(syncInfoMap["tendis_last_seq"], 10, 64)
		task.LastSeq = nowSeq.Seq
		task.Runid = nowSeq.RunID
		task.Err = task.syncSeqSave.SyncSeqWriter(&nowSeq, true)
		if task.Err != nil {
			task.SetMessage(task.Err.Error())
			task.SetStatus(-1)
			task.UpdateRow()
			// not return
		}
		// 如果redis-sync seq 60分钟没有任何变化,则代表同步hang住了
		// 例外情况:
		// 1. 回档临时环境,不会有心跳写入,tendis_last_seq不会变;
		if nowSeq.Seq == lastSeqAndTime.Seq && jobRows[0].SrcClusterType != constvar.UserTwemproxyType {
			if time.Now().Local().Sub(lastSeqAndTime.Time.Time).Minutes() > 60 {
				task.Err = fmt.Errorf("binlog seq 已经60分钟未更新,redis-sync是否hang住?")
				task.SetStatus(-1)
				task.UpdateDbAndLogLocal(task.Err.Error())
				return
			}
		} else {
			lastSeqAndTime = nowSeq
		}
	}
}

// IsSyncAlive sync是否存活
func (task *MakeSyncTask) IsSyncAlive() (isAlive bool, err error) {
	isSyncAliaveCmd := fmt.Sprintf("ps -ef|grep %s_%d|grep 'taskid%d-'|grep -v grep|grep sync|grep conf || true",
		task.RowData.SrcIP, task.RowData.SrcPort, task.RowData.ID)
	task.Logger.Info("", zap.String("isSyncAliaveCmd", isSyncAliaveCmd))
	ret, err := util.RunLocalCmd("bash", []string{"-c", isSyncAliaveCmd}, "", nil, 1*time.Minute, task.Logger)
	if err != nil {
		task.Logger.Error("RedisSyncStop IsSyncAlive fail", zap.Error(err))
		return false, err
	}
	ret = strings.TrimSpace(ret)
	if ret != "" {
		return true, nil
	}
	return false, nil
}

// IsSyncStateOK 同步状态是否本来就ok
func (task *MakeSyncTask) IsSyncStateOK() (ok bool) {
	ok, task.Err = task.IsSyncAlive()
	if task.Err != nil {
		return false
	}
	if !ok {
		return false
	}

	jobRows, err := tendisdb.GetTendisDTSJob(task.RowData.BillID, task.RowData.SrcCluster,
		task.RowData.DstCluster, task.Logger)
	if err != nil {
		return false
	}
	syncInfoMap := task.RedisSyncInfo("tendis-ssd")
	if task.Err != nil {
		return false
	}
	if jobRows[0].SrcClusterType != constvar.UserTwemproxyType {
		// 回档临时环境不会时时有心跳写入,tendis_last_seq不会变
		// 所以直接返回成功
		return true
	}
	firstSeq, _ := strconv.ParseUint(syncInfoMap["tendis_last_seq"], 10, 64)

	time.Sleep(10 * time.Second)

	syncInfoMap = task.RedisSyncInfo("tendis-ssd")
	if task.Err != nil {
		return false
	}
	secondSeq, _ := strconv.ParseUint(syncInfoMap["tendis_last_seq"], 10, 64)

	// 第二次获取的seq比第一次大,则认为sync同步正常
	if secondSeq > firstSeq {
		return true
	}
	return false
}

// RedisSyncStop 关闭redis-sync
func (task *MakeSyncTask) RedisSyncStop() {
	var isAlive bool
	var err error
	isAlive, _ = task.IsSyncAlive()
	if isAlive == false {
		task.Logger.Info(fmt.Sprintf("RedisSyncStop srcRedis:%s#%d sync is not alive",
			task.RowData.SrcIP, task.RowData.SrcPort))
		return
	}
	task.Logger.Info(fmt.Sprintf("RedisSyncStop srcRedis:%s#%d sync is alive", task.RowData.SrcIP, task.RowData.SrcPort))

	// record last sync seq
	opts := []string{"SYNCADMIN", "stop"}
	stopRet := task.redisSyncRunCmd(opts, true)
	if task.Err != nil {
		task.Err = nil // 这里已经需要关闭sync,所以 SYNCADMIN stop 执行错误可忽略
	} else {
		lastSeq, err := dtsTask.SyncSeqItemDecode(stopRet)
		if err != nil {
			task.Err = err
			return
		}
		lastSeq.Time.Time = time.Now().Local()
		task.Err = task.syncSeqSave.SyncSeqWriter(&lastSeq, true)
		if task.Err != nil {
			return
		}
		task.LastSeq = lastSeq.Seq
	}

	// kill redis-sync
	killCmd := fmt.Sprintf(`
	ps -ef|grep %s_%d|grep 'taskid%d-'|grep -v grep|grep sync|grep conf|awk '{print $2}'|while read pid
	do
	kill -9 $pid
	done
	`, task.RowData.SrcIP, task.RowData.SrcPort, task.RowData.ID)
	task.Logger.Info("RedisSyncStop...", zap.String("killCmd", killCmd))
	retryTimes := 0
	for isAlive == true && retryTimes < 5 {
		msg := fmt.Sprintf("Killing redis-sync  times:%d ...", retryTimes+1)
		task.Logger.Info(msg)
		// redis-sync is alive, now kill it
		_, err = util.RunLocalCmd("bash", []string{"-c", killCmd}, "", nil, 1*time.Minute, task.Logger)
		if err != nil {
			task.Logger.Error("Kill redis-sync process fail", zap.Error(err))
		}
		time.Sleep(10 * time.Second)
		retryTimes++
		isAlive, _ = task.IsSyncAlive()
		if isAlive == true {
			task.Logger.Error(fmt.Sprintf("srcRedis:%s#%d,Kill redis-sync fail,process still alive",
				task.RowData.SrcIP, task.RowData.SrcPort))
		}
	}
	if isAlive == true && retryTimes == 5 {
		task.Logger.Error(fmt.Sprintf("srcRedis:%s#%d,Kill redis-sync process failed",
			task.RowData.SrcIP, task.RowData.SrcPort))
		task.Err = fmt.Errorf("Kill redis-sync process failed")
		return
	}
	task.Logger.Info(fmt.Sprintf("srcRedis:%s#%d,kill redis-sync success", task.RowData.SrcIP, task.RowData.SrcPort))
	return
}

func (task *MakeSyncTask) clearOldSyncConfigFile() {
	task.SyncConfFile = strings.TrimSpace(task.SyncConfFile)
	if task.SyncConfFile == "" {
		return
	}
	_, err := os.Stat(task.SyncConfFile)
	if err == nil {
		// rm old sync config file
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s",
			filepath.Dir(task.SyncConfFile), filepath.Base(task.SyncConfFile))
		task.Logger.Info(rmCmd)
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 20*time.Second, task.Logger)
	}
}
func (task *MakeSyncTask) clearOldSyncLogFile() {
	task.SyncLogFile = strings.TrimSpace(task.SyncLogFile)
	if task.SyncLogFile == "" {
		return
	}
	_, err := os.Stat(task.SyncLogFile)
	if err == nil {
		// rm old sync log file
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s",
			filepath.Dir(task.SyncLogFile), filepath.Base(task.SyncLogFile))
		task.Logger.Info(rmCmd)
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 20*time.Second, task.Logger)
	}
}

// createSyncConfigFile create redis-sync config file if not exists
func (task *MakeSyncTask) createSyncConfigFile() {
	syncDir := task.MkSyncDirIfNotExists()
	if task.Err != nil {
		return
	}
	task.SyncConfFile = filepath.Join(syncDir,
		fmt.Sprintf("sync-taskid%d-%d.conf", task.RowData.ID, task.RowData.SyncerPort))

	_, err := os.Stat(task.SyncConfFile)
	if err == nil {
		// if config file exists,return
		task.Logger.Info(fmt.Sprintf("redis-sync config file:%s already exists", task.SyncConfFile))
		return
	}

	currentPath, _ := util.CurrentExecutePath()
	tempFile := filepath.Join(currentPath, "tendisssd-sync-template.conf")
	tempContent, err := ioutil.ReadFile(tempFile)
	if err != nil {
		task.Logger.Error("Read redis-sync template conf fail",
			zap.Error(err), zap.String("templateConfig", tempFile))
		task.Err = fmt.Errorf("Read redis-sync template conf fail.err:%v", err)
		return
	}
	loglevel := "warning"
	debug := viper.GetBool("TENDIS_DEBUG")
	if debug == true {
		loglevel = "debug"
	}
	var keyWhiteRegex string = ""
	var keyBlackRegex string = ""
	if task.RowData.KeyWhiteRegex != "" && !task.IsMatchAny(task.RowData.KeyWhiteRegex) {
		// 部分key迁移时,额外迁移 master_ip 这个 key目的是让binglog seq始终更新
		keyWhiteRegex = task.RowData.KeyWhiteRegex + "|^master_ip"
	}
	if task.RowData.KeyBlackRegex != "" && !task.IsMatchAny(task.RowData.KeyBlackRegex) {
		keyBlackRegex = task.RowData.KeyBlackRegex
	}
	tempData := string(tempContent)
	tempData = strings.ReplaceAll(tempData, "{{SYNC_PORT}}", strconv.Itoa(task.RowData.SyncerPort))
	tempData = strings.ReplaceAll(tempData, "{{SYNC_LOG_FILE}}", task.SyncLogFile)
	tempData = strings.ReplaceAll(tempData, "{{SRC_ADDR}}", task.SrcADDR)
	tempData = strings.ReplaceAll(tempData, "{{SRC_PASSWORD}}", task.SrcPassword)
	tempData = strings.ReplaceAll(tempData, "{{KEY_WHITE_REGEX}}", keyWhiteRegex)
	tempData = strings.ReplaceAll(tempData, "{{KEY_BLACK_REGEX}}", keyBlackRegex)
	tempData = strings.ReplaceAll(tempData, "{{DST_ADDR}}", task.DstADDR)
	tempData = strings.ReplaceAll(tempData, "{{DST_PASSWORD}}", task.DstPassword)
	tempData = strings.ReplaceAll(tempData, "{{LOG_LEVEL}}", loglevel)

	// 如果目标集群是域名,则redis-sync需要先解析域名中的 proxy ips,而后连接;该行为通过 proxy-enable 参数控制
	proxyEnable := "no"
	if util.IsDbDNS(task.GetDstRedisAddr()) {
		proxyEnable = "yes"
	}
	tempData = strings.ReplaceAll(tempData, "{{PROXY_ENABLE}}", proxyEnable)
	err = ioutil.WriteFile(task.SyncConfFile, []byte(tempData), 0755)
	if err != nil {
		task.Logger.Error("Save redis-sync conf fail", zap.Error(err), zap.String("syncConfig", task.SyncConfFile))
		task.Err = fmt.Errorf("Save redis-sync conf fail.err:%v", err)
		return
	}
	task.Logger.Info(fmt.Sprintf("create redis-sync config file:%s success", task.SyncConfFile))
	return
}
func (task *MakeSyncTask) createSyncLogFile() {
	syncDir := task.MkSyncDirIfNotExists()
	if task.Err != nil {
		return
	}
	task.SyncLogFile = filepath.Join(syncDir,
		fmt.Sprintf("log-taskid%d-%d.log", task.RowData.ID, task.RowData.SyncerPort))
	// _, err := os.Stat(syncLogFile)
	// if err == nil {
	// 	// rm old sync log file
	// 	rmCmd := fmt.Sprintf("cd %s && rm -rf %s", syncDir, filepath.Base(syncLogFile))
	// 	task.logger.Info(rmCmd)
	// 	util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 20*time.Second, task.logger)
	// }
	return
}

func (task *MakeSyncTask) redisSyncRunCmd(cmds []string, recordLog bool) (cmdRet string) {
	localIP, err := util.GetLocalIP()
	if err != nil {
		task.Err = err
		task.Logger.Error(err.Error())
		return
	}
	localIP = "127.0.0.1" // redis-sync 绑定的是 127.0.0.1

	opts := []string{"--no-auth-warning", "-h", localIP, "-p", strconv.Itoa(task.RowData.SyncerPort)}
	opts = append(opts, cmds...)

	logCmd := task.RedisCliTool + " " + strings.Join(opts, " ")
	if recordLog == true {
		task.Logger.Info("redis-sync cmd ...", zap.String("cmd", logCmd))
	}

	cmdRet, err = util.RunLocalCmd(task.RedisCliTool, opts, "", nil, 5*time.Second, task.Logger)
	if err != nil {
		task.Err = err
		task.Logger.Error("redis-sync cmd fail", zap.Error(task.Err), zap.String("cmd", logCmd))
		return
	}
	if strings.HasPrefix(cmdRet, "ERR ") == true {
		task.Logger.Info("redis-sync cmd fail", zap.String("cmdRet", cmdRet))
		task.Err = fmt.Errorf("redis-sync cmd fail,err:%v", cmdRet)
		return
	}
	if recordLog == true {
		task.Logger.Info("redis-sync cmd success", zap.String("cmdRet", cmdRet))
	}
	return cmdRet
}

// RedisSyncInfo redis-sync执行info [tendis-ssd]等
func (task *MakeSyncTask) RedisSyncInfo(section string) (infoRets map[string]string) {
	opts := []string{"info", section}
	var str01 string
	maxRetryTimes := 5
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		task.Err = nil
		str01 = task.redisSyncRunCmd(opts, false)
		if task.Err != nil {
			time.Sleep(5 * time.Second)
			continue
		}
		break
	}
	if task.Err != nil {
		return
	}
	infoList := strings.Split(str01, "\n")
	infoRets = make(map[string]string)
	for _, infoItem := range infoList {
		infoItem = strings.TrimSpace(infoItem)
		if strings.HasPrefix(infoItem, "#") {
			continue
		}
		if len(infoItem) == 0 {
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		list01[0] = strings.TrimSpace(list01[0])
		list01[1] = strings.TrimSpace(list01[1])
		infoRets[list01[0]] = list01[1]
	}
	return infoRets
}

// RedisSyncStart 启动redis-sync
func (task *MakeSyncTask) RedisSyncStart(reacquirePort bool) {
	task.Logger.Info(fmt.Sprintf("redis-sync start 源%s 目的%s ...", task.SrcADDR, task.DstADDR))
	defer task.Logger.Info("end redis-sync start")

	dtsTask.PortSyncerMut.Lock() // 串行获取redis-sync端口 和 启动
	defer dtsTask.PortSyncerMut.Unlock()

	if reacquirePort == true {
		task.getMySyncPort(0)
		if task.Err != nil {
			return
		}
	}
	maxRetryTimes := 5
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		task.Err = nil

		task.createSyncLogFile()
		if task.Err != nil {
			return
		}
		task.createSyncConfigFile()
		if task.Err != nil {
			return
		}

		logFile, err := os.OpenFile(task.SyncLogFile, os.O_RDWR|os.O_CREATE, 0755)
		if err != nil {
			task.Logger.Error("open logfile fail", zap.Error(err), zap.String("syncLogFile", task.SyncConfFile))
			task.Err = fmt.Errorf("open logfile fail,err:%v syncLogFile:%s", err, task.SyncLogFile)
			return
		}

		logCmd := fmt.Sprintf("%s -f %s", task.RedisSyncTool, task.SyncConfFile)
		task.Logger.Info(logCmd)

		ctx, cancel := context.WithCancel(context.Background())
		cmd := exec.CommandContext(ctx, task.RedisSyncTool, "-f", task.SyncConfFile)
		cmd.Stdout = logFile
		cmd.Stderr = logFile

		err = cmd.Start()
		if err != nil {
			defer cancel()
			logFile.Close()
			task.Logger.Error("cmd.Start fail", zap.Error(err), zap.String("cmd", logCmd))
			task.Err = fmt.Errorf("cmd.Start fail,err:%v command:%s", err, logCmd)
			return
		}
		go func() {
			err = cmd.Wait()
			if err != nil {
				task.Logger.Error("redis-sync cmd.wait error", zap.Error(err))
			}
		}()

		time.Sleep(5 * time.Second)
		isAlive, err := task.IsSyncAlive()
		if err != nil {
			defer cancel()
			logFile.Close()
			task.Err = err
			task.Logger.Error(task.Err.Error())
			return
		}
		if isAlive == false {
			defer cancel()
			logFile.Close()
			logContent, _ := ioutil.ReadFile(task.SyncLogFile)
			task.Logger.Error("redis-sync start fail", zap.String("failDetail", string(logContent)))
			task.Err = fmt.Errorf("redis-sync start fail,detail:%s", string(logContent))
			if strings.Contains(string(logContent), "Address already in use") {
				// port address already used
				// clear and get sync port again and  retry
				task.clearOldSyncLogFile()
				task.clearOldSyncConfigFile()
				task.getMySyncPort(task.RowData.SyncerPort + 1)
				if task.Err != nil {
					return
				}
				continue
			}
		}
		task.SetSyncerPid(cmd.Process.Pid)
		break
	}
	if task.Err != nil {
		task.Err = fmt.Errorf("make sync start fail")
		return
	}

	// 命令: redis-cli -h $redis_sync_ip -p $redis_sync_port CNYS 2 $last_seq x $runid
	opts := []string{"CNYS", "2", strconv.FormatUint(task.LastSeq, 10), "x", task.Runid}
	ret01 := task.redisSyncRunCmd(opts, true)
	if task.Err != nil {
		return
	}
	task.Logger.Info("redis-sync CNYS cmd success", zap.String("cmdRet", ret01))

	// 命令: redis-cli -h $redis_sync_ip -p $redis_sync_port SYNCADMIN start
	opts = []string{"SYNCADMIN", "start"}
	ret02 := task.redisSyncRunCmd(opts, true)
	if task.Err != nil {
		return
	}
	task.Logger.Info("redis-sync SYNCADMIN cmd success", zap.String("cmdRet", ret02))
	task.UpdateDbAndLogLocal("redis-sync %d start success", task.RowData.SyncerPort)

	return
}

// PauseAndResumeSync pause and resume redis-sync
func (task *MakeSyncTask) PauseAndResumeSync() {
	// record last sync seq
	opts := []string{"SYNCADMIN", "stop"}
	stopRet := task.redisSyncRunCmd(opts, true)
	if task.Err != nil {
		task.SetSyncOperate(constvar.RedisSyncPauseFail)
		task.UpdateDbAndLogLocal("redis-sync pause fail")
		return
	}
	lastSeq, err := dtsTask.SyncSeqItemDecode(stopRet)
	if err != nil {
		task.Err = err
		task.SetSyncOperate(constvar.RedisSyncPauseFail)
		task.UpdateDbAndLogLocal("redis-sync pause fail,err:%v", err)
		return
	}
	lastSeq.Time.Time = time.Now().Local()
	task.Err = task.syncSeqSave.SyncSeqWriter(&lastSeq, true)
	if task.Err != nil {
		return
	}
	task.SetSyncOperate(constvar.RedisSyncPauseSucc)
	task.UpdateDbAndLogLocal("Redis-sync 暂停同步成功,seq:%d", lastSeq.Seq)

	for {
		time.Sleep(10 * time.Second)

		row01, err := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
		if err != nil {
			task.Err = err
			return
		}
		if row01 == nil {
			task.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", task.RowData.ID, row01)
			return
		}
		task.RowData = row01
		if task.RowData.SyncOperate == constvar.RedisSyncResumeTodo {
			opts = []string{"SYNCADMIN", "start"}
			task.redisSyncRunCmd(opts, true)
			if task.Err != nil {
				task.SetSyncOperate(constvar.RedisSyncResumeFail)
				task.Logger.Error("redis-sync resume fail", zap.Error(task.Err))
				return
			}
			task.SetSyncOperate(constvar.RedisSyncResumeSucc)
			task.UpdateDbAndLogLocal("Redis-sync 恢复同步成功")
			return
		}
	}
}

// UpgradeSyncMedia 更新redis-sync介质
func (task *MakeSyncTask) UpgradeSyncMedia() {
	defer func() {
		if task.Err != nil {
			task.SetSyncOperate(constvar.RedisSyncUpgradeFail)
		}
	}()
	// stop redis-sync and save lastSeq
	task.RedisSyncStop()
	if task.Err != nil {
		return
	}
	task.GetMyRedisSyncTool(true)
	if task.Err != nil {
		return
	}
	task.RedisSyncStart(false)
	if task.Err != nil {
		return
	}
}

// ReSyncFromSpecTime 从某个时间点重新开始同步
func (task *MakeSyncTask) ReSyncFromSpecTime(time01 time.Time) {
	defer func() {
		if task.Err != nil {
			task.SetSyncOperate(constvar.ReSyncFromSpecTimeFail)
		}
	}()
	specTimeSyncSeq := task.GetSpecificTimeSyncSeq(time01, SyncSubOffset)
	if task.Err != nil {
		return
	}
	// tendisSSD slave确保binlog存在
	task.ConfirmSrcRedisBinlogOK(specTimeSyncSeq.Seq)
	if task.Err != nil {
		return
	}
	// shutdown sync
	task.RedisSyncStop()
	if task.Err != nil {
		return
	}
	// 更新LastSeq
	task.LastSeq = specTimeSyncSeq.Seq

	// start sync
	task.RedisSyncStart(false)
	if task.Err != nil {
		return
	}
}
