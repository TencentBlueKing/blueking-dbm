package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// ReplicaItem 主从关系单项,每个项填写密码主要是因为 如果一次性操作多对 主从版, 主从版之间是密码并不相同
type ReplicaItem struct {
	MasterIP      string `json:"master_ip" validate:"required"`
	MasterPort    int    `json:"master_port" validate:"required"`
	MasterAuth    string `json:"master_auth" validate:"required"`
	SlaveIP       string `json:"slave_ip" validate:"required"`
	SlavePort     int    `json:"slave_port" validate:"required"`
	SlavePassword string `json:"slave_password" validate:"required"`
}

// MasterAddr masteraddr
func (item *ReplicaItem) MasterAddr() string {
	return item.MasterIP + ":" + strconv.Itoa(item.MasterPort)
}

// SlaveAddr slaveaddr
func (item *ReplicaItem) SlaveAddr() string {
	return item.SlaveIP + ":" + strconv.Itoa(item.SlavePort)
}

// RedisReplicaOfParams 建立主从关系 参数
type RedisReplicaOfParams struct {
	ReplicaPairs []ReplicaItem `json:"replica_pairs" validate:"required"`
}

// RedisReplicaOf redis主从关系 原子任务
type RedisReplicaOf struct {
	runtime *jobruntime.JobGenericRuntime
	params  RedisReplicaOfParams
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisReplicaOf)(nil)

// NewRedisReplicaOf new
func NewRedisReplicaOf() jobruntime.JobRunner {
	return &RedisReplicaOf{}
}

// Init 初始化,参数校验
func (job *RedisReplicaOf) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m

	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v\n", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("RedisReplicaOf Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisReplicaOf Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
	}
	return nil
}

// Name 名字
func (job *RedisReplicaOf) Name() string {
	return "redis_replicaof"
}

// Run 执行
func (job *RedisReplicaOf) Run() error {
	tasks := []*ReplicaTask{}
	for _, item := range job.params.ReplicaPairs {
		task := &ReplicaTask{
			ReplicaItem: item,
			runtime:     job.runtime,
		}
		tasks = append(tasks, task)
	}
	err := GroupRunReplicaTasksAndWait(tasks, job.runtime)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("all replicas ok")
	return nil
}

// Retry 返回可重试次数
func (job *RedisReplicaOf) Retry() uint {
	return 2
}

// Rollback 回滚函数,一般不用实现
func (job *RedisReplicaOf) Rollback() error {
	return nil
}

// ReplicaTask 建立主从关系task
type ReplicaTask struct {
	ReplicaItem
	MasterCli      *myredis.RedisClient `json:"-"`
	SlaveCli       *myredis.RedisClient `json:"-"`
	ClusterEnabled string               `json:"cluster_enabled"`
	// version信息
	SlaveVersion       string `json:"slave_version"`
	SlaveBaseVer       uint64 `json:"slave_base_ver"`
	SlaveSubVer        uint64 `json:"slave_sub_ver"`
	InfoReplRole       string `json:"info_repl_role"`
	InfoReplMasterHost string `json:"info_repl_master_host"`
	InfoReplMasterPort string `json:"info_repl_master_port"`
	InfoReplLinkStatus string `json:"info_repl_link_status"`
	DbType             string `json:"db_type"`
	runtime            *jobruntime.JobGenericRuntime
	Err                error `json:"-"`
}

// NewReplicaTask new replica task
func NewReplicaTask(masterIP string, masterPort int, masterAuth string, slaveIP string, slavePort int,
	slavePassword string, runtime *jobruntime.JobGenericRuntime) *ReplicaTask {
	return &ReplicaTask{
		ReplicaItem: ReplicaItem{
			MasterIP:      masterIP,
			MasterPort:    masterPort,
			MasterAuth:    masterAuth,
			SlaveIP:       slaveIP,
			SlavePort:     slavePort,
			SlavePassword: slavePassword,
		},
		runtime: runtime,
	}
}

// InfoReplMasterAddr 'info replication' master addr
func (task *ReplicaTask) InfoReplMasterAddr() string {
	return task.InfoReplMasterHost + ":" + task.InfoReplMasterPort
}

