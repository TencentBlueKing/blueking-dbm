// Package rotate TODO
package rotate

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/backup"
	binlog_parser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/log"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"

	"github.com/pkg/errors"
)

// BinlogRotateConfig TODO
type BinlogRotateConfig struct {
}

// BinlogRotate TODO
type BinlogRotate struct {
	backupClient    backup.BackupClient
	binlogDir       string
	binlogInst      models.BinlogFileModel
	sizeToFreeMB    int64 // MB
	binlogSizeMB    int64 // MB
	purgeInterval   time.Duration
	rotateInterval  time.Duration
	maxKeepDuration time.Duration
}

// String 用于打印
func (r *BinlogRotate) String() string {
	return fmt.Sprintf(
		"{binlogDir:%s, sizeToFreeMB:%dMB, binlogSizeMB:%dMB, purgeInterval:%s, rotateInterval:%s maxKeepDuration:%s}",
		r.binlogDir,
		r.sizeToFreeMB,
		r.binlogSizeMB,
		r.purgeInterval.String(),
		r.rotateInterval.String(),
		r.maxKeepDuration.String(),
	)
}

// BinlogReport TODO
type BinlogReport struct {
	BKBizID       int    `json:"bk_biz_id"`
	ClusterId     int    `json:"cluster_id"`
	ClusterDomain string `json:"cluster_domain"`
	Host          string `json:"host"`
	Port          int    `json:"port"`
	FileName      string `json:"file_name"`
	FileSize      int64  `json:"file_size"`
	FileMtime     string `json:"file_mtime"`
	MD5           string `json:"md5"`
	StartTime     string `json:"start_time"`
	StopTime      string `json:"stop_time"`
	SourceDir     string `json:"source_dir"`
	FileTag       string `json:"file_tag"`

	TaskId string `json:"task_id"`
}

// BinlogBackupStatus TODO
type BinlogBackupStatus struct {
	Status       string `json:"status"`
	Desc         string `json:"desc"`
	ExpireTime   string `json:"expire_time"`
	SubmitTime   string `json:"submit_time"`
	CompleteTime string `json:"complete_time"`
}

// BinlogStatusReport TODO
type BinlogStatusReport struct {
	BinlogReport
	BinlogBackupStatus
}

const (
	// FileSubmitted 备份提交成功
	FileSubmitted = "submitted"
	// FileWaiting 等待备份系统调度上传
	FileWaiting = "waiting"
	// FileUploading 上传中、拉取中
	FileUploading = "uploading"
	// FileUploaded 备份上传成功
	FileUploaded = "uploaded"
	// FileFailed 备份失败
	FileFailed = "fail"
	// FileCancel 取消上传、取消检查该文件状态
	FileCancel = "cancel"
	// KeepPolicyMost 尽可能多的保留binlog
	KeepPolicyMost = "most"
	// KeepPolicyLeast 尽可能少的保留binlog
	KeepPolicyLeast = "least"
	// PolicyLeastMaxSize keep_policy=least 尽可能少的保留 binlog 时，使用一个特殊常量代表需要删除的binlog大小
	PolicyLeastMaxSize int64 = 99999999
)

// FlushLogs TODO
func (i *ServerObj) FlushLogs() error {
	var err error
	_, binlogFilesObj, err := i.getBinlogFilesLocal() // todo 精简参数，是否需要改成 SHOW BINARY LOGS?
	if err != nil {
		return err
	}
	i.binlogFiles = binlogFilesObj
	_ = i.RemoveMaxKeepDuration() // ignore error

	// 最后一个文件是当前正在写入的，获取倒数第二个文件的结束时间，在 5m 内，说明 mysqld 自己已经做了切换
	if len(binlogFilesObj) >= 1 {
		fileName := filepath.Join(i.binlogDir, binlogFilesObj[len(binlogFilesObj)-1].Filename)
		bp, _ := binlog_parser.NewBinlogParse("", 0)
		events, err := bp.GetTime(fileName, true, false) // 只获取start_time
		if err != nil {
			logger.Warn(err.Error())
			_ = i.flushLogs()
		} else {
			lastRotateTime, _ := time.ParseInLocation(cst.DBTimeLayout, events[0].EventTime, time.Local)
			lastRotateSince := time.Now().Sub(lastRotateTime).Seconds() - i.rotate.rotateInterval.Seconds()
			if lastRotateSince > -5 {
				// 留 5s 的误差。比如rotateInterval=300s, 那么实际等到 295s 也可以进行rotate，不然等到下一轮还需要 300s
				_ = i.flushLogs()
			}
		}
	} else {
		_ = i.flushLogs()
	}

	var lastFileBefore *models.BinlogFileModel // 之前登记处理过的最后一个文件
	if lastFileBefore, err = i.rotate.binlogInst.QueryLastFileReport(models.DB.Conn); err != nil {
		return err
	}
	logger.Info("last binlog file processed: %s", lastFileBefore)
	return i.RegisterBinlog(lastFileBefore.Filename)
}

