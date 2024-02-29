package atomredis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisVersionUpdateParams redis 版本更新参数
type RedisVersionUpdateParams struct {
	common.MediaPkg
	IP       string `json:"ip" validate:"required"`
	Ports    []int  `json:"ports" validate:"required"`
	Password string `json:"password" validate:"required"`
	Role     string `json:"role" validate:"required"` // redis_master or redis_slave
}

// RedisVersionUpdate TODO
type RedisVersionUpdate struct {
	runtime          *jobruntime.JobGenericRuntime
	params           RedisVersionUpdateParams
	localPkgBaseName string
	AddrMapCli       map[string]*myredis.RedisClient `json:"addr_map_cli"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisVersionUpdate)(nil)

// NewRedisVersionUpdate new
func NewRedisVersionUpdate() jobruntime.JobRunner {
	return &RedisVersionUpdate{}
}

// Init prepare run env
func (job *RedisVersionUpdate) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisVersionUpdate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisVersionUpdate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if len(job.params.Ports) == 0 {
		err = fmt.Errorf("RedisVersionUpdate Init ports(%+v) is empty", job.params.Ports)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// Name 原子任务名
func (job *RedisVersionUpdate) Name() string {
	return "redis_version_update"
}

// Run Command Run
func (job *RedisVersionUpdate) Run() (err error) {
	err = myredis.LocalRedisConnectTest(job.params.IP, job.params.Ports, job.params.Password)
	if err != nil {
		return err
	}
	err = job.allInstsAbleToConnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()

	if job.params.Role == consts.MetaRoleRedisMaster {
		err = job.isAllInstanceMaster()
		if err != nil {
			return err
		}
	} else if job.params.Role == consts.MetaRoleRedisSlave {
		err = job.isAllInstanceSlave()
		if err != nil {
			return err
		}
	} else {
		err = fmt.Errorf("role:%s not support", job.params.Role)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	err = job.getLocalRedisPkgBaseName()
	if err != nil {
		return err
	}
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	err = job.checkRedisLocalPkgAndTargetPkgSameType()
	if err != nil {
		return err
	}
	// 关闭 dbmon,最后再拉起
	err = util.StopBkDbmon()
	if err != nil {
		return err
	}
	defer util.StartBkDbmon()
	// 当前/usr/local/redis 指向版本不是 目标版本
	if job.localPkgBaseName != job.params.GePkgBaseName() {
		err = job.untarMedia()
		if err != nil {
			return err
		}
		// 先 stop 所有 redis
		for _, port := range job.params.Ports {
			err = job.checkAndBackupRedis(port)
			if err != nil {
				return
			}
			err = job.stopRedis(port)
			if err != nil {
				return err
			}
		}
		// 更新 /usr/local/redis 软链接
		err = job.updateFileLink()
		if err != nil {
			return err
		}
		// 再 start 所有 redis
		for _, port := range job.params.Ports {
			err = job.startRedis(port)
			if err != nil {
				return err
			}
		}
	}
	// 当前 /usr/local/redis 指向版本已经是 目标版本
	// 检查每个redis 运行版本是否是目标版本,如果不是则重启
	for _, port := range job.params.Ports {
		addr := fmt.Sprintf("%s:%d", job.params.IP, port)
		cli := job.AddrMapCli[addr]
		ok, err := job.isRedisRuntimeVersionOK(cli)
		if err != nil {
			return err
		}
		if ok {
			// 当前 redis 运行版本已经是目标版本
			continue
		}
		err = job.checkAndBackupRedis(port)
		if err != nil {
			return err
		}
		// 当前 redis 运行版本不是目标版本
		err = job.stopRedis(port)
		if err != nil {
			return err
		}
		err = job.startRedis(port)
		if err != nil {
			return err
		}
	}

	return nil
}

func (job *RedisVersionUpdate) getLocalRedisPkgBaseName() (err error) {
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	_, err = os.Stat(redisSoftLink)
	if err != nil && os.IsNotExist(err) {
		err = fmt.Errorf("redis soft link(%s) not exist", redisSoftLink)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	realLink, err := os.Readlink(redisSoftLink)
	if err != nil {
		err = fmt.Errorf("readlink redis soft link(%s) failed,err:%+v", redisSoftLink, err)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.localPkgBaseName = filepath.Base(realLink)
	job.runtime.Logger.Info("before update,%s->%s", redisSoftLink, realLink)
	return nil
}

// checkRedisLocalPkgAndTargetPkgSameType 检查reids本地包与目标包是同一类型,避免 cache redis 传的是 tendisplus 的包
func (job *RedisVersionUpdate) checkRedisLocalPkgAndTargetPkgSameType() (err error) {
	targetPkgName := job.params.GePkgBaseName()
	targetDbType := util.GetRedisDbTypeByPkgName(targetPkgName)
	localDbType := util.GetRedisDbTypeByPkgName(job.localPkgBaseName)
	if targetDbType != localDbType {
		err = fmt.Errorf("/usr/local/redis->%s cannot update to %s", job.localPkgBaseName, targetPkgName)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// allInstsAbleToConnect 检查所有实例可连接
func (job *RedisVersionUpdate) allInstsAbleToConnect() (err error) {
	instsAddrs := make([]string, 0, len(job.params.Ports))
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	for _, port := range job.params.Ports {
		instsAddrs = append(instsAddrs, fmt.Sprintf("%s:%d", job.params.IP, port))
	}
	for _, addr := range instsAddrs {
		cli, err := myredis.NewRedisClientWithTimeout(addr, job.params.Password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if err != nil {
			return err
		}
		job.AddrMapCli[addr] = cli
	}
	job.runtime.Logger.Info("all redis instances able to connect,(%+v)", instsAddrs)
	return nil
}

// allInstDisconnect 所有实例断开连接
func (job *RedisVersionUpdate) allInstDisconnect() {
	for _, cli := range job.AddrMapCli {
		cli.Close()
	}
}

func (job *RedisVersionUpdate) isAllInstanceMaster() (err error) {
	for _, item := range job.AddrMapCli {
		cli := item
		repls, err := cli.Info("replication")
		if err != nil {
			return err
		}
		if repls["role"] != consts.RedisMasterRole {
			err = fmt.Errorf("redis instance(%s) is not master", cli.Addr)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		// 是否要检查 master 是否还有 slave?
	}
	return nil
}
func (job *RedisVersionUpdate) isAllInstanceSlave() (err error) {
	for _, item := range job.AddrMapCli {
		cli := item
		repls, err := cli.Info("replication")
		if err != nil {
			return err
		}
		if repls["role"] != consts.RedisSlaveRole {
			err = fmt.Errorf("redis instance(%s) is not slave", cli.Addr)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		if repls["master_link_status"] != consts.MasterLinkStatusUP {
			err = fmt.Errorf("redis instance(%s) master_link_status:%s is not UP", cli.Addr, repls["master_link_status"])
			job.runtime.Logger.Error(err.Error())
			return err
		}
		master_last_io_seconds_ago, err := strconv.Atoi(repls["master_last_io_seconds_ago"])
		if err != nil {
			err = fmt.Errorf("redis instance(%s) master_last_io_seconds_ago:%s is not int", cli.Addr,
				repls["master_last_io_seconds_ago"])
			job.runtime.Logger.Error(err.Error())
			return err
		}
		if master_last_io_seconds_ago > 20 {
			err = fmt.Errorf("redis instance(%s) master_last_io_seconds_ago:%d is greater than 20", cli.Addr,
				master_last_io_seconds_ago)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		job.runtime.Logger.Info(
			"redis instance(%s) is slave,master(%s:%s),master_link_status:%s,master_last_io_seconds_ago:%d",
			cli.Addr, repls["master_host"], repls["master_port"],
			repls["master_link_status"], master_last_io_seconds_ago)
	}
	return nil
}

// untarMedia 解压介质
func (job *RedisVersionUpdate) untarMedia() (err error) {
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	pkgAbsPath := job.params.GetAbsolutePath()
	untarCmd := fmt.Sprintf("tar -zxf %s -C %s", pkgAbsPath, consts.UsrLocal)
	job.runtime.Logger.Info(untarCmd)
	_, err = util.RunBashCmd(untarCmd, "", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("untar %s success", pkgAbsPath)
	return nil
}

// updateFileLink 更新 /usr/local/redis 软链接
func (job *RedisVersionUpdate) updateFileLink() (err error) {
	pkgBaseName := job.params.GePkgBaseName()
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	_, err = os.Stat(redisSoftLink)
	if err == nil {
		// 删除 /usr/local/redis 软链接
		err = os.Remove(redisSoftLink)
		if err != nil {
			err = fmt.Errorf("remove redis soft link(%s) failed,err:%+v", redisSoftLink, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	// 创建 /usr/local/redis -> /usr/local/$pkgBaseName 软链接
	err = os.Symlink(filepath.Join(consts.UsrLocal, pkgBaseName), redisSoftLink)
	if err != nil {
		err = fmt.Errorf("os.Symlink %s -> %s fail,err:%s", redisSoftLink, filepath.Join(consts.UsrLocal, pkgBaseName), err)
		job.runtime.Logger.Error(err.Error())
		return
	}
	util.LocalDirChownMysql(redisSoftLink)
	util.LocalDirChownMysql(redisSoftLink + "/")
	job.runtime.Logger.Info("create softLink success,%s -> %s", redisSoftLink, filepath.Join(consts.UsrLocal, pkgBaseName))
	return nil
}

// checkAndBackupRedis 如果有必要先备份reids
func (job *RedisVersionUpdate) checkAndBackupRedis(port int) (err error) {
	// 如果是 master 且是 cache,则先备份
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	if job.params.Role != consts.MetaRoleRedisMaster {
		job.runtime.Logger.Info("redis instance(%s) is not master,skip backup", addr)
		return nil
	}
	cli := job.AddrMapCli[addr]
	var dbType string
	dbType, err = cli.GetTendisType()
	if err != nil {
		return err
	}
	if dbType != consts.TendisTypeRedisInstance {
		job.runtime.Logger.Info("redis instance(%s) is not cache,skip backup", addr)
		return nil
	}
	job.runtime.Logger.Info("redis instance(%s) is cache,start bgsave", addr)
	err = cli.BgSaveAndWaitForFinish()
	if err != nil {
		return nil
	}
	return
}

func (job *RedisVersionUpdate) stopRedis(port int) (err error) {
	stopScript := filepath.Join(consts.UsrLocal, "redis", "bin", "stop-redis.sh")
	_, err = os.Stat(stopScript)
	if err != nil && os.IsNotExist(err) {
		job.runtime.Logger.Info("%s not exist", stopScript)
		return nil
	}
	// 先执行 stop-redis.sh 脚本,再检查端口是否还在使用
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\"",
		consts.MysqlAaccount, stopScript+" "+strconv.Itoa(port)+" xxxx"))
	_, err = util.RunLocalCmd("su",
		[]string{consts.MysqlAaccount, "-c", stopScript + " " + strconv.Itoa(port) + " " + job.params.Password},
		"", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	maxRetryTimes := 5
	inUse := false
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		inUse, err = util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
		if err != nil {
			job.runtime.Logger.Error(fmt.Sprintf("check %s:%d inUse failed,err:%v", job.params.IP, port, err))
			return err
		}
		if !inUse {
			break
		}
		time.Sleep(2 * time.Second)
	}
	if inUse {
		err = fmt.Errorf("stop redis instance(%s:%d) failed,port:%d still using", job.params.IP, port, port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("stop redis instance(%s:%d) success", job.params.IP, port)
	return nil
}

func (job *RedisVersionUpdate) startRedis(port int) (err error) {
	startScript := filepath.Join(consts.UsrLocal, "redis", "bin", "start-redis.sh")
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\" 2>/dev/null",
		consts.MysqlAaccount, startScript+" "+strconv.Itoa(port)))
	_, err = util.RunLocalCmd("su",
		[]string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(port) + " 2>/dev/null"},
		"", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli, err := myredis.NewRedisClientWithTimeout(addr, job.params.Password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	job.AddrMapCli[addr] = cli
	job.runtime.Logger.Info("start redis instance(%s:%d) success", job.params.IP, port)

	if job.params.Role == consts.MetaRoleRedisMaster {
		return nil
	}
	// 多次检测直到 redis instance 成为 slave,且同步状态正常
	_, err = job.isReplStateOK(cli, 1*time.Minute)
	if err != nil {
		return err
	}
	return nil
}

func (job *RedisVersionUpdate) isReplStateOK(cli *myredis.RedisClient, timeout time.Duration) (ok bool, err error) {
	maxRetryTimes := timeout / (2 * time.Second)
	if maxRetryTimes == 0 {
		maxRetryTimes = 1
	}
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		time.Sleep(2 * time.Second)
		err = nil
		repls, err := cli.Info("replication")
		if err != nil {
			return false, err
		}
		if repls["role"] != consts.RedisSlaveRole {
			job.runtime.Logger.Info("redis instance(%s) role:%s is not slave", cli.Addr, repls["role"])
			continue
		}
		if repls["master_link_status"] != consts.MasterLinkStatusUP {
			job.runtime.Logger.Info("redis instance(%s) master_link_status:%s is not UP", cli.Addr, repls["master_link_status"])
			continue
		}
		job.runtime.Logger.Info("redis instance(%s) is slave,master(%s:%s),master_link_status:%s",
			cli.Addr, repls["master_host"], repls["master_port"], repls["master_link_status"])
		return true, nil
	}
	err = fmt.Errorf("cost %d seconds, redis instance(%s) is not slave", int(timeout.Seconds()), cli.Addr)
	job.runtime.Logger.Error(err.Error())
	return false, err
}

func (job *RedisVersionUpdate) isRedisRuntimeVersionOK(cli *myredis.RedisClient) (ok bool, err error) {
	repls, err := cli.Info("server")
	if err != nil {
		return false, err
	}
	runtimeBaseVer, runtimeSubVer, err := util.VersionParse(repls["redis_version"])
	if err != nil {
		return false, err
	}
	pkgBaseVer, pkgSubVer, err := util.VersionParse(job.params.GePkgBaseName())
	if err != nil {
		return false, err
	}
	if runtimeBaseVer != pkgBaseVer || runtimeSubVer != pkgSubVer {
		return false, nil
	}
	return true, nil
}

// Retry times
func (job *RedisVersionUpdate) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisVersionUpdate) Rollback() error {
	return nil
}
