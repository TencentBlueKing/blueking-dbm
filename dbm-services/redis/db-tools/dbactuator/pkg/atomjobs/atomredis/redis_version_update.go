package atomredis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
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
	IP          string `json:"ip" validate:"required"`
	Ports       []int  `json:"ports" validate:"required"`
	Role        string `json:"role" validate:"required"` // redis_master or redis_slave
	ClusterType string `json:"cluster_type"`
	// FlushAfterUpgrade 为 true 时, 在 startRedis (新版本) 启动完成、AOF/RDB load 完毕后,
	// 立刻向实例发送 flushall (cleanall / flushalldisk) 清空数据集. 用于 old_master 升级:
	// 升级后会作为 new_slave 重做全量同步, 旧数据冗余.
	//
	// 之所以在 start 之后 flush (而不是 stop 之前):
	//   - RedisInstance 主从架构, switch act 内部已 SHUTDOWN 旧 master,
	//     升级 act 介入时实例已死, 没有"还活着的连接"可供 flush.
	//   - 在 start 之后 flush 同时覆盖 Twemproxy 与 RedisInstance 两种路径, 行为统一.
	//
	// 仅以下三种 cluster_type 启用:
	//   - TwemproxyRedisInstance
	//   - RedisInstance
	//   - TwemproxyTendisSSDInstance
	FlushAfterUpgrade bool `json:"flush_after_upgrade"`
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
	if job.params.Role == consts.MetaRoleRedisMaster && job.params.ClusterType == consts.TendisTypeRedisInstance {
		// 对RedisInstance + redis_master 升级,单独处理
		return job.upgradeRedisInstanceMaster()
	}
	// 本地redis连接测试
	err = myredis.LocalRedisConnectTest(job.params.IP, job.params.Ports, "")
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
			if job.params.FlushAfterUpgrade {
				err = job.flushDataAfterStart(port)
				if err != nil {
					return err
				}
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
		// 当前 redis 运行版本不是目标版本: stop / start, start 之后按需 flushall.
		err = job.stopRedis(port)
		if err != nil {
			return err
		}
		err = job.startRedis(port)
		if err != nil {
			return err
		}
		if job.params.FlushAfterUpgrade {
			err = job.flushDataAfterStart(port)
			if err != nil {
				return err
			}
		}
	}

	return nil
}