func (task *ReplicaTask) newConnects() {
	task.runtime.Logger.Info("begin to connect master:%s", task.MasterAddr())
	task.MasterCli, task.Err = myredis.NewRedisClientWithTimeout(task.MasterAddr(), task.MasterAuth,
		0, consts.TendisTypeRedisInstance, 5*time.Second)
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("begin to connect slave:%s", task.SlaveAddr())
	task.SlaveCli, task.Err = myredis.NewRedisClientWithTimeout(task.SlaveAddr(), task.SlavePassword,
		0, consts.TendisTypeRedisInstance, 5*time.Second)
	if task.Err != nil {
		return
	}
	var infoRet map[string]string
	infoRet, task.Err = task.SlaveCli.Info("server")
	if task.Err != nil {
		return
	}
	task.SlaveVersion = infoRet["redis_version"]
	task.SlaveBaseVer, task.SlaveSubVer, task.Err = util.VersionParse(task.SlaveVersion)
	if task.Err != nil {
		return
	}
	task.DbType, task.Err = task.SlaveCli.GetTendisType()
}
func (task *ReplicaTask) confirmClusterEnabled() {
	confData, err := task.SlaveCli.ConfigGet("cluster-enabled")
	if err != nil {
		task.Err = err
		return
	}
	defer task.runtime.Logger.Info("slave:%s cluster-enabled=%s",
		task.SlaveCli.Addr, task.ClusterEnabled)
	val, ok := confData["cluster-enabled"]
	if ok && strings.ToLower(val) == "yes" {
		task.ClusterEnabled = "yes"
		return
	}
	task.ClusterEnabled = "no"
}

func (task *ReplicaTask) getReplicaStatusData() {
	infoRet, err := task.SlaveCli.Info("replication")
	if err != nil {
		task.Err = err
		return
	}
	task.InfoReplRole = infoRet["role"]
	task.InfoReplMasterHost = infoRet["master_host"]
	task.InfoReplMasterPort = infoRet["master_port"]
	task.InfoReplLinkStatus = infoRet["master_link_status"]
}

