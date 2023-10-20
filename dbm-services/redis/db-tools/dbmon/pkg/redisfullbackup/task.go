package redisfullbackup

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/customtime"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"

	"github.com/gofrs/flock"
)

// TendisSSDSetLogCount tendisSSD设置log参数
type TendisSSDSetLogCount struct {
	LogCount          int64 `json:"log-count"`
	SlaveLogKeepCount int64 `json:"slave-log-keep-count"`
}

// BackupTask redis备份task
type BackupTask struct {
	ReportType       string                `json:"report_type"`
	BkBizID          string                `json:"bk_biz_id"`
	BkCloudID        int64                 `json:"bk_cloud_id"`
	ServerIP         string                `json:"server_ip"`
	ServerPort       int                   `json:"server_port"`
	Domain           string                `json:"domain"`
	Password         string                `json:"-"`
	ToBackupSystem   string                `json:"-"`
	DbType           string                `json:"db_type"` // RedisInstance or TendisplusInstance or TendisSSDInstance
	BackupType       string                `json:"-"`       // 常规备份、下线备份
	CacheBackupMode  string                `json:"-"`       // aof or rdb
	RealRole         string                `json:"role"`
	DataSize         uint64                `json:"-"` // redis实例数据大小
	DataDir          string                `json:"-"`
	BackupDir        string                `json:"backup_dir"`
	TarSplit         bool                  `json:"-"` // 是否对tar文件做split
	TarSplitPartSize string                `json:"-"`
	BackupFile       string                `json:"backup_file"`      // 备份的目标文件,如果文件过大会切割成多个
	BackupFileSize   int64                 `json:"backup_file_size"` // 备份文件大小(已切割 or 已压缩 or 已打包)
	BackupTaskID     string                `json:"backup_taskid"`
	BackupMD5        string                `json:"backup_md5"`  // 目前为空
	BackupTag        string                `json:"backup_tag"`  // REDIS_FULL
	ShardValue       string                `json:"shard_value"` // shard值
	StartTime        customtime.CustomTime `json:"start_time"`  // 生成全备的起始时间
	EndTime          customtime.CustomTime `json:"end_time"`    // //生成全备的结束时间
	Status           string                `json:"status"`
	Message          string                `json:"message"`
	Cli              *myredis.RedisClient  `json:"-"`
	SSDLogCount      TendisSSDSetLogCount  `json:"-"`
	reporter         report.Reporter
	backupClient     backupsys.BackupClient
	Err              error `json:"-"`
}

// NewFullBackupTask new backup task
func NewFullBackupTask(bkBizID string, bkCloudID int64, domain, ip string, port int, password,
	toBackupSys, backupType, cacheBackupMode, backupDir string, tarSplit bool, tarSplitSize, shardValue string,
	reporter report.Reporter) (ret *BackupTask, err error) {
	ret = &BackupTask{
		ReportType:       consts.RedisFullBackupReportType,
		BkBizID:          bkBizID,
		BkCloudID:        bkCloudID,
		Domain:           domain,
		ServerIP:         ip,
		ServerPort:       port,
		Password:         password,
		ToBackupSystem:   toBackupSys,
		BackupType:       backupType,
		CacheBackupMode:  cacheBackupMode,
		BackupDir:        backupDir,
		TarSplit:         tarSplit,
		TarSplitPartSize: tarSplitSize,
		BackupTaskID:     "",
		BackupMD5:        "",
		BackupTag:        consts.RedisFullBackupTAG,
		ShardValue:       shardValue,
		reporter:         reporter,
	}
	// ret.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisFullBackupTAG)
	ret.backupClient, err = backupsys.NewCosBackupClient(consts.COSBackupClient, "", consts.RedisFullBackupTAG)
	return
}

// Addr string
func (task *BackupTask) Addr() string {
	return task.ServerIP + ":" + strconv.Itoa(task.ServerPort)
}

// ToString ..
func (task *BackupTask) ToString() string {
	tmpBytes, _ := json.Marshal(task)
	return string(tmpBytes)
}

