package atomredis

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RedisShutdownParams redis shutdown参数
type RedisShutdownParams struct {
	IP                     string `json:"ip" validate:"required"`
	Ports                  []int  `json:"ports" validate:"required"`
	IsAllInstancesShutdown bool   `json:"is_all_instances_shutdown"`
	// 是否是集群下架，来区分实例下架场景。如果slot != 0&cluster status is ok & !is_cluster_shutdown需要报错
	// 默认值: false，表示非集群下架场景，会进行slot检查
	IsClusterShutdown bool `json:"is_cluster_shutdown"`
	Debug             bool `json:"debug"`
}

// RedisShutdown redis shutdown 结构体
type RedisShutdown struct {
	runtime        *jobruntime.JobGenericRuntime
	params         *RedisShutdownParams
	RealDataDir    string // /data/redis
	RedisBinDir    string // /usr/local/redis
	RedisBackupDir string

	errChan chan error
}

// NewRedisShutdown 创建一个redis shutdown对象
func NewRedisShutdown() jobruntime.JobRunner {
	return &RedisShutdown{}
}

// Init 初始化
func (job *RedisShutdown) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisShutdown Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisShutdown Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	// 6379<= start_port <= 64534
	ports := job.params.Ports
	for _, p := range ports {
		if p > 64534 || p < 6379 {
			err = fmt.Errorf("RedisShutdown port[%d] must range [6379,64534]", p)
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}

	return nil
}

// Run 运行下架流程
func (job *RedisShutdown) Run() (err error) {

	job.InitRealDataDir()
	ports := job.params.Ports

	// 非集群下架场景下，检查实例是否仍拥有slot且集群状态ok
	if !job.params.IsClusterShutdown {
		if err = job.checkInstanceSlotsBeforeShutdown(ports); err != nil {
			return err
		}
	}

	wg := sync.WaitGroup{}
	for _, port := range ports {
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			shutdownFlag := job.Shutdown(port)
			// 只有进程没了，才去mv目录
			if shutdownFlag {
				job.BackupDir(port)
			}
		}(port)
	}
	wg.Wait()
	close(job.errChan)

	errMsg := ""
	for err := range job.errChan {
		errMsg = fmt.Sprintf("%s\n%s", errMsg, err.Error())
	}
	if errMsg != "" {
		return fmt.Errorf(errMsg)
	}

	err = job.ClearWhenAllInstancesShutdown()
	if err != nil {
		return err
	}

	return nil
}

// InitRealDataDir 初始化参数
func (job *RedisShutdown) InitRealDataDir() {
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	job.RedisBinDir = filepath.Join(redisSoftLink, "bin")
	job.runtime.Logger.Info("GetRedisBinDir success,binDir:%s", job.RedisBinDir)

	job.RealDataDir = filepath.Join(consts.GetRedisDataDir(), "/redis")
	job.runtime.Logger.Info("GetRealDataDir success,dataDir:%s", job.RealDataDir)

	job.RedisBackupDir = filepath.Join(consts.GetRedisBackupDir(), "dbbak")
	job.runtime.Logger.Info("GeRedisBackupDir success,backupDir:%s", job.RedisBackupDir)

	job.errChan = make(chan error, len(job.params.Ports))
}

