// Package tendispluslightning TODO
package tendispluslightning

import (
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/txycos"
	"dbm-services/redis/redis-dts/util"
)

// CosFileDownloadTask TODO
type CosFileDownloadTask struct {
	LightningFatherTask
	cosWorker *txycos.TxyCosWoker
}

// NewCosFileDownloadTask cos 文件下载task
func NewCosFileDownloadTask(row *tendisdb.TbTendisplusLightningTask) *CosFileDownloadTask {
	return &CosFileDownloadTask{
		LightningFatherTask: NewLightningFatherTask(row),
	}
}

// TaskType task类型
func (task *CosFileDownloadTask) TaskType() string {
	return constvar.TendisplusLightningCosFileDownload
}

// NextTask 下一个task类型
func (task *CosFileDownloadTask) NextTask() string {
	return constvar.TendisplusLightningFileSplit
}

func (task *CosFileDownloadTask) initTxyCos() {
	if task.cosWorker == nil {
		task.cosWorker, task.Err = txycos.NewTxyCosWoker(task.Logger)
	}
}

// Execute TODO
func (task *CosFileDownloadTask) Execute() {
	if task.Err != nil {
		return
	}
	defer func() {
		if task.Err != nil {
			task.SetStatus(-1)
			task.SetMessage(task.Err.Error())
			task.UpdateRow()
		} else {
			task.SetTaskType(task.NextTask())
			task.SetStatus(0)
			task.SetMessage("等待执行cos文件split")
			task.UpdateRow()
		}
	}()

	task.SetStatus(1)
	task.SetMessage("开始下载cos中文件")
	task.UpdateRow()

	// 初始化 txy cos
	task.initTxyCos()
	if task.Err != nil {
		return
	}

	localCosFile := task.GetLocalCosFile()
	localFullPath := filepath.Join(task.TaskDir, localCosFile)
	// 如果本地文件存在先删除
	if util.FileExists(localFullPath) {
		rmCmd := fmt.Sprintf("cd  %s && rm -rf %s", task.TaskDir, localCosFile)
		task.Logger.Info(rmCmd)
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 120*time.Second, task.Logger)
	}

	// 下载cos文件
	task.Logger.Info(fmt.Sprintf("start download cos file,cosKey:%s,localFile:%s",
		task.RowData.CosKey,
		localFullPath))
	task.Err = task.cosWorker.DownloadAFile(task.RowData.CosKey, localFullPath)
	if task.Err != nil {
		return
	}
	// cos文件下载成功
	task.Logger.Info(fmt.Sprintf("download cos file success,cosKey:%s,localFile:%s",
		task.RowData.CosKey,
		localFullPath))

}
