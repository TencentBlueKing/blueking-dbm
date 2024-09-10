// Package tendispluslightning TODO
package tendispluslightning

import (
	"fmt"
	"path/filepath"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
	"dbm-services/redis/redis-dts/util"
)

// ScpSstTask TODO
type ScpSstTask struct {
	LightningFatherTask
}

// NewScpSstTask 新建一个task
func NewScpSstTask(row *tendisdb.TbTendisplusLightningTask) *ScpSstTask {
	return &ScpSstTask{
		LightningFatherTask: NewLightningFatherTask(row),
	}
}

// TaskType task类型
func (task *ScpSstTask) TaskType() string {
	return constvar.TendisplusLightningScpSst
}

// NextTask 下一个task类型
func (task *ScpSstTask) NextTask() string {
	return constvar.TendisplusLightningSlaveLoadSst
}

// Execute TODO
func (task *ScpSstTask) Execute() {
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
			task.SetMessage("scp sst完成,等待slave load sst")
			task.UpdateRow()
		}
	}()

	zstdTool, err := util.IsToolExecutableInCurrDir(constvar.ToolZstd)
	if err != nil {
		task.Logger.Error(err.Error())
		task.Err = err
		return
	}
	localIp, err := util.GetLocalIP()
	if err != nil {
		task.Logger.Error(err.Error())
		task.Err = err
		return
	}

	// 获取dst集群的nodes信息
	clusterNodes := task.GetDstClusterNodes()
	if task.Err != nil {
		return
	}
	var slaveSstSaveDir string
	var fullPath string
	var tarFile string
	var zstdFile string
	var tarCmd string                    // 打包命令
	var zstdCmd string                   // 压缩命令
	var rmCmd string                     // 删除命令
	transferMap := map[string][]string{} // key是dst ip,value是 zstd文件列表
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		slaveIP, slavePort, _ := clusterNode.GetSlaveIpPort()
		slaveSstSaveDir = task.GetSlaveNodeSstDir(slaveIP, slavePort)
		tarFile = slaveSstSaveDir + ".tar"
		zstdFile = tarFile + ".zst"
		fullPath = filepath.Join(task.TaskDir, slaveSstSaveDir)

		// 如果 tar不存在,zst文件存在,则跳过 打包压缩环节
		isSkipCompress := util.FileExists(filepath.Join(task.TaskDir, zstdFile)) &&
			!util.FileExists(filepath.Join(task.TaskDir, tarFile))
		if !isSkipCompress {
			if !util.FileExists(fullPath) {
				task.Err = fmt.Errorf("slave_sst_dir:%s not exists", fullPath)
				task.Logger.Error(task.Err.Error())
				return
			}
			if util.FileExists(tarFile) {
				// 删除老的tar包
				rmCmd = fmt.Sprintf("cd %s && rm -rf %s", task.TaskDir, tarFile)
				task.Logger.Info(rmCmd)
				util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, time.Hour, task.Logger)
			}
			// 打包
			tarCmd = fmt.Sprintf("cd %s && tar -cf %s %s && rm -rf %s", task.TaskDir, tarFile, slaveSstSaveDir, slaveSstSaveDir)
			task.Logger.Info(tarCmd)
			_, task.Err = util.RunLocalCmd("bash", []string{"-c", tarCmd}, "", nil, time.Hour, task.Logger)
			if task.Err != nil {
				return
			}
			// 压缩
			zstdCmd = fmt.Sprintf("cd %s && %s %s && rm -rf %s", task.TaskDir, zstdTool, tarFile, tarFile)
			task.Logger.Info(zstdCmd)
			_, task.Err = util.RunLocalCmd("bash", []string{"-c", zstdCmd}, "", nil, time.Hour, task.Logger)
			if task.Err != nil {
				return
			}
		}
		// 构造参数
		if _, ok := transferMap[slaveIP]; !ok {
			transferMap[slaveIP] = []string{}
		}
		transferMap[slaveIP] = append(transferMap[slaveIP], filepath.Join(task.TaskDir, zstdFile))

	}
	// 多个slave ip 并发传输文件
	type transferWorker struct {
		SrcIP    string
		SrcFiles []string
		DstIP    string
		DstDir   string
		Err      error
	}
	wokers := []*transferWorker{}
	for dstIP, files := range transferMap {
		wokers = append(wokers, &transferWorker{
			SrcIP:    localIp,
			SrcFiles: files,
			DstIP:    dstIP,
			DstDir:   constvar.DbbakDir,
		})
	}
	var wg sync.WaitGroup
	for _, woker01 := range wokers {
		woker := woker01
		wg.Add(1)
		go func(woker *transferWorker) {
			defer wg.Done()
			var cli *scrdbclient.Client
			cli, woker.Err = scrdbclient.NewClient(constvar.BkDbm, task.Logger)
			if woker.Err != nil {
				return
			}
			param := scrdbclient.TransferFileReq{
				SourceList: []scrdbclient.TransferFileSourceItem{
					{
						BkCloudID: int(task.RowData.BkCloudID),
						IP:        localIp,
						Account:   constvar.MysqlOSAccount,
						FileList:  woker.SrcFiles,
					},
				},
				TargetAccount: constvar.MysqlOSAccount,
				TargetDir:     woker.DstDir,
				TargetIPList: []scrdbclient.IPItem{
					{BkCloudID: int(task.RowData.BkCloudID), IP: woker.DstIP},
				},
				Timeout: 86300,
			}
			woker.Err = cli.SendNew(param, 5)
			if woker.Err != nil {
				return
			}
		}(woker)
	}
	wg.Wait()
	for _, woker01 := range wokers {
		woker := woker01
		if woker.Err != nil {
			task.Err = woker.Err
			return
		}
	}
	// 文件传输文成后,删除本地压缩文件
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		slaveIP, slavePort, _ := clusterNode.GetSlaveIpPort()
		slaveSstSaveDir = task.GetSlaveNodeSstDir(slaveIP, slavePort)
		tarFile = slaveSstSaveDir + ".tar"
		zstdFile = tarFile + ".zst"
		fullPath = filepath.Join(task.TaskDir, zstdFile)
		if util.FileExists(fullPath) {
			rmCmd = fmt.Sprintf("cd %s && rm -rf %s", task.TaskDir, zstdFile)
			task.Logger.Info(rmCmd)
			util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, time.Hour, task.Logger)
		}
	}
}
