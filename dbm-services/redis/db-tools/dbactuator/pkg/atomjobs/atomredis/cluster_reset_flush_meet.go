package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"sync"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

// ClusterResetFlushMeetItem cluster reset flush meet item
type ClusterResetFlushMeetItem struct {
	ResetIP            string `json:"reset_ip" validate:"required"`
	ResetPort          int    `json:"reset_port" validate:"required"`
	ResetRedisPassword string `json:"reset_redis_password" validate:"required"`
	MeetIP             string `json:"meet_ip" validate:"required"`
	MeetPort           int    `json:"meet_port" validate:"required"`
	DoFlushall         bool   `json:"do_flushall"`     // 是否执行flushall
	DoClusterMeet      bool   `json:"do_cluster_meet"` // 是否执行cluster meet
}

// ResetRedisAddr reset redis addr
func (item *ClusterResetFlushMeetItem) ResetRedisAddr() string {
	return fmt.Sprintf("%s:%d", item.ResetIP, item.ResetPort)
}

// ClusterResetFlushMeetParams 参数
type ClusterResetFlushMeetParams struct {
	ResetFlushMeetParams []ClusterResetFlushMeetItem `json:"reset_flush_meet_params" validate:"required"`
}

// ClusterResetFlushMeet TODO
type ClusterResetFlushMeet struct {
	runtime *jobruntime.JobGenericRuntime
	params  ClusterResetFlushMeetParams
	tasks   []*clusterResetFlushMeetTask
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ClusterResetFlushMeet)(nil)

// NewClusterResetFlushMeet new
func NewClusterResetFlushMeet() jobruntime.JobRunner {
	return &ClusterResetFlushMeet{}
}

// Init 初始化,参数校验
func (job *ClusterResetFlushMeet) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("ClusterResetFlushMeet Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ClusterResetFlushMeet Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
	}
	return nil
}

// Name 名字
func (job *ClusterResetFlushMeet) Name() string {
	return "redis_cluster_reset_flush_meet"
}

// Run 执行
func (job *ClusterResetFlushMeet) Run() (err error) {
	job.tasks = make([]*clusterResetFlushMeetTask, 0, len(job.params.ResetFlushMeetParams))
	for _, item := range job.params.ResetFlushMeetParams {
		task := &clusterResetFlushMeetTask{
			ClusterResetFlushMeetItem: item,
			runtime:                   job.runtime,
		}
		job.tasks = append(job.tasks, task)
	}
	err = job.allInstCconnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()

	for _, tmp := range job.tasks {
		task := tmp
		task.resetAndFlushallAndMeet()
		if task.Err != nil {
			return task.Err
		}
	}
	return nil
}

func (job *ClusterResetFlushMeet) allInstCconnect() (err error) {
	wg := sync.WaitGroup{}
	// 并发确认所有实例是否可连接
	for _, tmp := range job.tasks {
		task := tmp
		wg.Add(1)
		go func(task *clusterResetFlushMeetTask) {
			defer wg.Done()
			task.createResetConn()
		}(task)
	}
	wg.Wait()
	for _, tmp := range job.tasks {
		task := tmp
		if task.Err != nil {
			return task.Err
		}
	}
	return nil
}

// allInstDisconnect 所有实例断开连接
func (job *ClusterResetFlushMeet) allInstDisconnect() {
	for _, tmp := range job.tasks {
		task := tmp
		if task.resetRedisConn != nil {
			task.resetRedisConn.Close()
			task.resetRedisConn = nil
		}
	}
}

// Retry 返回可重试次数
func (job *ClusterResetFlushMeet) Retry() uint {
	return 2
}

// Rollback 回滚函数,一般不用实现
func (job *ClusterResetFlushMeet) Rollback() error {
	return nil
}

// clusterResetFlushMeetTask task,为了做并发连接,单独定义一个struct
type clusterResetFlushMeetTask struct {
	ClusterResetFlushMeetItem
	resetRedisConn *myredis.RedisClient
	runtime        *jobruntime.JobGenericRuntime
	Err            error
}

// createResetConn 创建连接
func (task *clusterResetFlushMeetTask) createResetConn() {
	task.resetRedisConn, task.Err = myredis.NewRedisClientWithTimeout(task.ResetRedisAddr(), task.ResetRedisPassword, 0,
		consts.TendisTypeRedisInstance, 10*time.Hour)
}

// resetAndFlushallAndMeet cluster reset并flushall并meet
func (task *clusterResetFlushMeetTask) resetAndFlushallAndMeet() {
	var role string
	var clustreInfo *myredis.CmdClusterInfo
	var addrToNodes map[string]*myredis.ClusterNodeData
	// 先执行cluster reset
	task.runtime.Logger.Info(fmt.Sprintf("redis %s cluster reset start", task.ResetRedisAddr()))
	task.Err = task.resetRedisConn.ClusterReset()
	if task.Err != nil {
		return
	}
	for {
		role, _ = task.resetRedisConn.GetRole()
		clustreInfo, _ = task.resetRedisConn.ClusterInfo()
		if role == consts.RedisMasterRole && clustreInfo.ClusterState != consts.ClusterStateOK {
			task.runtime.Logger.Info(fmt.Sprintf("redis %s cluster reset success,current_role:%s cluster_state:%s",
				task.ResetRedisAddr(), role, clustreInfo.ClusterState))
			break
		}
		task.runtime.Logger.Info(fmt.Sprintf("redis %s cluster reset done,but current_role:%s cluster_state:%s",
			task.ResetRedisAddr(), role, clustreInfo.ClusterState))
		time.Sleep(3 * time.Second)
	}
	if task.DoFlushall {
		// 执行flushall
		task.runtime.Logger.Info(fmt.Sprintf("redis %s flushall start", task.ResetRedisAddr()))
		cmd := []string{consts.TendisPlusFlushAllRename} // cache 和 tendisplus的 flushall 命令一样
		_, task.Err = task.resetRedisConn.DoCommand(cmd, 0)
		if task.Err != nil {
			return
		}
	}
	if task.DoClusterMeet {
		// 执行cluster meet
		task.runtime.Logger.Info(fmt.Sprintf("redis %s 'cluster meet %s %d' start",
			task.ResetRedisAddr(), task.MeetIP, task.MeetPort))
		_, task.Err = task.resetRedisConn.ClusterMeet(task.MeetIP, strconv.Itoa(task.MeetPort))
		if task.Err != nil {
			return
		}
		for {
			addrToNodes, task.Err = task.resetRedisConn.GetAddrMapToNodes()
			if task.Err != nil {
				return
			}
			if _, ok := addrToNodes[task.ResetRedisAddr()]; ok {
				task.runtime.Logger.Info(fmt.Sprintf("redis %s 'cluster meet %s %d' success",
					task.ResetRedisAddr(), task.MeetIP, task.MeetPort))
				break
			}
			task.runtime.Logger.Info(fmt.Sprintf("redis %s 'cluster meet %s %d' done,but not in 'cluster nodes'",
				task.ResetRedisAddr(), task.MeetIP, task.MeetPort))
			time.Sleep(3 * time.Second)
		}
	}
}
