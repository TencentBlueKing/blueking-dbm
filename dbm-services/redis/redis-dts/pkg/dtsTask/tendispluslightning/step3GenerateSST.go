// Package tendispluslightning TODO
package tendispluslightning

import (
	"fmt"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"
)

// GenerateSstTask TODO
type GenerateSstTask struct {
	LightningFatherTask
}

// NewGenerateSstTask 新建一个task
func NewGenerateSstTask(row *tendisdb.TbTendisplusLightningTask) *GenerateSstTask {
	return &GenerateSstTask{
		LightningFatherTask: NewLightningFatherTask(row),
	}
}

// TaskType task类型
func (task *GenerateSstTask) TaskType() string {
	return constvar.TendisplusLightningGenerateSst
}

// NextTask 下一个task类型
func (task *GenerateSstTask) NextTask() string {
	return constvar.TendisplusLightningScpSst
}

// Execute TODO
func (task *GenerateSstTask) Execute() {
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
			task.SetMessage("等待执行scp sst")
			task.UpdateRow()
		}
	}()

	// 确保 tendisplus_lightning_sst_generator 工具存在
	sstGenTool, err := util.IsToolExecutableInCurrDir(constvar.ToolLightningSstGenerator)
	if err != nil {
		task.Err = err
		return
	}

	// 先清理之前的sst目录
	var slaveSstSaveDir string
	var fullPath string
	var rmCmd string

	// 获取dst集群的nodes信息
	clusterNodes := task.GetDstClusterNodes()
	if task.Err != nil {
		return
	}
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		ip, port, err := clusterNode.GetSlaveIpPort()
		if err != nil {
			task.Err = err
			task.Logger.Error(task.Err.Error())
			return
		}
		slaveSstSaveDir = task.GetSlaveNodeSstDir(ip, port)
		fullPath = filepath.Join(task.TaskDir, slaveSstSaveDir)
		if util.FileExists(fullPath) {
			rmCmd = fmt.Sprintf("cd %s && rm -rf %s", task.TaskDir, slaveSstSaveDir)
			task.Logger.Info(rmCmd)
			_, task.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, time.Hour, task.Logger)
			if task.Err != nil {
				return
			}
		}
	}
	// 获取到 split输出目录
	splitOutputDir := task.GetSplitOutputDir()
	// 在创建sst目录,并执行 sst_generator
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		ip, port, err := clusterNode.GetSlaveIpPort()
		if err != nil {
			task.Err = err
			task.Logger.Error(task.Err.Error())
			return
		}
		slaveSstSaveDir = task.GetSlaveNodeSstDir(ip, port)
		var fullPath string
		// 创建目录,$taskDir/$slaveSstDir/0、/1、/2、....、/9,对应的是tendisplus的10个kvstore
		for i := 0; i < 10; i++ {
			fullPath = filepath.Join(task.TaskDir, slaveSstSaveDir, strconv.Itoa(i))
			if !util.FileExists(fullPath) {
				mkCmd := fmt.Sprintf("mkdir -p %s", fullPath)
				task.Logger.Info(mkCmd)
				_, task.Err = util.RunLocalCmd("bash", []string{"-c", mkCmd}, "", nil, time.Hour, task.Logger)
				if task.Err != nil {
					return
				}
			}
		}
		// 执行 sst_generator
		sstGenCmd := fmt.Sprintf("cd %s && %s -i %s -o %s -s %q -t 5",
			task.TaskDir,
			sstGenTool, splitOutputDir,
			slaveSstSaveDir, clusterNode.Slots)
		task.Logger.Info(sstGenCmd)
		_, task.Err = util.RunLocalCmd("bash", []string{"-c", sstGenCmd}, "", nil, 10*time.Hour, task.Logger)
		if task.Err != nil {
			return
		}
	}
	task.Logger.Info("generate sst success")

	// sst文件生成成功后,删除split输出目录
	fullPath = filepath.Join(task.TaskDir, splitOutputDir)
	if util.FileExists(fullPath) {
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s", task.TaskDir, splitOutputDir)
		task.Logger.Info(rmCmd)
		_, task.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, time.Hour, task.Logger)
		if task.Err != nil {
			return
		}
	}
	return
}
