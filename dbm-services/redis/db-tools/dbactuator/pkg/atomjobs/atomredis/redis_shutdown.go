package atomredis

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RedisShutdownParams redis shutdown参数
type RedisShutdownParams struct {
	IP    string `json:"ip" validate:"required"`
	Ports []int  `json:"ports" validate:"required"`
	Debug bool   `json:"debug"`
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
	// 6379<= start_port <= 55535
	ports := job.params.Ports
	for _, p := range ports {
		if p > 55535 || p < 6379 {
			err = fmt.Errorf("RedisShutdown port[%d] must range [6379,5535]", p)
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

	wg := sync.WaitGroup{}
	for _, port := range ports {
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			job.Shutdown(port)
			job.BackupDir(port)
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

// Shutdown 停止进程
func (job *RedisShutdown) Shutdown(port int) {
	shutDownSucc := false
	status := true
	var err error
	stopScript := filepath.Join(job.RedisBinDir, "stop-redis.sh")
	job.runtime.Logger.Info("get port[%d] pwd begin.", port)
	pwd, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		job.errChan <- fmt.Errorf("get redis port[%d] password failed err[%s]", port, err.Error())
		return
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
		_, err = util.RunLocalCmd("su", []string{
			consts.MysqlAaccount, "-c", stopScript + "  " + strconv.Itoa(port) + " " + pwd}, "",
			nil, 10*time.Second)
		if err != nil {
			job.runtime.Logger.Warn(err.Error())
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
		return
	}

	job.runtime.Logger.Info("shuwdown redis port[%d] succ....", port)
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
		job.RedisBackupDir, port, time.Now().Format("20060102150405"))
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
