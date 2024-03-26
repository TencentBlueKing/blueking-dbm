package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

type instItem struct {
	IP   string `json:"ip" validate:"required"`
	Port int    `json:"port" validate:"required"`
}

// Addr TODO
func (item instItem) Addr() string {
	return fmt.Sprintf("%s:%d", item.IP, item.Port)
}

type masterSlavePair struct {
	Master instItem `json:"master" validate:"required"`
	Slave  instItem `json:"slave" validate:"required"`
}

// RedisClusterFailoverParam redis cluster failover param
type RedisClusterFailoverParam struct {
	RedisPassword         string            `json:"redis_password" validate:"required"`
	RedisMasterSlavePairs []masterSlavePair `json:"redis_master_slave_pairs" validate:"required"` // {"master_ip:master_port","slave_ip:slave_port"}
	// 如果是强制failover,则不检查集群状态是否ok,不检查所有slave的link状态是否ok,failover时加上force 参数,failover后也不检查new_slave(old_master)同步是否跟上
	Force bool `json:"force"`
}

// RedisClusterFailover redis cluster failover
type RedisClusterFailover struct {
	runtime *jobruntime.JobGenericRuntime
	params  RedisClusterFailoverParam
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisClusterFailover)(nil)

// NewRedisClusterFailover new
func NewRedisClusterFailover() jobruntime.JobRunner {
	return &RedisClusterFailover{}
}

// Init 初始化
func (job *RedisClusterFailover) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisClusterFailover Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisClusterFailover Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisClusterFailover) Name() string {
	return "redis_cluster_failover"
}

// Run Command 执行
func (job *RedisClusterFailover) Run() (err error) {
	if job.params.Force {
		err = job.checkAllSlaveConnected()
		if err != nil {
			return
		}
		err = job.checkAllRedisInCluster()
		if err != nil {
			return
		}
		err = job.allClusterMastersConfSetMasterauth()
		if err != nil {
			return
		}
	} else {
		err = job.checkAllRedisConnected()
		if err != nil {
			return
		}
		err = job.checkClusterStatus()
		if err != nil {
			return
		}
		err = job.checkAllRedisInCluster()
		if err != nil {
			return
		}
		err = job.checkAllSlaveLinkStatus()
		if err != nil {
			return
		}
		err = job.allClusterMastersConfSetMasterauth()
		if err != nil {
			return
		}
	}
	err = job.groupRunFailoverAndWaitReplicateStateOk()
	if err != nil {
		return
	}
	return nil
}

func (job *RedisClusterFailover) checkAllRedisConnected() (err error) {
	allRedisAddr := make([]string, 0, len(job.params.RedisMasterSlavePairs)*2)
	for _, ms := range job.params.RedisMasterSlavePairs {
		allRedisAddr = append(allRedisAddr, ms.Master.Addr(), ms.Slave.Addr())
	}
	err = myredis.CheckMultiRedisConnected(allRedisAddr, job.params.RedisPassword)
	if err != nil {
		job.runtime.Logger.Error("checkAllRedisConnected failed,err:%v", err)
		return
	}
	job.runtime.Logger.Info("checkAllRedisConnected success")
	return nil
}

// checkAllSlaveConnected 检查所有 slave 是否可连接
func (job *RedisClusterFailover) checkAllSlaveConnected() (err error) {
	allSlaveAddr := make([]string, 0, len(job.params.RedisMasterSlavePairs))
	for _, ms := range job.params.RedisMasterSlavePairs {
		allSlaveAddr = append(allSlaveAddr, ms.Slave.Addr())
	}
	err = myredis.CheckMultiRedisConnected(allSlaveAddr, job.params.RedisPassword)
	if err != nil {
		job.runtime.Logger.Error("checkAllSlaveConnected failed,err:%v", err)
		return
	}
	job.runtime.Logger.Info("checkAllSlaveConnected success")
	return nil
}

