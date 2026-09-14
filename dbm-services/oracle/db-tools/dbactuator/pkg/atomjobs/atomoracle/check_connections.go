package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// CheckConnectionsParams 检查长事务初始化参数
type CheckConnectionsParams struct {
}

// CheckConnections 检查长事务原子任务   oracle用户执行
type CheckConnections struct {
	BaseJob
	Params *CheckConnectionsParams `json:"extend"`
	CheckConnectionsRunTimeCtx
}

// CheckConnectionsRunTimeCtx 运行时上下文
type CheckConnectionsRunTimeCtx struct {
	Sessions []Session `json:"sessions"`
}

// NewCheckConnections new
func NewCheckConnections() jobruntime.JobRunner {
	return &CheckConnections{}
}

// Init 初始化
func (e *CheckConnections) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of InstallOracle fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of InstallOracle fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *CheckConnections) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of CheckConnections")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of CheckConnections fail, error:%s", err)
		return fmt.Errorf("validate parameters of CheckConnections fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *CheckConnections) Name() string {
	return "check-connections"
}

// Run 执行函数
func (e *CheckConnections) Run() error {
	e.Runtime.Logger.Info("start to check connections")
	sessions, err := querySessions(common.GetSessionsSql)
	if err != nil {
		e.Runtime.Logger.Error("check connections fail, error:%s", err)
		return fmt.Errorf("check connections fail, error:%s", err)
	}
	for _, session := range sessions {
		e.Runtime.Logger.Info("sid: %s, serial: %s, username: %s, machine: %s, last_call_et: %d, sql_id: %s",
			session.Sid, session.Serial, session.Username, session.Machine, session.LastCallEt, session.SqlId)
	}
	if len(sessions) > 0 {
		return fmt.Errorf("active sessions found: %s", common.GetSessionsSql)
	}
	e.Runtime.Logger.Info("check connections successfully")
	return nil
}

// Retry times
func (e *CheckConnections) Retry() uint {
	return 2
}

// Rollback rollback
func (e *CheckConnections) Rollback() error {
	return nil
}
