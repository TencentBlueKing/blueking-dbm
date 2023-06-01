package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// ClusterReplicaItem 集群主从关系对
type ClusterReplicaItem struct {
	MasterIP   string `json:"master_ip" validate:"required"`
	MasterPort int    `json:"master_port" validate:"required"`
	SlaveIP    string `json:"slave_ip"` // 不是所有 master都需要slave
	SlavePort  int    `json:"slave_port"`
	// 如 0-4095 6000 6002-60010, 如果为空,则不进行cluster addslots
	Slots string `json:"slots"`
}

// MasterAddr masteraddr
func (item *ClusterReplicaItem) MasterAddr() string {
	return item.MasterIP + ":" + strconv.Itoa(item.MasterPort)
}

// SlaveAddr slaveaddr
func (item *ClusterReplicaItem) SlaveAddr() string {
	return item.SlaveIP + ":" + strconv.Itoa(item.SlavePort)
}

// ClusterMeetSlotsAssignParams 集群关系建立和slots分配
type ClusterMeetSlotsAssignParams struct {
	Password        string               `json:"password"`          // 如果password为空,则自动从本地获取
	UseForExpansion bool                 `json:"use_for_expansion"` // 是否用于扩容，true ：是用于扩容
	SlotsAutoAssgin bool                 `json:"slots_auto_assign"` // slots 自动分配
	ReplicaPairs    []ClusterReplicaItem `json:"replica_pairs"`
}

