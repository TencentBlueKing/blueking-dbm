package atomredis

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

/*
	kill 掉长时间不活跃的链接 (包含可能的Dead connection)
	// 输入参数
	{
    "instances":[{"ip":"","port":""},],
		"idel_time":600,
		"cluster_type":"",
	}
*/

// KillDeadParam TODO
// SwitchParam cluster bind entry
type KillDeadParam struct {
	IgnoreKill   bool            `json:"ignore_kill"`
	Instances    []InstanceParam `json:"instances"`
	ConnIdleTime int             `json:"idle_time"`
	ClusterType  string          `json:"cluster_type"`
}

// RedisKillDeadConn entry
type RedisKillDeadConn struct {
	runtime *jobruntime.JobGenericRuntime
	params  *KillDeadParam
}

// NewRedisSceneKillDeadConn TODO
func NewRedisSceneKillDeadConn() jobruntime.JobRunner {
	return &RedisKillDeadConn{}
}

// Init 初始化
func (job *RedisKillDeadConn) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisKillDeadConn Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisKillDeadConn Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}

	return nil
}

// Run 运行干掉旧链接逻辑
func (job *RedisKillDeadConn) Run() (err error) {
	job.runtime.Logger.Info("kill dead conn start; params:%+v", job.params)

	for _, storage := range job.params.Instances {
		addr := fmt.Sprintf("%s:%d", storage.IP, storage.Port)
		pwd, err := myredis.GetRedisPasswdFromConfFile(storage.Port)
		if err != nil {
			job.runtime.Logger.Error("get redis pass from local failed,err %s:%v", addr, err)
			if job.params.IgnoreKill {
				return nil
			}
			return err
		}
		rconn, err := myredis.NewRedisClientWithTimeout(addr, pwd, 0, job.params.ClusterType, time.Second)
		if err != nil {
			job.runtime.Logger.Error("conn redis failed,err %s:%v", addr, err)
			if job.params.IgnoreKill {
				return nil
			}
			return fmt.Errorf("conn redis %s failed:%+v", addr, err)
		}
		defer rconn.Close()

		cs, err := rconn.DoCommand([]string{"Client", "List"}, 0)
		if err != nil {
			job.runtime.Logger.Error("do cmd failed ,err %s:%v", addr, err)
			if job.params.IgnoreKill {
				return nil
			}
			return fmt.Errorf("do cmd failed %s:%+v", addr, err)
		}
		var totalked int
		if clis, ok := cs.([]byte); ok {
			sx := []byte{}
			for _, cli := range clis {
				if cli != 10 { // byte(\n)==10 ASIC
					sx = append(sx, cli)
				} else {
					ws := strings.Split(string(sx), " ")
					if len(ws) > 1 && strings.HasPrefix(ws[1], "addr=") && !(strings.Contains(string(sx), "replconf")) {
						idleTime, _ := strconv.Atoi(strings.Split(ws[5], "=")[1])
						if idleTime >= job.params.ConnIdleTime {
							kcli := strings.Split(ws[1], "=")[1]
							_, err = rconn.DoCommand([]string{"Clinet", "Kill", kcli}, 0)
							job.runtime.Logger.Info("redis send %s:kill [%s] , rst:%+v", addr, sx, err)
							totalked++
						}
					}
					sx = []byte{}
				}
			}
		} else {
			job.runtime.Logger.Warn(fmt.Sprintf("client list assert failed %+s ,result not []string", addr))
		}
		job.runtime.Logger.Info("redis send %s:total killed [%d].", addr, totalked)
	}

	job.runtime.Logger.Info("kill dead conn all success ^_^")
	return nil
}

// Name 原子任务名
func (job *RedisKillDeadConn) Name() string {
	return "redis_kill_conn"
}

// Retry times
func (job *RedisKillDeadConn) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisKillDeadConn) Rollback() error {
	return nil
}
