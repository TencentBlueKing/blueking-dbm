package redisbinlogbackup

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
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

// tendisssd binlog文件正则
// 例如: binlog-30000-0007426-20221109221541.log
// tendisplus binlog文件正则
// 例如: binlog-0-0000887-20221107123830.log
var tendisBinlogReg = regexp.MustCompile(`binlog-(\d+)-(\d+)-(\d+).log`)

// Task redis binlog备份task
type Task struct {
	ReportType     string                `json:"report_type"`
	BkBizID        string                `json:"bk_biz_id"`
	BkCloudID      int64                 `json:"bk_cloud_id"`
	ServerIP       string                `json:"server_ip"`
	ServerPort     int                   `json:"server_port"`
	Domain         string                `json:"domain"`
	Password       string                `json:"-"`
	ToBackupSystem string                `json:"-"`
	OldFileLeftDay int                   `json:"-"`
	DbType         string                `json:"db_type"` // TendisplusInstance or TendisSSDInstance
	RealRole       string                `json:"role"`
	DumpDir        string                `json:"-"`
	KvStoreCount   int                   `json:"-"`
	BackupDir      string                `json:"backup_dir"`       // 备份路径,如 /data/dbbak/binlog/30000
	BackupFile     string                `json:"backup_file"`      // 备份的目标文件(已压缩)
	KvstoreIdx     int                   `json:"kvstoreidx"`       // binlog对应的 kvstoreidx
	BackupFileSize int64                 `json:"backup_file_size"` // 备份文件大小(已压缩)
	StartTime      customtime.CustomTime `json:"start_time"`       // binlog文件生成时间(非压缩)
	EndTime        customtime.CustomTime `json:"end_time"`         // binlog文件最后修改时间(非压缩)
	BackupTaskID   string                `json:"backup_taskid"`
	BackupMD5      string                `json:"backup_md5"`  // 目前为空
	BackupTag      string                `json:"backup_tag"`  // REDIS_BINLOG
	ShardValue     string                `json:"shard_value"` // shard值
	Status         string                `json:"status"`
	Message        string                `json:"message"`
	Cli            *myredis.RedisClient  `json:"-"`
	reporter       report.Reporter
	backupClient   backupsys.BackupClient
	lockFile       string `json:"-"`
	Err            error  `json:"-"`
}

// NewBinlogBackupTask new binlog backup task
func NewBinlogBackupTask(bkBizID string, bkCloudID int64, domain, ip string, port int,
	password, toBackupSys, backupDir, shardValue string, oldFileLeftDay int,
	reporter report.Reporter) *Task {

	ret := &Task{
		ReportType:     consts.RedisBinlogBackupReportType,
		BkBizID:        bkBizID,
		BkCloudID:      bkCloudID,
		Domain:         domain,
		ServerIP:       ip,
		ServerPort:     port,
		Password:       password,
		ToBackupSystem: toBackupSys,
		OldFileLeftDay: oldFileLeftDay,
		BackupDir:      backupDir,
		BackupTag:      consts.RedisBinlogTAG,
		reporter:       reporter,
		ShardValue:     shardValue,
	}
	ret.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisBinlogTAG)
	// ret.backupClient, ret.Err = backupsys.NewCosBackupClient(consts.COSBackupClient, "", consts.RedisBinlogTAG)
	return ret
}

// Addr string
func (task *Task) Addr() string {
	return task.ServerIP + ":" + strconv.Itoa(task.ServerPort)
}

// ToString ..
func (task *Task) ToString() string {
	tmpBytes, _ := json.Marshal(task)
	return string(tmpBytes)
}

// BackupLocalBinlogs 备份本地binlog文件
func (task *Task) BackupLocalBinlogs() {
	var err error
	var locked bool
	task.newConnect()
	if task.Err != nil {
		return
	}
	defer task.Cli.Close()

	defer util.LocalDirChownMysql(task.BackupDir)

	if task.DbType == consts.TendisTypeRedisInstance {
		return
	}

	task.reGetShardValWhenClusterEnabled()
	if task.Err != nil {
		return
	}

	// 获取文件锁
	lockFile := fmt.Sprintf("lock.%s.%d", task.ServerIP, task.ServerPort)
	lockFile = filepath.Join(task.BackupDir, lockFile)
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

	binlogs := task.GetTendisBinlogs()
	if task.Err != nil {
		return
	}
	oldFileLeftSec := task.OldFileLeftDay * 24 * 3600
	for _, item := range binlogs {
		// 如果文件太旧则删除
		if time.Now().Local().Sub(item.FileMtime).Seconds() > float64(oldFileLeftSec) {
			if util.FileExists(item.File) {
				err = os.Remove(item.File)
				if err != nil {
					err = fmt.Errorf("os.Remove %s fail,err:%v", item.File, err)
					mylog.Logger.Error(err.Error())
				} else {
					mylog.Logger.Info(fmt.Sprintf("old binlog %s removed,nowTime=%s,fmtime=%s,subSecs=%d,", item.File,
						time.Now().Local().Format(consts.UnixtimeLayout),
						item.FileMtime.Format(consts.UnixtimeLayout),
						int(time.Now().Local().Sub(item.FileMtime).Seconds())))
				}
				continue
			}
		}
		task.BackupFile = item.File
		task.KvstoreIdx = item.KvStoreIdx
		task.StartTime.Time = item.StartTime
		task.EndTime.Time = item.FileMtime
		task.compressAndUpload() // 无论成功还是失败,都继续下一个binlog file
	}
}
func (task *Task) newConnect() {
	task.Cli, task.Err = myredis.NewRedisClient(task.Addr(), task.Password, 0, consts.TendisTypeRedisInstance)
	if task.Err != nil {
		return
	}
	task.RealRole, task.Err = task.Cli.GetRole()
	if task.Err != nil {
		return
	}
	task.DumpDir, task.Err = task.Cli.GetDumpDir()
	if task.Err != nil {
		return
	}
	task.DbType, task.Err = task.Cli.GetTendisType()
	if task.Err != nil {
		return
	}
	// 除tendisplus外,其余db类型, kvstorecount=1
	if task.DbType != consts.TendisTypeTendisplusInsance {
		task.KvStoreCount = 1
		return
	}
	// tendisplus的kvstorecount实际获取
	task.KvStoreCount, task.Err = task.Cli.GetKvstoreCount()
	if task.Err != nil {
		return
	}
	return
}

