package atomredis

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"fmt"
)

// RedisDtsDataRepair dts数据修复
type RedisDtsDataRepair struct {
	*RedisDtsDataCheck
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisDtsDataRepair)(nil)

// NewRedisDtsDataRepair 创建dts数据修复实例
func NewRedisDtsDataRepair() jobruntime.JobRunner {
	dataCheck := &RedisDtsDataCheck{}
	return &RedisDtsDataRepair{dataCheck}
}

// Init 初始化
func (job *RedisDtsDataRepair) Init(m *jobruntime.JobGenericRuntime) error {
	job.Name() // 这一步是必须的
	return job.RedisDtsDataCheck.Init(m)
}

// Name 原子任务名
func (job *RedisDtsDataRepair) Name() string {
	if job.atomJobName == "" {
		job.atomJobName = "redis_dts_datarepair"
	}
	return job.atomJobName
}

// Run 运行
func (job *RedisDtsDataRepair) Run() (err error) {
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
	// 3. 并发修复,并发度默认2,可通过参数concurrency传入,运行中可通过并发度控制文件动态调整
	taskList, err := job.runTasksWithDynamicConcurrency(func(task *RedisInsDtsDataCheckAndRepairTask) {
		task.RunDataRepair()
	})
	if err != nil {
		return err
	}

	var totalHotKeysCnt uint64 = 0
	for _, tmp := range taskList {
		task := tmp
		if task.Err != nil {
			return task.Err
		}
		totalHotKeysCnt += task.HotKeysCnt
	}
	if totalHotKeysCnt > 0 {
		err = fmt.Errorf("RedisDtsDataRepair totalHotKeysCnt:%d", totalHotKeysCnt)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.runtime.Logger.Info("RedisDtsDataRepair success totalHotKeysCnt:%d", totalHotKeysCnt)
	return
}
