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
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"

	"github.com/gofrs/flock"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// tendisssd binlog文件正则
// 例如: binlog-30000-0007426-20221109221541.log
// tendisplus binlog文件正则
// 例如: binlog-0-0000887-20221107123830.log
var tendisBinlogReg = regexp.MustCompile(`binlog-(\d+)-(\d+)-(\d+).log`)

// RedisBinlogHistorySchema TODO
type RedisBinlogHistorySchema struct {
	ID         int64  `json:"-" gorm:"primaryKey;column:id;not null`
	ReportType string `json:"report_type" gorm:"column:report_type;not null;default:''"`
	BkBizID    string `json:"bk_biz_id" gorm:"column:bk_biz_id;not null;default:''"`
	BkCloudID  int64  `json:"bk_cloud_id" gorm:"column:bk_cloud_id;not null;default:0"`
	ServerIP   string `json:"server_ip" gorm:"column:server_ip;not null;default:''"`
	ServerPort int    `json:"server_port" gorm:"column:server_port;not null;default:0"`
	Domain     string `json:"domain" gorm:"column:domain;not null;default:'';index"`
	// TendisplusInstance or TendisSSDInstance
	DbType   string `json:"db_type" gorm:"column:db_type;not null;default:''"`
	RealRole string `json:"role" gorm:"column:role;not null;default:''"`
	// 备份路径,如 /data/dbbak/binlog/30000
	BackupDir string `json:"backup_dir" gorm:"column:backup_dir;not null;default:''"`
	// 备份的目标文件(已压缩)
	BackupFile string `json:"backup_file" gorm:"column:backup_file;not null;default:''"`
	// binlog对应的 kvstoreidx
	KvstoreIdx int `json:"kvstoreidx" gorm:"column:kvstoreidx;not null;default:0"`
	// 备份文件大小(已压缩)
	BackupFileSize int64 `json:"backup_file_size" gorm:"column:backup_file_size;not null;default:0"`
	// binlog文件生成时间(非压缩)
	StartTime time.Time `json:"start_time" gorm:"column:start_time;not null;default:'';index"`
	// binlog文件最后修改时间(非压缩)
	EndTime      time.Time `json:"end_time" gorm:"column:end_time;not null;default:'';index"`
	TimeZone     string    `json:"time_zone" gorm:"column:time_zone;not null;default:''"`
	BackupTaskID string    `json:"backup_taskid" gorm:"column:backup_taskid;not null;default:''"`
	// 目前为空
	BackupMD5 string `json:"backup_md5" gorm:"column:backup_md5;not null;default:''"`
	// REDIS_BINLOG
	BackupTag string `json:"backup_tag" gorm:"column:backup_tag;not null;default:''"`
	// shard值
	ShardValue string `json:"shard_value" gorm:"column:shard_value;not null;default:''"`
	Status     string `json:"status" gorm:"column:status;not null;default:''"`
	Message    string `json:"message" gorm:"column:message;not null;default:''"`
	// 本地文件是否已删除,未被删除为0,已被删除为1
	LocalFileRemoved int `json:"-" gorm:"column:local_file_removed;not null;default:0"`
}

// TableName TODO
func (r *RedisBinlogHistorySchema) TableName() string {
	return "redis_binlog_history"
}

// Addr string
func (r *RedisBinlogHistorySchema) Addr() string {
	return r.ServerIP + ":" + strconv.Itoa(r.ServerPort)
}

type redisBinlogReport struct {
	RedisBinlogHistorySchema
	StartTime string `json:"start_time"`
	EndTime   string `json:"end_time"`
}

// BackupRecordReport 备份记录上报
func (r *RedisBinlogHistorySchema) BackupRecordReport(reporter report.Reporter) {
	if reporter == nil {
		return
	}
	reportRow := redisBinlogReport{
		RedisBinlogHistorySchema: *r,
		StartTime:                r.StartTime.Local().Format(time.RFC3339),
		EndTime:                  r.EndTime.Local().Format(time.RFC3339),
	}
	tmpBytes, _ := json.Marshal(reportRow)
	reporter.AddRecord(string(tmpBytes)+"\n", true)
}