// ClusterMeetSlotsAssign 节点加入集群,建立主从关系,分配slots
type ClusterMeetSlotsAssign struct {
	runtime    *jobruntime.JobGenericRuntime
	params     ClusterMeetSlotsAssignParams
	AddrMapCli map[string]*myredis.RedisClient `json:"addr_map_cli"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ClusterMeetSlotsAssign)(nil)

// NewClusterMeetSlotsAssign new
func NewClusterMeetSlotsAssign() jobruntime.JobRunner {
	return &ClusterMeetSlotsAssign{}
}

// Init 初始化与参数校验
func (job *ClusterMeetSlotsAssign) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisClusterMeetSlotsAssign Init params validate failed,err:%v,params:%+v", err,
				job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisClusterMeetSlotsAssign Init params validate failed,err:%v,params:%+v", err,
				job.params)
			return err
		}
	}
	if job.params.SlotsAutoAssgin {
		for _, pair := range job.params.ReplicaPairs {
			if pair.Slots != "" {
				err = fmt.Errorf("SlotsAutoAssgin=%v 和 redis(%s) slots:%s 不能同时指定",
					job.params.SlotsAutoAssgin, pair.MasterAddr(), pair.Slots)
				job.runtime.Logger.Error(err.Error())
				return err
			}
		}
	}
	job.AddrMapCli = make(map[string]*myredis.RedisClient)
	job.runtime.Logger.Info("RedisClusterMeetSlotsAssign init success")
	return nil
}

// Name 原子任务名称
func (job *ClusterMeetSlotsAssign) Name() string {
	return "clustermeet_slotsassign"
}

// Run 执行
func (job *ClusterMeetSlotsAssign) Run() (err error) {
	var ok bool
	err = job.allInstsAbleToConnect()
	if err != nil {
		return
	}
	defer job.allInstDisconnect()

	err = job.AddInstsToCluster()
	if err != nil {
		return
	}
	err = job.SlotsBelongToWho()
	if err != nil {
		return
	}
	err = job.AddSlots()
	if err != nil {
		return
	}
	err = job.CreateReplicas()
	if err != nil {
		return
	}
	maxRetryTimes := 60 // 等待两分钟,等待集群状态ok
	i := 0
	for {
		i++
		for i > maxRetryTimes {
			break
		}
		ok, err = job.IsClusterStateOK()
		if err != nil {
			return
		}
		if !ok {
			job.runtime.Logger.Info("redisCluster(%s) cluster_state not ok,sleep 2s and retry...",
				job.params.ReplicaPairs[0].MasterAddr())
			time.Sleep(2 * time.Second)
			continue
		}
		break
	}
	if !ok {
		err = fmt.Errorf("wait 120s,redisCluster(%s) cluster_state still not ok", job.params.ReplicaPairs[0].MasterAddr())
		job.runtime.Logger.Error(err.Error())
		return
	}
	return nil
}

// allInstsAbleToConnect 检查所有实例可连接
func (job *ClusterMeetSlotsAssign) allInstsAbleToConnect() (err error) {
	instsAddrs := []string{}
	for _, item := range job.params.ReplicaPairs {
		instsAddrs = append(instsAddrs, item.MasterAddr())
		if item.SlaveIP == "" {
			continue
		}
		instsAddrs = append(instsAddrs, item.SlaveAddr())
	}
	for _, addr01 := range instsAddrs {
		cli, err := myredis.NewRedisClient(addr01, job.params.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			return err
		}
		job.AddrMapCli[addr01] = cli
	}
	job.runtime.Logger.Info("all redis instances able to connect,(%+v)", instsAddrs)
	return nil
}

// AddInstsToCluster 添加实例到集群中
func (job *ClusterMeetSlotsAssign) AddInstsToCluster() (err error) {
	firstAddr := job.params.ReplicaPairs[0].MasterAddr()
	firstIP := job.params.ReplicaPairs[0].MasterIP
	firstPort := job.params.ReplicaPairs[0].MasterPort
	firstCli := job.AddrMapCli[firstAddr]
	addrMap, err := firstCli.GetAddrMapToNodes()
	if err != nil {
		return
	}
	for add01, cli := range job.AddrMapCli {
		if add01 == firstAddr {
			continue
		}
		node01, ok := addrMap[add01]
		if ok && myredis.IsRunningNode(node01) {
			continue
		}
		_, err = cli.ClusterMeet(firstIP, strconv.Itoa(firstPort))
		if err != nil {
			return
		}
	}
	time.Sleep(10 * time.Second)
	job.runtime.Logger.Info("all redis instances add to cluster")
	return nil
}

// CreateReplicas 建立主从关系
func (job *ClusterMeetSlotsAssign) CreateReplicas() (err error) {
	tasks := []*ReplicaTask{}
	for _, item := range job.params.ReplicaPairs {
		if item.SlaveIP == "" {
			continue
		}
		task01 := NewReplicaTask(item.MasterIP, item.MasterPort, job.params.Password,
			item.SlaveIP, item.SlavePort, job.params.Password, job.runtime)
		tasks = append(tasks, task01)
	}
	err = GroupRunReplicaTasksAndWait(tasks, job.runtime)
	if err != nil {
		return
	}
	job.runtime.Logger.Info("all replicas ok")
	return nil
}

// SlotsBelongToWho 确认slots属于哪个节点(只在创建新集群后,调用该函数自动均衡分配slots)
// 用户也可以在上层指定slots应该如何归属,而不由 dbactuator 来分配
func (job *ClusterMeetSlotsAssign) SlotsBelongToWho() (err error) {
	if !job.params.SlotsAutoAssgin {
		return nil
	}
	firstAddr := job.params.ReplicaPairs[0].MasterAddr()
	firstCli := job.AddrMapCli[firstAddr]
	clusterInfo, err := firstCli.ClusterInfo()
	if err != nil {
		return err
	}
	if clusterInfo.ClusterState == consts.ClusterStateOK {
		// 集群已经是ok状态,跳过cluster addslot步骤
		job.runtime.Logger.Info("redisCluster:%s cluaster_state:%s, skip slotsAsssign ...", firstAddr,
			clusterInfo.ClusterState)
		return
	}
	masterCnt := len(job.params.ReplicaPairs)
	perMasterSlotsCnt := (consts.DefaultMaxSlots + 1) / masterCnt
	leftSlotCnt := (consts.DefaultMaxSlots + 1) % masterCnt

	stepCnt := perMasterSlotsCnt
	if leftSlotCnt > 0 {
		// 不能整除的情况,前面的节点每个多分配一个slot
		stepCnt++
	}
	var start, end int
	for idx := 0; idx < masterCnt; idx++ {
		start = idx * stepCnt
		end = (idx+1)*stepCnt - 1
		if start > consts.DefaultMaxSlots {
			break
		}
		if end > consts.DefaultMaxSlots {
			end = consts.DefaultMaxSlots
		}
		job.params.ReplicaPairs[idx].Slots = fmt.Sprintf("%d-%d", start, end)

	}
	return nil
}

// AddSlots 每个节点添加slots
func (job *ClusterMeetSlotsAssign) AddSlots() (err error) {
	var slots []int
	var selfNode *myredis.ClusterNodeData = nil
	for _, pair := range job.params.ReplicaPairs {
		if strings.TrimSpace(pair.Slots) == "" {
			continue
		}
		slots, _, _, _, err = myredis.DecodeSlotsFromStr(pair.Slots, " ")
		if err != nil {
			return
		}
		if len(slots) == 0 {
			continue
		}
		masterCli := job.AddrMapCli[pair.MasterAddr()]
		selfNode, err = masterCli.GetMyself()
		if err != nil {
			return err
		}
		// 找出redis Node中目前缺少的slots
		diffSlots := myredis.SlotSliceDiff(selfNode.Slots, slots)
		if len(diffSlots) == 0 {
			job.runtime.Logger.Info("redis_master(%s) slots(%s) is ok,skip addslots ...",
				pair.MasterAddr(), myredis.ConvertSlotToStr(selfNode.Slots))
			continue
		}
		_, err = masterCli.ClusterAddSlots(diffSlots)
		if err != nil {
			return err
		}
		job.runtime.Logger.Info("redis_master(%s) addslots(%s) ok", pair.MasterAddr(), myredis.ConvertSlotToStr(diffSlots))
	}
	return nil
}

// IsClusterStateOK 集群状态是否ok
func (job *ClusterMeetSlotsAssign) IsClusterStateOK() (ok bool, err error) {
	// 如果用于扩容，则不检查cluster state 直接返回true
	if job.params.UseForExpansion {
		return true, nil
	}
	firstAddr := job.params.ReplicaPairs[0].MasterAddr()
	firstCli := job.AddrMapCli[firstAddr]
	clusterInfo, err := firstCli.ClusterInfo()
	if err != nil {
		return false, err
	}
	if clusterInfo.ClusterState == consts.ClusterStateOK {
		return true, nil
	}
	return false, nil
}

// allInstDisconnect 所有实例断开连接
func (job *ClusterMeetSlotsAssign) allInstDisconnect() {
	for _, cli := range job.AddrMapCli {
		cli.Close()
	}
}

// Retry 返回可重试次数
func (job *ClusterMeetSlotsAssign) Retry() uint {
	return 2
}

// Rollback 回滚函数,一般不用实现
func (job *ClusterMeetSlotsAssign) Rollback() error {
	return nil
}
