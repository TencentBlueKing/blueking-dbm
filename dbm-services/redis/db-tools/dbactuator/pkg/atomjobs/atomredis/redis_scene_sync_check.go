package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

/*
	针对 故障本地修复场景而生
		1. 全部/部分 实例可能已经挂了
		2.
	{
		"instances":[{"ip":"","port":}],
		"watch_seconds":600,
		"cluster_type":"",
		"last_io_second_ago":60,
	}
*/

// CheckSyncParam TODO
type CheckSyncParam struct {
	Instances                []InstanceParam `json:"instances"`
	ClusterType              string          `json:"cluster_type"`
	MaxSlaveLastIOSecondsAgo int             `json:"last_io_second_ago"` // slave io线程最大时间
	WatchSeconds             int             `json:"watch_seconds"`
}

// RedisSyncCheck entry
type RedisSyncCheck struct {
	runtime *jobruntime.JobGenericRuntime
	params  *CheckSyncParam
}

// NewRedisSceneSyncCheck TODO
func NewRedisSceneSyncCheck() jobruntime.JobRunner {
	return &RedisSyncCheck{}
}

// Init 初始化
func (job *RedisSyncCheck) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("redissynccheck Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("redissynccheck Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Run TODO
func (job *RedisSyncCheck) Run() (err error) {
	for i := 0; i < job.params.WatchSeconds; i++ {
		var statusNk int
		for _, ins := range job.params.Instances {
			if err := job.checkReplication(ins); err != nil {
				job.runtime.Logger.Warn("instance %d:[%+v] replication sames tobe not ok -_-", i, ins)
				statusNk++
			}
		}

		if statusNk == 0 {
			job.runtime.Logger.Info("all instances replication sames tobe ok ^_^")
			break
		}
		job.runtime.Logger.Info("%d:(%d) instances replication sames tobe not ok -_-, waiting", i, statusNk)
		time.Sleep(time.Second)
	}
	return nil
}

// Name 原子任务名
func (job *RedisSyncCheck) Name() string {
	return "redis_sync_check"
}

// Retry times
func (job *RedisSyncCheck) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisSyncCheck) Rollback() error {
	return nil
}

// checkReplication TODO
func (job *RedisSyncCheck) checkReplication(ins InstanceParam) error {
	addr := fmt.Sprintf("%s:%d", ins.IP, ins.Port)
	pwd, err := myredis.GetRedisPasswdFromConfFile(ins.Port)
	if err != nil {
		job.runtime.Logger.Error("get redis pass from local failed,err %s:%v", addr, err)
		return err
	}
	rc1, err := myredis.NewRedisClientWithTimeout(addr, pwd, 0, job.params.ClusterType, time.Second)
	if err != nil {
		return fmt.Errorf("conn redis %s failed:%+v", addr, err)
	}
	defer rc1.Close()

	rep, err := rc1.Info("Replication")
	if err != nil {
		job.runtime.Logger.Error("get replication info faeild %s:%v", addr, err)
	}
	// 	port:30000 master_link_status:up
	// port:30000 master_last_io_seconds_ago:1
	last_io_second_ago, _ := strconv.Atoi(rep["master_last_io_seconds_ago"])
	linkstatus := rep["master_link_status"]
	if linkstatus == "up" && last_io_second_ago < job.params.MaxSlaveLastIOSecondsAgo {
		job.runtime.Logger.Info("%s:link_status:%s,last_io_seconds:%d", addr, linkstatus, last_io_second_ago)
		return nil
	}

	return fmt.Errorf("%s:linkStatus:%s,lastIO:%d", addr, linkstatus, last_io_second_ago)
}
