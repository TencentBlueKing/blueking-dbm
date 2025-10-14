package rotate

import (
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/reportlog"
	binlog_parser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"

	"github.com/pkg/errors"
)

// RegisterOneBinlog 注册一个 binlog 文件
// 如果传入了有效的 originalStatus(>-10)，则直接以这个状态注册，否则根据当前的配置文件自动判断
func (i *ServerObj) RegisterOneBinlog(binlogDir string, fileName string, backupEnable bool) error {
	var filesModel []*models.BinlogFileModel

	fileNameFull := filepath.Join(binlogDir, fileName)
	fi, err := os.Stat(fileNameFull)
	if err != nil {
		return errors.Wrapf(err, "os.Stat %s failed", fileNameFull)
	}

	var backupStatus int
	if backupEnable {
		backupStatus = models.IBStatusNew
	} else if i.Tags.DBRole == models.RoleSlave || i.Tags.DBRole == models.RoleOrphan { // slave 无需备份 binlog
		backupStatus = models.FileStatusNoNeedUpload
	} else {
		backupStatus = models.FileStatusNoNeedUpload
	}

	backupStatusInfo := ""
	bp, _ := binlog_parser.NewBinlogParse("", 0, reportlog.ReportTimeLayout1)
	events, err := bp.GetTimeIgnoreStopErr(fileNameFull, true, true)
	// end time > start time TODO
	if err != nil {
		logger.Warn("binlog %s GetTime failed: %s,events:%+v. use stop_time use start_time",
			fileName, err.Error(), events)
		if strings.Contains(err.Error(), "no such file or directory") {
			backupStatus = models.FileStatusForceRemoved
			backupStatusInfo = "register failed"
		} else if len(events) > 0 {
			events = append(events, events[0])
		}
	}

	var startTime, stopTime string
	if len(events) >= 2 {
		startTime = events[0].EventTime
		stopTime = events[1].EventTime
	}
	ff := &models.BinlogFileModel{
		BkBizId:          i.Tags.BkBizId,
		ClusterId:        i.Tags.ClusterId,
		ClusterDomain:    i.Tags.ClusterDomain,
		DBRole:           i.Tags.DBRole,
		Host:             i.Host,
		Port:             i.Port,
		BackupEnable:     backupEnable,
		Filename:         fileName,
		Filesize:         fi.Size(),
		FileMtime:        fi.ModTime().Format(time.RFC3339),
		BackupStatus:     backupStatus,
		BackupStatusInfo: backupStatusInfo,
		StartTime:        startTime,
		StopTime:         stopTime,
		BinlogDir:        binlogDir,
	}
	if i.backupEnable {
		ff.FileRetentionTag = i.backupClient.StorageTag()
	}
	filesModel = append(filesModel, ff)

	logger.Info("new binlog files to process: %+v", filesModel)
	if err := i.rotate.binlogInst.BatchSave(filesModel, models.DB.Conn); err != nil {
		return err
	} else {
		logger.Info("binlog files to process: %+v", filesModel)
	}
	return nil
}