// checkClusterStatus 连接第一个 master,检查集群状态是否 ok
func (job *RedisClusterFailover) checkClusterStatus() (err error) {
	firstMasterAddr := ""
	for _, ms := range job.params.RedisMasterSlavePairs {
		firstMasterAddr = ms.Master.Addr()
		break
	}
	rc, err := myredis.NewRedisClientWithTimeout(firstMasterAddr, job.params.RedisPassword, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return
	}
	defer rc.Close()
	clusterStatus, err := rc.ClusterInfo()
	if err != nil {
		return
	}
	if clusterStatus.ClusterState != consts.ClusterStateOK {
		err = fmt.Errorf("cluster state not ok,clusterState:%s", clusterStatus.ClusterState)
		job.runtime.Logger.Error("checkClusterStatus failed,err:%v", err)
		return
	}
	job.runtime.Logger.Info("checkClusterStatus success")
	return nil
}

// checkAllRedisInCluster 连接第一个 slave,获取cluster nodes 信息,确保所有redis节点都在集群中
func (job *RedisClusterFailover) checkAllRedisInCluster() (err error) {
	firstSlaveAddr := ""
	for _, ms := range job.params.RedisMasterSlavePairs {
		firstSlaveAddr = ms.Slave.Addr()
		break
	}
	rc, err := myredis.NewRedisClientWithTimeout(firstSlaveAddr, job.params.RedisPassword, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return
	}
	defer rc.Close()
	addrToClusterNode, err := rc.GetAddrMapToNodes()
	if err != nil {
		return
	}
	for _, ms := range job.params.RedisMasterSlavePairs {
		if _, ok := addrToClusterNode[ms.Master.Addr()]; !ok {
			err = fmt.Errorf("redis node:%s not in cluster,firstMasterAddr:%s", ms.Master.Addr(), firstSlaveAddr)
			job.runtime.Logger.Error("checkAllRedisInCluster failed,err:%v", err)
			return
		}
		if _, ok := addrToClusterNode[ms.Slave.Addr()]; !ok {
			err = fmt.Errorf("redis node:%s not in cluster,firstMasterAddr:%s", ms.Slave.Addr(), firstSlaveAddr)
			job.runtime.Logger.Error("checkAllRedisInCluster failed,err:%v", err)
			return
		}
	}
	job.runtime.Logger.Info("checkAllRedisInCluster success")
	return nil
}

// allClusterMastersConfSetMasterauth 集群masters执行config set masterauth + config rewrite
func (job *RedisClusterFailover) allClusterMastersConfSetMasterauth() (err error) {
	firstSlaveAddr := ""
	for _, ms := range job.params.RedisMasterSlavePairs {
		firstSlaveAddr = ms.Slave.Addr()
		break
	}
	rc, err := myredis.NewRedisClientWithTimeout(firstSlaveAddr, job.params.RedisPassword, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return
	}
	defer rc.Close()
	_, err = rc.RedisClusterConfigSetOnlyMasters("masterauth", job.params.RedisPassword)
	if err != nil {
		return
	}
	_, err = rc.RedisClusterMastersRunCmd([]string{"confxx", "rewrite"})
	if err != nil {
		return
	}
	job.runtime.Logger.Info("allClusterMastersConfSetMasterauth success")
	return nil
}

