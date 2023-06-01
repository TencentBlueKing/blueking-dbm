package atomredis

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// TendisssdDrRestoreParams tendisSSD建立dr关系参数
type TendisssdDrRestoreParams struct {
	// 备份信息
	BackupTasks []BackupTask `json:"backup_tasks"  validate:"required"`
	// master信息
	MasterIP        string `json:"master_ip" validate:"required"`
	MasterStartPort int    `json:"master_start_port"`
	MasterInstNum   int    `json:"master_inst_num"`
	MasterPorts     []int  `json:"master_ports"`
	MasterAuth      string `json:"master_auth" validate:"required"`
	// slave信息
	SlaveIP        string `json:"slave_ip" validate:"required"`
	SlaveStartPort int    `json:"slave_start_port"`
	SlaveInstNum   int    `json:"slave_inst_num"`
	SlavePorts     []int  `json:"slave_ports"`
	SlavePassword  string `json:"slave_password" validate:"required"`
	// 全备所在目录
	BackupDir string `json:"backup_dir"`
}

// TendisssdDrRestore tendisssd dr restore atomjob
type TendisssdDrRestore struct {
	runtime *jobruntime.JobGenericRuntime
	params  TendisssdDrRestoreParams
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*TendisssdDrRestore)(nil)

// NewTendisssdDrRestore new
func NewTendisssdDrRestore() jobruntime.JobRunner {
	return &TendisssdDrRestore{}
}

