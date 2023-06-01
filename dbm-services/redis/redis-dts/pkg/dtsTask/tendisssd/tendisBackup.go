package tendisssd

import (
	"encoding/base64"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/redis/redis-dts/models/myredis"
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
	"dbm-services/redis/redis-dts/util"

	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// TendisBackupTask src tendisssd备份task
type TendisBackupTask struct {
	dtsTask.FatherTask
	srcClient *myredis.RedisWorker `json:"-"`
	dstClient *myredis.RedisWorker `json:"-"`
}

// TaskType task类型
func (task *TendisBackupTask) TaskType() string {
	return constvar.TendisBackupTaskType
}

// NextTask 下一个task类型
func (task *TendisBackupTask) NextTask() string {
	return constvar.BackupfileFetchTaskType
}

// NewTendisBackupTask 新建一个src tendisssd备份拉取task
func NewTendisBackupTask(row *tendisdb.TbTendisDTSTask) *TendisBackupTask {
	return &TendisBackupTask{
		FatherTask: dtsTask.NewFatherTask(row),
	}
}

// Init 初始化
func (task *TendisBackupTask) Init() {
	if task.Err != nil {
		return
	}
	defer func() {
		if task.Err != nil {
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
		}
	}()
	task.FatherTask.Init()
	if task.Err != nil {
		return
	}

	srcAddr := fmt.Sprintf("%s:%d", task.RowData.SrcIP, task.RowData.SrcPort)
	srcPasswd, err := base64.StdEncoding.DecodeString(task.RowData.SrcPassword)
	if err != nil {
		task.Logger.Error(constvar.TendisBackupTaskType+" init base64.decode srcPasswd fail",
			zap.Error(err), zap.String("rowData", task.RowData.ToString()))
		task.Err = fmt.Errorf("[%s] get src password fail,err:%v", task.TaskType(), err)
		return
	}
	task.srcClient, err = myredis.NewRedisClient(srcAddr, string(srcPasswd), 0, task.Logger)
	if err != nil {
		task.Err = err
		return
	}
	dstAddr := strings.TrimSpace(task.RowData.DstCluster)
	dstPasswd, err := base64.StdEncoding.DecodeString(task.RowData.DstPassword)
	if err != nil {
		task.Logger.Error(constvar.TendisBackupTaskType+" init base64.decode dstPasswd fail",
			zap.Error(err), zap.String("rowData", task.RowData.ToString()))
		task.Err = fmt.Errorf("[%s] get dst password fail,err:%v", task.TaskType(), err)
		return
	}
	task.dstClient, err = myredis.NewRedisClient(dstAddr, string(dstPasswd), 0, task.Logger)
	if err != nil {
		task.Err = err
		return
	}
	defer task.dstClient.Close() // dstClient主要测试连接性, 未来用不到

	task.SetStatus(1)
	task.UpdateDbAndLogLocal("[%s] 源:%s 目的:%s 连接测试成功", task.TaskType(), srcAddr, dstAddr)

	return
}

// PreClear 清理以往产生的垃圾数据
func (task *TendisBackupTask) PreClear() {
	var err error
	task.Err = task.InitTaskDir()
	if task.Err != nil {
		return
	}
	if strings.Contains(task.TaskDir, fmt.Sprintf("%s_%d", task.RowData.SrcIP, task.RowData.SrcPort)) == false {
		return
	}
	_, err = os.Stat(task.TaskDir)
	if err == nil {
		// 目录存在,清理
		rmCmd := fmt.Sprintf("rm -rf %s >/dev/null 2>&1", filepath.Join(task.TaskDir, "*"))
		task.Logger.Info(fmt.Sprintf("TendisBackupTask PreClear execute localCommand:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 120*time.Second, task.Logger)
	}
}

// Execute src tendisSSD执行backup命令
func (task *TendisBackupTask) Execute() {
	if task.Err != nil {
		return
	}
	layout := "20060102150405"
	defer func() {
		if task.Err != nil {
			task.SetStatus(-1)
			task.SetMessage(task.Err.Error())
			task.UpdateRow()
		}
	}()

	task.PreClear()
	if task.Err != nil {
		return
	}

	waitTimeout := 3600 // 等待执行中的备份完成,等待1小时
	limit := waitTimeout / 60
	for {
		if limit == 0 {
			task.Err = fmt.Errorf("timeout")
			task.Logger.Error("timeout")
			return
		}
		isRunning, err := task.srcClient.TendisSSDIsBackupRunning()
		if err != nil {
			task.Err = err
			return
		}
		if isRunning == false {
			break
		}
		task.UpdateDbAndLogLocal("当前有一个backup任务执行中,等待其完成")
		time.Sleep(60 * time.Second)
		limit = limit - 1
	}
	// backupDir:=fmt.Sprintf("tasks/%d_%s_%s/backup")
	backupFile := fmt.Sprintf("REDIS_FULL_rocksdb_%s_%d_%s",
		task.RowData.SrcIP, task.RowData.SrcPort, time.Now().Format(layout))
	backupDir := "/data/dbbak/" + backupFile
	task.UpdateDbAndLogLocal("tendis:%s 开始创建备份目录:%s", task.srcClient.Addr, backupDir)

	cli, err := scrdbclient.NewClient(constvar.BkDbm, task.Logger)
	if err != nil {
		task.Err = err
		return
	}
	_, err = cli.ExecNew(scrdbclient.FastExecScriptReq{
		Account:        "mysql",
		Timeout:        3600,
		ScriptLanguage: 1,
		ScriptContent:  fmt.Sprintf(`mkdir -p %s`, backupDir),
		IPList: []scrdbclient.IPItem{
			{
				BkCloudID: int(task.RowData.BkCloudID),
				IP:        task.RowData.SrcIP,
			},
		},
	}, 5)
	if err != nil {
		task.Err = err
		return
	}

	ssdSlaveLogKeepCount := viper.GetInt64("ssdSlaveLogKeepCount")
	if ssdSlaveLogKeepCount == 0 {
		ssdSlaveLogKeepCount = 200000000 // 默认值设置为两亿
	}
	task.UpdateDbAndLogLocal("开始执行备份slave-log-keep-count参数,并将%s中slave-log-keep-count设置为:%d",
		task.srcClient.Addr, ssdSlaveLogKeepCount)
	task.SaveSrcSSDKeepCount()
	if task.Err != nil {
		return
	}
	task.SetSrcNewLogCount(ssdSlaveLogKeepCount)
	_, err = task.srcClient.ConfigSet("slave-log-keep-count", ssdSlaveLogKeepCount)
	if err != nil {
		task.Err = err
		return
	}

	task.UpdateDbAndLogLocal("开始执行backup任务...")

	task.Err = task.srcClient.TendisSSDBakcup(backupDir)
	if task.Err != nil {
		return
	}

	task.UpdateDbAndLogLocal("%s backup %s 执行中...", task.srcClient.Addr, backupDir)

	waitTimeout = 7200 // 等待执行中的备份完成,最多等待2小时
	limit = waitTimeout / 60
	msg := ""
	for {
		time.Sleep(60 * time.Second)
		if limit == 0 {
			task.Err = fmt.Errorf("timeout")
			task.Logger.Error("timeout")
			break
		}
		isRunning, err := task.srcClient.TendisSSDIsBackupRunning()
		if err != nil {
			task.Err = err
			return
		}
		if isRunning == false {
			time.Sleep(1 * time.Minute) // 确认备份成功后,再sleep 60s
			break
		}
		row01, _ := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
		if task.RowData.SyncOperate != row01.SyncOperate {
			task.SetSyncOperate(row01.SyncOperate)
			msg = row01.SyncOperate + "等待备份完成,"
		}
		if row01 == nil {
			task.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", task.RowData.ID, row01)
			return
		}
		task.UpdateDbAndLogLocal("%s%s backup %s 执行中...", msg, task.srcClient.Addr, backupDir)
		limit = limit - 1
	}

	if !constvar.IsGlobalEnv() {
		lsCmd := fmt.Sprintf(`ls %s`, backupDir)
		lsRets, err := cli.ExecNew(scrdbclient.FastExecScriptReq{
			Account:        "mysql",
			Timeout:        3600,
			ScriptLanguage: 1,
			ScriptContent:  lsCmd,
			IPList: []scrdbclient.IPItem{
				{
					BkCloudID: int(task.RowData.BkCloudID),
					IP:        task.RowData.SrcIP,
				},
			},
		}, 5)
		if err != nil {
			task.Err = err
			return
		}

		ret01 := strings.TrimSpace(lsRets[0].LogContent)
		if ret01 == "" {
			task.Err = fmt.Errorf("备份文件:%s  不存在?,shellCmd:%s,ret:%s", backupDir, lsCmd, ret01)
			task.Logger.Error(task.Err.Error())
			return
		}
	}
	task.SetTendisbackupFile(backupDir)
	task.EndClear()
	if task.Err != nil {
		return
	}

	task.SetTaskType(task.NextTask())
	task.SetStatus(0)
	task.SetMessage("等待拉取%s", backupDir)
	task.UpdateRow()

	return
}

// EndClear src tendisSSD备份且打包完成后,清理原始备份目录
func (task *TendisBackupTask) EndClear() {
	row01, err := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
	if err != nil {
		task.Err = err
		return
	}
	if row01 == nil {
		task.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", task.RowData.ID, row01)
		return
	}
	if row01.SyncOperate == constvar.RedisForceKillTaskTodo {
		// 任务提前终止,清理src redis备份
		task.ClearSrcHostBackup()
		if task.Err != nil {
			return
		}
		task.RestoreSrcSSDKeepCount()
		task.SetSyncOperate(constvar.RedisForceKillTaskSuccess)
		task.Err = fmt.Errorf("%s...", constvar.RedisForceKillTaskSuccess)
		return
	}

	return
}