// checkAllSlaveLinkStatus 连接所有redis slave,
// 根据 info replication 获取其role 信息,
// 如果role 是 slave,则获取其 master addr,
// 确保其 master addr 与 job.params.RedisMasterSlavePair 中的 master addr 一致,
// 如果一致则继续检查master_link_status==up、master_last_binlog_seconds_ago<10 ,不一致报错;
// 如果 role 是 master,则获取其 slave 列表,
// 如果job.params.RedisMasterSlavePair 中的 master addr 在 slave 列表中,
// 则代表已经 cluster failover过了,否则报错;
func (job *RedisClusterFailover) checkAllSlaveLinkStatus() (err error) {
	var replMasterHost, replMasterPort, replMasterAddr, replLinkStatus string
	var masterLastIOSecAgo int
	for _, ms := range job.params.RedisMasterSlavePairs {
		rc, err := myredis.NewRedisClientWithTimeout(ms.Slave.Addr(), job.params.RedisPassword, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if err != nil {
			return err
		}
		defer rc.Close()
		infoRepl, err := rc.Info("replication")
		if err != nil {
			return err
		}
		if infoRepl["role"] == consts.RedisSlaveRole {
			replMasterHost = infoRepl["master_host"]
			replMasterPort = infoRepl["master_port"]
			replLinkStatus = infoRepl["master_link_status"]
			replMasterAddr = fmt.Sprintf("%s:%s", replMasterHost, replMasterPort)
			if replMasterAddr != ms.Master.Addr() {
				err = fmt.Errorf("slave:%s master addr:%s not equal to master addr:%s", ms.Slave.Addr(),
					replMasterAddr, ms.Master.Addr())
				job.runtime.Logger.Error("checkAllSlaveLinkStatus failed,err:%v", err)
				return err
			}
			if replLinkStatus != consts.MasterLinkStatusUP {
				err = fmt.Errorf("slave:%s master link status:%s not equal to up", ms.Slave.Addr(), replLinkStatus)
				job.runtime.Logger.Error("checkAllSlaveLinkStatus failed,err:%v", err)
				return err
			}
			masterLastIOSecAgo, err = strconv.Atoi(infoRepl["master_last_io_seconds_ago"])
			if err != nil {
				err = fmt.Errorf("slave:%s master last io seconds ago:%s convert to int failed,err:%v",
					ms.Slave.Addr(), infoRepl["master_last_io_seconds_ago"], err)
				job.runtime.Logger.Error("checkAllSlaveLinkStatus failed,err:%v", err)
				return err
			}
			if masterLastIOSecAgo > 10 {
				err = fmt.Errorf("slave:%s master last binlog seconds ago:%d greater than 10", ms.Slave.Addr(), masterLastIOSecAgo)
				job.runtime.Logger.Error("checkAllSlaveLinkStatus failed,err:%v", err)
				return err
			}
		} else if infoRepl["role"] == consts.RedisMasterRole {
			_, slaveMap, err := rc.GetInfoReplSlaves()
			if err != nil {
				return err
			}
			if _, ok := slaveMap[ms.Master.Addr()]; !ok {
				err = fmt.Errorf("old_slave:%s now is master,but old_master not in new_slaves:[%s]",
					ms.Slave.Addr(), util.ToString(slaveMap))
				job.runtime.Logger.Error("checkAllSlaveLinkStatus failed,err:%v", err)
				return err
			}
		} else {
			err = fmt.Errorf("redis node:%s role:%s not equal to slave or master", ms.Slave.Addr(), infoRepl["role"])
			job.runtime.Logger.Error("checkAllSlaveLinkStatus failed,err:%v", err)
			return err
		}
	}
	job.runtime.Logger.Info("checkAllSlaveLinkStatus success")
	return nil
}

// groupRunFailoverAndWaitReplicateStateOk 按照 slave_ip 分组,
// 生成多个 redisFailOverTask保存在 groupTasks=map[string][]*redisFailOverTask中,同时记录下slave_ip对应tasks 的最大数量
// 例如:groupTasks=map[string][]*redisFailOverTask{"slave_ip1":[task1,task2],"slave_ip2":[task3,task4,task5]}
// 利用 groupTasks,实现相同 slave_ip 上 tasks 串行执行,多个 slave_ip 上 tasks 并行执行
func (job *RedisClusterFailover) groupRunFailoverAndWaitReplicateStateOk() (err error) {
	var slaveIP string
	groupTasks := make(map[string][]*redisFailOverTask)
	maxTaskCount := 0
	for _, ms := range job.params.RedisMasterSlavePairs {
		slaveIP, _, err = util.AddrToIpPort(ms.Slave.Addr())
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		if _, ok := groupTasks[slaveIP]; !ok {
			groupTasks[slaveIP] = []*redisFailOverTask{}
		}
		task := &redisFailOverTask{
			MasterAddr:    ms.Master.Addr(),
			SlaveAddr:     ms.Slave.Addr(),
			RedisPassword: job.params.RedisPassword,
			Force:         job.params.Force,
		}
		groupTasks[slaveIP] = append(groupTasks[slaveIP], task)
		if len(groupTasks[slaveIP]) > maxTaskCount {
			maxTaskCount = len(groupTasks[slaveIP])
		}
	}
	job.runtime.Logger.Info("groupTasks:%+v,maxTaskCount:%d", groupTasks, maxTaskCount)
	for i := 0; i < maxTaskCount; i++ {
		currTasks := []*redisFailOverTask{}
		for slaveIP := range groupTasks {
			if len(groupTasks[slaveIP]) > i {
				currTasks = append(currTasks, groupTasks[slaveIP][i])
			}
		}
		// 串行执行 cluster failover
		for _, task := range currTasks {
			taskItem := task
			taskItem.RunFailOverAndWaitDone()
			if taskItem.Err != nil {
				return taskItem.Err
			}
		}
		// 并行执行 waitReplicateStateOK
		wg := sync.WaitGroup{}
		for _, task := range currTasks {
			taskItem := task
			wg.Add(1)
			go func(item *redisFailOverTask) {
				defer wg.Done()
				item.WaitReplicateStateOK()
			}(taskItem)
		}
		wg.Wait()
		for _, task := range currTasks {
			taskItem := task
			if taskItem.Err != nil {
				return taskItem.Err
			}
		}
	}
	job.runtime.Logger.Info("groupRunFailoverAndWaitReplicateStateOk success")
	return nil
}

// Retry times
func (job *RedisClusterFailover) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisClusterFailover) Rollback() error {
	return nil
}

