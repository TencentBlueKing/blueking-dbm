package atomredis

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

/*
	// 输入参数
	{
		"instances":[{"master":{"ip":"","port":},"slave":{"ip":"","port":}}],
		"cluster_type":"",
		"slave_master_diff_time":100,
		"last_io_second_ago":60,
	}
*/

// DoSyncParam TODO
// SyncParam
type DoSyncParam struct {
	Instances   []InstanceSwitchParam `json:"instances"`
	ClusterType string                `json:"cluster_type"`
	// "disk-delete-count", "maxmemory", "log-count", "log-keep-count"
	ParamList []string `json:"params"`
}

// RedisPramsSync tendis ssd 参数同步
type RedisPramsSync struct {
	runtime *jobruntime.JobGenericRuntime
	params  *DoSyncParam
}

// NewRedisSceneSyncPrams TODO
func NewRedisSceneSyncPrams() jobruntime.JobRunner {
	return &RedisPramsSync{}
}

// Init 初始化
func (job *RedisPramsSync) Init(m *jobruntime.JobGenericRuntime) error {
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
func (job *RedisPramsSync) Run() (err error) {
	job.runtime.Logger.Info("redisparamsync start; params:%+v", job.params)
	for _, pair := range job.params.Instances {
		addr1 := fmt.Sprintf("%s:%d", pair.MasterInfo.IP, pair.MasterInfo.Port)
		pwd, err := myredis.GetRedisPasswdFromConfFile(pair.MasterInfo.Port)
		if err != nil {
			job.runtime.Logger.Error("get redis pass from local failed,err %s:%v", addr1, err)
			return err
		}
		rc1, err := myredis.NewRedisClientWithTimeout(addr1, pwd, 0, job.params.ClusterType, time.Second)
		if err != nil {
			return fmt.Errorf("conn redis %s failed:%+v", addr1, err)
		}
		defer rc1.Close()

		addr2 := fmt.Sprintf("%s:%d", pair.SlaveInfo.IP, pair.SlaveInfo.Port)
		rc2, err := myredis.NewRedisClientWithTimeout(addr2, pwd, 0, job.params.ClusterType, time.Second)
		if err != nil {
			return fmt.Errorf("conn redis %s failed:%+v", addr2, err)
		}
		defer rc2.Close()

		for _, cc := range job.params.ParamList {
			v, err := rc1.DoCommand([]string{"Confxx", "GET", cc}, 0)
			if err != nil {
				job.runtime.Logger.Warn(fmt.Sprintf("get config value failed:%+v:%+v:%+v", addr1, cc, err))
				continue
			}
			if vv, ok := v.([]interface{}); ok && len(vv) == 2 {
				if _, err = rc2.DoCommand([]string{"Confxx", "SET", cc, fmt.Sprintf("%s", vv[1])}, 0); err != nil {
					job.runtime.Logger.Warn(fmt.Sprintf("set config value failed:%+v:%s:%+v", addr2, cc, err))
					continue
				}
				job.runtime.Logger.Info(fmt.Sprintf("sync config %s from %s to %s value:%s done",
					cc, addr1, addr2, fmt.Sprint(vv[1])))
			}
		}
	}
	job.runtime.Logger.Info("redisparamsync switch all success.")
	return nil
}

// Name 原子任务名
func (job *RedisPramsSync) Name() string {
	return "redis_param_sync"
}

// Retry times
func (job *RedisPramsSync) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisPramsSync) Rollback() error {
	return nil
}