func (i *ServerObj) flushLogs() error {
	// >= 5.5.0: flush binary logs
	// < 5.5.0: flush logs
	// //ti := TimeInterval{TaskName: "flush_binary_logs", Tag: cast.ToString(i.Port)}
	// //if ti.IntervalOut(DB.Conn, i.rotate.rotateInterval) {
	logger.Info("flush binary logs for %d", i.Port)
	if _, err := i.dbWorker.ExecWithTimeout(5*time.Second, "FLUSH BINARY LOGS"); err != nil {
		return errors.Wrap(err, "flush logs")
	} else {
		// if err = ti.Update(DB.Conn); err != nil {
		//	logger.Error(err.Error())
		// }
	}
	// }
	return nil
}

// RemoveMaxKeepDuration 超过最大保留时间的 binlogFiles 直接删除
// 同时也会删除 sqlite 里面的元数据
func (i *ServerObj) RemoveMaxKeepDuration() error {
	if i.rotate.maxKeepDuration == 0 {
		return nil
	}
	nowTime := time.Now()
	fileTimeExpire := nowTime.Add(-1 * i.rotate.maxKeepDuration).Format(cst.DBTimeLayout)

	num := len(i.binlogFiles)
	var binlogFilesNew []*BinlogFile
	var binlogFilesDel []*BinlogFile
	for j, f := range i.binlogFiles {
		if f.Mtime < fileTimeExpire {
			binlogFilesDel = append(binlogFilesDel, f)
			logger.Info("%s [%s]has exceed max_keep_duration=%s", f.Filename, f.Mtime, i.rotate.maxKeepDuration)
			if num-j-cst.ReserveMinBinlogNum < 0 {
				binlogFilesNew = append(binlogFilesNew, f)
				// logger.Info("RemoveMaxKeepDuration keep ReserveMinBinlogNum=%d", ReserveMinBinlogNum)
				continue
			}
			if err := os.Remove(filepath.Join(i.binlogDir, f.Filename)); err != nil {
				logger.Error(err.Error())
			}
		} else {
			binlogFilesNew = append(binlogFilesNew, f)
		}
	}
	if len(binlogFilesDel) > 0 {
		if _, err := i.rotate.binlogInst.DeleteExpired(models.DB.Conn, fileTimeExpire); err != nil {
			logger.Error("delete expired file from sqlite: %s", fileTimeExpire)
		}
	}

	i.binlogFiles = binlogFilesNew
	return nil
}

// RegisterBinlog 将新产生的 binlog 记录存入 本地 sqlite db
// lastFileBefore 是上一次处理的最后一个文件
// 实例最后一个 binlog 正在使用，不登记
func (i *ServerObj) RegisterBinlog(lastFileBefore string) error {
	fLen := len(i.binlogFiles)
	var filesModel []*models.BinlogFileModel
	for j, fileObj := range i.binlogFiles {
		if fileObj.Filename <= lastFileBefore || j == fLen-1 { // 忽略最后一个binlog
			continue
		}
		backupStatus := models.IBStatusNew
		backupStatusInfo := ""
		bp, _ := binlog_parser.NewBinlogParse("", 0)
		fileName := filepath.Join(i.binlogDir, fileObj.Filename)
		events, err := bp.GetTime(fileName, true, true)
		if err != nil {
			logger.Warn(err.Error())
			backupStatus = models.IBStatusClientFail
			backupStatusInfo = err.Error()
		}
		if i.Tags.DBRole == models.RoleSlave { // slave 无需备份 binlog
			backupStatus = models.FileStatusNoNeedUpload
		}
		startTime := events[0].EventTime
		stopTime := events[1].EventTime
		ff := &models.BinlogFileModel{
			BkBizId:          i.Tags.BkBizId,
			ClusterId:        i.Tags.ClusterId,
			ClusterDomain:    i.Tags.ClusterDomain,
			DBRole:           i.Tags.DBRole,
			Host:             i.Host,
			Port:             i.Port,
			Filename:         fileObj.Filename,
			Filesize:         fileObj.Size,
			FileMtime:        fileObj.Mtime,
			BackupStatus:     backupStatus,
			BackupStatusInfo: backupStatusInfo,
			StartTime:        startTime,
			StopTime:         stopTime,
		}
		filesModel = append(filesModel, ff)
	}
	if err := i.rotate.binlogInst.BatchSave(filesModel, models.DB.Conn); err != nil {
		return err
	} else {
		logger.Info("binlog files to process: %+v", filesModel)
	}
	return nil
}