// IsReplicaStatusOk 复制关系是否已ok
func (task *ReplicaTask) IsReplicaStatusOk() (status bool) {
	task.getReplicaStatusData()
	if task.Err != nil {
		return false
	}
	if task.InfoReplRole == consts.RedisSlaveRole {
		// I am a slave
		if task.InfoReplMasterHost == task.MasterIP &&
			task.InfoReplMasterPort == strconv.Itoa(task.MasterPort) &&
			task.InfoReplLinkStatus == consts.MasterLinkStatusUP {
			// 同步关系已ok
			return true
		}
		// slave角色,但其master信息不正确
		if task.InfoReplMasterHost != task.MasterIP || task.InfoReplMasterPort != strconv.Itoa(task.MasterPort) {
			task.Err = fmt.Errorf("slave(%s) current master %s,not %s",
				task.SlaveAddr(), task.InfoReplMasterAddr(), task.MasterAddr())
			task.runtime.Logger.Error(task.Err.Error())
			return
		}
		// slavejues,master信息正确,单link-status !=up
		return false
	}
	// I am a master
	dbsize, err := task.SlaveCli.DbSize()
	if err != nil {
		task.Err = err
		return
	}
	if dbsize > 20 {
		task.Err = fmt.Errorf("redis(%s) is a master,but has %d keys", task.SlaveAddr(), dbsize)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	return false
}

// CreateReplicaREL create replica relationship
func (task *ReplicaTask) CreateReplicaREL() {
	_, task.Err = task.MasterCli.ConfigSet("appendonly", "no")
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("master(%s) 'confxx set appendonly no' ok ", task.MasterAddr())

	_, task.Err = task.SlaveCli.ConfigSet("appendonly", "yes")
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("slave(%s) 'confxx set appendonly yes' ok ", task.SlaveAddr())

	_, task.Err = task.SlaveCli.ConfigSet("masterauth", task.MasterAuth)
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("slave(%s) 'confxx set masterauth xxx' ok ", task.SlaveAddr())

	if consts.IsRedisInstanceDbType(task.DbType) {
		_, task.Err = task.SlaveCli.ConfigSet("slave-read-only", "yes")
		if task.Err != nil {
			return
		}
		task.runtime.Logger.Info("slave(%s) 'confxx set slave-read-only yes' ok ", task.SlaveAddr())
	}

	if task.InfoReplRole == consts.RedisMasterRole {
		if task.ClusterEnabled == "no" {
			_, task.Err = task.SlaveCli.SlaveOf(task.MasterIP, strconv.Itoa(task.MasterPort))
			if task.Err != nil {
				return
			}
			task.runtime.Logger.Info("slave(%s) 'slaveof %s %d' ok ",
				task.SlaveAddr(), task.MasterIP, task.MasterPort)
		} else {
			// cluster-enabled=yes
			// 先获取masterID
			addrMap, err := task.SlaveCli.GetAddrMapToNodes()
			if err != nil {
				task.Err = err
				return
			}
			masterAddr := task.MasterAddr()
			masterNode, ok := addrMap[masterAddr]
			if !ok {
				task.Err = fmt.Errorf("redis(%s) cluster nodes result not found masterNode(%s)", task.SlaveAddr(), masterAddr)
				task.runtime.Logger.Error(task.Err.Error())
				return
			}
			if !myredis.IsRunningMaster(masterNode) {
				task.Err = fmt.Errorf("cluster nodes redis(%s) is not a running master,addr:%s", masterAddr, task.SlaveCli.Addr)
				task.runtime.Logger.Error(task.Err.Error())
				task.runtime.Logger.Info(masterNode.String())
				return
			}
			_, task.Err = task.SlaveCli.ClusterReplicate(masterNode.NodeID)
			if task.Err != nil {
				return
			}
			task.runtime.Logger.Info("slave(%s)  'cluster replicate %s' ok, master(%s)",
				task.SlaveAddr(), masterNode.NodeID, masterAddr)
		}
	}
	_, task.Err = task.MasterCli.ConfigRewrite()
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("master(%s) 'confxx rewrite' ok ", task.MasterAddr())

	_, task.Err = task.SlaveCli.ConfigRewrite()
	if task.Err != nil {
		return
	}
	task.runtime.Logger.Info("slave(%s) 'confxx rewrite' ok ", task.SlaveAddr())
}

// CreateReplicaAndWait slaveof and wait util status==up
func (task *ReplicaTask) CreateReplicaAndWait() {
	var msg string
	task.newConnects()
	if task.Err != nil {
		return
	}
	defer task.SlaveCli.Close()
	defer task.MasterCli.Close()

	task.confirmClusterEnabled()
	if task.Err != nil {
		return
	}
	status := task.IsReplicaStatusOk()
	if task.Err != nil {
		return
	}
	if status {
		msg = fmt.Sprintf("redis(%s) master(%s) master_link_status:%s,skip...",
			task.SlaveAddr(),
			task.InfoReplMasterAddr(),
			task.InfoReplLinkStatus)
		task.runtime.Logger.Info(msg)
		return
	}
	task.CreateReplicaREL()
	if task.Err != nil {
		return
	}
	maxRetryTimes := 720 // 1 hour timeout
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		task.getReplicaStatusData()
		if task.Err != nil {
			return
		}
		if task.InfoReplLinkStatus != consts.MasterLinkStatusUP {
			if maxRetryTimes%3 == 0 {
				// 半分钟输出一次日志
				msg = fmt.Sprintf("redis(%s) master_link_status:%s", task.SlaveAddr(), task.InfoReplLinkStatus)
				task.runtime.Logger.Info(msg)
			}
			time.Sleep(5 * time.Second)
			continue
		}
		break
	}
	if task.InfoReplLinkStatus != consts.MasterLinkStatusUP {
		task.Err = fmt.Errorf("redis(%s) master_link_status:%s", task.SlaveAddr(), task.InfoReplLinkStatus)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	msg = fmt.Sprintf("redis(%s) master(%s) master_link_status:%s",
		task.SlaveAddr(),
		task.InfoReplMasterAddr(),
		task.InfoReplLinkStatus)
	task.runtime.Logger.Info(msg)
	return
}

// GroupRunReplicaTasksAndWait 根据masterIP,分批执行赋值任务,不同master机器间并行,同一master实例间串行
func GroupRunReplicaTasksAndWait(tasks []*ReplicaTask, runtime *jobruntime.JobGenericRuntime) error {
	util.StopBkDbmon()
	defer util.StartBkDbmon()
	// 根据masterIP做分组
	tasksMapSlice := make(map[string][]*ReplicaTask)
	maxCount := 0
	for _, task01 := range tasks {
		task := task01
		tasksMapSlice[task.MasterIP] = append(tasksMapSlice[task.MasterIP], task)
		if len(tasksMapSlice[task.MasterIP]) > maxCount {
			maxCount = len(tasksMapSlice[task.MasterIP])
		}
	}
	// 同masterIP实例间串行,多masterIP实例间并行
	for idx := 0; idx < maxCount; idx++ {
		groupTasks := []*ReplicaTask{}
		for masterIP := range tasksMapSlice {
			if len(tasksMapSlice[masterIP]) > idx {
				groupTasks = append(groupTasks, tasksMapSlice[masterIP][idx])
			}
		}
		wg := sync.WaitGroup{}
		for _, taskItem := range groupTasks {
			task01 := taskItem
			wg.Add(1)
			go func(task02 *ReplicaTask) {
				defer wg.Done()
				task02.CreateReplicaAndWait()
			}(task01)
		}
		wg.Wait()
		for _, taskItem := range groupTasks {
			task01 := taskItem
			if task01.Err != nil {
				return task01.Err
			}
		}
	}
	return nil
}
