package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"

	"github.com/go-playground/validator/v10"
)

// ClusterNodesItem redis 节点信息
type ClusterNodesItem struct {
	MasterIP   string `json:"master_ip" validate:"required"`
	MasterPort int    `json:"master_port" validate:"required"`
}

// MasterAddr masteraddr
func (item *ClusterNodesItem) MasterAddr() string {
	return item.MasterIP + ":" + strconv.Itoa(item.MasterPort)
}

// ClusterMeetCheckFinishParams 恢复回档后的集群关系和检查集群状态是否恢复，到这一步前面的回档子任务都全部成功了
type ClusterMeetCheckFinishParams struct {
	Password string `json:"password"` // 如果password为空,则自动从本地获取
	//集群节点信息
	ReplicaPairs []ClusterNodesItem `json:"replica_pairs"`
}

// ClusterMeetCheckFinish 恢复回档时的集群关系和检查集群状态是否恢复
type ClusterMeetCheckFinish struct {
	runtime    *jobruntime.JobGenericRuntime
	params     ClusterMeetCheckFinishParams
	AddrMapCli map[string]*myredis.RedisClient `json:"addr_map_cli"`
	Err        error                           `json:"-"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ClusterMeetCheckFinish)(nil)

// NewClusterMeetCheckFinish  new
func NewClusterMeetCheckFinish() jobruntime.JobRunner {
	return &ClusterMeetCheckFinish{}
}

// Name 原子任务名
func (task *ClusterMeetCheckFinish) Name() string {
	return "clustermeet_checkfinish"
}

// Retry times
func (task *ClusterMeetCheckFinish) Retry() uint {
	return 2
}

// Rollback rollback
func (task *ClusterMeetCheckFinish) Rollback() error {
	return nil

}

// Init 初始化
func (task *ClusterMeetCheckFinish) Init(m *jobruntime.JobGenericRuntime) error {
	task.runtime = m
	err := json.Unmarshal([]byte(task.runtime.PayloadDecoded), &task.params)
	if err != nil {
		task.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(task.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			task.runtime.Logger.Error("ClusterMeetCheckFinish Init params validate failed,err:%v,params:%+v",
				err, task.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			task.runtime.Logger.Error("ClusterMeetCheckFinish Init params validate failed,err:%v,params:%+v",
				err, task.params)
			return err
		}
	}
	task.AddrMapCli = make(map[string]*myredis.RedisClient)
	task.runtime.Logger.Info("ClusterMeetCheckFinish init success")
	return nil
}

// Run 执行
func (task *ClusterMeetCheckFinish) Run() (err error) {
	err = task.allInstsAbleToConnect()
	if err != nil {
		return
	}
	defer task.allInstDisconnect()

	err = task.AddInstsToCluster()
	if err != nil {
		return
	}
	var ok bool
	maxRetryTimes := 60 // 等待两分钟,等待集群状态ok
	i := 0
	for {
		i++
		for i > maxRetryTimes {
			break
		}
		ok, err = task.IsClusterStateOK()
		if err != nil {
			return
		}
		if !ok {
			task.runtime.Logger.Info("redisCluster(%s) cluster_state not ok,sleep 2s and retry...",
				task.params.ReplicaPairs[0].MasterAddr())
			time.Sleep(2 * time.Second)
			continue
		}
		break
	}
	if !ok {
		err = fmt.Errorf("wait 120s,redisCluster(%s) cluster_state still not ok", task.params.ReplicaPairs[0].MasterAddr())
		task.runtime.Logger.Error(err.Error())
		return
	}

	return nil
}

// allInstsAbleToConnect 检查所有实例可连接
func (task *ClusterMeetCheckFinish) allInstsAbleToConnect() (err error) {
	instsAddrs := []string{}
	for _, item := range task.params.ReplicaPairs {
		instsAddrs = append(instsAddrs, item.MasterAddr())
	}
	for _, addr01 := range instsAddrs {
		cli, err := myredis.NewRedisClient(addr01, task.params.Password, 0, consts.TendisTypeTendisplusInsance)
		if err != nil {
			return err
		}
		task.AddrMapCli[addr01] = cli
	}
	task.runtime.Logger.Info("all tendisplus instances able to connect,(%+v)", instsAddrs)
	return nil
}

// allInstDisconnect 所有实例断开连接
func (task *ClusterMeetCheckFinish) allInstDisconnect() {
	for _, cli := range task.AddrMapCli {
		cli.Close()
	}
}

// AddInstsToCluster 添加实例到集群中
func (task *ClusterMeetCheckFinish) AddInstsToCluster() (err error) {
	firstAddr := task.params.ReplicaPairs[0].MasterAddr()
	firstIP := task.params.ReplicaPairs[0].MasterIP
	firstPort := task.params.ReplicaPairs[0].MasterPort
	firstCli := task.AddrMapCli[firstAddr]
	addrMap, err := firstCli.GetAddrMapToNodes()
	if err != nil {
		return
	}
	for add01, cli := range task.AddrMapCli {
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
	task.runtime.Logger.Info("all tendisplus instances add to cluster")
	return nil
}

// IsClusterStateOK 集群状态是否ok
func (task *ClusterMeetCheckFinish) IsClusterStateOK() (ok bool, err error) {

	firstAddr := task.params.ReplicaPairs[0].MasterAddr()
	firstCli := task.AddrMapCli[firstAddr]
	clusterInfo, err := firstCli.ClusterInfo()
	if err != nil {
		return false, err
	}
	if clusterInfo.ClusterState == consts.ClusterStateOK {
		return true, nil
	}
	return false, nil
}