// Backup binlog 提交到备份系统
// 下一轮运行时判断上一次以及之前的提交任务状态
func (r *BinlogRotate) Backup() error {
	if r.backupClient == nil {
		logger.Warn("no backup_client found. ignoring backup")
		return nil
	}
	files, err := r.binlogInst.QueryUnfinished(models.DB.Conn)
	if err != nil {
		return errors.Wrap(err, "query unfinished")
	}
	logger.Info("%d binlog files unfinished: %d", r.binlogInst.Port, len(files))
	for _, f := range files {
		// 需要上传的，提交上传任务
		if f.BackupStatus == models.IBStatusNew || f.BackupStatus == models.IBStatusClientFail {
			filename := filepath.Join(r.binlogDir, f.Filename)
			// 需要修改 binlog 的权限
			if err := os.Chmod(filename, 0655); err != nil {
				return errors.Wrap(err, "chmod 655")
			}
			if f.StartTime == "" || f.StopTime == "" {
				bp, _ := binlog_parser.NewBinlogParse("", 0)
				events, err := bp.GetTime(filename, true, true)
				if err != nil {
					logger.Warn(err.Error())
					// f.BackupStatus = FileStatusAbnormal
				} else {
					f.StartTime = events[0].EventTime
					f.StopTime = events[0].EventTime
				}
			}
			if taskid, err := r.backupClient.Upload(filename); err != nil {
				logger.Error("fail to upload file %s. err: %v", filename, err.Error())
				f.BackupStatus = models.IBStatusClientFail
				f.BackupStatusInfo = err.Error()
			} else {
				f.BackupTaskid = taskid
				f.BackupStatus = models.IBStatusWaiting
			}
		} else { // 等待上传的，查询上传结果
			if f.BackupTaskid == "" {
				logger.Error("binlog backup task_id should not empty %s", f.Filename)
				f.BackupStatus = models.IBStatusFail
			} else {
				taskStatus, err := r.backupClient.Query(f.BackupTaskid)
				if err != nil {
					return err
				}
				if taskStatus == f.BackupStatus { // 上传状态没有进展
					continue
				} else {
					f.BackupStatus = taskStatus
					if taskStatus == models.IBStatusSuccess {
						log.Reporter().Result.Println(f)
					}
					log.Reporter().Status.Println(f)
				}
			}
		}
		if err = f.Update(models.DB.Conn); err != nil {
			return err
		}
	}
	return nil
}

// Remove 删除本地 binlog
// 将本地 done,success 的超过阈值的 binlog 文件删除，更新 binlog 列表状态
// 超过 max_keep_days 的强制删除，单位 bytes
// sizeBytesToFree=999999999 代表尽可能删除
func (r *BinlogRotate) Remove(sizeBytesToFree int64) error {
	if sizeBytesToFree == 0 {
		logger.Info("no need to free %d binlog size", r.binlogInst.Port)
		return nil
	}
	binlogFiles, err := r.binlogInst.QuerySuccess(models.DB.Conn)
	if err != nil {
		return err
	}
	// sort.Slice(binlogFiles, func(i, j int) bool { return binlogFiles[i].Filename < binlogFiles[j].Filename }) // 升序
	var sizeDeleted int64
	var fileDeleted int
	stopFile := ""
	num := len(binlogFiles)
	for i, f := range binlogFiles {
		if num-i-cst.ReserveMinBinlogNum < 0 {
			logger.Info("rotate binlog keep ReserveMinBinlogNum=%d", cst.ReserveMinBinlogNum)
			break
		}
		fileFullPath := filepath.Join(r.binlogDir, f.Filename)
		logger.Info("remove file: %s", fileFullPath)
		if err = os.Remove(fileFullPath); err != nil {
			logger.Error(err.Error())
			// return err
		}
		if !cmutil.FileExists(fileFullPath) {
			f.BackupStatus = models.FileStatusRemoved
			if err = f.Update(models.DB.Conn); err != nil {
				logger.Error(err.Error())
				// return err
			}
			sizeDeleted += f.Filesize
			fileDeleted += 1
			stopFile = f.Filename
			if sizeDeleted >= sizeBytesToFree {
				break
			}
		}
	}
	if sizeDeleted < sizeBytesToFree && sizeBytesToFree != PolicyLeastMaxSize*1024*1024 {
		logger.Warn(
			"disk space freed does not satisfy needed after delete all allowed binlog files. "+
				"sizeDeleted:%d sizeBytesToFree:%d",
			sizeDeleted, sizeBytesToFree,
		)
		// todo 可能需要开始删除 备份未完成的 binlog
	}
	logger.Info("sizeBytesDeleted:%d, fileDeleted:%d. binlog lastDeleted: %s", sizeDeleted, fileDeleted, stopFile)
	return nil
}