// checkInstanceSlotsBeforeShutdown 非集群下架场景下，检查实例是否仍拥有slot且集群状态ok
// 判断条件: IsClusterShutdown == false && cluster state is ok && 实例拥有slot => 报错
func (job *RedisShutdown) checkInstanceSlotsBeforeShutdown(ports []int) error {
	for _, port := range ports {
		insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
		pwd, err := myredis.GetRedisPasswdFromConfFile(port)
		if err != nil {
			err = fmt.Errorf("checkInstanceSlotsBeforeShutdown: get redis port[%d] password failed: %v", port, err)
			// 区分两种情况:
			//   1) 端口不监听 -> 实例进程已挂, 可安全跳过(已下架实例不可能持有 slot)
			//   2) 端口仍在监听(或探测出错) -> 实例仍存活, 可能仍持有 slot, 必须中止下架
			if down, ok := job.isInstancePortDown(port); ok && down {
				job.runtime.Logger.Error(err.Error() + "; instance is not listening, treat as already down, skip slot check")
				continue
			}
			job.runtime.Logger.Error(err.Error())
			return err
		}
		redisClient, err := myredis.NewRedisClient(insAddr, pwd, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			err = fmt.Errorf("checkInstanceSlotsBeforeShutdown: connect redis %s failed: %v", insAddr, err)
			// 区分两种情况:
			//   1) 端口不监听 -> 实例进程已挂, 可安全跳过
			//   2) 端口仍在监听(或探测出错) -> 实例仍存活, 连接失败意味着无法确认 slot 状态, 必须中止下架
			if down, ok := job.isInstancePortDown(port); ok && down {
				job.runtime.Logger.Error(err.Error() + "; instance is not listening, treat as already down, skip slot check")
				continue
			}
			job.runtime.Logger.Error(err.Error())
			return err
		}

		// 检查是否为集群模式
		clusterEnabled, err := redisClient.IsClusterEnabled()
		if err != nil {
			redisClient.Close()
			err = fmt.Errorf("checkInstanceSlotsBeforeShutdown: check %s cluster_enabled failed: %v", insAddr, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		if !clusterEnabled {
			redisClient.Close()
			job.runtime.Logger.Info("redis %s is not cluster mode, skip slot check", insAddr)
			continue
		}

		// 检查集群状态是否ok
		clusterInfo, err := redisClient.ClusterInfo()
		if err != nil {
			redisClient.Close()
			err = fmt.Errorf("checkInstanceSlotsBeforeShutdown: get %s cluster info failed: %v", insAddr, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		if clusterInfo.ClusterState != consts.ClusterStateOK {
			redisClient.Close()
			job.runtime.Logger.Info("redis %s cluster state is %s, not ok, skip slot check", insAddr, clusterInfo.ClusterState)
			continue
		}

		// 集群状态ok，检查实例是否拥有slot
		addrToNodes, err := redisClient.GetAddrMapToNodes()
		redisClient.Close()
		if err != nil {
			err = fmt.Errorf("checkInstanceSlotsBeforeShutdown: get %s cluster nodes failed: %v", insAddr, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		nodeData, ok := addrToNodes[insAddr]
		if ok && len(nodeData.Slots) > 0 {
			err = fmt.Errorf(
				"cannot shutdown redis %s: instance still has %d slots and cluster state is ok, "+
					"please migrate slots first or set is_cluster_shutdown=true", insAddr, len(nodeData.Slots))
			job.runtime.Logger.Error(err.Error())
			return err
		}
		job.runtime.Logger.Info("redis %s has 0 slots in a healthy cluster, safe to shutdown", insAddr)
	}
	return nil
}

// Shutdown 停止进程
func (job *RedisShutdown) Shutdown(port int) bool {
	shutDownSucc := false
	status := true
	var err error
	status, err = job.IsRedisRunning(port)
	if err == nil && !status {
		job.runtime.Logger.Info("redis port[%d] is not running", port)
		return true
	}
	stopScript := filepath.Join(job.RedisBinDir, "stop-redis.sh")
	job.runtime.Logger.Info("get port[%d] pwd begin.", port)
	pwd, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		job.errChan <- fmt.Errorf("get redis port[%d] password failed err[%s]", port, err.Error())
		return false
	}
	job.runtime.Logger.Info("get port[%d] pwd success.", port)

	for i := 1; i <= 10; i++ {
		job.runtime.Logger.Info("shuwdown redis port[%d] count[%d/10] begin....", port, i)
		status, _ = job.IsRedisRunning(port)
		if !status {
			job.runtime.Logger.Info("redis port[%d] status is not running. shutdown succ....", port)
			shutDownSucc = true
			break
		}
		job.runtime.Logger.Info("check port[%d] conn status.", port)
		if err = job.CheckSlaveConn(port, pwd); err != nil {
			job.runtime.Logger.Warn(err.Error())
			continue
		}

		// 先通过stop脚本去停止，如果停止失败再尝试用redis-client的方式去shutdown
		rst, err := util.RunLocalCmdReplacePkey("su", []string{
			consts.MysqlAaccount, "-c", stopScript + "  " + strconv.Itoa(port) + " " + pwd}, pwd, "",
			nil, 10*time.Second)
		if err != nil || rst != "" {
			job.runtime.Logger.Warn("shutdwon failed by call bash . %s:%+v", rst, err)
			job.runtime.Logger.Info("shuwdown redis port[%d] count[%d/10] try use redis-client to shutdown", port, i)
			job.ShutdownByClient(port, pwd)
		}
		status, _ = job.IsRedisRunning(port)
		if !status {
			job.runtime.Logger.Info("redis port[%d] status is not running. shutdown succ....", port)
			shutDownSucc = true
			break
		}
		job.runtime.Logger.Info("shuwdown redis port[%d] count[%d/10] end. redis is running. sleep 60s after continue...",
			port, i)
		time.Sleep(60 * time.Second)
	}
	if !shutDownSucc {
		job.errChan <- fmt.Errorf("shutdown redis port[%d] failed err[%s]", port, err.Error())
		return false
	}

	job.runtime.Logger.Info("shuwdown redis port[%d] succ....", port)
	return true
}

// ShutdownByClient 使用客户端shutdown的方式去停止实例
func (job *RedisShutdown) ShutdownByClient(port int, pwd string) {
	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, pwd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return
	}
	defer redisClient.Close()

	_ = redisClient.Shutdown()
}

// CheckSlaveConn 检查是否有slave连接
func (job *RedisShutdown) CheckSlaveConn(port int, pwd string) error {
	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, pwd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer redisClient.Close()

	replInfo, err := redisClient.Info("replication")
	if err != nil {
		return err
	}
	if replInfo["role"] == consts.RedisMasterRole {
		if replInfo["connected_slaves"] != "0" {
			return fmt.Errorf("%s have %s slave conn, pleace waiting",
				insAddr, replInfo["connected_slaves"])
		}
	}

	return nil
}

// BackupDir 备份目录
func (job *RedisShutdown) BackupDir(port int) {
	job.runtime.Logger.Info("redis port[%d] backup dir begin....", port)
	if job.params.Debug {
		return
	}
	// 判断目录是否存在
	insDir := fmt.Sprintf("%s/%d", job.RealDataDir, port)
	exist := util.FileExists(insDir)
	if !exist {
		job.runtime.Logger.Info("dir %s is not exists. nothing to do", insDir)
		return
	}
	job.runtime.Logger.Info("redis port[%d] backup dir to doing....", port)
	mvCmd := fmt.Sprintf("mv %s/%d %s/shutdown_%d_%s", job.RealDataDir, port,
		job.RealDataDir, port, time.Now().Format("20060102150405"))
	job.runtime.Logger.Info(mvCmd)
	cmd := []string{"su", consts.MysqlAaccount, "-c", mvCmd}
	_, err := util.RunLocalCmd(cmd[0], cmd[1:], "",
		nil, 10*time.Second)
	if err != nil {
		job.errChan <- fmt.Errorf("exec mv dir cmd error[%s]", err.Error())
		return
	}

	exist = util.FileExists(insDir)
	if !exist {
		job.runtime.Logger.Info("mv redis port[%d] dir succ....", port)
		return
	}
	job.runtime.Logger.Info("redis port[%d] backup dir end....", port)
	job.errChan <- fmt.Errorf("redis port[%d] dir [%s] exists too..pleace check", port, insDir)
}

// IsRedisRunning 检查实例是否在运行
func (job *RedisShutdown) IsRedisRunning(port int) (installed bool, err error) {
	time.Sleep(10 * time.Second)
	portIsUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	return portIsUse, err
}

// isInstancePortDown 通过探测端口是否仍被监听来判断实例进程是否已停止。
// 返回 (down, ok)：
//   - down=true,  ok=true: 确认实例端口未在监听(进程已挂, 可安全跳过 slot 检查)
//   - down=false, ok=true: 确认实例端口仍在监听(进程仍存活, 可能仍持有 slot)
//   - down=false, ok=false: 探测过程出错(状态未知, 一律按"仍存活"处理, 保守地中止下架)
func (job *RedisShutdown) isInstancePortDown(port int) (down bool, ok bool) {
	inUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	if err != nil {
		job.runtime.Logger.Warn("isInstancePortDown: check port[%d] failed: %v", port, err)
		return false, false
	}
	return !inUse, true
}

// ClearWhenAllInstancesShutdown TODO
func (job *RedisShutdown) ClearWhenAllInstancesShutdown() (err error) {
	if !job.params.IsAllInstancesShutdown {
		job.runtime.Logger.Info("%s not all instances shutdown,nothing to do", job.params.IP)
		return nil
	}
	var psRet string
	// 再次判断是否还有不必要的进程存在
	psCmd := `ps aux|grep -iwE "tendisplus|redis-server"|grep -vE "grep|IEDBACKUP" || { true; }`
	job.runtime.Logger.Info(psCmd)
	psRet, err = util.RunBashCmd(psCmd, "", nil, 10*time.Second)
	if err != nil {
		job.runtime.Logger.Error("exec ps cmd error[%s]", err.Error())
		return err
	}
	if psRet != "" {
		job.runtime.Logger.Info("IsAllInstancesShutdown=%v, psCmd:%s result:%s",
			job.params.IsAllInstancesShutdown, psCmd, psRet)
		return fmt.Errorf("ps result:%s", psRet)
	}
	job.runtime.Logger.Error("%s all instances have been shutdown,start clear some dirs", job.params.IP)
	// 清理 backup-client 相关数据
	job.runtime.Logger.Info("start clear backup-client dir")
	err = util.ClearBackupClientDir()
	if err != nil {
		return
	}
	// 清理 exporter 相关数据
	job.runtime.Logger.Info("start clear .exporter config file")
	for _, port := range job.params.Ports {
		common.DeleteExporterConfigFile(port)
	}
	// 清理 /usr/local/redis
	job.runtime.Logger.Info("start clear /usr/local/redis dir")
	err = util.ClearUsrLocalRedis(true)
	if err != nil {
		return
	}
	// 清理环境变量 REDIS_DATA_DIR
	job.runtime.Logger.Info("start clear env REDIS_DATA_DIR")
	err = consts.RemoveRedisDataDirFromEnv()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return
	}
	// 清理环境变量 REDIS_BACKUP_DIR
	job.runtime.Logger.Info("start clear env REDIS_BACKUP_DIR")
	err = consts.RemoveRedisBackupDirFromEnv()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return
	}
	// util.CleanRedisExporter()
	return nil
}

// Name 原子任务名
func (job *RedisShutdown) Name() string {
	return "redis_shutdown"
}

// Retry times
func (job *RedisShutdown) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisShutdown) Rollback() error {
	return nil
}
