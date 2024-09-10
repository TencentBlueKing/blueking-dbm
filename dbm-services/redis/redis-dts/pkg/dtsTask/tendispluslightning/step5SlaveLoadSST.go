// Package tendispluslightning TODO
package tendispluslightning

import (
	"fmt"
	"path/filepath"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/models/myredis"
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
)

// SlaveLoadSstTask TODO
type SlaveLoadSstTask struct {
	LightningFatherTask
}

// NewSlaveLoadSstTask TODO
// NewScpSstTask 新建一个task
func NewSlaveLoadSstTask(row *tendisdb.TbTendisplusLightningTask) *SlaveLoadSstTask {
	return &SlaveLoadSstTask{
		LightningFatherTask: NewLightningFatherTask(row),
	}
}

// TaskType task类型
func (task *SlaveLoadSstTask) TaskType() string {
	return constvar.TendisplusLightningSlaveLoadSst
}

// NextTask 下一个task类型,没有下一个task type了
func (task *SlaveLoadSstTask) NextTask() string {
	return constvar.TendisplusLightningSlaveLoadSst
}

// Execute TODO
func (task *SlaveLoadSstTask) Execute() {
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
			task.SetStatus(2)
			task.SetMessage("slave load sst文件完成")
			task.UpdateRow()
		}
	}()
	clusterNodes := task.GetDstClusterNodes()
	if task.Err != nil {
		return
	}

	var slaveSstSaveDir string
	var tarFile string
	var zstdFile string
	var unCompressCmd string

	type remoteWorker struct {
		SlaveIP string
		Cmd     string
		Err     error
	}
	unCompressWorkers := []*remoteWorker{}
	rmWorkers := []*remoteWorker{}
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		slaveIP, slavePort, _ := clusterNode.GetSlaveIpPort()
		slaveSstSaveDir = task.GetSlaveNodeSstDir(slaveIP, slavePort)
		tarFile = slaveSstSaveDir + ".tar"
		zstdFile = tarFile + ".zst"
		unCompressCmd = fmt.Sprintf("cd %s && rm -rf %s && /home/mysql/dbtools/zstd -d %s && tar -xf %s && rm -rf %s",
			constvar.DbbakDir, slaveSstSaveDir, zstdFile, tarFile, tarFile)
		unCompressWorkers = append(unCompressWorkers, &remoteWorker{
			SlaveIP: slaveIP,
			Cmd:     unCompressCmd,
		})
		rmWorkers = append(rmWorkers, &remoteWorker{
			SlaveIP: slaveIP,
			Cmd:     fmt.Sprintf("cd %s && rm -rf %s %s", constvar.DbbakDir, zstdFile, slaveSstSaveDir),
		})
	}
	// 多个slave ip并发执行命令
	task.Logger.Info("slave start uncompress sst file")
	var wg sync.WaitGroup
	for _, tmp := range unCompressWorkers {
		worker := tmp
		wg.Add(1)
		go func(worker *remoteWorker) {
			defer wg.Done()
			var cli *scrdbclient.Client
			cli, worker.Err = scrdbclient.NewClient(constvar.BkDbm, task.Logger)
			if worker.Err != nil {
				return
			}
			_, worker.Err = cli.ExecNew(scrdbclient.FastExecScriptReq{
				Account:        constvar.MysqlOSAccount,
				Timeout:        3600,
				ScriptLanguage: 1,
				ScriptContent:  worker.Cmd,
				IPList: []scrdbclient.IPItem{
					{
						BkCloudID: int(task.RowData.BkCloudID),
						IP:        worker.SlaveIP,
					},
				},
			}, 5)
			if worker.Err != nil {
				return
			}
		}(worker)
	}
	wg.Wait()

	for _, worker := range unCompressWorkers {
		if worker.Err != nil {
			task.Err = worker.Err
			return
		}
	}
	// slave执行 loadexternalfiles 命令
	task.Logger.Info("slave start load sst file")
	var slaveSaveDir string
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		slaveIP, slavePort, _ := clusterNode.GetSlaveIpPort()
		slaveSstSaveDir = task.GetSlaveNodeSstDir(slaveIP, slavePort)
		slaveSaveDir = filepath.Join(constvar.DbbakDir, slaveSstSaveDir)
		task.TendisplusSlaveLoadSST(clusterNode, slaveSaveDir)
		if task.Err != nil {
			return
		}
	}

	// slave执行 loadexternalfiles命令成功后,删除slave本地的zst文件
	task.Logger.Info("slave start rm local zst file")
	var wg01 sync.WaitGroup
	for _, tmp := range rmWorkers {
		worker := tmp
		wg01.Add(1)
		go func(worker *remoteWorker) {
			defer wg01.Done()
			var cli *scrdbclient.Client
			cli, worker.Err = scrdbclient.NewClient(constvar.BkDbm, task.Logger)
			if worker.Err != nil {
				return
			}
			_, worker.Err = cli.ExecNew(scrdbclient.FastExecScriptReq{
				Account:        constvar.MysqlOSAccount,
				Timeout:        3600,
				ScriptLanguage: 1,
				ScriptContent:  worker.Cmd,
				IPList: []scrdbclient.IPItem{
					{
						BkCloudID: int(task.RowData.BkCloudID),
						IP:        worker.SlaveIP,
					},
				},
			}, 5)
			if worker.Err != nil {
				return
			}
		}(worker)
	}
	wg01.Wait()
}

// TendisplusSlaveLoadSST TODO
func (task *SlaveLoadSstTask) TendisplusSlaveLoadSST(cNode *clusterNodeItem, slaveSaveDir string) {
	var slaveConn *myredis.RedisWorker
	slaveConn, task.Err = myredis.NewRedisClientWithTimeout(cNode.SlaveAddr, cNode.RedisPassword,
		0, 2*time.Hour, task.Logger)
	if task.Err != nil {
		return
	}
	defer slaveConn.Close()
	task.Logger.Info(fmt.Sprintf("slave %s start 'loadexternalfiles %s all copy'", cNode.SlaveAddr, slaveSaveDir))
	task.Err = slaveConn.Loadexternalfiles(slaveSaveDir, "all", "copy")
	if task.Err != nil {
		return
	}
}