func (task *Task) reGetShardValWhenClusterEnabled() {
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

type tendisBinlogItem struct {
	File       string    `json:"file"` // full path
	KvStoreIdx int       `json:"kvstoreidx"`
	BinlogId   int64     `json:"binlogId"`
	StartTime  time.Time `json:"start_time"`
	FileMtime  time.Time `json:"file_mtime"`
	FileSize   int64     `json:"file_size"`
}

// GetTendisBinlogs 获取需备份的binlogs
func (task *Task) GetTendisBinlogs() (rets []tendisBinlogItem) {
	var maxBinlogID int64 = 0
	var binlogID int64
	var startTime, fmTime time.Time
	var fnameLayout string = "20060102150405"
	var tempDumpDir string

	for storeIdx := 0; storeIdx < task.KvStoreCount; storeIdx++ {
		if task.DbType != consts.TendisTypeTendisplusInsance {
			tempDumpDir = task.DumpDir
		} else {
			tempDumpDir = filepath.Join(task.DumpDir, strconv.Itoa(storeIdx))
		}
		maxBinlogID = 0 // 重置maxBinlogID
		// 获取maxBinlogID
		task.Err = filepath.Walk(tempDumpDir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				err = fmt.Errorf("filepath.Walk %s fail,err:%v", tempDumpDir, err)
				return err
			}
			if info.IsDir() {
				return nil
			}
			if tendisBinlogReg.MatchString(info.Name()) {
				l01 := tendisBinlogReg.FindStringSubmatch(info.Name())
				if len(l01) != 4 {
					return nil
				}
				binlogID, err = strconv.ParseInt(l01[2], 10, 64)
				if err != nil {
					err = fmt.Errorf("binlogfile:%s %s to int64 fail,err:%v", info.Name(), l01[2], err)
					return err
				}
				if binlogID > maxBinlogID {
					maxBinlogID = binlogID
				}
			}
			return nil
		})
		if task.Err != nil {
			mylog.Logger.Error(task.Err.Error())
			return
		}
		mylog.Logger.Info(fmt.Sprintf("GetTendisBinlogs redis(%s) kvstore:%d maxBinlogID:%d",
			task.Addr(), storeIdx, maxBinlogID))

		task.Err = filepath.Walk(tempDumpDir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				err = fmt.Errorf("filepath.Walk %s fail,err:%v", tempDumpDir, err)
				return err
			}
			if info.IsDir() {
				return nil
			}

			if tendisBinlogReg.MatchString(info.Name()) {
				l01 := tendisBinlogReg.FindStringSubmatch(info.Name())
				if len(l01) != 4 {
					return nil
				}
				binlogID, err = strconv.ParseInt(l01[2], 10, 64)
				if err != nil {
					err = fmt.Errorf("binlogfile:%s %s to int64 fail,err:%v", info.Name(), l01[2], err)
					return err
				}
				// 只处理 binlogID < maxBinlogID 的文件
				if binlogID >= maxBinlogID {
					return nil
				}

				startTime, err = time.ParseInLocation(fnameLayout, l01[3], time.Local)
				if err != nil {
					err = fmt.Errorf("time.Parse '%s' fail,err:%v,binlogfile:%s", l01[3], err, info.Name())
					return err
				}
				fmTime = info.ModTime().Local()
				// 如果binlog文件最近两分钟内修改过,则跳过暂不处理
				if time.Now().Local().Sub(fmTime).Seconds() < 120 {
					return nil
				}

				rets = append(rets, tendisBinlogItem{
					File:       path,
					BinlogId:   binlogID,
					KvStoreIdx: storeIdx,
					StartTime:  startTime,
					FileMtime:  fmTime,
					FileSize:   info.Size(),
				})
			}
			return nil
		})
		if task.Err != nil {
			mylog.Logger.Error(task.Err.Error())
			return
		}
	}
	mylog.Logger.Info(fmt.Sprintf("redis(%s) dbType:%s get %d binlog files", task.Addr(), task.DbType, len(rets)))
	return
}