// BakcupToLocal 执行备份task,备份到本地
func (task *BackupTask) BakcupToLocal() {
	var connSlaves int
	var locked bool
	task.newConnect()
	if task.Err != nil {
		return
	}
	defer task.Cli.Close()

	connSlaves, task.Err = task.Cli.ConnectedSlaves()
	// 如果是redis_master且对应的slave大于0,则跳过备份
	if task.RealRole == consts.RedisMasterRole && connSlaves > 0 {
		mylog.Logger.Info(fmt.Sprintf("redis(%s) is master and has slaves,skip backup", task.Addr()))
		return
	}
	task.reGetShardValWhenClusterEnabled()
	if task.Err != nil {
		return
	}

	// 获取文件锁
	lockFile := fmt.Sprintf("lock.%s.%d", task.ServerIP, task.ServerPort)
	lockFile = filepath.Join(task.BackupDir, "backup", lockFile)
	mylog.Logger.Info(fmt.Sprintf("redis(%s) try to get filelock:%s", task.Addr(), lockFile))

	// 每10秒检测一次是否上锁成功,最多等待3小时
	flock := flock.New(lockFile)
	lockctx, lockcancel := context.WithTimeout(context.Background(), 3*time.Hour)
	defer lockcancel()
	locked, task.Err = flock.TryLockContext(lockctx, 10*time.Second)
	if task.Err != nil {
		task.Err = fmt.Errorf("try to get filelock(%s) fail,err:%v,redis(%s)", lockFile, task.Err, task.Addr())
		mylog.Logger.Error(task.Err.Error())
		return
	}
	if !locked {
		return
	}
	defer flock.Unlock()

	defer func() {
		if task.Err != nil && task.Status == "" {
			task.Message = task.Err.Error()
			task.Status = consts.BackupStatusFailed
		}
		task.BackupRecordReport()
	}()

	task.Status = consts.BackupStatusRunning
	task.Message = "start backup..."
	task.BackupRecordReport()

	mylog.Logger.Info(fmt.Sprintf("redis(%s) dbType:%s start backup...", task.Addr(), task.DbType))

	task.PrecheckDisk()
	if task.Err != nil {
		return
	}

	// 如果有备份正在执行,则先等待其完成
	task.Err = task.Cli.WaitForBackupFinish()
	if task.Err != nil {
		return
	}
	if task.DbType == consts.TendisTypeRedisInstance {
		task.RedisInstanceBackup()
	} else if task.DbType == consts.TendisTypeTendisplusInsance {
		task.TendisplusInstanceBackup()
	} else if task.DbType == consts.TendisTypeTendisSSDInsance {
		task.TendisSSDInstanceBackup()
		if task.Err != nil {
			return
		}
		task.TendisSSDSetLougCount()
	}
	if task.Err != nil {
		return
	}
	defer task.BackupRecordSaveToDoingFile()
	// 备份上传备份系统
	if strings.ToLower(task.ToBackupSystem) != "yes" {
		task.Status = consts.BackupStatusLocalSuccess
		task.Message = "本地备份成功,无需上传备份系统"
		return
	}
	task.TransferToBackupSystem()
	if task.Err != nil {
		task.Status = consts.BackupStatusToBakSystemFailed
		task.Message = task.Err.Error()
		return
	}
	task.Status = consts.BackupStatusToBakSystemStart
	task.Message = "上传备份系统中"
}

func (task *BackupTask) newConnect() {
	task.Cli, task.Err = myredis.NewRedisClient(task.Addr(), task.Password, 0, consts.TendisTypeRedisInstance)
	if task.Err != nil {
		return
	}
	task.RealRole, task.Err = task.Cli.GetRole()
	if task.Err != nil {
		return
	}
	task.DataDir, task.Err = task.Cli.GetDir()
	if task.Err != nil {
		return
	}
	task.DbType, task.Err = task.Cli.GetTendisType()
	if task.Err != nil {
		return
	}
	// 获取数据量大小
	if task.DbType == consts.TendisTypeRedisInstance {
		task.DataSize, task.Err = task.Cli.RedisInstanceDataSize()
	} else if task.DbType == consts.TendisTypeTendisplusInsance {
		task.DataSize, task.Err = task.Cli.TendisplusDataSize()
	} else if task.DbType == consts.TendisTypeTendisSSDInsance {
		task.DataSize, task.Err = task.Cli.TendisSSDDataSize()
	}
	if task.Err != nil {
		return
	}
	return
}

