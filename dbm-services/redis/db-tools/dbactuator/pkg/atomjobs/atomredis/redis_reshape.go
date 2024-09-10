package atomredis

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

// RedisReshapeParam redis reshape param
type RedisReshapeParam struct {
	RedisPassword string     `json:"redis_password" validate:"required"`
	Instances     []instItem `json:"instances" validate:"required"`
}

// reshapeTaskItem reshape task item,便于做并发
type reshapeTaskItem struct {
	instItem
	Password  string `json:"password"`
	redisConn *myredis.RedisClient
	Err       error
}

// RedisReshape redis shape
type RedisReshape struct {
	runtime      *jobruntime.JobGenericRuntime
	params       RedisReshapeParam
	ReshapeTasks []*reshapeTaskItem
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisReshape)(nil)

// NewRedisReshape new
func NewRedisReshape() jobruntime.JobRunner {
	return &RedisReshape{}
}

// Init 初始化
func (job *RedisReshape) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisReshape Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisReshape Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisReshape) Name() string {
	return "redis_reshape"
}

// Run Command Run
func (job *RedisReshape) Run() (err error) {
	job.ReshapeTasks = make([]*reshapeTaskItem, 0, len(job.params.Instances))
	for _, instItem := range job.params.Instances {
		reshapeTask := &reshapeTaskItem{
			instItem: instItem,
			Password: job.params.RedisPassword,
		}
		job.ReshapeTasks = append(job.ReshapeTasks, reshapeTask)
	}
	err = job.allInstCconnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()

	err = job.ReshapeAndWaitDone()
	if err != nil {
		return err
	}
	return nil
}

func (job *RedisReshape) allInstCconnect() (err error) {
	wg := sync.WaitGroup{}
	// 并发建立连接
	for _, tmp := range job.ReshapeTasks {
		task := tmp
		wg.Add(1)
		go func(task *reshapeTaskItem) {
			defer wg.Done()
			task.redisConn, task.Err = myredis.NewRedisClientWithTimeout(task.Addr(), task.Password, 0,
				consts.TendisTypeRedisInstance, 10*time.Hour)
		}(task)
	}
	wg.Wait()
	for _, tmp := range job.ReshapeTasks {
		task := tmp
		if task.Err != nil {
			return task.Err
		}
	}
	return nil
}

// allInstDisconnect 所有实例断开连接
func (job *RedisReshape) allInstDisconnect() {
	for _, tmp := range job.ReshapeTasks {
		task := tmp
		if task.redisConn != nil {
			task.redisConn.Close()
			task.redisConn = nil
		}
	}
}

// ReshapeAndWaitDone 多实例并发执行reshape
func (job *RedisReshape) ReshapeAndWaitDone() error {
	// 根据salveIP做分组
	tasksMapSlice := make(map[string][]*reshapeTaskItem)
	maxCount := 0
	for _, tmp := range job.ReshapeTasks {
		task := tmp
		tasksMapSlice[task.IP] = append(tasksMapSlice[task.IP], task)
		if len(tasksMapSlice[task.IP]) > maxCount {
			maxCount = len(tasksMapSlice[task.IP])
		}
	}
	// 同IP实例间串行,多IP实例间并行
	for idx := 0; idx < maxCount; idx++ {
		groupTasks := []*reshapeTaskItem{}
		for ip := range tasksMapSlice {
			if len(tasksMapSlice[ip]) > idx {
				groupTasks = append(groupTasks, tasksMapSlice[ip][idx])
			}
		}
		wg := sync.WaitGroup{}
		for _, taskItem := range groupTasks {
			task01 := taskItem
			wg.Add(1)
			go func(task02 *reshapeTaskItem) {
				defer wg.Done()
				job.runtime.Logger.Info("tendisplus %s start reshape", task02.Addr())
				task02.Err = task02.redisConn.TendisReshapeAndWaitDone()
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

// Retry times
func (job *RedisReshape) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisReshape) Rollback() error {
	return nil
}