// Task redis binlog备份task
type Task struct {
	RedisBinlogHistorySchema
	Password       string               `json:"-"`
	ToBackupSystem string               `json:"-"`
	OldFileLeftDay int                  `json:"-"`
	DumpDir        string               `json:"-"`
	KvStoreCount   int                  `json:"-"`
	Cli            *myredis.RedisClient `json:"-"`
	reporter       report.Reporter
	backupClient   backupsys.BackupClient
	sqdb           *gorm.DB
	lockFile       string `json:"-"`
	Err            error  `json:"-"`
}

// NewBinlogBackupTask new binlog backup task
func NewBinlogBackupTask(bkBizID string, bkCloudID int64, domain, ip string, port int,
	password, toBackupSys, backupDir, shardValue string, oldFileLeftDay int,
	reporter report.Reporter, storageType string,
	sqdb *gorm.DB) (ret *Task, err error) {

	timeZone, _ := time.Now().Local().Zone()
	ret = &Task{
		Password:       password,
		ToBackupSystem: toBackupSys,
		OldFileLeftDay: oldFileLeftDay,
		reporter:       reporter,
		sqdb:           sqdb,
	}
	ret.RedisBinlogHistorySchema = RedisBinlogHistorySchema{
		ReportType: consts.RedisBinlogBackupReportType,
		BkBizID:    bkBizID,
		BkCloudID:  bkCloudID,
		Domain:     domain,
		ServerIP:   ip,
		ServerPort: port,
		BackupDir:  backupDir,
		BackupTag:  consts.RedisBinlogTAG,
		ShardValue: shardValue,
		TimeZone:   timeZone,
	}
	// ret.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisBinlogTAG)
	ret.backupClient, err = backupsys.NewCosBackupClient(consts.COSBackupClient,
		consts.COSInfoFile, consts.RedisBinlogTAG, storageType)
	if err != nil && strings.HasPrefix(err.Error(), "backup_client path not found") {
		ret.backupClient = nil
		err = nil
	}
	return ret, err
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
		task.StartTime = item.StartTime
		task.EndTime = item.FileMtime
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
	task.DbType, task.Err = task.Cli.GetTendisType()
	if task.Err != nil {
		return
	}
	if task.DbType != consts.TendisTypeRedisInstance {
		task.DumpDir, task.Err = task.Cli.GetDumpDir()
		if task.Err != nil {
			return
		}
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
		task.BackupRecordReport(task.reporter)
		task.BackupRecordSaveToLocalDB()
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
	// backup-client 不存在,无法上传备份系统
	if task.backupClient == nil {
		task.Status = consts.BackupStatusLocalSuccess
		task.Message = "本地备份成功,backup-client不存在,无法上传备份系统"
		return
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
	task.BackupTaskID, task.Err = task.backupClient.Upload(task.BackupFile)
	if task.Err != nil {
		return
	}
	msg = fmt.Sprintf("redis(%s) backupFile:%s taskid(%+v) uploading to backupSystem",
		task.Addr(), task.BackupFile, task.BackupTaskID)
	mylog.Logger.Info(msg)
	return
}

// BackupRecordSaveToLocalDB 备份记录保存到本地sqlite中
func (task *Task) BackupRecordSaveToLocalDB() {
	if task.sqdb == nil {
		return
	}
	task.RedisBinlogHistorySchema.ID = 0 // 重置为0,以便gorm自增
	task.Err = task.sqdb.Clauses(clause.OnConflict{
		UpdateAll: true,
	}).Create(&task.RedisBinlogHistorySchema).Error
	if task.Err != nil {
		task.Err = fmt.Errorf("BackupRecordSaveToLocalDB sqdb.Create fail,err:%v", task.Err)
		mylog.Logger.Error(task.Err.Error())
		return
	}
}
