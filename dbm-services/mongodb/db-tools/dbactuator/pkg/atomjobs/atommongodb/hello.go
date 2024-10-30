package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"

	"github.com/pkg/errors"
)

// hello 总是返回成功. 用于测试流程

// helloParams 备份任务参数，由前端传入
type helloParams struct {
	IP            string `json:"ip"`
	Port          int    `json:"port"`
	AdminUsername string `json:"adminUsername"`
	AdminPassword string `json:"adminPassword"`
}

type helloJob struct {
	BaseJob
	ConfParams *helloParams
}

func (s *helloJob) Param() string {
	o, _ := json.MarshalIndent(backupParams{}, "", "\t")
	return string(o)
}

// NewHelloJob 实例化结构体
func NewHelloJob() jobruntime.JobRunner {
	return &helloJob{}
}

// Name 获取原子任务的名字
func (s *helloJob) Name() string {
	return "mongodb_hello"
}

// Run 运行原子任务
func (s *helloJob) Run() error {
	s.runtime.Logger.Info("Run")
	return nil
}

// Init 初始化
func (s *helloJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = "" // 备份进程，不再需要sudo，请以普通用户执行
	if checkIsRootUser() {
		s.runtime.Logger.Error("This job cannot be executed as root user")
		return errors.New("This job cannot be executed as root user")
	}
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}

	return nil
}