// PrecheckDisk 磁盘检查
func (task *BackupTask) PrecheckDisk() {
	// 检查磁盘空间是否足够
	bakDiskUsg, err := util.GetLocalDirDiskUsg(task.BackupDir)
	task.Err = err
	if task.Err != nil {
		return
	}
	dataDiskUsg, err := util.GetLocalDirDiskUsg(task.DataDir)
	task.Err = err
	if task.Err != nil {
		return
	}
	// 磁盘空间使用已有85%,则报错
	if bakDiskUsg.UsageRatio > 85 || dataDiskUsg.UsageRatio > 85 {
		task.Err = fmt.Errorf("%s disk Used%d%% > 85%% or %s disk Used(%d%%) >85%%",
			task.BackupDir, bakDiskUsg.UsageRatio,
			task.DataDir, dataDiskUsg.UsageRatio)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	if task.DbType == consts.TendisTypeRedisInstance {
		// redisInstance  rdb or aof 都会使用data磁盘空间,如备份会导致磁盘空间超95%则报错
		if int((task.DataSize+dataDiskUsg.UsedSize)*100/dataDiskUsg.TotalSize) > 95 {
			task.Err = fmt.Errorf("redis(%s) data_size(%dMB) bgsave/bgrewriteaof,disk(%s) space will occupy more than 95%%",
				task.Addr(), task.DataSize/1024/1024, task.DataDir)
			mylog.Logger.Error(task.Err.Error())
			return
		}
	}
	if int((task.DataSize+bakDiskUsg.UsedSize)*100/bakDiskUsg.TotalSize) > 95 {
		// 如果备份会导致磁盘空间超95%
		task.Err = fmt.Errorf("redis(%s) data_size(%dMB) backup disk(%s) space will occupy more than 95%%",
			task.Addr(), task.DataSize/1024/1024, task.BackupDir)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	mylog.Logger.Info(fmt.Sprintf(
		"check disk space ok,redis(%s) data_size(%dMB),backupDir disk(%s) available space %dMB",
		task.Addr(), task.DataSize/1024/1024, task.BackupDir, bakDiskUsg.AvailSize/1024/1024))
}

func (task *BackupTask) reGetShardValWhenClusterEnabled() {
	var enabled bool
	var masterNode *myredis.ClusterNodeData
	enabled, task.Err = task.Cli.IsClusterEnabled()
	if task.Err != nil {
		return
	}
	if !enabled {
		return
	}
	masterNode, task.Err = task.Cli.RedisClusterGetMasterNode(task.Addr())
	if task.Err != nil {
		return
	}
	task.ShardValue = masterNode.SlotSrcStr
}

// RedisInstanceBackup redis(cache)实例备份
func (task *BackupTask) RedisInstanceBackup() {
	var srcFile string
	var targetFile string
	var confMap map[string]string
	var fileSize int64
	nowtime := time.Now().Local().Format(consts.FilenameTimeLayout)
	task.StartTime.Time = time.Now().Local()
	if task.RealRole == consts.RedisMasterRole ||
		task.CacheBackupMode == consts.CacheBackupModeRdb {
		// redis master backup rdb
		confMap, task.Err = task.Cli.ConfigGet("dbfilename")
		if task.Err != nil {
			return
		}
		rdbFile := confMap["dbfilename"]
		srcFile = filepath.Join(task.DataDir, rdbFile)
		targetFile = filepath.Join(task.BackupDir,
			fmt.Sprintf("%s-redis-%s-%s-%d-%s.rdb",
				task.BkBizID, task.RealRole, task.ServerIP, task.ServerPort, nowtime))
		task.Err = task.Cli.BgSaveAndWaitForFinish()
	} else {
		srcFile = filepath.Join(task.DataDir, "appendonly.aof")
		targetFile = filepath.Join(task.BackupDir,
			fmt.Sprintf("%s-redis-%s-%s-%d-%s.aof",
				task.BkBizID, task.RealRole, task.ServerIP, task.ServerPort, nowtime))
		task.Err = task.Cli.BgRewriteAOFAndWaitForDone()
	}
	if task.Err != nil {
		return
	}
	task.EndTime.Time = time.Now().Local()
	cpCmd := fmt.Sprintf("cp %s %s", srcFile, targetFile)
	mylog.Logger.Info(cpCmd)
	_, task.Err = util.RunBashCmd(cpCmd, "", nil, 10*time.Minute)
	if task.Err != nil {
		return
	}
	// aof文件,压缩; redis-server默认会对rdb做压缩,所以rdb文件不做压缩
	if strings.HasSuffix(srcFile, ".aof") {
		targetFile, task.Err = util.CompressFile(targetFile, filepath.Dir(targetFile), true)
		if task.Err != nil {
			return
		}
	}
	util.LocalFileChmodAllRead(targetFile)
	task.BackupFile = targetFile
	fileSize, task.Err = util.GetFileSize(targetFile)
	if task.Err != nil {
		mylog.Logger.Error(task.Err.Error())
		return
	}
	task.BackupFileSize = fileSize
	util.LocalDirChownMysql(task.BackupDir)
	mylog.Logger.Info(fmt.Sprintf("redis(%s) local backup success", task.Addr()))
	return
}

// TendisplusInstanceBackup tendisplus实例备份
func (task *BackupTask) TendisplusInstanceBackup() {
	var tarFile string
	nowtime := time.Now().Local().Format(consts.FilenameTimeLayout)
	backName := fmt.Sprintf("%s-TENDISPLUS-FULL-%s-%s-%d-%s", task.BkBizID, task.RealRole, task.ServerIP, task.ServerPort,
		nowtime)
	backupFullDir := filepath.Join(task.BackupDir, backName)
	task.Err = util.MkDirsIfNotExists([]string{backupFullDir})
	if task.Err != nil {
		return
	}
	util.LocalDirChownMysql(task.BackupDir)
	task.StartTime.Time = time.Now().Local()
	task.Err = task.Cli.TendisplusBackupAndWaitForDone(backupFullDir)
	if task.Err != nil {
		return
	}
	task.EndTime.Time = time.Now().Local()
	tarFile, task.Err = util.TarADir(backupFullDir, task.BackupDir, true)
	task.BackupFile = tarFile
	if task.Err != nil {
		mylog.Logger.Error(task.Err.Error())
		return
	}
	task.GetBakFilesSize()
	if task.Err != nil {
		return
	}
	util.LocalFileChmodAllRead(task.BackupFile)
	util.LocalDirChownMysql(task.BackupDir)
	mylog.Logger.Info(fmt.Sprintf("tendisplus(%s) local backup success", task.Addr()))
	return
}

// tendisSSDBackupVerify 确定tendissd备份是否是有效的
func (task *BackupTask) tendisSSDBackupVerify(backupFullDir string) {
	var err error
	verifyBin := consts.TredisverifyBin
	if !util.FileExists(verifyBin) {
		task.Err = fmt.Errorf("%s not exists", verifyBin)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	cmd := fmt.Sprintf(`
export LD_PRELOAD=/usr/local/redis/bin/deps/libjemalloc.so;
export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/usr/local/redis/bin/deps;
%s %s  1 2>/dev/null
	`, verifyBin, backupFullDir)
	mylog.Logger.Info(cmd)
	_, err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if err != nil {
		task.Err = fmt.Errorf("backupData(%s) verify failed", backupFullDir)
		mylog.Logger.Error(task.Err.Error())
		return
	}
}

// TendisSSDInstanceBackup tendisSSD实例备份
func (task *BackupTask) TendisSSDInstanceBackup() {
	var tarFile string
	var binlogsizeRet myredis.TendisSSDBinlogSize
	nowtime := time.Now().Local().Format(consts.FilenameTimeLayout)
	backName := fmt.Sprintf("%s-TENDISSSD-FULL-%s-%s-%d-%s",
		task.BkBizID, task.RealRole, task.ServerIP, task.ServerPort, nowtime)
	backupFullDir := filepath.Join(task.BackupDir, backName)
	task.Err = util.MkDirsIfNotExists([]string{backupFullDir})
	if task.Err != nil {
		return
	}
	util.LocalDirChownMysql(task.BackupDir)
	task.StartTime.Time = time.Now().Local()
	binlogsizeRet, _, task.Err = task.Cli.TendisSSDBackupAndWaitForDone(backupFullDir)
	if task.Err != nil {
		return
	}
	task.EndTime.Time = time.Now().Local()

	task.tendisSSDBackupVerify(backupFullDir)
	if task.Err != nil {
		return
	}

	// 备份文件名带上 binlogPos
	fileWithBinlogPos := fmt.Sprintf("%s-%d", backupFullDir, binlogsizeRet.EndSeq)
	task.Err = os.Rename(backupFullDir, fileWithBinlogPos)
	if task.Err != nil {
		task.Err = fmt.Errorf("rename %s to %s fail,err:%v", backupFullDir, fileWithBinlogPos, task.Err)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	backupFullDir = fileWithBinlogPos

	// 只做打包,不做压缩,rocksdb中已经做了压缩
	tarFile, task.Err = util.TarADir(backupFullDir, task.BackupDir, true)
	if task.Err != nil {
		mylog.Logger.Error(task.Err.Error())
		return
	}
	task.BackupFile = tarFile
	task.GetBakFilesSize()
	if task.Err != nil {
		return
	}
	util.LocalFileChmodAllRead(task.BackupFile)
	util.LocalDirChownMysql(task.BackupDir)
	mylog.Logger.Info(fmt.Sprintf("tendisSSD(%s) local backup success", task.Addr()))
	return
}

// GetBakFilesSize 获取备份文件大小
func (task *BackupTask) GetBakFilesSize() {
	var fileSize int64
	fileSize, task.Err = util.GetFileSize(task.BackupFile)
	if task.Err != nil {
		mylog.Logger.Error(task.Err.Error())
		return
	}
	task.BackupFileSize = fileSize
}

// TendisSSDSetLougCount tendisSSD设置log-count参数
func (task *BackupTask) TendisSSDSetLougCount() {
	if task.SSDLogCount.LogCount > 0 {
		_, task.Err = task.Cli.ConfigSet("log-count", strconv.FormatInt(task.SSDLogCount.LogCount, 10))
		if task.Err != nil {
			return
		}
	}
	if task.SSDLogCount.SlaveLogKeepCount > 0 {
		_, task.Err = task.Cli.ConfigSet("slave-log-keep-count", strconv.FormatInt(task.SSDLogCount.LogCount, 10))
		if task.Err != nil {
			return
		}
	}
}

// TransferToBackupSystem 备份文件上传到备份系统
func (task *BackupTask) TransferToBackupSystem() {
	var msg string
	cliFileInfo, err := os.Stat(consts.COSBackupClient)
	if err != nil {
		err = fmt.Errorf("os.stat(%s) failed,err:%v", consts.COSBackupClient, err)
		mylog.Logger.Error(err.Error())
		return
	}
	if !util.IsExecOther(cliFileInfo.Mode().Perm()) {
		err = fmt.Errorf("%s is unable to execute by other", consts.COSBackupClient)
		mylog.Logger.Error(err.Error())
		return
	}
	mylog.Logger.Info(fmt.Sprintf("redis(%s) backupFiles:%+v start upload backupSystem", task.Addr(), task.BackupFile))
	task.BackupTaskID, task.Err = task.backupClient.Upload(task.BackupFile)
	if task.Err != nil {
		return
	}
	msg = fmt.Sprintf("redis(%s) backupFiles%+v taskid(%+v) uploading to backupSystem",
		task.Addr(), task.BackupFile, task.BackupTaskID)
	mylog.Logger.Info(msg)
	return
}

// BackupRecordReport 备份记录上报
func (task *BackupTask) BackupRecordReport() {
	if task.reporter == nil {
		return
	}
	tmpBytes, _ := json.Marshal(task)
	// task.Err=task.reporter.AddRecord(string(tmpBytes),true)
	task.reporter.AddRecord(string(tmpBytes)+"\n", true)
}

// BackupRecordSaveToDoingFile 备份记录保存到本地 redis_backup_file_list_${port}_doing 文件中
func (task *BackupTask) BackupRecordSaveToDoingFile() {
	backupDir := filepath.Dir(task.BackupFile)
	// 例如: /data/dbbak/backup/redis_backup_file_list_30000_doing
	doingFile := filepath.Join(backupDir, "backup", fmt.Sprintf(consts.DoingRedisFullBackFileList, task.ServerPort))
	f, err := os.OpenFile(doingFile, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0744)
	if err != nil {
		task.Err = fmt.Errorf("os.OpenFile %s failed,err:%v", doingFile, err)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	defer f.Close()
	tmpBytes, _ := json.Marshal(task)

	if _, err = f.WriteString(string(tmpBytes) + "\n"); err != nil {
		task.Err = fmt.Errorf("f.WriteString failed,err:%v,file:%s,line:%s", err, doingFile, string(tmpBytes))
		mylog.Logger.Error(task.Err.Error())
		return
	}
}
