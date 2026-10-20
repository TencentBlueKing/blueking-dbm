package redisbinlogbackup

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
	"dbm-services/redis/db-tools/dbmon/models/mysqlite"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/backupsys"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/models"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"

	"github.com/gofrs/flock"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// Task redis binlog备份task
type Task struct {
	models.RedisBinlogHistorySchema
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
	reporter report.Reporter, storageType string, backupFileTag string,
	sqdb *gorm.DB) (ret *Task, err error) {

	timeZone, _ := time.Now().Local().Zone()
	ret = &Task{
		Password:       password,
		ToBackupSystem: toBackupSys,
		OldFileLeftDay: oldFileLeftDay,
		reporter:       reporter,
		sqdb:           sqdb,
	}
	ret.RedisBinlogHistorySchema = models.RedisBinlogHistorySchema{
		ReportType: consts.RedisBinlogBackupReportType,
		BkBizID:    bkBizID,
		BkCloudID:  bkCloudID,
		Domain:     domain,
		ServerIP:   ip,
		ServerPort: port,
		BackupDir:  backupDir,
		BackupTag:  backupFileTag,
		ShardValue: shardValue,
		TimeZone:   timeZone,
	}
	// ret.backupClient = backupsys.NewIBSBackupClient(consts.IBSBackupClient, consts.RedisBinlogTAG)
	ret.backupClient, err = backupsys.NewCosBackupClient(consts.COSBackupClient,
		consts.COSInfoFile, backupFileTag, storageType)
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

	// 数据盘利用率超阈值时,先清理上一次备份文件和记录,再发起本次binlog备份
	task.CheckDiskUsageAndCleanPreviousBinlog()
	if task.Err != nil {
		return
	}

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

// CheckDiskUsageAndCleanPreviousBinlog 数据盘空间利用率超过阈值(consts.DiskUsageCleanThresholdBinlog)时,
// 在发起下一次binlog备份前,先清理该实例上一次备份文件和记录(与tendisplus全备清理策略对齐);
// 正在上传备份系统中的文件,轮询上传任务状态,待上传结束后再执行删除;
// 清理完成后检查被清理的备份是否已成功上传备份系统,只做检查记录error日志,不截断清理流程
// 注意: binlog备份文件数量多,所有文件等待上传任务结束的总时长上限为1小时(全备为单文件最多等待1小时);
// data1(数据盘)空间保护: 数据盘利用率达到consts.DiskUsageForceCleanThreshold(90%)时,
// 无论备份盘是否超阈值都会触发清理,且不再等待上传任务结束,直接强制删除本地文件,力保数据盘
func (task *Task) CheckDiskUsageAndCleanPreviousBinlog() {
	diskUsg, err := util.GetLocalDirDiskUsg(task.BackupDir)
	if err != nil {
		task.Err = err
		return
	}
	// data1(数据盘)空间保护: 数据盘利用率达到90%时,直接触发清理且不再等待上传任务结束
	forceClean := false
	dataDiskUsg, err := util.GetLocalDirDiskUsg(task.DumpDir)
	if err != nil {
		// 查询数据盘失败不影响后续清理流程,仅记录日志
		mylog.Logger.Warn(fmt.Sprintf("redis(%s) get data disk(%s) usage fail,err:%v",
			task.Addr(), task.DumpDir, err))
		err = nil
	} else if dataDiskUsg.UsageRatio >= consts.DiskUsageForceCleanThreshold {
		forceClean = true
		mylog.Logger.Warn(fmt.Sprintf(
			"redis(%s) data disk(%s) usage:%d%% >= %d%%,force clean binlogbackup to protect data disk",
			task.Addr(), task.DumpDir, dataDiskUsg.UsageRatio, consts.DiskUsageForceCleanThreshold))
	}
	if diskUsg.UsageRatio <= consts.DiskUsageCleanThresholdBinlog && !forceClean {
		return
	}
	mylog.Logger.Info(fmt.Sprintf(
		"redis(%s) disk(%s) usage:%d%% > %d%% or data disk forceClean:%v,clean previous binlogbackup before next binlogbackup",
		task.Addr(), task.BackupDir, diskUsg.UsageRatio, consts.DiskUsageCleanThresholdBinlog, forceClean))

	// 查询该实例本地文件未被清理的历史binlog备份记录,每次最多清理最旧的10个
	toCleanRows := []models.RedisBinlogHistorySchema{}
	err = task.sqdb.Where("server_ip=? and server_port=? and local_file_removed=?",
		task.ServerIP, task.ServerPort, 0).
		Order("end_time asc").Limit(10).Find(&toCleanRows).Error
	if err != nil {
		task.Err = fmt.Errorf("query previous binlogbackup records fail,err:%v", err)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	if len(toCleanRows) == 0 {
		return
	}

	// 所有文件等待上传任务结束的总时长上限
	waitDeadline := time.Now().Local().Add(1 * time.Hour)
	cleanedCnt := 0
	for _, row := range toCleanRows {
		// 如果该备份文件正在上传备份系统中,删除文件后上传进程仍持有文件句柄,磁盘空间不会立即释放;
		// 轮询备份系统上传任务状态,待上传结束后再执行删除
		if row.Status == consts.BackupStatusToBakSystemStart &&
			row.BackupTaskID != "" && task.backupClient != nil && !forceClean {
			for time.Now().Local().Before(waitDeadline) {
				// 等待过程中数据盘仍在持续写入,利用率达到90%时立即中断等待,强制清理
				if dataDiskUsg, checkErr := util.GetLocalDirDiskUsg(task.DumpDir); checkErr == nil &&
					dataDiskUsg.UsageRatio >= consts.DiskUsageForceCleanThreshold {
					mylog.Logger.Warn(fmt.Sprintf(
						"redis(%s) data disk(%s) usage:%d%% >= %d%%,stop waiting upload task(%s),force clean",
						task.Addr(), task.DumpDir, dataDiskUsg.UsageRatio,
						consts.DiskUsageForceCleanThreshold, row.BackupTaskID))
					forceClean = true
					break
				}
				var taskStatus int
				var statusMsg string
				taskStatus, statusMsg, err = task.backupClient.TaskStatus(row.BackupTaskID)
				if err != nil {
					mylog.Logger.Warn(fmt.Sprintf("redis(%s) query upload task(%s) status fail,err:%v,continue waiting",
						task.Addr(), row.BackupTaskID, err))
				} else if taskStatus >= 4 {
					// taskStatus==4 上传成功;taskStatus>4 上传失败
					if taskStatus == 4 {
						row.Status = consts.BackupStatusToBakSysSuccess
						row.Message = "上传备份系统成功"
					} else {
						row.Status = consts.BackupStatusToBakSystemFailed
						row.Message = fmt.Sprintf("上传失败,statusCode:%d,err:%s", taskStatus, statusMsg)
					}
					if saveErr := task.sqdb.Save(&row).Error; saveErr != nil {
						mylog.Logger.Error(fmt.Sprintf("redis(%s) save binlogbackup record fail,err:%v",
							task.Addr(), saveErr))
					}
					break
				}
				// 上传中,1分钟后再次查询
				time.Sleep(1 * time.Minute)
			}
			if row.Status == consts.BackupStatusToBakSystemStart {
				mylog.Logger.Error(fmt.Sprintf(
					"redis(%s) upload task(%s) still running after waiting,file(%s) will be deleted anyway,"+
						"disk space may not released until upload finished",
					task.Addr(), row.BackupTaskID, row.BackupFile))
			}
		}
		if util.FileExists(row.BackupFile) {
			if err = os.Remove(row.BackupFile); err != nil {
				// 单个文件删除失败不截断整体清理流程,下次任务继续重试
				mylog.Logger.Error(fmt.Sprintf("os.Remove fail,err:%v,file:%s", err, row.BackupFile))
				continue
			}
		}
		// 删除该次备份的记录
		if err = task.sqdb.Delete(&row).Error; err != nil {
			mylog.Logger.Error(fmt.Sprintf("redis(%s) delete previous binlogbackup record fail,err:%v",
				task.Addr(), err))
			continue
		}
		// 检查该备份文件是否已成功上传备份系统,只做检查并记录error日志,不截断清理流程
		if row.Status != consts.BackupStatusToBakSysSuccess {
			mylog.Logger.Error(fmt.Sprintf(
				"redis(%s) previous binlogbackup file(%s) status(%s) not uploaded to backup system,"+
					"it has been deleted due to disk(%s) usage %d%%,backup data may lost",
				task.Addr(), row.BackupFile, row.Status, task.BackupDir, diskUsg.UsageRatio))
		}
		cleanedCnt++
	}
	mylog.Logger.Info(fmt.Sprintf(
		"redis(%s) %d previous binlogbackup files and records cleaned,disk(%s) usage %d%%",
		task.Addr(), cleanedCnt, task.BackupDir, diskUsg.UsageRatio))
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
			if models.TendisBinlogReg.MatchString(info.Name()) {
				l01 := models.TendisBinlogReg.FindStringSubmatch(info.Name())
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

			if models.TendisBinlogReg.MatchString(info.Name()) {
				l01 := models.TendisBinlogReg.FindStringSubmatch(info.Name())
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
					// FileMtime:  fmTime,
					FileMtime: time.Now(), // tendisplus slave在备份的时候，master会导出binlog
					FileSize:  info.Size(),
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
	if strings.Contains(filename, "-"+strconv.Itoa(task.ServerPort)+"-") {
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
		if err := report.RedisBinlogReport(&task.RedisBinlogHistorySchema, task.reporter); err != nil {
			mylog.Logger.Error(err.Error())
		}
		// task.BackupRecordReport(task.reporter)
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
	task.Err = mysqlite.RetryOnWriteErr(func() error {
		return task.sqdb.Clauses(clause.OnConflict{
			UpdateAll: true,
		}).Create(&task.RedisBinlogHistorySchema).Error
	})
	if task.Err != nil {
		task.Err = fmt.Errorf("BackupRecordSaveToLocalDB sqdb.Create fail,err:%v", task.Err)
		mylog.Logger.Error(task.Err.Error())
		return
	}
}
