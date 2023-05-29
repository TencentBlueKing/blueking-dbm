package tendisssd

import (
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask"
	"dbm-services/redis/redis-dts/util"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// TredisdumpTask 对备份文件执行tredisdump
type TredisdumpTask struct {
	dtsTask.FatherTask
}

// TaskType task类型
func (task *TredisdumpTask) TaskType() string {
	return constvar.TredisdumpTaskType
}

// NextTask 下一个task类型
func (task *TredisdumpTask) NextTask() string {
	return constvar.CmdsImporterTaskType
}

// NewTredisdumpTask 新建tredisdump task
func NewTredisdumpTask(row *tendisdb.TbTendisDTSTask) *TredisdumpTask {
	return &TredisdumpTask{
		FatherTask: dtsTask.NewFatherTask(row),
	}
}

// PreClear 清理以往生成的垃圾数据,如拉取到本地的备份.tar文件
func (task *TredisdumpTask) PreClear() {
	if task.Err != nil {
		return
	}
	task.ClearLocalSQLDir()
}

// Execute 执行tredisdump
func (task *TredisdumpTask) Execute() {
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
	task.SetStatus(1)
	task.UpdateDbAndLogLocal("开始对执行tredisdump task")

	var dumperClient string
	dumperClient, task.Err = util.IsToolExecutableInCurrDir("tredisdump")
	if task.Err != nil {
		return
	}
	task.Logger.Info("tredisdump client is ok", zap.String("dumperClient", dumperClient))

	// 本地目录: deps 是否存在,保存着 tredisdumper依赖的包
	currExecPath, err := util.CurrentExecutePath()
	if err != nil {
		return
	}

	depsDir := filepath.Join(currExecPath, "deps")
	_, err = os.Stat(depsDir)
	if err != nil && os.IsNotExist(err) == true {
		task.Err = fmt.Errorf("%s not exists,err:%v", depsDir, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.Logger.Info("library deps is ok", zap.String("depsDir", depsDir))

	_, err = os.Stat(task.RowData.FetchFile)
	if err != nil && os.IsNotExist(err) == true {
		task.Err = fmt.Errorf("备份文件:%s not exists", task.RowData.FetchFile)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.Logger.Info("backupFile is ok", zap.String("backupFile", task.RowData.FetchFile))

	task.Err = task.InitTaskDir()
	if task.Err != nil {
		return
	}
	task.PreClear()
	if task.Err != nil {
		return
	}

	cmdFilesBase := fmt.Sprintf("TREDISDUMP_SQL_%s_%d_%s",
		task.RowData.SrcIP, task.RowData.SrcPort, time.Now().Format(layout))
	cmdFilesDir := filepath.Join(task.TaskDir, cmdFilesBase)
	task.Err = util.MkDirIfNotExists(cmdFilesDir)
	if task.Err != nil {
		return
	}
	task.SetSqlfileDir(cmdFilesDir)
	task.Logger.Info("create dump sqldir ok", zap.String("sqlDir", cmdFilesDir))

	outputFormat := task.TredisdumpOuputFormat()
	outputFileSize := task.TredisdumpOuputFileSize()
	threadCnt := task.TredisdumpThreadCnt()

	task.SetMessage("开始执行")
	dumperLogFile := filepath.Join(task.TaskDir, fmt.Sprintf("tredisdump_%s_%d.log", task.RowData.SrcIP,
		task.RowData.SrcPort))

	var keyWhiteRegex string = ""
	var keyBlackRegex string = ""
	if task.RowData.KeyWhiteRegex != "" && !task.IsMatchAny(task.RowData.KeyWhiteRegex) {
		keyWhiteRegex = fmt.Sprintf(" --key_white_regex %q ", task.RowData.KeyWhiteRegex)
	}
	if task.RowData.KeyBlackRegex != "" && !task.IsMatchAny(task.RowData.KeyBlackRegex) {
		keyBlackRegex = fmt.Sprintf(" --key_black_regex %q ", task.RowData.KeyBlackRegex)
	}

	dumperCmd := fmt.Sprintf(
		`export LD_LIBRARY_PATH=LD_LIBRARY_PATH:%s && cd %s && %s --db_path %s/private/1  --sst_path  %s/shared  --file_size %d --output_format %s --threads %d %s %s`,
		depsDir, cmdFilesDir, dumperClient, task.RowData.FetchFile,
		task.RowData.FetchFile, outputFileSize, outputFormat, threadCnt,
		keyWhiteRegex, keyBlackRegex)

	if task.RowData.SrcSegStart >= 0 &&
		task.RowData.SrcSegEnd <= 419999 &&
		task.RowData.SrcSegStart < task.RowData.SrcSegEnd {
		if task.RowData.SrcSegStart < 0 || task.RowData.SrcSegEnd < 0 {
			task.Err = fmt.Errorf("srcTendis:%s#%d segStart:%d<0 or segEnd:%d<0",
				task.RowData.SrcIP, task.RowData.SrcPort, task.RowData.SrcSegStart, task.RowData.SrcSegEnd)
			task.Logger.Error(err.Error())
			return
		}
		if task.RowData.SrcSegStart >= task.RowData.SrcSegEnd {
			task.Err = fmt.Errorf("srcTendis:%s#%d segStart:%d >= segEnd:%d",
				task.RowData.SrcIP, task.RowData.SrcPort, task.RowData.SrcSegStart, task.RowData.SrcSegEnd)
			task.Logger.Error(err.Error())
			return
		}
		dumperCmd = fmt.Sprintf("%s --start_segment %d --end_segment %d",
			dumperCmd, task.RowData.SrcSegStart, task.RowData.SrcSegEnd)
	}

	dumperCmd = fmt.Sprintf("%s >%s 2>&1", dumperCmd, dumperLogFile)

	task.UpdateDbAndLogLocal("开始解析全备,Command:%s", dumperCmd)

	timeout := viper.GetInt("tredisdumperTimeout")
	if timeout == 0 {
		timeout = 604800
	}
	_, err = util.RunLocalCmd("bash", []string{"-c", dumperCmd}, "", task, time.Duration(timeout)*time.Second, task.Logger)
	if task.RowData.SyncOperate == constvar.RedisForceKillTaskSuccess {
		task.ClearLocalFetchBackup()
		task.ClearLocalSQLDir()
		task.RestoreSrcSSDKeepCount()
		return
	}
	if err != nil && strings.Contains(err.Error(), "exit status 255") {
		// 如果tredisdump 出现 exit status 255 错误,则该任务从头再来一次
		task.SetTaskType(constvar.TendisBackupTaskType)
		task.SetTendisbackupFile("")
		task.SetFetchFile("")
		task.SetStatus(0)
		task.UpdateDbAndLogLocal("备份文件不对,tredisdump解析失败,重新发起任务...")
		return
	} else if err != nil {
		task.Err = err
		return
	}
	// grep 语句的错误结果直接忽略,因为grep 如果结果为空,则exit 1
	grepRet, _ := util.RunLocalCmd("bash",
		[]string{"-c", "grep -i -w -E 'err|error' " + dumperLogFile + "||true"}, "",
		nil, 60*time.Second, task.Logger)
	if grepRet != "" {
		task.Err = fmt.Errorf("tredisdump some error occur,pls check logfile:%s", dumperLogFile)
		task.Logger.Error(task.Err.Error())
		return
	}
	grepRet, _ = util.RunLocalCmd("bash",
		[]string{"-c", "grep -i -w 'fail' " + dumperLogFile + "||true"}, "",
		nil, 1*time.Hour, task.Logger)
	if grepRet != "" {
		task.Err = fmt.Errorf("tredisdump some error occur,pls check logfile:%s", dumperLogFile)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.Logger.Info("tredisdump 执行成功")

	// confirm binlog seq is OK in src redis
	fullBackupSyncSeq := task.GetSyncSeqFromFullBackup()
	if task.Err != nil {
		return
	}
	task.ConfirmSrcRedisBinlogOK(fullBackupSyncSeq.Seq - 1)
	if task.Err != nil {
		return
	}

	task.EndClear()
	if task.Err != nil {
		return
	}

	task.SetTaskType(task.NextTask())
	task.SetStatus(0)
	task.UpdateDbAndLogLocal("等待执行数据导入")

	return
}

// EndClear tredisdump完成后清理本地tendisSSD备份文件
func (task *TredisdumpTask) EndClear() {
	if task.RowData.FetchFile == "" {
		return
	}
	if strings.Contains(task.RowData.FetchFile, "REDIS_FULL_rocksdb_") == false {
		return
	}

	debug := viper.GetBool("TENDIS_DEBUG")
	if debug == true {
		return
	}

	// 备份文件tredisdump解析完后, 备份:REDIS_FULL_rocksdb_ 目录可删除
	task.ClearLocalFetchBackup()
}
