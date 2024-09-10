// Package tendispluslightning TODO
package tendispluslightning

import (
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"
)

// FileSplitTask TODO
type FileSplitTask struct {
	LightningFatherTask
}

// NewFileSplitTask 新建一个task
func NewFileSplitTask(row *tendisdb.TbTendisplusLightningTask) *FileSplitTask {
	return &FileSplitTask{
		LightningFatherTask: NewLightningFatherTask(row),
	}
}

// TaskType task类型
func (task *FileSplitTask) TaskType() string {
	return constvar.TendisplusLightningFileSplit
}

// NextTask 下一个task类型
func (task *FileSplitTask) NextTask() string {
	return constvar.TendisplusLightningGenerateSst
}

// Execute TODO
func (task *FileSplitTask) Execute() {
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
			task.SetMessage("等待执行sst文件生成")
			task.UpdateRow()
		}
	}()

	task.SetStatus(1)
	task.SetMessage("开始执行cos文件split")
	task.UpdateRow()

	// 确保 tendisplus_lightning_kv_split 工具存在
	kvSplitTool, err := util.IsToolExecutableInCurrDir(constvar.ToolLightningKVFileSplit)
	if err != nil {
		task.Err = err
		return
	}

	// 如果本地split输出目录存在,则删除
	splitOutDir := task.GetSplitOutputDir()
	fullPath := filepath.Join(task.TaskDir, splitOutDir)
	if util.FileExists(fullPath) {
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s", task.TaskDir, splitOutDir)
		task.Logger.Info(rmCmd)
		_, task.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, time.Hour, task.Logger)
		if task.Err != nil {
			return
		}
	}
	// 创建split输出目录
	task.Err = util.MkDirIfNotExists(fullPath)
	if task.Err != nil {
		return
	}
	splitCmd := fmt.Sprintf("cd %s && %s %s %s", task.TaskDir, kvSplitTool, task.GetLocalCosFile(), splitOutDir)
	task.Logger.Info(splitCmd)
	_, task.Err = util.RunLocalCmd("bash", []string{"-c", splitCmd}, "", nil, 10*time.Hour, task.Logger)
	if task.Err != nil {
		return
	}
	// split 成功
	task.Logger.Info("file split success")

	// split成功后,删除本地cos文件
	localCosFile := task.GetLocalCosFile()
	localFullPath := filepath.Join(task.TaskDir, localCosFile)
	if util.FileExists(localFullPath) {
		rmCmd := fmt.Sprintf("cd  %s && rm -rf %s", task.TaskDir, localCosFile)
		task.Logger.Info(rmCmd)
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 120*time.Second, task.Logger)
	}
}
