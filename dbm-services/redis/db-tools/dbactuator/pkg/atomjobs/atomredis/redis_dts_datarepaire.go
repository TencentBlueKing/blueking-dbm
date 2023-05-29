package atomredis

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"fmt"
	"sync"

	"github.com/panjf2000/ants/v2"
)

// RedisDtsDataRepaire dts数据修复
type RedisDtsDataRepaire struct {
	*RedisDtsDataCheck
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisDtsDataRepaire)(nil)

// NewRedisDtsDataRepaire 创建dts数据修复实例
func NewRedisDtsDataRepaire() jobruntime.JobRunner {
	dataCheck := &RedisDtsDataCheck{}
	return &RedisDtsDataRepaire{dataCheck}
}

// Init 初始化
func (job *RedisDtsDataRepaire) Init(m *jobruntime.JobGenericRuntime) error {
	job.Name() // 这一步是必须的
	return job.RedisDtsDataCheck.Init(m)
}

// Name 原子任务名
func (job *RedisDtsDataRepaire) Name() string {
	if job.atomJobName == "" {
		job.atomJobName = "redis_dts_datarepaire"
	}
	return job.atomJobName
}

// Run 运行
func (job *RedisDtsDataRepaire) Run() (err error) {
	// 1. 测试redis是否可连接
	err = job.TestConnectable()
	if err != nil {
		return
	}
	// 2. 获取工具
	err = job.GetTools()
	if err != nil {
		return
	}
	// 3. 并发提取与校验,并发度5
	var wg sync.WaitGroup
	taskList := make([]*RedisInsDtsDataCheckAndRepairTask, 0, len(job.params.SrcRedisPortSegmentList))
	pool, err := ants.NewPoolWithFunc(5, func(i interface{}) {
		defer wg.Done()
		task := i.(*RedisInsDtsDataCheckAndRepairTask)
		task.RunDataRepaire()
	})
	if err != nil {
		job.runtime.Logger.Error("RedisDtsDataRepaire Run NewPoolWithFunc failed,err:%v", err)
		return err
	}
	defer pool.Release()

	for _, portItem := range job.params.SrcRedisPortSegmentList {
		wg.Add(1)
		task, err := NewRedisInsDtsDataCheckAndRepaireTask(job.params.SrcRedisIP, portItem, job.RedisDtsDataCheck)
		if err != nil {
			continue
		}
		taskList = append(taskList, task)
		_ = pool.Invoke(task)
	}
	// 等待所有task执行完毕
	wg.Wait()

	var totalHotKeysCnt uint64 = 0
	for _, tmp := range taskList {
		task := tmp
		if task.Err != nil {
			return task.Err
		}
		totalHotKeysCnt += task.HotKeysCnt
	}
	if totalHotKeysCnt > 0 {
		err = fmt.Errorf("RedisDtsDataRepaire totalHotKeysCnt:%d", totalHotKeysCnt)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.runtime.Logger.Info("RedisDtsDataRepaire success totalHotKeysCnt:%d", totalHotKeysCnt)
	return
}
