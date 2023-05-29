package pitr

import (
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/backupsys"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/report"
	"time"

	log "github.com/sirupsen/logrus"
)

// BackupOption 备份参数
type BackupOption struct {
	MongoHost          *mymongo.MongoHost
	BackupType         string
	Dir                string
	Zip                bool
	FullFreq           uint64
	IncrFreq           uint64
	FullTag            string
	IncrTag            string
	SendToBackupSystem bool
	RemoveOldFileFirst bool
	ReportFile         string
	BkDbmLabel         *config.BkDbmLabel
	DryRun             bool
}

// DoJob 执行一个备份任务
func DoJob(option *BackupOption) {
	var bm *BackupMetaV2
	var err error
	log.Debugf("DoJob option %+v", option)
	log.Infof("DoJob %s %s %s", option.MongoHost.Host, option.BackupType, option.Dir)
	if bm, err = NewBackupMetaV2(option.Dir, option.MongoHost); err != nil {
		log.Fatalf("CreateMetaFile Error: %v", err)
	} else {
		log.Debugf("Get BackupMeta %+v GetMetaFile:%s", bm, bm.GetMetaFileName())
	}

	if option.RemoveOldFileFirst {
		log.Infof("RemoveOldFileFirst")
		bm.RemoveOldFileFirst()
	}

	prevFull, lastIncr, err := bm.GetLastBackup()
	log.Debugf("GetLastBackup full:%+v incr:%+v err:%v", prevFull, lastIncr, err)
	now := time.Now()
	// 检查是否可以跳过备份.
	// 如果是AUTO。 它会根据上一次全备和增量备份的时间，来决定本次是全备还是增量备份，并修改option.BackupType
	if canSkip(option, prevFull, lastIncr, now) {
		return
	}

	var lastBackup *BackupFileName
	if BackupTypeFull == option.BackupType || lastIncr == nil {
		lastBackup = prevFull
	} else {
		lastBackup = lastIncr
	}

	log.Printf("lastBackup %+v", lastBackup)
	currBackup, err := DoBackup(option.MongoHost, option.BackupType, option.Dir, option.Zip, lastBackup, nil)
	if err != nil || currBackup == nil {
		log.Errorf("backup failed %v %v", currBackup, err)
		return
	}
	bm.Append(currBackup) // 保存一次.meta文件，给result.FileName赋值
	// backup success. filename: 这是给dbmon接收的，格式不能改.
	log.Printf("do %s backup success. filename:'%s'", option.BackupType, currBackup.GetFullPath())
	// todo 如果备份系统返回TaskId失败怎么办？ 要写入另外一个文件。另外一段时间后再尝试重试.
	// todo 提前检查 ReportFile 是否存在，是否可写
	uploadFileAndAppendToReportFile(option, currBackup)
	// 如果是全备，且之前有过全备，再将增量备份一次
	backupIncrForPrevFull(option, bm, prevFull, currBackup)
}

func backupIncrForPrevFull(option *BackupOption, bm *BackupMetaV2,
	prevFull, currBackup *BackupFileName) {
	if !(option.BackupType == BackupTypeFull && prevFull != nil) {
		return
	}
	lastIncr, _ := bm.GetLastIncr(prevFull)
	if lastIncr == nil {
		// 上一次全备并没有增量备份，这里，应该抛出一个事件
		lastIncr = prevFull
		log.Warnf("set lastInc to lastFull %+v", lastIncr)
	}
	incrResult, err := DoBackup(option.MongoHost, BackupTypeIncr, option.Dir, option.Zip, lastIncr, &currBackup.LastTs)
	if incrResult != nil {
		bm.Append(incrResult)
		uploadFileAndAppendToReportFile(option, incrResult)
	} else {
		log.Errorf("incr backup failed %v %v", incrResult, err)
	}
}

func uploadFileAndAppendToReportFile(option *BackupOption, result *BackupFileName) {
	task, err := sendToBackupSystem(option, result)
	if err == nil {
		log.Infof("sendToBackupSystem file: %s, taskid: %s err:%v", task.FilePath, task.TaskId, err)
	} else {
		log.Errorf("sendToBackupSystem file: %s, err:%v", result.GetFullPath(), err)
	}

	if option.ReportFile == "" {
		log.Infof("skip appendToReportFile because ReportFile is empty")
	} else {
		err = appendToReportFile(option, result, task)
		log.Infof("appendToReportFile file: %s err:%v", result.GetFullPath(), err)
	}

}

