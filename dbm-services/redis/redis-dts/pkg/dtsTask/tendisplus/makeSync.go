package tendisplus

import (
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/redis-dts/models/myredis"
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask"
	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"

	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// MakeSyncTask 启动redis-sync
type MakeSyncTask struct {
	dtsTask.FatherTask
	RedisCliTool   string `json:"redisCliTool"`
	RedisSyncTool  string `json:"redisSyncTool"`
	SyncLogFile    string `json:"syncLogFile"`
	SyncConfigFile string `json:"syncConfigFile"`
	SyncDir        string `json:"syncDir"`
}

// TaskType task 类型
func (task *MakeSyncTask) TaskType() string {
	return constvar.TendisplusMakeSyncTaskType
}

// NextTask 下一个task类型
func (task *MakeSyncTask) NextTask() string {
	return constvar.TendisplusSendBulkTaskType
}

// NewMakeSyncTask 新建一个 redis-sync启动task
func NewMakeSyncTask(row *tendisdb.TbTendisDTSTask) *MakeSyncTask {
	return &MakeSyncTask{
		FatherTask: dtsTask.NewFatherTask(row),
	}
}

// PreClear 关闭以前生成的redis-sync
func (task *MakeSyncTask) PreClear() {
	if task.Err != nil {
		return
	}
	if task.RowData.SyncerPort == 0 {
		return
	}
	defer func() {
		// clear old sync config file and log file
		task.MkSyncDirIfNotExists()
		if task.Err != nil {
			return
		}
		rmCmd := fmt.Sprintf("cd %s && rm -rf *-taskid%d-*.log *-taskid%d-*.conf", task.SyncDir, task.RowData.ID,
			task.RowData.ID)
		task.Logger.Info(fmt.Sprintf("tendisplus makeSync preClear execute:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 10*time.Second, task.Logger)

	}()

	task.RedisSyncStop()
	return
}

// Execute 执行启动redis-sync
func (task *MakeSyncTask) Execute() {
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
	task.UpdateDbAndLogLocal("开始创建sync关系")

	task.GetMyRedisCliTool()
	if task.Err != nil {
		return
	}
	task.GetMyRedisSyncTool()
	if task.Err != nil {
		return
	}

	isSyncOk := task.IsSyncStateOK()
	if isSyncOk {
		// 同步状态本来就是ok的,直接watcht redis-sync即可
		task.Logger.Info(fmt.Sprintf("redis:%s 同步状态ok,开始watch...", task.GetSrcRedisAddr()))
		task.SetTaskType(task.NextTask())
		task.SetStatus(1)
		task.UpdateRow()
		task.WatchSync()
		return
	}
	task.PreClear()
	if task.Err != nil {
		return
	}
	task.isRedisConnectOK()
	if task.Err != nil {
		return
	}

	task.TendisplusMasterSlaveConfigSet()
	if task.Err != nil {
		return
	}
	task.RedisSyncStart(true)
	if task.Err != nil {
		return
	}
	task.UpdateDbAndLogLocal("tendis redis-sync 拉起ok,srcRedisAddr:%s,taskid:%d", task.GetSrcRedisAddr(), task.RowData.ID)

	task.WatchSync()
	return
}

// MkSyncDirIfNotExists create sync directory if not exists
func (task *MakeSyncTask) MkSyncDirIfNotExists() {
	task.Err = task.InitTaskDir()
	if task.Err != nil {
		return
	}
	task.SyncDir = task.TaskDir
	return
}

// GetMyRedisSyncTool 本地获取redis-sync
func (task *MakeSyncTask) GetMyRedisSyncTool() {
	task.RedisSyncTool, task.Err = util.IsToolExecutableInCurrDir("redis-sync")
	return
}

// GetMyRedisCliTool 本地获取redis-cli
func (task *MakeSyncTask) GetMyRedisCliTool() {
	task.RedisCliTool, task.Err = util.IsToolExecutableInCurrDir("redis-cli")
	return
}

func (task *MakeSyncTask) getSlaveConn() (slaveConn *myredis.RedisWorker) {
	slaveConn, task.Err = myredis.NewRedisClient(task.GetSrcRedisAddr(), task.GetSrcRedisPasswd(), 0, task.Logger)
	if task.Err != nil {
		return
	}
	return
}

func (task *MakeSyncTask) getMasterConn() (masterConn *myredis.RedisWorker) {
	var masterAddr, masterAuth string
	slaveConn := task.getSlaveConn()
	if task.Err != nil {
		return
	}
	defer slaveConn.Close()
	masterAddr, masterAuth, task.Err = slaveConn.GetMasterAddrAndPasswd()
	masterConn, task.Err = myredis.NewRedisClient(masterAddr, masterAuth, 0, task.Logger)
	return
}

func (task *MakeSyncTask) isRedisConnectOK() {
	task.GetSrcRedisPasswd()
	if task.Err != nil {
		return
	}
	slaveConn := task.getSlaveConn()
	if task.Err != nil {
		return
	}
	defer slaveConn.Close()

	masterConn := task.getMasterConn()
	if task.Err != nil {
		return
	}
	defer masterConn.Close()
}

// TendisplusMasterSlaveConfigSet 'config set'修改必要配置
// redis-sync will connect to tendisplus slave or master when migrating data
// 1. tendisplus master/slave aof-enabled=yes
// 2. tendisplus slave fullpsync-notice-enabled=yes
// 3. tendisplus slave fullpushthreadnum=10
// 4. tendisplus master/slave incrpushthreadnum >=10
// 5. tendisplus slave supply-fullpsync-key-batch-num=50
func (task *MakeSyncTask) TendisplusMasterSlaveConfigSet() {
	var ok bool
	// slaveConn 和 masterConn 可能指向同一个tendisplus实例
	slaveConn := task.getSlaveConn()
	if task.Err != nil {
		return
	}
	defer slaveConn.Close()
	masterConn := task.getMasterConn()
	if task.Err != nil {
		return
	}
	defer masterConn.Close()

	_, task.Err = slaveConn.ConfigSet("aof-enabled", "yes")
	if task.Err != nil {
		return
	}
	_, task.Err = masterConn.ConfigSet("aof-enabled", "yes")
	if task.Err != nil {
		return
	}
	task.Logger.Info(fmt.Sprintf("tendisplus master:%s config set 'aof-enabled' 'yes' success", masterConn.Addr))
	task.Logger.Info(fmt.Sprintf("tendisplus slave:%s config set 'aof-enabled' 'yes' success", masterConn.Addr))

	slaveConn.ConfigSet("fullpsync-notice-enabled", "yes")

	var slaveFullThreadNum int
	var masterIncrThreadNum int
	var slaveIncrThreadNum int
	var tmpMap map[string]string
	var tmpVal string
	// slave fullpushthreadnum
	tmpMap, task.Err = slaveConn.ConfigGet("fullpushthreadnum")
	if task.Err != nil {
		return
	}
	tmpVal, ok = tmpMap["fullpushthreadnum"]
	if ok == false {
		task.Err = fmt.Errorf("tendisplus slave:%s config get 'fullpushthreadnum' fail,empty val", slaveConn.Addr)
		return
	}
	slaveFullThreadNum, _ = strconv.Atoi(tmpVal)
	if slaveFullThreadNum < 10 {
		slaveConn.ConfigSet("fullpushthreadnum", "10")
	}
	// slave incrpushthreadnum
	tmpMap, _ = slaveConn.ConfigGet("incrpushthreadnum")
	tmpVal, ok = tmpMap["incrpushthreadnum"]
	if ok == false {
		task.Err = fmt.Errorf("tendisplus slave:%s config get 'incrpushthreadnum' fail,empty val", slaveConn.Addr)
		return
	}
	slaveIncrThreadNum, _ = strconv.Atoi(tmpVal)
	if slaveIncrThreadNum < 10 {
		slaveConn.ConfigSet("incrpushthreadnum", "10")
	}
	fullsyncBatchNum := viper.GetInt("tendisplus-full-sync-batchNum")
	if fullsyncBatchNum == 0 {
		fullsyncBatchNum = 50
	} else if fullsyncBatchNum < 10 {
		fullsyncBatchNum = 10
	} else if fullsyncBatchNum > 500 {
		fullsyncBatchNum = 500
	}
	slaveConn.ConfigSet("supply-fullpsync-key-batch-num", strconv.Itoa(fullsyncBatchNum))

	// master incrpushthreadnum
	tmpMap, _ = masterConn.ConfigGet("incrpushthreadnum")
	tmpVal, ok = tmpMap["incrpushthreadnum"]
	if ok == false {
		task.Err = fmt.Errorf("tendisplus master:%s config get 'incrpushthreadnum' fail,empty val", masterConn.Addr)
		return
	}
	masterIncrThreadNum, _ = strconv.Atoi(tmpVal)
	if masterIncrThreadNum < 10 {
		masterConn.ConfigSet("incrpushthreadnum", "10")
	}
}

// getMySyncPort 获取redis-sync port, 40000<=port<50000
func (task *MakeSyncTask) getMySyncPort(initSyncPort int) {
	taskTypes := []string{}
	var syncerPort int
	taskTypes = append(taskTypes, constvar.MakeSyncTaskType)
	if initSyncPort <= 0 {
		initSyncPort = 40000
		dtsSvrMaxSyncPortTask, err := tendisdb.GetDtsSvrMaxSyncPort(task.RowData.BkCloudID, task.RowData.DtsServer,
			constvar.TendisTypeTendisplusInsance, taskTypes, task.Logger)
		if (err != nil && gorm.IsRecordNotFoundError(err)) || dtsSvrMaxSyncPortTask == nil {
			initSyncPort = 40000
		} else if err != nil {
			task.Err = err
			return
		} else {
			if dtsSvrMaxSyncPortTask.SyncerPort >= 40000 {
				initSyncPort = dtsSvrMaxSyncPortTask.SyncerPort + 1
			}
		}
	}
	if initSyncPort > 50000 {
		initSyncPort = 40000
	}
	syncerPort, task.Err = util.GetANotUsePort("127.0.0.1", initSyncPort, 1)
	if task.Err != nil {
		task.Logger.Error(task.Err.Error())
		return
	}
	task.SetSyncerPort(syncerPort)

	return
}

func (task *MakeSyncTask) createSyncLogFile() {
	task.MkSyncDirIfNotExists()
	if task.Err != nil {
		return
	}
	task.SyncLogFile = filepath.Join(task.SyncDir,
		fmt.Sprintf("log-%s-%d-kvstore-%d-%d.log", task.RowData.SrcIP, task.RowData.SrcPort,
			task.RowData.SrcKvStoreID, task.RowData.SyncerPort))
	return
}

func (task *MakeSyncTask) clearOldSyncLogFile() {
	task.SyncLogFile = strings.TrimSpace(task.SyncLogFile)
	if task.SyncLogFile == "" {
		return
	}
	_, err := os.Stat(task.SyncLogFile)
	if err == nil {
		// rm old sync log file
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s",
			filepath.Dir(task.SyncLogFile), filepath.Base(task.SyncLogFile))
		task.Logger.Info(rmCmd)
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 20*time.Second, task.Logger)
	}
}

// IsKeysExistsRewrite 当目的端key存在时,是否覆盖写(如 del+hset)
func (task *MakeSyncTask) IsKeysExistsRewrite() bool {
	if task.RowData.WriteMode == constvar.WriteModeDeleteAndWriteToRedis {
		// 用户选择的就是 del + hset
		return true
	}
	if task.RowData.WriteMode == constvar.WriteModeFlushallAndWriteToRedis &&
		task.RowData.RetryTimes > 0 {
		// 用户选择 flushall + hset,第一次无需执行del,重试迁移时,先执行del
		return true
	}

	return false
}
func (task *MakeSyncTask) createSyncConfigFile() {
	task.MkSyncDirIfNotExists()
	if task.Err != nil {
		return
	}
	// 必须是 kvstore-%d-,最后的-很重要,因为可能出现 kvstore-1-、kvstore-10-
	task.SyncConfigFile = filepath.Join(task.SyncDir,
		fmt.Sprintf("sync-taskid%d-%d-kvstore-%d-.conf",
			task.RowData.ID, task.RowData.SyncerPort, task.RowData.SrcKvStoreID))

	_, err := os.Stat(task.SyncConfigFile)
	if err == nil {
		// if config file exists,return
		task.Logger.Info(fmt.Sprintf("redis-sync config file:%s already exists", task.SyncConfigFile))
		return
	}
	sampleFile, err := util.IsFileExistsInCurrDir("tendisplus-sync-template.conf")
	if err != nil {
		task.Err = err
		task.Logger.Error(task.Err.Error())
		return
	}
	sampleBytes, err := ioutil.ReadFile(sampleFile)
	if err != nil {
		task.Err = fmt.Errorf("read tendisplus redis-sync template file(%s) fail,err:%v", sampleFile, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	var keyWhiteRegex string = ""
	var keyBlackRegex string = ""
	if task.RowData.KeyWhiteRegex != "" && !task.IsMatchAny(task.RowData.KeyWhiteRegex) {
		keyWhiteRegex = task.RowData.KeyWhiteRegex
	}
	if task.RowData.KeyBlackRegex != "" && !task.IsMatchAny(task.RowData.KeyBlackRegex) {
		keyBlackRegex = task.RowData.KeyBlackRegex
	}
	var fullsyncDelKeysFirst string = "no"
	if task.IsKeysExistsRewrite() {
		fullsyncDelKeysFirst = "yes"
	}
	sampleData := string(sampleBytes)
	sampleData = strings.ReplaceAll(sampleData, "{{SYNC_PORT}}", strconv.Itoa(task.RowData.SyncerPort))
	// sampleData = strings.ReplaceAll(sampleData, "{{SYNC_LOG_FILE}}", task.SyncLogFile)
	sampleData = strings.ReplaceAll(sampleData, "{{SYNC_LOG_FILE}}", "./"+filepath.Base(task.SyncLogFile))
	sampleData = strings.ReplaceAll(sampleData, "{{KV_STORE_ID}}", strconv.Itoa(task.RowData.SrcKvStoreID))
	sampleData = strings.ReplaceAll(sampleData, "{{SRC_ADDR}}", task.GetSrcRedisAddr())
	sampleData = strings.ReplaceAll(sampleData, "{{SRC_PASSWORD}}", task.GetSrcRedisPasswd())
	sampleData = strings.ReplaceAll(sampleData, "{{DST_ADDR}}", task.GetDstRedisAddr())
	sampleData = strings.ReplaceAll(sampleData, "{{DST_PASSWORD}}", task.GetDstRedisPasswd())
	sampleData = strings.ReplaceAll(sampleData, "{{KEY_WHITE_REGEX}}", keyWhiteRegex)
	sampleData = strings.ReplaceAll(sampleData, "{{KEY_BLACK_REGEX}}", keyBlackRegex)
	sampleData = strings.ReplaceAll(sampleData, "{{FULLSYNC_DEL_KEYS_FIRST}}", fullsyncDelKeysFirst)
	// 如果目标集群是域名,则redis-sync需要先解析域名中的 proxy ips,而后连接;该行为通过 proxy-enable 参数控制
	proxyEnable := "no"
	if util.IsDbDNS(task.GetDstRedisAddr()) {
		proxyEnable = "yes"
	}
	sampleData = strings.ReplaceAll(sampleData, "{{PROXY_ENABLE}}", proxyEnable)
	err = ioutil.WriteFile(task.SyncConfigFile, []byte(sampleData), 0755)
	if err != nil {
		task.Err = fmt.Errorf("save redis-sync config file(%s) fail,err:%v", task.SyncConfigFile, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.Logger.Info(fmt.Sprintf("save redis-sync config file(%s) succeess", task.SyncConfigFile))
	return
}

func (task *MakeSyncTask) clearOldSyncConfigFile() {
	task.SyncConfigFile = strings.TrimSpace(task.SyncConfigFile)
	if task.SyncConfigFile == "" {
		return
	}
	_, err := os.Stat(task.SyncConfigFile)
	if err == nil {
		// rm old sync config file
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s",
			filepath.Dir(task.SyncConfigFile), filepath.Base(task.SyncConfigFile))
		task.Logger.Info(rmCmd)
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 20*time.Second, task.Logger)
	}
}

func (task *MakeSyncTask) redisSyncRunCmd(cmds []string, recordLog bool) (cmdRet string) {
	localIP := "127.0.0.1"
	opts := []string{"--no-auth-warning", "-h", localIP, "-p", strconv.Itoa(task.RowData.SyncerPort)}
	opts = append(opts, cmds...)

	logCmd := task.RedisCliTool + " " + strings.Join(opts, " ")
	if recordLog {
		task.Logger.Info("redis-sync cmd ...", zap.String("cmd", logCmd))
	}

	cmdRet, err := util.RunLocalCmd(task.RedisCliTool, opts, "", nil, 5*time.Second, task.Logger)
	if err != nil {
		task.Err = err
		task.Logger.Error("redis-sync cmd fail", zap.Error(task.Err), zap.String("cmd", logCmd))
		return
	}
	if strings.HasPrefix(cmdRet, "ERR ") == true {
		task.Logger.Error("redis-sync cmd fail", zap.String("cmdRet", cmdRet))
		task.Err = fmt.Errorf("redis-sync cmd fail,err:%v", cmdRet)
		return
	}
	if recordLog {
		task.Logger.Info("redis-sync cmd success", zap.String("cmdRet", cmdRet))
	}
	return cmdRet
}

// RedisSyncInfo redis-sync执行info [tendis-plus]等
func (task *MakeSyncTask) RedisSyncInfo(section string) (infoRets map[string]string) {
	opts := []string{"info"}
	if section != "" {
		opts = append(opts, section)
	}
	var str01 string
	maxRetryTimes := 5
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		task.Err = nil
		str01 = task.redisSyncRunCmd(opts, false)
		if task.Err != nil {
			time.Sleep(5 * time.Second)
			continue
		}
		break
	}
	if task.Err != nil {
		return
	}
	infoList := strings.Split(str01, "\n")
	infoRets = make(map[string]string)
	for _, infoItem := range infoList {
		infoItem = strings.TrimSpace(infoItem)
		if strings.HasPrefix(infoItem, "#") {
			continue
		}
		if len(infoItem) == 0 {
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		list01[0] = strings.TrimSpace(list01[0])
		list01[1] = strings.TrimSpace(list01[1])
		infoRets[list01[0]] = list01[1]
	}
	return infoRets
}

// IsSyncAlive sync是否存活
func (task *MakeSyncTask) IsSyncAlive() (isAlive bool, err error) {
	isSyncAliaveCmd := fmt.Sprintf("ps -ef|grep 'taskid%d-'|grep 'kvstore-%d-'|grep -v grep|grep sync|grep conf || true",
		task.RowData.ID, task.RowData.SrcKvStoreID)
	tclog.Logger.Info("", zap.String("isSyncAliaveCmd", isSyncAliaveCmd))
	ret, err := util.RunLocalCmd("bash", []string{"-c", isSyncAliaveCmd}, "", nil, 1*time.Minute, task.Logger)
	if err != nil {
		return false, err
	}
	ret = strings.TrimSpace(ret)
	if ret != "" {
		return true, nil
	}
	return false, nil
}

// IsSyncStateOK 同步状态是否本来就ok
func (task *MakeSyncTask) IsSyncStateOK() (ok bool) {
	// redis-sync是否存活
	ok, task.Err = task.IsSyncAlive()
	if task.Err != nil {
		return false
	}
	if !ok {
		task.Logger.Warn("redis-sync not alive", zap.String("srcRedisAddr", task.GetSrcRedisAddr()),
			zap.Int64("taskid", task.RowData.ID))
		return false
	}
	task.Logger.Warn("redis-sync alive", zap.String("srcRedisAddr", task.GetSrcRedisAddr()),
		zap.Int64("taskid", task.RowData.ID))

	// 从配置文件中获取 syncerPort
	getSyncPortCmd := fmt.Sprintf(`
	confFile=$(ps -ef|grep 'taskid%d-'|grep 'kvstore-%d-'|grep conf| \
	grep -P --only-match "redis-sync -f (.*.conf)$"|awk '{print $3}')
	if [ -n "$confFile" ] &&  [ -f "$confFile" ]
	then
			ret=$(grep -i "^port=" $confFile|awk -F= '{print $2}')
			echo $ret
	else
			echo "0000"
	fi
	`, task.RowData.ID, task.RowData.SrcKvStoreID)
	task.Logger.Info("IsSyncStateOK ", zap.String("getSyncPortCmd", getSyncPortCmd))
	ret, err := util.RunLocalCmd("bash", []string{"-c", getSyncPortCmd}, "", nil, 1*time.Minute, task.Logger)
	if err != nil {
		task.Logger.Error("IsSyncStateOK fail", zap.Error(err))
		return false
	}
	ret = strings.TrimSpace(ret)
	task.Logger.Info("IsSyncStateOK ", zap.String("getSyncPortCmd result:", ret))
	if ret == "0000" || ret == "" {
		return false
	}
	syncPort, _ := strconv.Atoi(ret)

	task.SetSyncerPort(syncPort)
	task.UpdateRow()
	// 同步状态是否本来就是ok的
	syncInfoMap := task.RedisSyncInfo("")
	if task.Err != nil {
		return
	}
	syncState := syncInfoMap["sync_redis_state"]
	if syncState == constvar.SyncOnlineState {
		return true
	}
	return false
}

// RedisSyncStop 关闭redis-sync
func (task *MakeSyncTask) RedisSyncStop() {
	isAlive, err := task.IsSyncAlive()
	if !isAlive {
		tclog.Logger.Info(fmt.Sprintf("RedisSyncStop srcRedis:%s kvStore:%d sync is not alive",
			task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID))
		return
	}
	tclog.Logger.Info(fmt.Sprintf("RedisSyncStop srcRedis:%s kvStore:%d sync is alive",
		task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID))

	opts := []string{"SYNCADMIN", "stop"}
	task.redisSyncRunCmd(opts, true)
	if task.Err != nil {
		task.Err = nil // 这里已经需要关闭sync,所以 SYNCADMIN stop 执行错误可忽略
	}

	// kill redis-sync
	killCmd := fmt.Sprintf(`
	ps -ef|grep 'taskid%d-'|grep 'kvstore-%d-'|grep -v grep|grep sync|grep conf|awk '{print $2}'|while read pid
	do
	kill -9 $pid
	done
	`, task.RowData.ID, task.RowData.SrcKvStoreID)
	task.Logger.Info("RedisSyncStop...", zap.String("killCmd", killCmd))
	retryTimes := 0
	for isAlive == true && retryTimes < 5 {
		msg := fmt.Sprintf("Killing redis-sync  times:%d ...", retryTimes+1)
		task.Logger.Info(msg)
		// redis-sync is alive, now kill it
		_, err = util.RunLocalCmd("bash", []string{"-c", killCmd}, "", nil, 1*time.Minute, task.Logger)
		if err != nil {
			task.Logger.Error("Kill redis-sync process fail", zap.Error(err))
		}
		time.Sleep(10 * time.Second)
		retryTimes++
		isAlive, _ = task.IsSyncAlive()
		if isAlive {
			task.Logger.Error(fmt.Sprintf("srcRedis:%s kvStoreId:%d,Kill redis-sync fail,process still alive",
				task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID))
		}
	}
	if isAlive && retryTimes == 5 {
		task.Logger.Error(fmt.Sprintf("srcRedis:%s kvStoreId:%d,Kill redis-sync process failed",
			task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID))
		task.Err = fmt.Errorf("Kill redis-sync process failed")
		return
	}
	task.Logger.Info(fmt.Sprintf("srcRedis:%s kvStoreId:%d,kill redis-sync success",
		task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID))
	return
}

// RedisSyncStart 启动redis-sync
func (task *MakeSyncTask) RedisSyncStart(reacquirePort bool) {
	tclog.Logger.Info(fmt.Sprintf("redis-sync start srcRedisAddr:%s kvStoreId:%d dstCluster:%s ...",
		task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID, task.GetDstRedisAddr()))
	defer tclog.Logger.Info("end redis-sync start")

	if reacquirePort {
		task.getMySyncPort(0)
		if task.Err != nil {
			return
		}
	}
	maxRetryTimes := 5
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		task.Err = nil

		task.createSyncLogFile()
		if task.Err != nil {
			return
		}
		task.createSyncConfigFile()
		if task.Err != nil {
			return
		}

		startCmds := fmt.Sprintf(`cd %s && nohup %s -f %s >>%s 2>&1 &`,
			task.TaskDir,
			task.RedisSyncTool, task.SyncConfigFile,
			filepath.Base(task.SyncLogFile))
		task.Logger.Info(startCmds)

		go func(bgcmd string) {
			util.RunLocalCmd("bash", []string{"-c", bgcmd}, "", nil, 10*time.Second, task.Logger)
		}(startCmds)

		time.Sleep(5 * time.Second)
		isAlive, err := task.IsSyncAlive()
		if err != nil {
			task.Err = err
			task.Logger.Error(task.Err.Error())
			return
		}
		if !isAlive {
			logContent, _ := ioutil.ReadFile(task.SyncLogFile)
			task.Logger.Error("redis-sync start fail", zap.String("failDetail", string(logContent)))
			task.Err = fmt.Errorf("redis-sync start fail,detail:%s", string(logContent))
			if strings.Contains(string(logContent), "Address already in use") {
				// port address already used
				// clear and get sync port again and  retry
				task.clearOldSyncLogFile()
				task.clearOldSyncConfigFile()
				task.getMySyncPort(task.RowData.SyncerPort + 1)
				if task.Err != nil {
					return
				}
				continue
			}
		}
		break
	}
	if task.Err != nil {
		task.Err = fmt.Errorf("make sync start fail")
		return
	}

	// 命令: redis-cli -h $redis_sync_ip -p $redis_sync_port SYNCADMIN start
	opts := []string{"SYNCADMIN", "start"}
	ret02 := task.redisSyncRunCmd(opts, true)
	if task.Err != nil {
		return
	}
	tclog.Logger.Info("redis-sync 'syncadmin start' success", zap.String("cmdRet", ret02))

	task.UpdateDbAndLogLocal("redis-sync %d start success", task.RowData.SyncerPort)
	return
}

// WatchSync 监听redis-sync
// 获取binlog-lag 与 last-key等信息
// 执行stop 等操作
func (task *MakeSyncTask) WatchSync() {
	tenSlaveCli := task.getSlaveConn()
	if task.Err != nil {
		task.SetStatus(-1)
		task.UpdateDbAndLogLocal(task.Err.Error())
		return
	}

	task.SetTaskType(constvar.TendisplusSendBulkTaskType)
	task.UpdateRow()

	for {
		time.Sleep(10 * time.Second)
		row01, err := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
		if err != nil {
			task.Err = err
			return
		}
		task.RowData = row01
		if task.RowData.KillSyncer == 1 ||
			task.RowData.SyncOperate == constvar.RedisSyncStopTodo ||
			task.RowData.SyncOperate == constvar.RedisForceKillTaskTodo { // stop redis-sync

			succ := constvar.RedisSyncStopSucc
			fail := constvar.RedisSyncStopFail
			if task.RowData.SyncOperate == constvar.RedisForceKillTaskTodo {
				succ = constvar.RedisForceKillTaskSuccess
				fail = constvar.RedisForceKillTaskFail
			}
			task.Logger.Info(fmt.Sprintf("start execute %q ...", task.RowData.SyncOperate))
			task.RedisSyncStop()
			if task.Err == nil {
				task.SetSyncOperate(succ)
				task.SetStatus(2)
				task.UpdateDbAndLogLocal("tendisplus redis-sync:%d终止成功", task.RowData.SyncerPid)
				task.Err = nil
			} else {
				task.RowData.SyncOperate = fail
				task.SetSyncOperate(fail)
				task.SetStatus(-1)
				task.UpdateDbAndLogLocal("tendisplus redis-sync:%d终止失败,err:%v", task.RowData.SyncerPid, task.Err)
			}
			return
		}
		syncInfoMap := task.RedisSyncInfo("")
		if task.Err != nil {
			return
		}
		redisIP := syncInfoMap["redis_ip"]
		redisPort := syncInfoMap["redis_port"]
		if redisIP != task.RowData.SrcIP || redisPort != strconv.Itoa(task.RowData.SrcPort) {
			task.Err = fmt.Errorf("redis-sync(%s:%d) 同步redis(%s:%s) 的数据 不等于 %s,同步源redis不对",
				"127.0.0.1", task.RowData.SyncerPort, redisIP, redisPort, task.GetSrcRedisAddr())
			task.SetMessage(task.Err.Error())
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			return
		}
		syncState := syncInfoMap["sync_redis_state"]
		if syncState != constvar.SyncOnlineState {
			task.Err = fmt.Errorf("redis-sync(%s:%d) sync-redis-state:%s != %s",
				"127.0.0.1", task.RowData.SyncerPort, syncState, constvar.SyncOnlineState)
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			// return
			continue
		}
		infoRepl, err := tenSlaveCli.TendisplusInfoRepl()
		if err != nil {
			task.Err = err
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			return
		}
		if len(infoRepl.RocksdbSlaveList) == 0 {
			task.Err = fmt.Errorf("tendisplus slave(%s) 'info replication' not found rocksdb slaves",
				task.GetSrcRedisAddr())
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			return
		}
		var myRockSlave *myredis.InfoReplRocksdbSlave = nil
		for _, slave01 := range infoRepl.RocksdbSlaveList {
			if slave01.DestStoreID == task.RowData.SrcKvStoreID {
				myRockSlave = &slave01
				break
			}
		}
		if myRockSlave == nil {
			task.Err = fmt.Errorf("tendisplus slave(%s) 'info replication' not found dst_store_id:%d rocksdb slave",
				task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID)
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			task.Logger.Info(infoRepl.String())
			return
		}
		if myRockSlave.State != constvar.TendisplusReplSendbulk &&
			myRockSlave.State != constvar.TendisplusReplOnline {
			task.Err = fmt.Errorf("tendisplus slave(%s) 'info replication' dst_store_id:%d rocksdbSlave state=%s not %s/%s",
				task.GetSrcRedisAddr(), task.RowData.SrcKvStoreID, myRockSlave.State,
				constvar.TendisplusReplSendbulk, constvar.TendisplusReplOnline)
			task.SetStatus(-1)
			task.UpdateDbAndLogLocal(task.Err.Error())
			return
		}
		task.SetStatus(1)
		if myRockSlave.State == constvar.TendisplusReplSendbulk {
			task.SetTaskType(constvar.TendisplusSendBulkTaskType)
			task.UpdateDbAndLogLocal("全量迁移中,binlog_pos:%d,lag:%d", myRockSlave.BinlogPos, myRockSlave.Lag)
		} else {
			task.SetTaskType(constvar.TendisplusSendIncrTaskType)
			task.UpdateDbAndLogLocal("增量同步中,binlog_pos:%d,lag:%d", myRockSlave.BinlogPos, myRockSlave.Lag)
		}
	}
}
