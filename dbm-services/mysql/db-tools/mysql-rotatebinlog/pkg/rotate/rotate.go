// Package rotate TODO
package rotate

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/samber/lo"

	reapi "dbm-services/common/reverseapi/apis/common"
	recore "dbm-services/common/reverseapi/pkg/core"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/util"

	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/reportlog"
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
	//backupClient    backup.BackupClient
	binlogDir  string
	binlogInst models.BinlogFileModel
	// sizeToFreeMB 计划释放这么多，可能因为没有上传实际没有释放这么多
	sizeToFreeMB int64 // MB
	// hardSizeToFree 一定要释放这么多
	// 当 > 0 时，说明 binlog目录大小达到了硬限制，一定要清理
	// 当 <= 0 时，说明目录没有达到清理阈值，或者只是达到了软限制，可以把超出软限制的部分挪到 stage 目录
	hardSizeToFree  int64 // MB
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
	// PolicyLeastMaxSize keep_policy=least 尽可能少的保留 binlog 时，使用一个特殊常量代表需要删除的binlog大小. MB
	PolicyLeastMaxSize int64 = 99999999
)

// FlushLogs 根据时间间隔需要，决定是否 flush logs
func (i *ServerObj) FlushLogs() error {
	var err error
	_, i.binlogFiles, err = i.getBinlogFilesLocal() // todo 精简参数，是否需要改成 SHOW BINARY LOGS?
	if err != nil {
		return err
	}
	_ = i.RemoveMaxKeepDuration() // ignore error

	// 最后一个文件是当前正在写入的，获取倒数第二个文件的结束时间，在 5m 内，说明 mysqld 自己已经做了切换，rotatebinlog 不需要再处理
	if len(i.binlogFiles) >= 1 {
		fileName := filepath.Join(i.binlogDir, i.binlogFiles[len(i.binlogFiles)-1].Filename)
		bp, _ := binlog_parser.NewBinlogParse("", 0, time.RFC3339)
		events, err := bp.GetTime(fileName, true, false) // 只获取start_time
		if err != nil {
			logger.Warn("FlushLogs GetTime %s", fileName, err.Error())
			//_ = i.flushLogs()
		}
		if len(events) > 0 {
			lastRotateTime, _ := time.ParseInLocation(reportlog.ReportTimeLayout1, events[0].EventTime, time.Local)
			lastRotateSince := time.Now().Sub(lastRotateTime).Seconds() - i.rotate.rotateInterval.Seconds()
			if lastRotateSince > -5 {
				// 留 5s 的误差。比如rotateInterval=300s, 那么实际等到 295s 也可以进行rotate，不然等到下一轮还需要 300s
				_ = i.flushLogs()
			}
			// 无需 执行 flush logs，可能因达到 max_binlog_size 自动切换 binlog 了
		}
	} else {
		_ = i.flushLogs()
	}
	return nil
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
// 同时也会删除 sqlite 里面的元数据，每天凌晨 06 点清理
func (i *ServerObj) RemoveMaxKeepDuration() error {
	nowTime := time.Now()
	if i.rotate.maxKeepDuration == 0 || nowTime.Hour() != 6 {
		return nil
	}
	fileTimeExpire := nowTime.Add(-1 * i.rotate.maxKeepDuration)

	num := len(i.binlogFiles)
	var binlogFilesNew []*BinlogFile
	var binlogFilesDel []*BinlogFile
	for j, f := range i.binlogFiles {
		if f.Mtime.Compare(fileTimeExpire) < 0 {
			binlogFilesDel = append(binlogFilesDel, f)
			logger.Info("%s [%s]has exceed max_keep_duration=%s", f.Filename, f.Mtime, i.rotate.maxKeepDuration)
			if num-j-cst.ReserveMinBinlogNum < 0 {
				binlogFilesNew = append(binlogFilesNew, f)
				continue
			}
			fileFullPath := filepath.Join(i.binlogDir, f.Filename)
			logger.Info("max_keep_duration remove file: %s", fileFullPath)
			if err := os.Remove(fileFullPath); err != nil {
				logger.Error(err.Error())
			}
		} else {
			binlogFilesNew = append(binlogFilesNew, f)
		}
	}
	if _, err := i.rotate.binlogInst.DeleteExpired(models.DB.Conn, fileTimeExpire); err != nil {
		logger.Error("delete expired file from sqlite: %s", fileTimeExpire)
	}

	i.binlogFiles = binlogFilesNew
	return nil
}

// Backup binlog 提交到备份系统
// 下一轮运行时判断上一次以及之前的提交任务状态
func (r *BinlogRotate) Backup(backupClient backup.BackupClient) error {
	retryOpts := []retry.Option{
		retry.Attempts(2),
		retry.Delay(1 * time.Second),
		retry.DelayType(retry.FixedDelay),
	}
	reportCore, err := recore.NewCore(0, retryOpts...)
	if err != nil {
		return err
	}
	if backupClient == nil {
		logger.Warn("no backup_client found. ignoring backup")
		return nil
	}

	files, err := r.binlogInst.QueryUnfinished(models.DB.Conn)
	if err != nil {
		return errors.Wrap(err, "query unfinished")
	}
	maxOldDaysToUpload := viper.GetInt("public.max_old_days_to_upload")
	if maxOldDaysToUpload == 0 {
		maxOldDaysToUpload = 7
	}
	logger.Info("%d binlog files unfinished: %d", r.binlogInst.Port, len(files))

	type ClusterInstance struct {
		AppId         int
		ClusterDomain string
		Host          string
		Port          int
		DBRole        string
	}
	abnormalCounts := make(map[ClusterInstance]int64)

	for _, f := range files {
		// 超过 maxOldDaysToUpload 天的，全部标记为异常
		if fMtime, err := time.ParseInLocation(time.RFC3339, f.FileMtime, time.Local); err == nil {
			if time.Now().Sub(fMtime).Hours() > float64(24*maxOldDaysToUpload) {
				f.BackupStatus = models.IBStatusUploadAbnormal
				_ = f.Update(models.DB.Conn)
				continue
			}
		}
		filename := filepath.Join(r.binlogDir, f.Filename)

		// 需要上传的，提交上传任务
		if f.BackupStatus == models.IBStatusNew || f.BackupStatus == models.IBStatusClientFail {
			if !cmutil.FileExists(filename) {
				f.BackupStatus = models.FileStatusForceRemoved
				_ = f.Update(models.DB.Conn)
				logger.Info("force removed already: %s(%d)", f.Filename, f.BackupTaskid)
				abnormalCounts[ClusterInstance{
					AppId:         f.BkBizId,
					ClusterDomain: f.ClusterDomain,
					Host:          f.Host,
					Port:          f.Port,
					DBRole:        f.DBRole,
				}] += 1
				continue
			}
			if f.StartTime == "" || f.StopTime == "" {
				bp, _ := binlog_parser.NewBinlogParse("", 0, reportlog.ReportTimeLayout1)
				events, err := bp.GetTimeIgnoreStopErr(filename, true, true)
				if err != nil {
					logger.Warn("Backup GetTime %s", filename, err.Error())
					f.BackupStatus = models.FileStatusAbnormal
				} else {
					f.StartTime = events[0].EventTime
					f.StopTime = events[1].EventTime
				}
			}
			logger.Info("backup_client upload register file %s", filename)
			if taskid, err := backupClient.Upload(filename); err != nil {
				logger.Error("fail to upload register file %s. err: %v", filename, err.Error())
				f.BackupStatus = models.IBStatusClientFail
				f.BackupStatusInfo = err.Error()
			} else {
				// 异步查询状态
				f.BackupTaskid = taskid
				f.BackupStatus = models.IBStatusWaiting
			}
		} else { // 等待上传的，查询上传结果
			if f.BackupTaskid == "" {
				logger.Error("binlog backup task_id should not empty %s", f.Filename)
				f.BackupStatus = models.IBStatusFail
			} else {
				taskStatus, err := backupClient.Query(f.BackupTaskid)
				if err != nil {
					logger.Error("backup_client query status: %s, taskid:%s, err: %v",
						f.Filename, f.BackupTaskid, err.Error())
					continue
				}
				if !cmutil.FileExists(filename) && taskStatus != models.IBStatusSuccess {
					if f.BackupStatus == models.FileStatusForceRemoved { // 这个状态说明已经上报过异常了
						continue
					}
					f.BackupStatus = models.FileStatusForceRemoved
					_ = f.Update(models.DB.Conn)
					logger.Info("force removed already: %s(%d)", f.Filename, f.BackupTaskid)
					abnormalCounts[ClusterInstance{
						AppId:         f.BkBizId,
						ClusterDomain: f.ClusterDomain,
						Host:          f.Host,
						Port:          f.Port,
						DBRole:        f.DBRole,
					}] += 1
					continue
				}

				if taskStatus == models.IBStatusSuccess {
					f.BackupStatus = taskStatus
					log.Reporter().Result.Println(f)
					ev := log.MysqlBinlogResultEvent(*f)
					if resp, err := reapi.SyncReportWithDelegateRetry(reportCore, &ev); err != nil {
						logger.Warn("report binlog status failed:%s, resp=%s", err.Error(), string(resp))
						//return reportErr
					}
				} else if taskStatus == f.BackupStatus { // 上传状态没有进展
					if fMtime, err := time.ParseInLocation(time.RFC3339, f.FileMtime, time.Local); err == nil {
						if time.Now().Sub(fMtime).Hours() > float64(24*maxOldDaysToUpload) {
							f.BackupStatus = models.IBStatusUploadAbnormal
							if err = f.Update(models.DB.Conn); err != nil {
								return err
							}
							continue
						}
					}
					continue
				} else if taskStatus < models.IBStatusSuccess { // 未成功，且在上传中或者等待备份系统内部重试
					f.BackupStatus = taskStatus
				} else { // 状态有变化，但不是 success，保持之前的状态，下一轮再看
					logger.Info("backup_client query file: %s, taskid:%s, status: %d. local status:%d",
						f.Filename, f.BackupTaskid, taskStatus, f.BackupStatus)
					if taskStatus == models.IBStatusCanceledByRemote {
						f.BackupStatus = taskStatus
					} else {
						// 只更新 info 信息。保持之前的状态吗，下一轮再看
						f.BackupStatusInfo = fmt.Sprintf("remote status: %d", taskStatus)
					}
					if err = f.Update(models.DB.Conn); err != nil {
						return err
					}
					continue
				}
			}
		}
		if err = f.Update(models.DB.Conn); err != nil {
			return err
		}
	}
	for inst, cnt := range abnormalCounts {
		_ = util.SendMonitorMetrics("binlog_upload_failed", cnt,
			map[string]interface{}{
				"appid":          inst.AppId,
				"cluster_domain": inst.ClusterDomain,
				"db_role":        inst.DBRole,
				"host":           inst.Host,
				"port":           inst.Port,
			})
	}
	return nil
}

// RemoveToSoftLimit remove binlog
// 处理的对象是从本地 sqlite里查询的 binlog 列表
func (r *BinlogRotate) RemoveToSoftLimit(sizeBytesToFree int64, server *ServerObj) (err error) {
	if sizeBytesToFree <= 0 {
		logger.Info("no need to free %d binlog size", r.binlogInst.Port)
		return nil
	}
	var binlogFiles []*models.BinlogFileModel
	binlogFiles, err = r.binlogInst.QueryToRemove(models.DB.Conn)
	if err != nil {
		return err
	}

	var sizeDeleted int64
	var fileDeleted int
	stopFile := ""
	num := len(binlogFiles)
	for i, f := range binlogFiles {
		if num-i-cst.ReserveMinBinlogNum < 0 {
			logger.Info("rotate binlog %d keep ReserveMinBinlogNum=%d", r.binlogInst.Port, cst.ReserveMinBinlogNum)
			break
		}
		originalStatus := f.BackupStatus
		fileFullPath := filepath.Join(r.binlogDir, f.Filename)
		if cmutil.FileExists(fileFullPath) {
			logger.Info("remove file: %s, status=%d", fileFullPath, f.BackupStatus)
			if lo.Contains(models.StatusSuccess, f.BackupStatus) {
				if err = os.Remove(fileFullPath); err != nil {
					logger.Error("remove file failed: %s", err.Error())
				} else { // remove success
					f.BackupStatus = models.FileStatusRemoved
				}
			}
			if !cmutil.FileExists(fileFullPath) {
				sizeDeleted += f.Filesize
				fileDeleted += 1
				stopFile = f.Filename
			}
		} else {
			logger.Info("remove but file not exists: %s", fileFullPath)
			// 也要更新状态
			f.BackupStatus = models.FileStatusRemoved
		}
		if originalStatus != f.BackupStatus {
			if err = f.Update(models.DB.Conn); err != nil {
				logger.Error(err.Error())
			}
		}
		if sizeDeleted >= sizeBytesToFree {
			break
		}
	}
	if sizeDeleted < sizeBytesToFree && sizeBytesToFree != PolicyLeastMaxSize*1024*1024 {
		logger.Warn(
			"disk space freed does not satisfy needed after delete all allowed binlog files. "+
				"sizeDeleted:%d sizeBytesToFree:%d",
			sizeDeleted, sizeBytesToFree,
		)
		return nil
	}
	logger.Info("sizeBytesDeleted:%d, fileDeleted:%d. binlog lastDeleted: %s",
		sizeDeleted, fileDeleted, stopFile)
	return nil
}

// RemoveToHardLimit 强制清除这么多字节，从前往后，不管文件处于什么状态
// 如果有手动下载 binlog 到对应目录下，引起权限不包括 执行权限，不会触发删除
// 处理的对象是本地扫描到的 binlog 列表
func (r *BinlogRotate) RemoveToHardLimit(sizeBytesToFreeHard int64, server *ServerObj) int64 {
	if sizeBytesToFreeHard <= 0 {
		return 0
	}
	var sizeDeleted int64
	var fileDeleted int
	num := len(server.binlogFiles)
	var abnormalCount int64
	var err error

	for i, f := range server.binlogFiles {
		if num-i-cst.ReserveMinBinlogNum < 0 {
			logger.Info("rotate binlog %d keep ReserveMinBinlogNum=%d", r.binlogInst.Port, cst.ReserveMinBinlogNum)
			break
		}
		fileFullPath := filepath.Join(r.binlogDir, f.Filename)
		if err != nil {
			continue
		}
		if !cmutil.FileExists(fileFullPath) && !f.HasExecPerm {
			continue
		}
		if err = os.Remove(fileFullPath); err == nil {
			sizeDeleted += f.Size
			fileDeleted += 1
			logger.Info("force remove for hard limit: %s", fileFullPath)
		}
		fileObj, err := r.binlogInst.QueryByFileName(models.DB.Conn, f.Filename)
		if err != nil {
			logger.Error("query file %s failed: %s", f.Filename, err.Error())
			fileObj = &models.BinlogFileModel{BackupStatus: models.FileStatusForceRemoved} // 不进入下面的状态维护流程
		}
		// 本地文件的状态维护，下轮自动维护
		if (fileObj.BackupTaskid != "" && fileObj.BackupStatus != models.IBStatusSuccess) ||
			(fileObj.BackupStatus == models.IBStatusNew) { // 去备份系统查一下真实状态
			var backupStatus int
			if fileObj.BackupTaskid != "" && server.backupClient != nil {
				backupStatus, err = server.backupClient.Query(fileObj.BackupTaskid)
				if err != nil {
					logger.Error("query file status %s(%d) failed: %s",
						fileObj.Filename, fileObj.BackupTaskid, err.Error())
				}
			}
			if backupStatus == models.IBStatusSuccess {
				fileObj.BackupStatus = models.IBStatusSuccess
			} else {
				abnormalCount += 1
				fileObj.BackupStatus = models.FileStatusForceRemoved
			}
			if err = fileObj.Update(models.DB.Conn); err != nil {
				logger.Error(err.Error())
			}
		}
		if sizeDeleted >= sizeBytesToFreeHard {
			break
		}
	}
	if abnormalCount > 0 {
		_ = util.SendMonitorMetrics("binlog_upload_failed", abnormalCount,
			map[string]interface{}{
				"appid":          server.Tags.BkBizId,
				"cluster_domain": server.Tags.ClusterDomain,
				"db_role":        server.Tags.DBRole,
				"host":           server.Host,
				"port":           server.Port,
			})
	}
	return sizeDeleted
}

// Remove 删除本地 binlog
// 将本地 done,success 的超过阈值的 binlog 文件删除，更新 binlog 列表状态
// 超过 max_keep_days 的强制删除，单位 bytes
// sizeBytesToFree=999999999 代表尽可能删除
// sizeBytesToFreeHard 一定要清理这么多，<=0 代表不需要强制delete，可以先转 stage目录. > 0 时，达到到目录大小硬限制，必须删除
func (r *BinlogRotate) Remove(sizeBytesToFree, sizeBytesToFreeHard int64, server *ServerObj) (err error) {
	if sizeBytesToFree <= 0 {
		logger.Info("no need to free %d binlog size", r.binlogInst.Port)
		return nil
	}
	sizeDeleted := r.RemoveToHardLimit(sizeBytesToFreeHard, server)

	// server.binlogFiles = binlogFiles
	// 再按照本地文件状态，安全清理
	return r.RemoveToSoftLimit(sizeBytesToFree-sizeDeleted, server)
}