func (job *RedisVersionUpdate) upgradeRedisInstanceMaster() (err error) {
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	defer job.allInstDisconnect()

	err = job.getLocalRedisPkgBaseName()
	if err != nil {
		return err
	}
	err = job.params.Check()
	if err != nil {
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
		// 解压 介质 到 /usr/local/
		err = job.untarMedia()
		if err != nil {
			return err
		}
		// 注: 走到这里时, switch act 内部的 tryShutdownMasterInstance 多半已把旧 master 关掉,
		// CheckPortIsInUse 大概率返回 false; 这里仍兜底处理 "万一还活着" 的情况.
		isAlive := false
		for _, port := range job.params.Ports {
			isAlive, _ = util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
			if !isAlive {
				continue
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
	}
	// 再 start 所有 redis
	for _, port := range job.params.Ports {
		err = job.startRedis(port)
		if err != nil {
			return err
		}
		if job.params.FlushAfterUpgrade {
			err = job.flushDataAfterStart(port)
			if err != nil {
				return err
			}
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
	var addr, password string
	instsAddrs := make([]string, 0, len(job.params.Ports))
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	for _, port := range job.params.Ports {
		addr = fmt.Sprintf("%s:%d", job.params.IP, port)
		instsAddrs = append(instsAddrs, addr)
		password, err = myredis.GetRedisPasswdFromConfFile(port)
		if err != nil {
			return err
		}
		cli, err := myredis.NewRedisClientWithTimeout(addr, password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if err != nil {
			return err
		}
		cli.ConfigRewrite()
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
	var logTailNData string
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
			logTailNData, _ = cli.TailRedisLogFile(40)
			if strings.Contains(logTailNData, "Can't handle RDB format") {
				// RDB格式不兼容,忽略
				job.runtime.Logger.Warn(
					"redis instance(%s) master_link_status:%s is not UP, but RDB format is not compatible,ignore", cli.Addr,
					repls["master_link_status"])
				continue
			}
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

// flushDataAfterStart 在 startRedis 之后, 用于 old_master 升级:
// 升级后会作为 new_slave 重做全量同步
//
// 仅支持以下三种 cluster_type, 它们升级时依赖外部 (twemproxy 切换 / 主从对) 来重做全量同步:
//   - TwemproxyRedisInstance       (twemproxy + cache redis)
//   - RedisInstance                (cache redis 主从版)
//   - TwemproxyTendisSSDInstance   (twemproxy + TendisSSD)
//
// 不支持: 原生 RedisCluster / PredixyRedisCluster / 各类 Tendisplus / 单机版 TendisSSDInstance,
// 它们走自身 failover 协议或不需要 actuator 端 flush; 此处返回错误以暴露上游配置问题.
//
// 选用的命令:
//   - cache (cleanall, 4.0+ 追加 ASYNC 参数避免阻塞主线程)
//   - TendisSSD (flushalldisk)
//
// 调用前提: 调用方刚刚 startRedis 成功, 端口已 LISTEN; 实例可能仍在 AOF/RDB load 阶段
// (返回 LOADING). 函数内部会先 INFO persistence 等待 loading=0 再发 flush.
//
// 调用时机: 此时 old_master 已完成域名 / proxy 切换, 不再承载客户端流量, 也尚未 slaveof new_master,
// flush 不会向他处传播.
func (job *RedisVersionUpdate) flushDataAfterStart(port int) error {
	clusterType := job.params.ClusterType
	switch clusterType {
	case consts.TendisTypeTwemproxyRedisInstance,
		consts.TendisTypeTwemproxyTendisSSDInstance,
		consts.TendisTypeRedisInstance:
	default:
		return fmt.Errorf(
			"flush after upgrade: cluster_type(%s) not allowed; only %s / %s / %s are supported (port %d)",
			clusterType,
			consts.TendisTypeTwemproxyRedisInstance,
			consts.TendisTypeRedisInstance,
			consts.TendisTypeTwemproxyTendisSSDInstance,
			port)
	}

	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	password, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return fmt.Errorf("flush after upgrade: get pwd from conf failed,addr:%s,err:%v", addr, err)
	}
	cli, err := myredis.NewRedisClientWithTimeout(addr, password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return fmt.Errorf("flush after upgrade: connect %s failed,err:%v", addr, err)
	}
	defer cli.Close()

	// 升级后第一次连上, 实例可能仍在 AOF / RDB load. 直接 flush 会被拒绝 (LOADING).
	// 30 分钟与 isReplStateOK 等其他长等待保持一致, 兜得住大 AOF.
	if err := job.waitForLoadingFinish(cli, 30*time.Minute); err != nil {
		return fmt.Errorf("flush after upgrade: %v", err)
	}
	if err := job.validateFlushAfterUpgradeSafety(cli); err != nil {
		return err
	}

	cmd, err := buildFlushAllCmd(clusterType, cli)
	if err != nil {
		return fmt.Errorf("flush after upgrade: build cmd for %s failed,err:%v", addr, err)
	}

	job.runtime.Logger.Info("flush after upgrade: addr=%s cmd=%v", addr, cmd)
	result, err := cli.DoCommand(cmd, 0)
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s cmd=%v err=%v", addr, cmd, err)
	}
	resultStr, ok := result.(string)
	if !ok || !strings.Contains(resultStr, "OK") {
		return fmt.Errorf("flush after upgrade: addr=%s cmd=%v result=%+v not OK", addr, cmd, result)
	}
	if err := job.checkFlushAfterUpgradeResult(cli); err != nil {
		return err
	}
	job.runtime.Logger.Info("flush after upgrade done: %s", addr)
	return nil
}

// validateFlushAfterUpgradeSafety 做最后一道 actuator 侧保护:
// 仅允许 old_master 升级 act 在实例已是 master 且没有 replica 连接时清档.
func (job *RedisVersionUpdate) validateFlushAfterUpgradeSafety(cli *myredis.RedisClient) error {
	if job.params.Role != consts.MetaRoleRedisMaster {
		return fmt.Errorf("flush after upgrade: addr=%s job role(%s) not allowed, expect %s",
			cli.Addr, job.params.Role, consts.MetaRoleRedisMaster)
	}
	repls, err := cli.Info("replication")
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s info replication failed,err:%v", cli.Addr, err)
	}
	role := repls["role"]
	if role != consts.RedisMasterRole {
		return fmt.Errorf("flush after upgrade: addr=%s redis role(%s) not allowed, expect %s",
			cli.Addr, role, consts.RedisMasterRole)
	}
	connectedSlavesStr, ok := repls["connected_slaves"]
	if !ok || connectedSlavesStr == "" {
		return fmt.Errorf("flush after upgrade: addr=%s connected_slaves missing in info replication:%+v",
			cli.Addr, repls)
	}
	connectedSlaves, err := strconv.Atoi(connectedSlavesStr)
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s connected_slaves(%s) invalid,err:%v",
			cli.Addr, connectedSlavesStr, err)
	}
	if connectedSlaves != 0 {
		return fmt.Errorf("flush after upgrade: addr=%s still has %d connected replicas, refuse to flush",
			cli.Addr, connectedSlaves)
	}
	job.runtime.Logger.Info("flush after upgrade safety check passed: addr=%s role=%s connected_slaves=%d",
		cli.Addr, role, connectedSlaves)
	return nil
}

// checkFlushAfterUpgradeResult 与 redis_flush_data.go::RandomKey 的检查保持一致:
// 清档后允许没有 key, 也允许 dbha agent 心跳 key.
func (job *RedisVersionUpdate) checkFlushAfterUpgradeResult(cli *myredis.RedisClient) error {
	key, err := cli.Randomkey()
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s randomkey check failed,err:%v", cli.Addr, err)
	}
	if key != "" && !strings.HasPrefix(key, "dbha:agent:") {
		return fmt.Errorf("flush after upgrade: addr=%s randomkey check failed,key=%s", cli.Addr, key)
	}
	job.runtime.Logger.Info("flush after upgrade result check passed: addr=%s randomkey=%s", cli.Addr, key)
	return nil
}

// waitForLoadingFinish 轮询 INFO persistence 直到 loading=0; 期间容忍 LOADING 错误.
// 用于 startRedis (升级到新版本) 后, 实例仍在加载老 AOF/RDB 时, 等待加载完成再发命令.
func (job *RedisVersionUpdate) waitForLoadingFinish(cli *myredis.RedisClient, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	const sleepInterval = 2 * time.Second
	logged := false
	for {
		info, err := cli.Info("persistence")
		if err != nil {
			// 加载阶段对部分命令也可能返回 LOADING; INFO 一般允许, 但兜底处理一下.
			if !strings.Contains(err.Error(), "LOADING") {
				return fmt.Errorf("wait for loading: addr=%s info persistence err=%v", cli.Addr, err)
			}
		} else if info["loading"] == "0" {
			if logged {
				job.runtime.Logger.Info("wait for loading done: addr=%s, info.loading=%s", cli.Addr, info["loading"])
			}
			return nil
		} else if info["loading"] == "" {
			// loading 字段缺失视为非 cache redis (TendisSSD 没有 in-memory load 阶段), 直接通过.
			job.runtime.Logger.Info("wait for loading: addr=%s loading field absent, assuming non-cache redis", cli.Addr)
			return nil
		} else {
			// 仅在第一次发现仍在 loading 时打日志, 避免轮询期间刷屏.
			if !logged {
				job.runtime.Logger.Info("wait for loading: addr=%s loading=%s eta=%ss",
					cli.Addr, info["loading"], info["loading_eta_seconds"])
				logged = true
			}
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("wait for loading: timeout(%v) addr=%s", timeout, cli.Addr)
		}
		time.Sleep(sleepInterval)
	}
}

// buildFlushAllCmd 选取对应 cluster_type 的 flushall 命令 (rename 后).
// cache 4.0+ 自动追加 ASYNC 以非阻塞清理 (与 redis_flush_data.go::FlushAll 行为一致).
func buildFlushAllCmd(clusterType string, cli *myredis.RedisClient) ([]string, error) {
	switch clusterType {
	case consts.TendisTypeTwemproxyRedisInstance, consts.TendisTypeRedisInstance:
		cmd := []string{consts.CacheFlushAllRename}
		if v, err := cli.GetTendisVersion(); err == nil && v != "" {
			majorStr := strings.SplitN(v, ".", 2)[0]
			if major, convErr := strconv.Atoi(majorStr); convErr == nil && major >= 4 {
				cmd = append(cmd, consts.ASYNC)
			}
		}
		return cmd, nil
	case consts.TendisTypeTwemproxyTendisSSDInstance:
		return []string{consts.SSDFlushAllRename}, nil
	default:
		return nil, fmt.Errorf("unsupported cluster_type(%s)", clusterType)
	}
}

func (job *RedisVersionUpdate) stopRedis(port int) (err error) {
	var password string
	password, err = myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return err
	}
	stopScript := filepath.Join(consts.UsrLocal, "redis", "bin", "stop-redis.sh")
	_, err = os.Stat(stopScript)
	if err != nil && os.IsNotExist(err) {
		job.runtime.Logger.Info("%s not exist", stopScript)
		return nil
	}
	// 先执行 stop-redis.sh 脚本,再检查端口是否还在使用
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\"",
		consts.MysqlAaccount, stopScript+" "+strconv.Itoa(port)+" xxxx"))
	_, err = util.RunLocalCmdReplacePkey("su",
		[]string{consts.MysqlAaccount, "-c", fmt.Sprintf("%s %d %q", stopScript, port, password)}, password,
		"", nil, 10*time.Minute)
	if err != nil && !strings.Contains(err.Error(), "Warning: Using a password") {
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
	var password string
	password, err = myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return err
	}
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
	cli, err := myredis.NewRedisClientWithTimeout(addr, password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil && strings.Contains(err.Error(), "LOADING Redis is loading") {
		job.runtime.Logger.Warn(fmt.Sprintf("redis:%s conn warn,err:%v", addr, err))
		err = nil
	}
	if err != nil {
		return err
	}
	job.AddrMapCli[addr] = cli
	job.runtime.Logger.Info("start redis instance(%s:%d) success", job.params.IP, port)

	if job.params.Role == consts.MetaRoleRedisMaster {
		return nil
	}
	// 多次检测直到 redis instance 成为 slave,且同步状态正常
	_, err = job.isReplStateOK(cli, 30*time.Minute)
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