func getLastBackupTime(lastFull, lastIncr *BackupFileName, now time.Time) (lastFullStart, lastIncrStart time.Time) {
	if lastFull == nil {
		lastFullStart, _ = time.Parse("20060102150405", "19700101010101")
	} else {
		lastFullStart = lastFull.StartTime
	}

	if lastIncr == nil {
		lastIncrStart = lastFullStart
	} else {
		lastIncrStart = lastIncr.StartTime
	}

	log.Debugf("timediff Now:[%s] LastBackup:[%s] diff:[%f]",
		now.Format("2006-01-02 15:04:05"),
		lastFullStart.Format("2006-01-02 15:04:05"),
		now.Sub(lastFullStart).Seconds())
	return lastFullStart, lastIncrStart
}

func canSkip(option *BackupOption, lastFull, lastIncr *BackupFileName, now time.Time) bool {
	lastFullStart, lastIncrStart := getLastBackupTime(lastFull, lastIncr, now)
	isSkip := false
	if option.BackupType == BackupTypeAuto {
		if now.Sub(lastFullStart).Seconds() >= float64(option.FullFreq) {
			option.BackupType = BackupTypeFull
		} else if now.Sub(lastIncrStart).Seconds() >= float64(option.IncrFreq) {
			option.BackupType = BackupTypeIncr
		} else {
			log.Printf("Last %s Backup is Start at %s, Will Wait to %s",
				BackupTypeFull, lastFullStart, lastFullStart.Add(time.Second*time.Duration(option.FullFreq)))
			log.Printf("Last %s Backup is Start at %s, Will Wait to %s",
				BackupTypeIncr, lastIncrStart, lastIncrStart.Add(time.Second*time.Duration(option.IncrFreq)))
			return true
		}
	} else if option.BackupType == BackupTypeFull {
		if now.Sub(lastFullStart).Seconds() <= float64(option.FullFreq) {
			log.Printf("Last %s Backup is Start at %s, Will Wait to %s",
				option.BackupType, lastFullStart, lastFullStart.Add(time.Second*time.Duration(option.FullFreq)))
			return true
		}
	} else if option.BackupType == BackupTypeIncr {
		if now.Sub(lastFullStart).Seconds() < float64(option.IncrFreq) {
			log.Printf("Last %s Backup is Start at %s, Will Wait to %s",
				option.BackupType, lastFullStart, lastFullStart.Add(time.Second*time.Duration(option.IncrFreq)))
			return true
		}
	}
	return isSkip
}

func sendToBackupSystem(option *BackupOption, backupRec *BackupFileName) (task *backupsys.TaskInfo, err error) {
	if !option.SendToBackupSystem {
		task = &backupsys.TaskInfo{
			FilePath: backupRec.GetFullPath(),
		}
		return
	}
	var fileTag string
	if backupRec.Type == BackupTypeFull {
		fileTag = option.FullTag
	} else {
		fileTag = option.IncrTag
	}
	if task, err = backupsys.UploadFile(backupRec.FileName, fileTag); err != nil {
		log.Warnf("UploadFile failed %v", err)
		return
	}
	err = task.SaveToFile()
	return task, err
}

func appendToReportFile(option *BackupOption, backupRec *BackupFileName, bsInfo *backupsys.TaskInfo) error {
	rec := report.NewBackupRecord()
	rec.AppendFileInfo(backupRec.StartTime.Local().Format(time.RFC3339),
		backupRec.EndTime.Local().Format(time.RFC3339),
		backupRec.GetFullPath(),
		backupRec.FileName,
		backupRec.FileSize)

	rec.AppendMetaLabel(option.BkDbmLabel)
	fullStr, _ := backupRec.GetV0FullStr()
	rec.AppendDailySrc(fullStr, fullStr, backupRec.Type, backupRec.V0IncrSeq, backupRec.LastTs.Sec)
	if bsInfo != nil {
		rec.AppendBsInfo(bsInfo.TaskId, bsInfo.Tag)
	}
	return report.AppendObjectToFile(option.ReportFile, rec)
}
