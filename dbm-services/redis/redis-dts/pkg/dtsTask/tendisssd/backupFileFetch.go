package tendisssd

import (
	"path/filepath"

	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
)

// BakcupFileFetchTask 备份拉取task
type BakcupFileFetchTask struct {
	dtsTask.FatherTask
}

// TaskType task类型
func (task *BakcupFileFetchTask) TaskType() string {
	return constvar.BackupfileFetchTaskType
}

// NextTask 下一个task类型
func (task *BakcupFileFetchTask) NextTask() string {
	return constvar.TredisdumpTaskType
}

// NewBakcupFileFetchTask 新建一个备份拉取task
func NewBakcupFileFetchTask(row *tendisdb.TbTendisDTSTask) *BakcupFileFetchTask {
	return &BakcupFileFetchTask{
		FatherTask: dtsTask.NewFatherTask(row),
	}
}

// PreClear 清理以往生成的垃圾数据
func (task *BakcupFileFetchTask) PreClear() {
	if task.Err != nil {
		return
	}
	task.ClearLocalFetchBackup()
}

// Execute 执行文件拉取
func (task *BakcupFileFetchTask) Execute() {
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
	task.UpdateDbAndLogLocal("从%s拉取%s到本地...", task.RowData.SrcIP, task.RowData.TendisbackupFile)

	task.Err = task.InitTaskDir()
	if task.Err != nil {
		return
	}

	task.PreClear()
	if task.Err != nil {
		return
	}

	// 从srcIP上拉取备份文件
	// var absCli remoteOperation.RemoteOperation
	// absCli, task.Err = remoteOperation.NewIAbsClientByEnvVars(task.RowData.SrcIP, task.Logger)
	// if task.Err != nil {
	// 	return
	// }
	// task.Err = absCli.RemoteDownload(
	// 	filepath.Dir(task.RowData.TendisbackupFile),
	// 	task.TaskDir,
	// 	filepath.Base(task.RowData.TendisbackupFile),
	// 	constvar.GetABSPullBwLimit(),
	// )
	// if task.Err != nil {
	// 	return
	// }
	var localIP string
	localIP, task.Err = util.GetLocalIP()
	if task.Err != nil {
		return
	}
	cli, err := scrdbclient.NewClient(constvar.BkDbm, task.Logger)
	if err != nil {
		task.Err = err
		return
	}
	param := scrdbclient.TransferFileReq{}
	param.SourceList = append(param.SourceList, scrdbclient.TransferFileSourceItem{
		BkCloudID: int(task.RowData.BkCloudID),
		IP:        task.RowData.SrcIP,
		Account:   "mysql",
		FileList: []string{
			task.RowData.TendisbackupFile + string(filepath.Separator),
		},
	})
	param.TargetAccount = "mysql"
	param.TargetDir = task.TaskDir
	param.TargetIPList = append(param.TargetIPList, scrdbclient.IPItem{
		BkCloudID: int(task.RowData.BkCloudID),
		IP:        localIP,
	})
	param.Timeout = 2 * 86400
	err = cli.SendNew(param, 5)
	if err != nil {
		task.Err = err
		return
	}

	backupFile := filepath.Base(task.RowData.TendisbackupFile)
	task.SetFetchFile(filepath.Join(task.TaskDir, backupFile))
	task.UpdateDbAndLogLocal("%s上备份拉取成功", task.RowData.SrcIP)

	task.RefreshRowData()
	if task.Err != nil {
		return
	}
	if task.RowData.SyncOperate == constvar.RedisForceKillTaskSuccess {
		// task had been terminated by force
		// clear src host backup
		task.ClearSrcHostBackup()
		// clear local backup dir
		task.ClearLocalFetchBackup()
		// restore slave-log-keep-count
		task.RestoreSrcSSDKeepCount()
		return
	}

	task.EndClear()
	if task.Err != nil {
		return
	}

	task.SetStatus(0)
	task.SetTaskType(task.NextTask())
	task.UpdateDbAndLogLocal("备份文件:%s成功拉取到本地", task.RowData.FetchFile)
}

// EndClear 文件拉取完成后清理srcIP上残留备份信息
func (task *BakcupFileFetchTask) EndClear() {
	if task.RowData.TendisbackupFile == "" {
		return
	}
	// 备份文件拉取完成后,清理 srcIP上的backupFile文件,避免占用过多空间
	task.ClearSrcHostBackup()
}