// RegisterBinlog 将新产生的 binlog 记录存入 本地 sqlite db
// lastFileBefore 是上一次处理的最后一个文件
// 实例最后一个 binlog 正在使用，不登记
func (i *ServerObj) RegisterBinlog(lastFileBefore *models.BinlogFileModel) error {
	var roleSwitched bool
	if i.Tags.DBRole == cst.RoleMaster && lastFileBefore.DBRole == cst.RoleSlave {
		// 刚刚发生过切换，上报过去 24h 的 binlog
		roleSwitched = true
	}
	if roleSwitched {
		logger.Warn("RegisterBinlog detect instance %d role changed to master", i.Port)
		ff := &models.BinlogFileModel{
			BkBizId:       i.Tags.BkBizId,
			ClusterId:     i.Tags.ClusterId,
			ClusterDomain: i.Tags.ClusterDomain,
			DBRole:        i.Tags.DBRole,
			Host:          i.Host,
			Port:          i.Port,
		}
		if err := ff.HandleSwitchRole(i.backupEnable, models.DB.Conn); err != nil {
			return errors.WithMessage(err, "handle binlog for switching slave to master")
		}
	}

	fLen := len(i.binlogFiles)
	lastFileNameRegistered := filepath.Base(lastFileBefore.Filename)
	if fLen >= 1 && i.binlogFiles[fLen-1].Filename < lastFileNameRegistered { // 本地最大的 binlog 文件，不应该小于 local db 记录的
		logger.Warn("the last registered file %s is greater than the max binlog file %s in local",
			lastFileNameRegistered, i.binlogFiles[fLen-1].Filename)
		// reset binlog files
		whereMap := map[string]interface{}{
			"port": i.Port,
		}
		binlogInst := models.BinlogFileModel{}
		if rowsAffected, err := binlogInst.Delete(models.DB.Conn.DB, whereMap); err != nil {
			logger.Error("failed to reset binlog items in local db for %d, err:%s", i.Port, err.Error())
		} else {
			logger.Info("reset binlog items in local db rows %d for %d", rowsAffected, i.Port)
		}
		// 直接返回，下一轮生效
		return nil
	}

	var filesModel []*models.BinlogFileModel
	for j, fileObj := range i.binlogFiles {
		if (lastFileBefore.Filename != "" && fileObj.Filename <= lastFileNameRegistered) ||
			j == fLen-1 { // 忽略最后一个binlog
			continue
		}
		var backupStatus int
		if i.backupEnable {
			if i.publicCfg.MaxOldDaysToUpload > 0 &&
				fileObj.Mtime.Before(time.Now().Add(-time.Hour*24*time.Duration(i.publicCfg.MaxOldDaysToUpload))) {
				backupStatus = models.FileStatusTooOldToRegister
			} else {
				backupStatus = models.IBStatusNew
			}
		} else if i.Tags.DBRole == models.RoleSlave || i.Tags.DBRole == models.RoleOrphan { // slave 无需备份 binlog
			backupStatus = models.FileStatusNoNeedUpload
		} else {
			backupStatus = models.FileStatusNoNeedUpload
		}

		backupStatusInfo := ""
		bp, _ := binlog_parser.NewBinlogParse("", 0, reportlog.ReportTimeLayout1)
		fileName := filepath.Join(i.binlogDir, fileObj.Filename)
		events, err := bp.GetTimeIgnoreStopErr(fileName, true, true)
		// end time > start time TODO
		if err != nil {
			logger.Warn("binlog %s GetTime failed: %s,events:%+v. use stop_time use start_time",
				fileName, err.Error(), events)
			if len(events) > 0 {
				events = append(events, events[0])
			}
		}

		var startTime, stopTime string
		if len(events) >= 2 {
			startTime = events[0].EventTime
			stopTime = events[1].EventTime
		}
		ff := &models.BinlogFileModel{
			BkBizId:          i.Tags.BkBizId,
			ClusterId:        i.Tags.ClusterId,
			ClusterDomain:    i.Tags.ClusterDomain,
			DBRole:           i.Tags.DBRole,
			Host:             i.Host,
			Port:             i.Port,
			BackupEnable:     i.backupEnable,
			Filename:         fileObj.Filename,
			Filesize:         fileObj.Size,
			FileMtime:        fileObj.Mtime.Format(time.RFC3339),
			BackupStatus:     backupStatus,
			BackupStatusInfo: backupStatusInfo,
			StartTime:        startTime,
			StopTime:         stopTime,
			BinlogDir:        i.binlogDir,
		}
		if i.backupEnable {
			ff.FileRetentionTag = i.backupClient.StorageTag()
		}
		filesModel = append(filesModel, ff)
	}
	logger.Info("new binlog files to process: %+v", filesModel)

	if err := i.rotate.binlogInst.BatchSave(filesModel, models.DB.Conn); err != nil {
		return err
	} else {
		logger.Info("binlog files to process: %+v", filesModel)
	}
	return nil
}