// mvBinlogToBackupDir move binlogfile to backupDir
// When the binlog file name does not contain port information, the new file name add port.
func (task *Task) mvBinlogToBackupDir() {
	filename := filepath.Base(task.BackupFile)
	var mvCmd string
	var targetName, targetFullPath string
	if strings.Contains(filename, strconv.Itoa(task.ServerPort)) {
		// binlog-30012-0007515-20221110084710.log => binlog-1.1.1.1-30012-0007515-20221110084710.log
		targetName = strings.Replace(filename, "binlog-", "binlog-"+task.ServerIP+"-", -1)
		targetFullPath = filepath.Join(task.BackupDir, targetName)
	} else {
		// binlog-1-0002151-20230306160416.log => binlog-1.1.1.1-30000-1-0002151-20230306160416.log
		targetName = strings.Replace(filename, "binlog-", "binlog-"+task.ServerIP+"-"+strconv.Itoa(task.ServerPort)+"-", -1)
		targetFullPath = filepath.Join(task.BackupDir, targetName)
	}
	mvCmd = fmt.Sprintf("mv %s %s", task.BackupFile, targetFullPath)
	mylog.Logger.Info("mvBinlogToBackupDir mvCommand:" + mvCmd)
	_, task.Err = util.RunBashCmd(mvCmd, "", nil, 1*time.Minute)
	if task.Err != nil {
		return
	}
	task.BackupFile = targetFullPath
}
func (task *Task) compressAndUpload() {
	defer func() {
		task.BackupRecordReport()
		task.BackupRecordSaveToDoingFile()
	}()
	if strings.HasSuffix(task.BackupFile, ".log") {
		task.mvBinlogToBackupDir()
		if task.Err != nil {
			task.Status = consts.BackupStatusFailed
			task.Message = task.Err.Error()
			return
		}
		task.BackupFile, task.Err = util.CompressFile(task.BackupFile, task.BackupDir, true)
		if task.Err != nil {
			mylog.Logger.Error(task.Err.Error())
			task.Status = consts.BackupStatusFailed
			task.Message = task.Err.Error()
			return
		}
		util.LocalFileChmodAllRead(task.BackupFile)
		fileInfo, _ := os.Stat(task.BackupFile)
		task.BackupFileSize = fileInfo.Size()
	}
	if strings.ToLower(task.ToBackupSystem) == "yes" {
		task.TransferToBackupSystem()
		if task.Err != nil {
			task.Status = consts.BackupStatusToBakSystemFailed
			task.Message = fmt.Sprintf("上传备份系统失败,err:%v", task.Err)
			return
		}
		task.Status = consts.BackupStatusToBakSystemStart
		task.Message = "上传备份系统中"
	} else {
		task.Status = consts.BackupStatusLocalSuccess
		task.Message = "本地备份成功,无需上传备份系统"
	}
}

// TransferToBackupSystem 备份文件上传到备份系统
func (task *Task) TransferToBackupSystem() {
	var msg string
	cliFileInfo, err := os.Stat(consts.IBSBackupClient)
	if err != nil {
		err = fmt.Errorf("os.stat(%s) failed,err:%v", consts.IBSBackupClient, err)
		mylog.Logger.Error(err.Error())
		return
	}
	if !util.IsExecOther(cliFileInfo.Mode().Perm()) {
		err = fmt.Errorf("%s is unable to execute by other", consts.IBSBackupClient)
		mylog.Logger.Error(err.Error())
		return
	}
	task.BackupTaskID, task.Err = task.backupClient.Upload(task.BackupFile)
	if task.Err != nil {
		return
	}
	msg = fmt.Sprintf("redis(%s) backupFile:%s taskid(%+v) uploading to backupSystem",
		task.Addr(), task.BackupFile, task.BackupTaskID)
	mylog.Logger.Info(msg)
	return
}

// BackupRecordReport 备份记录上报
func (task *Task) BackupRecordReport() {
	if task.reporter == nil {
		return
	}
	tmpBytes, _ := json.Marshal(task)
	// task.Err=task.reporter.AddRecord(string(tmpBytes),true)
	task.reporter.AddRecord(string(tmpBytes)+"\n", true)
}

// BackupRecordSaveToDoingFile 备份记录保存到本地 redis_binlog_file_list_${port}_doing 文件中
func (task *Task) BackupRecordSaveToDoingFile() {
	backupDir := filepath.Dir(task.BackupFile)
	// 例如: /data/dbbak/binlog/30000/redis_binlog_file_list_30000_doing
	doingFile := filepath.Join(backupDir, fmt.Sprintf(consts.DoingRedisBinlogFileList, task.ServerPort))
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
