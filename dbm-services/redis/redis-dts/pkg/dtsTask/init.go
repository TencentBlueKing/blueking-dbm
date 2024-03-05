package dtsTask

import (
	"encoding/base64"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/myredis"
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"

	"github.com/dustin/go-humanize"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// FatherTask 迁移父task
type FatherTask struct {
	RowData            *tendisdb.TbTendisDTSTask `json:"rowData"`
	valueChangedFields []string                  // 值已变化的字段名
	TaskDir            string                    `json:"taskDir"`
	Logger             *zap.Logger               `json:"-"`
	Err                error                     `json:"-"`
}

// NewFatherTask  新建tredisdump task
func NewFatherTask(row *tendisdb.TbTendisDTSTask) FatherTask {
	ret := FatherTask{}
	ret.RowData = row
	return ret
}

// SetStatus 设置status的值
func (t *FatherTask) SetStatus(status int) {
	t.RowData.Status = status
	t.valueChangedFields = append(t.valueChangedFields, "Status")
}

// SetTaskType 设置task_type的值
func (t *FatherTask) SetTaskType(taskType string) {
	t.RowData.TaskType = taskType
	t.valueChangedFields = append(t.valueChangedFields, "TaskType")
}

// SetMessage 设置message的值
func (t *FatherTask) SetMessage(format string, args ...interface{}) {
	if len(args) == 0 {
		t.RowData.Message = format
	} else {
		t.RowData.Message = fmt.Sprintf(format, args...)
	}
	t.valueChangedFields = append(t.valueChangedFields, "Message")
}

// SetFetchFile set function
func (t *FatherTask) SetFetchFile(file string) {
	t.RowData.FetchFile = file
	t.valueChangedFields = append(t.valueChangedFields, "FetchFile")
}

// SetSqlfileDir set function
func (t *FatherTask) SetSqlfileDir(dir string) {
	t.RowData.SqlfileDir = dir
	t.valueChangedFields = append(t.valueChangedFields, "SqlfileDir")
}

// SetSyncOperate set function
func (t *FatherTask) SetSyncOperate(op string) {
	t.RowData.SyncOperate = op
	t.valueChangedFields = append(t.valueChangedFields, "SyncOperate")
}

// SetTendisBinlogLag set function
func (t *FatherTask) SetTendisBinlogLag(lag int64) {
	t.RowData.TendisBinlogLag = lag
	t.valueChangedFields = append(t.valueChangedFields, "TendisBinlogLag")
}

// SetSrcNewLogCount set function
func (t *FatherTask) SetSrcNewLogCount(logcnt int64) {
	t.RowData.SrcNewLogCount = logcnt
	t.valueChangedFields = append(t.valueChangedFields, "SrcNewLogCount")
}

// SetSrcOldLogCount set function
func (t *FatherTask) SetSrcOldLogCount(logcnt int64) {
	t.RowData.SrcOldLogCount = logcnt
	t.valueChangedFields = append(t.valueChangedFields, "SrcOldLogCount")
}

// SetIsSrcLogCountRestored set function
func (t *FatherTask) SetIsSrcLogCountRestored(isRestored int) {
	t.RowData.IsSrcLogCountRestored = isRestored
	t.valueChangedFields = append(t.valueChangedFields, "IsSrcLogCountRestored")
}

// SetIgnoreErrlist set function
func (t *FatherTask) SetIgnoreErrlist(errlist string) {
	t.RowData.IgnoreErrlist = errlist
	t.valueChangedFields = append(t.valueChangedFields, "IgnoreErrlist")
}

// SetSyncerPort set function
func (t *FatherTask) SetSyncerPort(syncport int) {
	t.RowData.SyncerPort = syncport
	t.valueChangedFields = append(t.valueChangedFields, "SyncerPort")
}

// SetSyncerPid set function
func (t *FatherTask) SetSyncerPid(syncpid int) {
	t.RowData.SyncerPid = syncpid
	t.valueChangedFields = append(t.valueChangedFields, "SyncerPid")
}

// SetSrcHaveListKeys set function
func (t *FatherTask) SetSrcHaveListKeys(havelist int) {
	t.RowData.SrcHaveListKeys = havelist
	t.valueChangedFields = append(t.valueChangedFields, "SrcHaveListKeys")
}

// SetTendisbackupFile set function
func (t *FatherTask) SetTendisbackupFile(file string) {
	t.RowData.TendisbackupFile = file
	t.valueChangedFields = append(t.valueChangedFields, "TendisbackupFile")
}

// SetDtsServer set function
func (t *FatherTask) SetDtsServer(svrip string) {
	t.RowData.DtsServer = svrip
	t.valueChangedFields = append(t.valueChangedFields, "DtsServer")
}

// UpdateDbAndLogLocal update db相关字段 并记录本地日志
func (t *FatherTask) UpdateDbAndLogLocal(format string, args ...interface{}) {
	t.SetMessage(format, args...)
	t.UpdateRow()
	t.Logger.Info(t.RowData.Message)
}

// UpdateRow update tendisdb相关字段(值变化了的字段)
func (t *FatherTask) UpdateRow() {
	if len(t.valueChangedFields) == 0 {
		return
	}
	t.RowData.UpdateFieldsValues(t.valueChangedFields, t.Logger)
	t.valueChangedFields = []string{}
}

// Init 初始化
func (t *FatherTask) Init() {
	defer func() {
		if t.Err != nil {
			t.SetStatus(-1)
			t.SetMessage(t.Err.Error())
		} else {
			t.SetStatus(1) // 更新为running状态
		}
		t.UpdateRow()
	}()
	t.Err = t.InitLogger()
	if t.Err != nil {
		return
	}
	if t.RowData.SyncOperate == constvar.RedisForceKillTaskTodo {
		t.RowData.SyncOperate = constvar.RedisForceKillTaskSuccess
		t.Err = fmt.Errorf(constvar.RedisForceKillTaskSuccess + "...")
		return
	}
}

// InitTaskDir 初始化本地任务目录
func (t *FatherTask) InitTaskDir() error {
	currExecPath, err := util.CurrentExecutePath()
	if err != nil {
		return err
	}
	domainPort := strings.Split(t.RowData.SrcCluster, ":")
	subDir := fmt.Sprintf("tasks/%d_%s_%s/%s_%d", t.RowData.BillID,
		domainPort[0], domainPort[1], t.RowData.SrcIP, t.RowData.SrcPort)
	t.TaskDir = filepath.Join(currExecPath, subDir)
	err = util.MkDirIfNotExists(t.TaskDir)
	if err != nil {
		return err
	}
	return nil
}

// InitLogger 初始化日志文件logger
func (t *FatherTask) InitLogger() error {
	err := t.InitTaskDir()
	if err != nil {
		return nil
	}
	var logFile string
	if t.RowData.SrcDbType == constvar.TendisTypeTendisplusInsance {
		logFile = fmt.Sprintf("task_%s_%d_kvstore_%d.log",
			t.RowData.SrcIP, t.RowData.SrcPort, t.RowData.SrcKvStoreID)
	} else {
		logFile = fmt.Sprintf("task_%s_%d.log", t.RowData.SrcIP, t.RowData.SrcPort)
	}
	fullPath := filepath.Join(t.TaskDir, logFile)
	t.Logger = tclog.NewFileLogger(fullPath)
	return nil
}

// IsSupportPipeImport 是否支持 redis-cli --pipe < $file 导入
func (t *FatherTask) IsSupportPipeImport() bool {
	// if strings.HasPrefix(t.RowData.DstCluster, "tendisx") || constvar.IsGlobalEnv() == true {
	// 	return true
	// }
	return true
}

// TredisdumpOuputFormat tredisdump结果文件内容格式,resp格式 或 普通命令格式
func (t *FatherTask) TredisdumpOuputFormat() string {
	if t.IsSupportPipeImport() {
		return constvar.TredisdumpRespFormat
	}
	return constvar.TredisdumpCmdFormat
}

// TredisdumpOuputFileSize tredisdump结果文件大小
func (t *FatherTask) TredisdumpOuputFileSize() uint64 {
	var fileSize uint64 = 0
	var sizeStr string
	if t.IsSupportPipeImport() {
		sizeStr = viper.GetString("tredisdumpOutputRespFileSize")
		fileSize, _ = humanize.ParseBytes(sizeStr)
		if fileSize <= 0 {
			fileSize = constvar.MiByte // resp格式,单文件默认1MB
		} else if fileSize > 100*constvar.MiByte {
			fileSize = 100 * constvar.MiByte // redis-cli --pipe < $file 导入单个文件不宜过大,否则可能导致proxy oom,最大100MB
		}
	} else {
		sizeStr = viper.GetString("tredisdumpOutputCmdFileSize")
		fileSize, _ = humanize.ParseBytes(sizeStr)
		if fileSize <= 0 {
			fileSize = 1 * constvar.GiByte // 普通命令格式,单个文件默认1GB
		} else if fileSize > 50*constvar.GiByte {
			fileSize = 50 * constvar.GiByte // redis-cli < $file 导入单个文件不宜过大,否则事件很长,最大50GB
		}
	}
	return fileSize
}

// ImportParallelLimit 导入并发度
func (t *FatherTask) ImportParallelLimit() int {
	limit := 0
	if t.IsSupportPipeImport() {
		limit = viper.GetInt("respFileImportParallelLimit")
		if limit <= 0 {
			limit = 1
		} else if limit > 10 {
			limit = 20 // redis-cli --pipe < $file 导入数据,并发度不宜过大
		}
	} else {
		limit = viper.GetInt("cmdFileImportParallelLimit")
		if limit <= 0 {
			limit = 40
		} else if limit > 100 {
			limit = 100 // redis-cli < $file 导入并发度控制100以内
		}
	}
	return limit
}

// ImportTimeout 导入并发度
func (t *FatherTask) ImportTimeout() int {
	timeout := 0
	if t.IsSupportPipeImport() {
		timeout = viper.GetInt("respFileImportTimeout")
		if timeout <= 0 {
			timeout = 120 // redis-cli --pipe --pipe-timeout 默认120s超时
		} else if timeout > 600 {
			timeout = 600 // redis-cli --pipe --pipe-timeout < $file,最大超时10分钟
		}
	} else {
		timeout = viper.GetInt("cmdFileImportTimeout")
		if timeout <= 0 {
			timeout = 604800 // redis-cli < $file,默认7天超时
		} else if timeout > 604800 {
			timeout = 604800 // redis-cli < $file 导入最大7天超时
		}
	}
	return timeout
}

func (t *FatherTask) newSrcRedisClient() *myredis.RedisWorker {
	srcAddr := fmt.Sprintf("%s:%d", t.RowData.SrcIP, t.RowData.SrcPort)
	srcPasswd, err := base64.StdEncoding.DecodeString(t.RowData.SrcPassword)
	if err != nil {
		t.Logger.Error("SaveSrcSSDKeepCount base64.decode srcPasswd fail",
			zap.Error(err), zap.String("rowData", t.RowData.ToString()))
		t.Err = fmt.Errorf("SaveSrcSSDKeepCount get src password fail,err:%v", err)
		return nil
	}
	srcClient, err := myredis.NewRedisClient(srcAddr, string(srcPasswd), 0, t.Logger)
	if err != nil {
		t.Err = err
		return nil
	}
	return srcClient
}

// SaveSrcSSDKeepCount 保存source ssd的 slave-log-keep-count值
func (t *FatherTask) SaveSrcSSDKeepCount() {
	var logcnt int64
	srcClient := t.newSrcRedisClient()
	if t.Err != nil {
		return
	}
	defer srcClient.Close()

	keepCountMap, err := srcClient.ConfigGet("slave-log-keep-count")
	if err != nil {
		t.Err = err
		return
	}
	if len(keepCountMap) > 0 {
		val01, ok := keepCountMap["slave-log-keep-count"]
		if ok == true {
			t.Logger.Info("SaveSrcSSDKeepCount slave-log-keep-count old value...",
				zap.String("slave-log-keep-count", val01))
			logcnt, _ = strconv.ParseInt(val01, 10, 64)
			t.SetSrcOldLogCount(logcnt)
			t.SetIsSrcLogCountRestored(1)
			t.UpdateRow()
			return
		}
	}
	return
}

// RestoreSrcSSDKeepCount 恢复source ssd的 slave-log-keep-count值
func (t *FatherTask) RestoreSrcSSDKeepCount() {
	srcClient := t.newSrcRedisClient()
	if t.Err != nil {
		return
	}
	defer srcClient.Close()

	_, t.Err = srcClient.ConfigSet("slave-log-keep-count", t.RowData.SrcOldLogCount)
	if t.Err != nil {
		return
	}
	t.SetIsSrcLogCountRestored(2)
	t.UpdateDbAndLogLocal("slave-log-keep-count restore ok")

	return
}

// ChangeSrcSSDKeepCount 修改source ssd的 slave-log-keep-count值
func (t *FatherTask) ChangeSrcSSDKeepCount(dstKeepCount int64) {
	srcClient := t.newSrcRedisClient()
	if t.Err != nil {
		return
	}
	defer srcClient.Close()

	_, t.Err = srcClient.ConfigSet("slave-log-keep-count", dstKeepCount)
	if t.Err != nil {
		return
	}
	return
}

// GetSyncSeqFromFullBackup get sync pos from full backup
func (t *FatherTask) GetSyncSeqFromFullBackup() (ret *SyncSeqItem) {
	var err error
	ret = &SyncSeqItem{}
	syncPosFile := filepath.Join(t.RowData.SqlfileDir, "sync-pos.txt")
	_, err = os.Stat(syncPosFile)
	if err != nil && os.IsNotExist(err) == true {
		t.Err = fmt.Errorf("%s not exists,err:%v", syncPosFile, err)
		t.Logger.Error(t.Err.Error())
		return nil
	}
	posData, err := ioutil.ReadFile(syncPosFile)
	if err != nil {
		t.Logger.Error("Read sync-pos.txt fail", zap.Error(err),
			zap.String("syncPosFile", syncPosFile))
		t.Err = fmt.Errorf("Read sync-pos.txt fail.err:%v", err)
		return nil
	}
	posStr := string(posData)
	posStr = strings.TrimSpace(posStr)
	posList := strings.Fields(posStr)
	if len(posList) < 2 {
		t.Err = fmt.Errorf("sync-pos.txt content nor correct,syncPosFile:%s", syncPosFile)
		t.Logger.Error(t.Err.Error())
		return nil
	}
	t.Logger.Info("sync-pos.txt content ...", zap.String("syncPosData", posStr))
	ret.RunID = posList[0]
	ret.Seq, err = strconv.ParseUint(posList[1], 10, 64)
	if err != nil {
		t.Err = fmt.Errorf("sync-pos.txt seq:%s to uint64 fail,err:%v", posList[1], err)
		t.Logger.Error(t.Err.Error())
		return nil
	}
	return ret
}

// ConfirmSrcRedisBinlogOK confirm binlog seq is OK in src redis
func (t *FatherTask) ConfirmSrcRedisBinlogOK(seq uint64) {
	srcAddr := fmt.Sprintf("%s:%d", t.RowData.SrcIP, t.RowData.SrcPort)
	srcPasswd, err := base64.StdEncoding.DecodeString(t.RowData.SrcPassword)
	if err != nil {
		t.Logger.Error(constvar.TendisBackupTaskType+" init base64.decode srcPasswd fail",
			zap.Error(err), zap.String("rowData", t.RowData.ToString()))
		t.Err = fmt.Errorf("[fatherTask] get src password fail,err:%v", err)
		return
	}
	srcClient, err := myredis.NewRedisClient(srcAddr, string(srcPasswd), 0, t.Logger)
	if err != nil {
		t.Err = err
		return
	}
	defer srcClient.Close()
	srcBinlogSeqRange, err := srcClient.TendisSSDBinlogSize()
	if err != nil {
		t.Err = err
		return
	}
	if seq < srcBinlogSeqRange.FirstSeq {
		t.Err = fmt.Errorf("srcRedis:%s current binlog seq range:[%d,%d] > seq:%d",
			srcAddr, srcBinlogSeqRange.FirstSeq, srcBinlogSeqRange.EndSeq, seq)
		t.Logger.Error(t.Err.Error())
		return
	}
	if seq > srcBinlogSeqRange.EndSeq {
		t.Err = fmt.Errorf("srcRedis:%s current binlog seq range:[%d,%d] < seq:%d",
			srcAddr, srcBinlogSeqRange.FirstSeq, srcBinlogSeqRange.EndSeq, seq)
		t.Logger.Error(t.Err.Error())
		return
	}
	t.Logger.Info(fmt.Sprintf("srcRedis:%s current binlog seq range:[%d,%d],seq:%d is ok",
		srcAddr, srcBinlogSeqRange.FirstSeq, srcBinlogSeqRange.EndSeq, seq))

	return
}

// ClearSrcHostBackup clear src redis remote backup
func (t *FatherTask) ClearSrcHostBackup() {
	if strings.Contains(t.RowData.TendisbackupFile, "REDIS_FULL_rocksdb_") == false {
		return
	}
	// 清理srcIP上的backupFile文件,避免占用过多空间
	t.Logger.Info("ClearSrcHostBackup srcIP clear backupfile",
		zap.String("cmd", fmt.Sprintf(`cd /data/dbbak/ && rm -rf %s >/dev/null 2>&1`, t.RowData.TendisbackupFile)),
		zap.String("srcIP", t.RowData.SrcIP))

	rmCmd := fmt.Sprintf(`cd /data/dbbak/ && rm -rf %s >/dev/null 2>&1`, t.RowData.TendisbackupFile)
	cli, err := scrdbclient.NewClient(constvar.BkDbm, t.Logger)
	if err != nil {
		t.Err = err
		return
	}
	_, err = cli.ExecNew(scrdbclient.FastExecScriptReq{
		Account:        "mysql",
		Timeout:        3600,
		ScriptLanguage: 1,
		ScriptContent:  rmCmd,
		IPList: []scrdbclient.IPItem{
			{
				BkCloudID: int(t.RowData.BkCloudID),
				IP:        t.RowData.SrcIP,
			},
		},
	}, 5)
	if err != nil {
		t.Err = err
		return
	}
}

// ClearLocalFetchBackup clear src redis local backup
func (t *FatherTask) ClearLocalFetchBackup() {
	srcAddr := fmt.Sprintf("%s_%d", t.RowData.SrcIP, t.RowData.SrcPort)
	if strings.Contains(t.RowData.FetchFile, srcAddr) == false {
		// fetchFile 必须包含 srcAddr,否则不确定传入的是什么参数,对未知目录 rm -rf 很危险
		t.Logger.Warn("ClearLocalFetchBackup fetchFile not include srcAddr",
			zap.String("fetchFile", t.RowData.FetchFile), zap.String("srcAddr", srcAddr))
		return
	}
	_, err := os.Stat(t.RowData.FetchFile)
	if err == nil {
		// 文件存在,则清理
		rmCmd := fmt.Sprintf("rm -rf %s > /dev/null 2>&1", t.RowData.FetchFile)
		t.Logger.Info(fmt.Sprintf("ClearLocalFetchBackup execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 120*time.Second, t.Logger)
	}
}

// ClearLocalSQLDir clear local sql dir(backup to commands)
func (t *FatherTask) ClearLocalSQLDir() {
	srcAddr := fmt.Sprintf("%s_%d", t.RowData.SrcIP, t.RowData.SrcPort)
	if strings.Contains(t.RowData.SqlfileDir, srcAddr) == false {
		// fetchFile 必须包含 srcAddr,否则不确定传入的是什么参数,对未知目录 rm -rf 很危险
		t.Logger.Warn("ClearLocalSqlDir sqlDir not include srcAddr",
			zap.String("sqlDir", t.RowData.SqlfileDir), zap.String("srcAddr", srcAddr))
		return
	}
	_, err := os.Stat(t.RowData.SqlfileDir)
	if err == nil {
		// 文件存在,则清理
		rmCmd := fmt.Sprintf("rm -rf %s > /dev/null 2>&1", t.RowData.SqlfileDir)
		t.Logger.Info(fmt.Sprintf("ClearLocalSqlDir execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 120*time.Second, t.Logger)
	}
}

// DealProcessPid 处理进程id;
// 如用户发送 ForceKillTaskTodo '强制终止' 指令,则tredisdump、redis-cli等命令均执行kill操作
func (t *FatherTask) DealProcessPid(pid int) error {
	go func(pid01 int) {
		bakTaskType := t.RowData.TaskType
		bakStatus := t.RowData.Status
		if bakStatus != 1 {
			return
		}
		for {
			time.Sleep(10 * time.Second)
			row01, err := tendisdb.GetTaskByID(t.RowData.ID, t.Logger)
			if err != nil {
				continue
			}
			if row01 == nil {
				t.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", t.RowData.ID, row01)
				continue
			}
			if row01.SyncOperate == constvar.RedisForceKillTaskTodo {
				// 命令执行中途,用户要求强制终止
				retryTimes := 0
				for retryTimes < 5 {
					retryTimes++
					isAlive, err := util.CheckProcessAlive(pid01)
					if err != nil {
						tclog.Logger.Error(err.Error() + ",retry ...")
						time.Sleep(1 * time.Second)
						continue
					}
					if !isAlive {
						t.Logger.Error(fmt.Sprintf("kill pid:%d success", pid01))
						break
					}
					err = util.KillProcess(pid01)
					if err != nil {
						t.Logger.Error(fmt.Sprintf("kill pid:%d fail,err:%v", pid01, err))
						continue
					}
					break
				}
				t.RowData.SyncOperate = constvar.RedisForceKillTaskSuccess
				t.Err = fmt.Errorf("%s...", constvar.RedisForceKillTaskSuccess)
				return
			}
			if row01.TaskType != bakTaskType || row01.Status != bakStatus {
				// task本阶段已执行完
				return
			}
		}
	}(pid)
	return nil
}

// TredisdumpThreadCnt get tredisdump threadcnt
func (t *FatherTask) TredisdumpThreadCnt() int {
	threadCnt := viper.GetInt("tredisdumpTheadCnt")
	if threadCnt <= 0 {
		threadCnt = 10 // default 10
	} else if threadCnt > 50 {
		threadCnt = 50 // max threadcnt 50,并发度不宜过大
	}
	return threadCnt
}

// SaveIgnoreErrs 记录忽略的错误类型
func (t *FatherTask) SaveIgnoreErrs(igErrs []string) {
	isUpdated := false
	for _, igErr := range igErrs {
		if strings.Contains(t.RowData.IgnoreErrlist, igErr) == false {
			if t.RowData.IgnoreErrlist == "" {
				t.SetIgnoreErrlist(igErr)
			} else {
				t.SetIgnoreErrlist(t.RowData.IgnoreErrlist + "," + igErr)
			}
			isUpdated = true
		}
	}
	if isUpdated == true {
		t.UpdateRow()
	}
}

// IsMatchAny is match all
func (t *FatherTask) IsMatchAny(reg01 string) bool {
	return reg01 == "*" || reg01 == ".*" || reg01 == "^.*$"
}

// RefreshRowData refresh task row data
func (task *FatherTask) RefreshRowData() {
	row01, err := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
	if err != nil {
		task.Err = err
		return
	}
	if row01 == nil {
		task.Err = fmt.Errorf("get task row data empty record,task_id:%d", task.RowData.ID)
		task.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", task.RowData.ID, row01)
		return
	}
	task.RowData = row01
}

// GetSrcRedisAddr 源redis_addr
func (task *FatherTask) GetSrcRedisAddr() string {
	return task.RowData.SrcIP + ":" + strconv.Itoa(task.RowData.SrcPort)
}

// GetSrcRedisPasswd 源redis_password
func (task *FatherTask) GetSrcRedisPasswd() string {
	srcPasswd, err := base64.StdEncoding.DecodeString(task.RowData.SrcPassword)
	if err != nil {
		task.Err = fmt.Errorf("decode srcPassword fail,err:%v,taskid:%d", err, task.RowData.ID)
		task.UpdateDbAndLogLocal("decode srcPassword fail,err:%v,encodedPassword:%s,taskID:%d",
			err, task.RowData.SrcPassword, task.RowData.ID)
	}
	return string(srcPasswd)
}

// GetDstRedisAddr 目的redis_addr
func (task *FatherTask) GetDstRedisAddr() string {
	return task.RowData.DstCluster
}

// GetDstRedisPasswd 目的redis_password
func (task *FatherTask) GetDstRedisPasswd() string {
	dstPasswd, err := base64.StdEncoding.DecodeString(task.RowData.DstPassword)
	if err != nil {
		task.Err = fmt.Errorf("decode DstPassword fail,err:%v,taskid:%d", err, task.RowData.ID)
		task.UpdateDbAndLogLocal("decode DstPassword fail,err:%v,encodedPassword:%s,taskID:%d",
			err, task.RowData.DstPassword, task.RowData.ID)
	}
	return string(dstPasswd)
}

// DisableDstClusterSlowlog  dst cluster 'config set slowlog-log-slower-than -1'
func (task *FatherTask) DisableDstClusterSlowlog() {
	dstProxyAddrs, err := util.LookupDbDNSIPs(task.RowData.DstCluster)
	if err != nil {
		task.Logger.Error(err.Error())
		return
	}
	task.Logger.Info(fmt.Sprintf(
		"DisableDstClusterSlowlog %s all proxys:[%+v] run 'config set slowlog-log-slower-than -1'",
		dstProxyAddrs, task.RowData.DstCluster))
	dstPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.DstPassword)
	wg := sync.WaitGroup{}
	for _, dstAddr := range dstProxyAddrs {
		wg.Add(1)
		go func(addr string) {
			defer wg.Done()
			cli01, err := myredis.NewRedisClient(addr, string(dstPasswd), 0, task.Logger)
			if err != nil {
				return
			}
			defer cli01.Close()
			cli01.ConfigSet("slowlog-log-slower-than", -1)
		}(dstAddr)
	}
	wg.Wait()
}

// EnableDstClusterSlowlog  dst cluster 'config set slowlog-log-slower-than 100000'
func (task *FatherTask) EnableDstClusterSlowlog() {
	dstProxyAddrs, err := util.LookupDbDNSIPs(task.RowData.DstCluster)
	if err != nil {
		task.Logger.Error(err.Error())
		return
	}
	task.Logger.Info(fmt.Sprintf(
		"EnablestClusterSlowlog %s all proxys:[%+v] run 'config set slowlog-log-slower-than 100000'",
		dstProxyAddrs, task.RowData.DstCluster))
	dstPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.DstPassword)
	wg := sync.WaitGroup{}
	for _, dstAddr := range dstProxyAddrs {
		wg.Add(1)
		go func(addr string) {
			defer wg.Done()
			cli01, err := myredis.NewRedisClient(addr, string(dstPasswd), 0, task.Logger)
			if err != nil {
				return
			}
			defer cli01.Close()
			cli01.ConfigSet("slowlog-log-slower-than", 100000)
		}(dstAddr)
	}
	wg.Wait()
}

// GetTaskParallelLimit 从配置文件中获取每一类task的并发度
func GetTaskParallelLimit(taskType string) int {
	limit01 := viper.GetInt(taskType + "ParallelLimit")
	if limit01 == 0 {
		limit01 = 5 // 默认值5
	}
	return limit01
}

// PortSyncerMut 保证makeSync串行执行,因为redis-syncer启动前需要获取port信息,避免彼此抢占
var PortSyncerMut *sync.Mutex

func init() {
	PortSyncerMut = &sync.Mutex{}
}
