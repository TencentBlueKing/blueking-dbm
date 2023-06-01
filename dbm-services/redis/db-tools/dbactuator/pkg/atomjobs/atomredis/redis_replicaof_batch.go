package atomredis

import (
	"encoding/json"
	"fmt"

	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// ReplicaBatchItem 批量主从关系项
type ReplicaBatchItem struct {
	MasterIP        string `json:"master_ip" validate:"required"`
	MasterStartPort int    `json:"master_start_port" validate:"required"`
	MasterInstNum   int    `json:"master_inst_num" validate:"required"`
	MasterAuth      string `json:"master_auth" validate:"required"`
	SlaveIP         string `json:"slave_ip" validate:"required"`
	SlaveStartPort  int    `json:"slave_start_port" validate:"required"`
	SlaveInstNum    int    `json:"slave_inst_num" validate:"required"`
	SlavePassword   string `json:"slave_password" validate:"required"`
}

// ReplicaBatchParams 批量主从关系参数
type ReplicaBatchParams struct {
	BatchPairs []ReplicaBatchItem `json:"bacth_pairs" validate:"required"`
}

// RedisReplicaBatch redis(批量)主从关系 原子任务
type RedisReplicaBatch struct {
	runtime *jobruntime.JobGenericRuntime
	params  ReplicaBatchParams
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisReplicaBatch)(nil)

// NewRedisReplicaBatch new
func NewRedisReplicaBatch() jobruntime.JobRunner {
	return &RedisReplicaBatch{}
}

// Init 初始化,参数校验
func (job *RedisReplicaBatch) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisReplicaBatch Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisReplicaBatch Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
	}
	for _, item := range job.params.BatchPairs {
		if item.MasterInstNum != item.SlaveInstNum {
			err = fmt.Errorf("masterIP:%s slaveIP:%s master_inst_num(%d) <> slave_inst_num(%d)",
				item.MasterIP, item.SlaveIP, item.MasterInstNum, item.SlaveInstNum)
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	return nil
}

// Name 名字
func (job *RedisReplicaBatch) Name() string {
	return "redis_replica_batch"
}

// Run 执行
func (job *RedisReplicaBatch) Run() error {
	var tasks []*ReplicaTask
	var cnt int = 0
	var masterPort, slavePort int
	for _, item := range job.params.BatchPairs {
		cnt += item.MasterInstNum
	}
	tasks = make([]*ReplicaTask, 0, cnt)
	for _, item := range job.params.BatchPairs {
		for i := 0; i < item.MasterInstNum; i++ {
			masterPort = item.MasterStartPort + i
			slavePort = item.SlaveStartPort + i
			task := &ReplicaTask{
				ReplicaItem: ReplicaItem{
					MasterIP:      item.MasterIP,
					MasterPort:    masterPort,
					MasterAuth:    item.MasterAuth,
					SlaveIP:       item.SlaveIP,
					SlavePort:     slavePort,
					SlavePassword: item.SlavePassword,
				},
				runtime: job.runtime,
			}
			tasks = append(tasks, task)
		}
	}
	err := GroupRunReplicaTasksAndWait(tasks, job.runtime)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("all replicas ok")
	return nil
}

// Retry 返回可重试次数
func (job *RedisReplicaBatch) Retry() uint {
	return 2
}

// Rollback 回滚函数,一般不用实现
func (job *RedisReplicaBatch) Rollback() error {
	return nil
}