// Init 初始化
func (job *TendisssdDrRestore) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("TendisssdDrRestore Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("TendisssdDrRestore Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	// MasterPorts 和 MasterInstNum 不能同时为空
	if len(job.params.MasterPorts) == 0 && job.params.MasterInstNum == 0 {
		err = fmt.Errorf("TendisssdDrRestore MasterPorts(%+v) and MasterInstNum(%d) is invalid", job.params.MasterPorts,
			job.params.MasterInstNum)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	if job.params.MasterInstNum > 0 {
		ports := make([]int, 0, job.params.MasterInstNum)
		for idx := 0; idx < job.params.MasterInstNum; idx++ {
			ports = append(ports, job.params.MasterStartPort+idx)
		}
		job.params.MasterPorts = ports
	} else {
		// 保持元素顺序,做一些去重
		job.params.MasterPorts = common.UniqueSlice(job.params.MasterPorts)
	}
	// SlavePorts 和 SlaveInstNum 不能同时为空
	if len(job.params.SlavePorts) == 0 && job.params.SlaveInstNum == 0 {
		err = fmt.Errorf("TendisssdDrRestore SlavePorts(%+v) and SlaveInstNum(%d) is invalid", job.params.SlavePorts,
			job.params.SlaveInstNum)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	if job.params.SlaveInstNum > 0 {
		ports := make([]int, 0, job.params.SlaveInstNum)
		for idx := 0; idx < job.params.SlaveInstNum; idx++ {
			ports = append(ports, job.params.SlaveStartPort+idx)
		}
		job.params.SlavePorts = ports
	} else {
		// 保持元素顺序,做一些去重
		job.params.SlavePorts = common.UniqueSlice(job.params.SlavePorts)
	}
	return nil
}

// Name 原子任务名
func (job *TendisssdDrRestore) Name() string {
	return "tendisssd_dr_restore"
}

// Run 执行
func (job *TendisssdDrRestore) Run() error {
	var err error
	backupMap := make(map[string]BackupTask, len(job.params.BackupTasks))
	for _, task01 := range job.params.BackupTasks {
		backupMap[task01.Addr()] = task01
	}
	restoreTasks := make([]*TendisssdDrRestoreTask, 0, len(job.params.SlavePorts))
	for idx, slavePort := range job.params.SlavePorts {
		masterAddr := job.params.MasterIP + ":" + strconv.Itoa(job.params.MasterPorts[idx])
		backTask, ok := backupMap[masterAddr]
		if !ok {
			err = fmt.Errorf("master(%s) not found backupFile in backup_tasks[%+v]", masterAddr, job.params.BackupTasks)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		restoreItem := NewSSDDrRestoreTask(backTask,
			job.params.MasterIP, job.params.MasterPorts[idx], job.params.MasterAuth,
			job.params.SlaveIP, slavePort, job.params.SlavePassword,
			job.params.BackupDir, job.runtime)
		restoreTasks = append(restoreTasks, restoreItem)
	}
	util.StopBkDbmon()
	defer util.StartBkDbmon()

	wg := sync.WaitGroup{}
	genChan := make(chan *TendisssdDrRestoreTask)
	limit := 3 // 并发度3
	for worker := 0; worker < limit; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for taskItem := range genChan {
				taskItem.Run()
			}
		}()
	}
	go func() {
		// 关闭genChan,以便让所有goroutine退出
		defer close(genChan)
		for _, task := range restoreTasks {
			restoreItem := task
			genChan <- restoreItem
		}
	}()
	wg.Wait()
	for _, task := range restoreTasks {
		restoreItem := task
		if restoreItem.Err != nil {
			return restoreItem.Err
		}
	}
	return nil
}

// Retry times
func (job *TendisssdDrRestore) Retry() uint {
	return 2
}

// Rollback rollback
func (job *TendisssdDrRestore) Rollback() error {
	return nil
}

// TendisssdDrRestoreTask tendis-ssd dr恢复task
type TendisssdDrRestoreTask struct {
	ReplicaItem
	BakTask            BackupTask           `json:"bak_task"`
	TaskDir            string               `json:"task_dir"`
	MasterCli          *myredis.RedisClient `json:"-"`
	SlaveCli           *myredis.RedisClient `json:"-"`
	MasterVersion      string               `json:"master_version"`
	DbType             string               `json:"db_type"`
	RestoreTool        string               `json:"restore_tool"`
	DepsDir            string               `json:"deps_dir"`
	LocalFullBackupDir string               `json:"local_full_backup_dir"`
	SlaveDataDir       string               `json:"slave_data_dir"`
	runtime            *jobruntime.JobGenericRuntime
	Err                error `json:"-"`
}

// NewSSDDrRestoreTask new tendis-ssd dr restore task
func NewSSDDrRestoreTask(bakTask BackupTask,
	masterIP string, masterPort int, masterAuth string,
	slaveIP string, slavePort int, slavePassword, taskDir string,
	runtime *jobruntime.JobGenericRuntime) *TendisssdDrRestoreTask {
	return &TendisssdDrRestoreTask{
		ReplicaItem: ReplicaItem{
			MasterIP:      masterIP,
			MasterPort:    masterPort,
			MasterAuth:    masterAuth,
			SlaveIP:       slaveIP,
			SlavePort:     slavePort,
			SlavePassword: slavePassword,
		},
		BakTask: bakTask,
		TaskDir: taskDir,
		DepsDir: "/usr/local/redis/bin/deps",
		runtime: runtime,
	}
}

// Run 执行恢复任务
func (task *TendisssdDrRestoreTask) Run() {
	var ok bool
	var masterType, slaveType string
	task.newConnect()
	if task.Err != nil {
		return
	}
	// master 和 slave都必须是 tendisSSD类型
	masterType, task.Err = task.MasterCli.GetTendisType()
	if task.Err != nil {
		return
	}
	slaveType, task.Err = task.MasterCli.GetTendisType()
	if task.Err != nil {
		return
	}
	if masterType != consts.TendisTypeTendisSSDInsance ||
		slaveType != consts.TendisTypeTendisSSDInsance {
		task.Err = fmt.Errorf("master(%s) dbType:%s,slave(%s) dbType:%s,dbType must be %s",
			task.MasterAddr(), masterType, task.SlaveAddr(), slaveType, consts.TendisTypeTendisSSDInsance)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}

	ok, _ = task.SlaveCli.IsTendisSSDReplicaStatusOk(task.MasterIP, strconv.Itoa(task.MasterPort))
	if ok {
		// 如果主从关系已经ok,则避免重复执行
		task.runtime.Logger.Info("tendisSSD slave(%s) master(%s) link_status:up", task.SlaveAddr(), task.MasterAddr())
		return
	}

	task.Precheck()
	if task.Err != nil {
		return
	}

	defer task.Clean()

	task.UnTarFullBackup()
	if task.Err != nil {
		return
	}
	task.RestoreLocalSlave()
	if task.Err != nil {
		return
	}
	task.TendisSSDSetLougCount()
}
func (task *TendisssdDrRestoreTask) newConnect() {
	task.runtime.Logger.Info("start connect master(%s)", task.MasterAddr())
	task.MasterCli, task.Err = myredis.NewRedisClient(task.MasterAddr(), task.MasterAuth, 0,
		consts.TendisTypeRedisInstance)
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("start connect slave(%s)", task.SlaveAddr())
	task.SlaveCli, task.Err = myredis.NewRedisClient(task.SlaveAddr(), task.SlavePassword, 0,
		consts.TendisTypeRedisInstance)
	if task.Err != nil {
		return
	}
	var infoRet map[string]string
	infoRet, task.Err = task.MasterCli.Info("server")
	if task.Err != nil {
		return
	}
	task.MasterVersion = infoRet["redis_version"]
	task.DbType, task.Err = task.MasterCli.GetTendisType()
	if task.Err != nil {
		return
	}
	if !consts.IsTendisSSDInstanceDbType(task.DbType) {
		task.Err = fmt.Errorf("redisMaster(%s) dbtype:%s not a tendis-ssd instance", task.MasterAddr(), task.DbType)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	task.SlaveDataDir, task.Err = task.SlaveCli.GetDir()
	if task.Err != nil {
		return
	}
}
func (task *TendisssdDrRestoreTask) getRestoreTool() {
	if strings.Contains(task.MasterVersion, "v1.2.") {
		task.RestoreTool = "/usr/local/redis/bin/rr_restore_backup"
	} else if strings.Contains(task.MasterVersion, "v1.3.") {
		task.RestoreTool = "/usr/local/redis/bin/tredisrestore"
	} else {
		task.Err = fmt.Errorf("redisMaster(%s) version:%s cannot find restore-tool", task.MasterAddr(), task.MasterVersion)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	if !util.FileExists(task.RestoreTool) {
		task.Err = fmt.Errorf("redis(%s) restore_tool:%s not exists", task.SlaveIP, task.RestoreTool)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
}

func (task *TendisssdDrRestoreTask) isSlaveInUsing() {
	var tmpKey string
	tmpKey, task.Err = task.SlaveCli.Randomkey()
	if task.Err != nil {
		return
	}
	if tmpKey != "" {
		task.Err = fmt.Errorf("redis(%s) RandomKey result=>%s, instance is using? cannot shutdown", task.SlaveAddr(), tmpKey)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
}

// Precheck 前置检查
func (task *TendisssdDrRestoreTask) Precheck() {
	if !util.FileExists(task.DepsDir) {
		task.Err = fmt.Errorf("redis(%s) deps:%s not exists", task.SlaveIP, task.DepsDir)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	if !util.FileExists("/usr/local/redis") {
		task.Err = fmt.Errorf("redis(%s) /usr/local/redis not exists", task.SlaveIP)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	task.isSlaveInUsing()
	if task.Err != nil {
		return
	}
	task.getRestoreTool()
	if task.Err != nil {
		return
	}
	return
}

// UnTarFullBackup 解压全备并检查
func (task *TendisssdDrRestoreTask) UnTarFullBackup() {
	if len(task.BakTask.BackupFiles) != 1 {
		task.Err = fmt.Errorf("master(%s) has %d backupFiles?? [%+v]", task.MasterAddr(), len(task.BakTask.BackupFiles),
			task.BakTask.BackupFiles)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	var localTarFile string
	var ret string
	localTarFile, task.Err = util.UnionSplitFiles(task.TaskDir, task.BakTask.BackupFiles)
	if task.Err != nil {
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	task.LocalFullBackupDir = strings.TrimSuffix(localTarFile, ".tar")
	if !util.FileExists(task.LocalFullBackupDir) {
		unTarCmd := fmt.Sprintf("tar -xf %s -C %s", localTarFile, task.TaskDir)
		task.runtime.Logger.Info(unTarCmd)
		_, task.Err = util.RunBashCmd(unTarCmd, "", nil, 24*time.Hour)
		if task.Err != nil {
			return
		}
	}
	util.LocalDirChownMysql(task.LocalFullBackupDir)
	versionFile := filepath.Join(task.LocalFullBackupDir, "meta/2")
	if util.FileExists(versionFile) {
		task.Err = fmt.Errorf("error: backup version bigger than 1, please check the backup,exit. file exists[%s]",
			versionFile)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	duCmd := fmt.Sprintf("du -s %s|awk '{print $1}'", task.LocalFullBackupDir)
	ret, task.Err = util.RunBashCmd(duCmd, "", nil, 1*time.Hour)
	if task.Err != nil {
		return
	}
	backupSize, _ := strconv.ParseUint(ret, 10, 64)
	if backupSize < 10000 {
		task.runtime.Logger.Info(fmt.Sprintf("master(%s) backupDir:%s dataSize:%d bytes, too small ?", task.MasterAddr(),
			task.LocalFullBackupDir, backupSize))
	} else {
		task.runtime.Logger.Info(fmt.Sprintf("master(%s) backupDir:%s dataSize:%dM", task.MasterAddr(),
			task.LocalFullBackupDir, backupSize/1024))
	}
	util.LocalDirChownMysql(task.LocalFullBackupDir)
	task.runtime.Logger.Info("UnTarFullBakcup success")
}

// Clean 最后清理
func (task *TendisssdDrRestoreTask) Clean() {
	if task.SlaveCli != nil {
		task.SlaveCli.Close()
		task.SlaveCli = nil
	}
	if task.MasterCli != nil {
		task.MasterCli.Close()
		task.MasterCli = nil
	}
	if task.LocalFullBackupDir == "" {
		return
	}
	if task.Err != nil {
		return
	}
	localTarFile := task.LocalFullBackupDir + ".tar"
	tarDir := filepath.Dir(localTarFile)
	if strings.Contains(localTarFile, task.MasterIP) && util.FileExists(localTarFile) {
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s", tarDir, filepath.Base(localTarFile))
		util.RunBashCmd(rmCmd, "", nil, 1*time.Hour)
		task.runtime.Logger.Info(rmCmd)
	}
	if strings.Contains(task.LocalFullBackupDir, task.MasterIP) && util.FileExists(task.LocalFullBackupDir) {
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s", tarDir, filepath.Base(task.LocalFullBackupDir))
		util.RunBashCmd(rmCmd, "", nil, 1*time.Hour)
		task.runtime.Logger.Info(rmCmd)
	}
}

// RestoreLocalSlave 恢复本地slave
// 1. 关闭slave 并 mv 本地rocksdb目录
// 2. 利用备份恢复数据,拉起slave;
func (task *TendisssdDrRestoreTask) RestoreLocalSlave() {
	task.Err = task.SlaveCli.Shutdown()
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("slave(%s) shutdown success", task.SlaveAddr())

	nowtime := time.Now().Local().Format(consts.FilenameTimeLayout)
	rockdbDir := filepath.Join(task.SlaveDataDir, "rocksdb")
	bakDir := filepath.Join(task.SlaveDataDir, "backup_rocksdb."+nowtime)
	var ret, slaveConfFile, msg string
	var infoRet map[string]string
	var slaveBinlogRange, masterBinlogRange myredis.TendisSSDBinlogSize

	mvCmd := fmt.Sprintf("mv %s %s", rockdbDir, bakDir)
	task.runtime.Logger.Info(mvCmd)
	util.RunBashCmd(mvCmd, "", nil, 2*time.Hour)
	util.LocalDirChownMysql(bakDir)

	var extraOpt string
	if strings.Contains(task.MasterVersion, "v1.2") {
		extraOpt = " 1"
	} else if strings.Contains(task.MasterVersion, "v1.3") {
		extraOpt = ""
	} else {
		task.Err = fmt.Errorf("unsupported tendis version:%s,exit.", task.MasterVersion)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	restoreCmd := fmt.Sprintf(`
export LD_PRELOAD=%s/libjemalloc.so
export LD_LIBRARY_PATH=LD_LIBRARY_PATH:%s
%s %s %s %s
`, task.DepsDir, task.DepsDir, task.RestoreTool, task.LocalFullBackupDir, rockdbDir, extraOpt)
	task.runtime.Logger.Info(restoreCmd)
	ret, task.Err = util.RunBashCmd(restoreCmd, "", nil, 6*time.Hour)
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("restore command result:" + ret)
	if util.FileExists(rockdbDir) {
		task.runtime.Logger.Info("restore ok, %s generated", rockdbDir)
	} else {
		task.Err = fmt.Errorf("restore command failed, %s not generated", rockdbDir)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	util.LocalDirChownMysql(rockdbDir)
	slaveConfFile, task.Err = myredis.GetRedisLoccalConfFile(task.SlavePort)
	if task.Err != nil {
		return
	}
	// 先注释掉slaveof命令,拉起后不要立刻同步master
	sedCmd := fmt.Sprintf("sed -i -e 's/^slaveof/#slaveof/g' %s", slaveConfFile)
	task.runtime.Logger.Info(sedCmd)
	util.RunBashCmd(sedCmd, "", nil, 1*time.Minute)

	startScript := filepath.Join("/usr/local/redis/bin", "start-redis.sh")
	_, task.Err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(
		task.SlavePort)}, "", nil, 10*time.Second)
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\"", consts.MysqlAaccount,
		startScript+"  "+strconv.Itoa(task.SlavePort)))
	time.Sleep(2 * time.Second)

	task.SlaveCli, task.Err = myredis.NewRedisClient(task.SlaveAddr(), task.SlavePassword, 0,
		consts.TendisTypeRedisInstance)
	if task.Err != nil {
		return
	}

	// 一些必要设置
	_, task.Err = task.SlaveCli.ConfigSet("masterauth", task.MasterAuth)
	if task.Err != nil {
		return
	}
	_, task.Err = task.SlaveCli.ConfigSet("is-master-snapshot", "1")
	if task.Err != nil {
		return
	}
	infoRet, task.Err = task.MasterCli.Info("server")
	if task.Err != nil {
		return
	}
	masterRunID := infoRet["run_id"]
	task.runtime.Logger.Info("slave(%s) confxx set server-runid %s", task.SlaveAddr(), masterRunID)
	_, task.Err = task.SlaveCli.ConfigSet("server-runid", masterRunID)
	if task.Err != nil {
		return
	}

	// 检查binlog范围ok
	slaveBinlogRange, task.Err = task.SlaveCli.TendisSSDBinlogSize()
	if task.Err != nil {
		return
	}
	masterBinlogRange, task.Err = task.MasterCli.TendisSSDBinlogSize()
	if task.Err != nil {
		return
	}
	if slaveBinlogRange.FirstSeq < masterBinlogRange.FirstSeq {
		task.Err = fmt.Errorf("slave(%s) binlog_first_seq:%d < master(%s) binlog_first_seq:%d",
			task.SlaveAddr(), slaveBinlogRange.FirstSeq, task.MasterAddr(), masterBinlogRange.FirstSeq)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	if slaveBinlogRange.EndSeq > masterBinlogRange.EndSeq {
		task.Err = fmt.Errorf("slave(%s) binlog_end_seq:%d > master(%s) binlog_end_seq:%d",
			task.SlaveAddr(), slaveBinlogRange.EndSeq, task.MasterAddr(), masterBinlogRange.EndSeq)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	msg = fmt.Sprintf("master(%s) binlog_range:%s,slave(%s) binlog_range:%s,is ok",
		task.MasterAddr(), masterBinlogRange.String(), task.SlaveAddr(), slaveBinlogRange.String())
	task.runtime.Logger.Info(msg)

	// slaveof
	_, task.Err = task.SlaveCli.SlaveOf(task.MasterIP, strconv.Itoa(task.MasterPort))
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("slave(%s) 'slaveof %s %d'", task.SlaveAddr(), task.MasterIP, task.MasterPort)

	// slave 'confxx set disk-delete-count 50'
	_, task.Err = task.SlaveCli.ConfigSet("disk-delete-count", "50")
	if task.Err != nil {
		return
	}

	// 最多等待10分钟
	maxRetryTimes := 120
	var i int = 0
	for {
		i++
		if i >= maxRetryTimes {
			break
		}
		task.Err = nil
		_, task.Err = task.SlaveCli.IsTendisSSDReplicaStatusOk(task.MasterIP, strconv.Itoa(task.MasterPort))
		if task.Err != nil {
			task.runtime.Logger.Info(task.Err.Error() + ",sleep 5 seconds and retry...")
			time.Sleep(5 * time.Second)
			continue
		}
		break
	}
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("tendisSSD slave(%s) master(%s) create replicate link success", task.SlaveAddr(),
		task.MasterAddr())
}

// TendisSSDSetLougCount tendisSSD恢复log-count参数
func (task *TendisssdDrRestoreTask) TendisSSDSetLougCount() {
	task.MasterCli.ConfigSet("log-count", "200000")
	task.MasterCli.ConfigSet("slave-log-keep-count", "0")
}