type redisFailOverTask struct {
	MasterAddr    string `json:"master_addr"`
	SlaveAddr     string `json:"slave_addr"`
	RedisPassword string `json:"redis_password"`
	Force         bool   `json:"force"`
	slaveCli      *myredis.RedisClient
	Err           error `json:"err"`
}

// newSlaveCli 新建slaveCli
func (task *redisFailOverTask) newSlaveCli() {
	task.slaveCli, task.Err = myredis.NewRedisClientWithTimeout(task.SlaveAddr, task.RedisPassword, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
}

// isFailOverDone 是否fail over 完成,如果slave 已经是 master,且master 已经是'它'的slave,则认为fail over 完成
func (task *redisFailOverTask) isFailOverDone() (done bool) {
	infoRepl, err := task.slaveCli.Info("replication")
	if err != nil {
		return
	}
	var slaveMap map[string]*myredis.InfoReplSlave
	if infoRepl["role"] == consts.RedisMasterRole {
		if task.Force {
			// 如果是强制 failover,则不检查old_master 是否变成了 new_slave
			done = true
			return
		}
		_, slaveMap, task.Err = task.slaveCli.GetInfoReplSlaves()
		if task.Err != nil {
			return
		}
		if _, ok := slaveMap[task.MasterAddr]; ok {
			done = true
			return
		}
	}
	return done
}

// RunFailOver slave 上 s执行 cluster failover
func (task *redisFailOverTask) RunFailOver() {
	if task.Force {
		task.Err = task.slaveCli.ClusterFailOver("takeover")
	} else {
		task.Err = task.slaveCli.ClusterFailOver("")
	}
	if task.Err != nil {
		return
	}
	return
}

// RunFailOverAndWaitDone 执行 cluster failover后,直到slave 成为 master,且master 成为 slave
// 最大等待 60s,每隔 2s 检查一次,每隔10秒打印一次日志,如果超时,则报错
func (task *redisFailOverTask) RunFailOverAndWaitDone() {
	task.newSlaveCli()
	if task.Err != nil {
		return
	}
	defer task.slaveCli.Close()
	done := task.isFailOverDone()
	if done {
		mylog.Logger.Info("slave:%s is already master,do nothing", task.SlaveAddr)
		return
	}
	task.RunFailOver()
	if task.Err != nil {
		return
	}
	for i := 0; i < 30; i++ {
		time.Sleep(2 * time.Second)
		done = task.isFailOverDone()
		if done {
			mylog.Logger.Info("slave:%s is already master,'cluster failover' success", task.SlaveAddr)
			return
		}
		if i%5 == 0 {
			mylog.Logger.Info("waitFailOverDone slave:%s not become master,wait 2s", task.SlaveAddr)
		}
	}
	task.Err = fmt.Errorf("waitFailOverDone slave:%s not become master,wait 60s timeout", task.SlaveAddr)
	mylog.Logger.Error(task.Err.Error())
	return
}

// WaitReplicateStateOK 等待master 成为 slave,'它'的master_host:master_port 等于 SlaveAddr,且 master_link_status为up
// 最大等待 2h,每隔 2s 检查一次,每隔30秒打印一次日志,如果超时,则报错;
func (task *redisFailOverTask) WaitReplicateStateOK() {
	if task.Force {
		mylog.Logger.Info(fmt.Sprintf("force failover,not wait old_master:%s replicate state ok", task.MasterAddr))
		return
	}
	task.newSlaveCli()
	if task.Err != nil {
		return
	}
	defer task.slaveCli.Close()
	var masterCli *myredis.RedisClient
	var logTailNData string
	masterCli, task.Err = myredis.NewRedisClientWithTimeout(task.MasterAddr, task.RedisPassword, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if task.Err != nil {
		return
	}
	defer masterCli.Close()
	for i := 0; i < 3600; i++ {
		time.Sleep(2 * time.Second)
		infoRepl, err := masterCli.Info("replication")
		if err != nil {
			task.Err = err
			return
		}
		if infoRepl["role"] == consts.RedisSlaveRole {
			currMasterAddr := fmt.Sprintf("%s:%s", infoRepl["master_host"], infoRepl["master_port"])
			if currMasterAddr == task.SlaveAddr && infoRepl["master_link_status"] == consts.MasterLinkStatusUP {
				mylog.Logger.Info("master:%s become a slave of slave:%s and master_link_status==up",
					task.MasterAddr, task.SlaveAddr)
				masterCli.ConfigRewrite()
				return
			}
		}
		if i%15 == 0 {
			mylog.Logger.Info("waitReplicateStateOK master:%s not become slave of slave:%s and master_link_status:%s,wait 30s",
				task.MasterAddr, task.SlaveAddr, infoRepl["master_link_status"])
		}
		logTailNData, err = masterCli.TailRedisLogFile(40)
		if err != nil {
			task.Err = err
			return
		}
		if strings.Contains(logTailNData, "Can't handle RDB format") {
			// RDB格式不兼容,忽略
			slaveVer, _ := task.slaveCli.GetTendisVersion()
			masterVer, _ := masterCli.GetTendisVersion()
			msg := fmt.Sprintf("redis_master(%s) redis_version:%s redis_slave(%s) redis_version:%s RDB format not compatible",
				masterCli.Addr, masterVer, task.SlaveAddr, slaveVer)
			mylog.Logger.Warn(msg)
			return
		}
	}
	task.Err = fmt.Errorf("waitReplicateStateOK master:%s not become slave of slave:%s,wait 2h timeout",
		task.MasterAddr, task.SlaveAddr)
	mylog.Logger.Error(task.Err.Error())
	return
}
