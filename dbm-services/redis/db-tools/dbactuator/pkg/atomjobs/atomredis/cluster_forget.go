package atomredis

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

/*
	RedisCluster Forget
	1. 支持 slave 节点forget
	2. 支持 master节点但未分配slots 信息

	// 输入参数
	{
    "cluster_meta":{
        "immute_domain":"xx.db",
        "cluster_type":"xxx",
				"RedisMasterSet":[],
				"StoragePassword":"",
    },
    "forget_list":[
        {
            "ip":"1.1.a.1",
            "port":30000,
        }
    ],
}
*/
// ClusterForgetParam  参数说明
type ClusterForgetParam struct { // NOCC:golint/structcomment(检查工具误报)
	ClusterMeta ClusterInfo     `json:"cluster_meta" validate:"required"`
	ForgetList  []InstanceParam `json:"forget_list" validate:"required"`
}

// RedisClusterForget entry
type RedisClusterForget struct {
	runtime *jobruntime.JobGenericRuntime
	params  *ClusterForgetParam
}

// NewRedisClusterForget 新建入口
func NewRedisClusterForget() jobruntime.JobRunner {
	return &RedisClusterForget{}
}

// Init 初始化
func (job *RedisClusterForget) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("ClusterRedoDR Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ClusterRedoDR Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if !consts.IsClusterDbType(job.params.ClusterMeta.ClusterType) {
		job.runtime.Logger.Error("cluster:%s:%s unsupport forget command,",
			job.params.ClusterMeta.ImmuteDomain, job.params.ClusterMeta.ClusterType)
		return fmt.Errorf("ErrUnSupportForget4:%s", job.params.ClusterMeta.ClusterType)
	}
	return nil
}

// Run 执行入口
func (job *RedisClusterForget) Run() (err error) {
	job.runtime.Logger.Info("clusterforget start; params:%+v", job.params)

	clusterNodes, err := job.tryGetClusterNodesInfo()
	if err != nil {
		return
	}

	for _, node := range job.params.ForgetList {
		forgetAddr := fmt.Sprintf("%s:%d", node.IP, node.Port)
		if _, ok := clusterNodes[forgetAddr]; !ok {
			job.runtime.Logger.Info("cluster does not exist node %s:%s",
				job.params.ClusterMeta.ImmuteDomain, forgetAddr)
			continue
		}

		// 允许 master with no slot || slave
		forgetDetail := clusterNodes[forgetAddr]
		if forgetDetail.Role == consts.RedisMasterRole {
			if forgetDetail.SlotSrcStr != "" {
				job.runtime.Logger.Error("err try forget node:{%s} role is master , but has slot asigned {%s}",
					forgetAddr, forgetDetail.SlotSrcStr)
				return fmt.Errorf("ErrNotAllowedMasterWithSlot:{%s}{%s}", forgetAddr, forgetDetail.SlotSrcStr)
			}
		}
		job.runtime.Logger.Info("try 2 forget node:%s role:%s,cluster's detail :%+v",
			forgetAddr, forgetDetail.Role, forgetDetail)

		if err := job.clusterForgetNode(clusterNodes, forgetDetail); err != nil {
			return err
		}
	}

	if currNodes, err := job.tryGetClusterNodesInfo(); err != nil {
		job.runtime.PipeContextData = currNodes
		return err
	}
	job.runtime.Logger.Info("cluster forget nodes succ ^_^; domain:%s", job.params.ClusterMeta.ImmuteDomain)
	return nil
}

// tryGetClusterNodesInfo 遍历传入的所有节点，尝试建立集群链接并获取集群节点
func (job *RedisClusterForget) tryGetClusterNodesInfo() (
	clusterNodes map[string]*myredis.ClusterNodeData, err error) {
	for idx, nodeAddr := range job.params.ClusterMeta.RedisMasterSet {
		var clusterConn *myredis.RedisClient
		job.runtime.Logger.Info("try make connect use %s:%s", job.params.ClusterMeta.ImmuteDomain, nodeAddr)

		clusterConn, err = myredis.NewRedisClientWithTimeout(nodeAddr,
			job.params.ClusterMeta.StoragePassword, 0, job.params.ClusterMeta.ClusterType, time.Second)
		if err != nil {
			job.runtime.Logger.Error("connect cluster node [%d]:%s failed:%+v", idx, nodeAddr, err)
			continue
		}
		defer clusterConn.Close()

		clusterNodes, err = clusterConn.GetAddrMapToNodes()
		if err != nil {
			job.runtime.Logger.Error("get cluster nodes use [%d] addr:%s failed:%+v", idx, nodeAddr, err)
		}

		for _, node := range clusterNodes {
			job.runtime.Logger.Info("current cluster node : %+v", node)
		}
		return
	}
	return nil, fmt.Errorf("can't connection cluster :%+v", err)
}

// clusterForgetNode 为了将节点从群集中彻底删除，必须将 CLUSTER FORGET 命令发送到所有其余节点，无论他们是Master/Slave。
// 不允许命令执行的特殊条件, 并在以下情况下返回错误：
// 1. 节点表中找不到指定的节点标识。
// 2. 接收命令的节点是从属节点，并且指定的节点ID标识其当前主节点。
// 3. 节点 ID 标识了我们发送命令的同一个节点。

// clusterForgetNode 返回值
// 简单的字符串回复：OK如果命令执行成功，否则返回错误。
// 我们有一个60秒的窗口来,所以这个函数必须在60s内执行完成
func (job *RedisClusterForget) clusterForgetNode(
	clusterNodes map[string]*myredis.ClusterNodeData, fnode *myredis.ClusterNodeData) error {
	beforeStart := time.Now().Unix()
	for _, node := range clusterNodes {
		if node.NodeID == fnode.NodeID {
			continue
		}
		job.runtime.Logger.Info("exec {cluster forget %s:%s} from [%s]", fnode.Addr, fnode.NodeID, node.Addr)
		var ignoreErr bool
		if len(node.FailStatus) != 0 {
			ignoreErr = true
			job.runtime.Logger.Warn("exec forget node maybe fail,will ignore err,%s:%+v", node.Addr, node.FailStatus)
		}

		nodeConn, err := myredis.NewRedisClientWithTimeout(node.Addr,
			job.params.ClusterMeta.StoragePassword, 0, job.params.ClusterMeta.ClusterType, time.Second)
		if err != nil {
			if ignoreErr {
				job.runtime.Logger.Warn("current node status maybe fail, ignore %s:%+v", node.Addr, err)
				continue
			}
			return err
		}
		defer nodeConn.Close()

		if err := nodeConn.ClusterForget(fnode.NodeID); err != nil {
			job.runtime.Logger.Error("forget node %s:%s failed :+%v", fnode.Addr, fnode.NodeID, err)
			if ignoreErr {
				job.runtime.Logger.Warn("current node status maybe fail, ignore %s:%+v", node.Addr, err)
				continue
			}
			return fmt.Errorf("ErrForgetNode:%s:%+v", fnode.Addr, err)
		}
	}
	forgetUseSeconds := time.Now().Unix() - beforeStart
	job.runtime.Logger.Info("exec cluster forget use %d seconds", forgetUseSeconds)
	return nil
}

// Name 原子任务名
func (job *RedisClusterForget) Name() string {
	return "redis_cluster_forget"
}

// Retry times
func (job *RedisClusterForget) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisClusterForget) Rollback() error {
	return nil
}
