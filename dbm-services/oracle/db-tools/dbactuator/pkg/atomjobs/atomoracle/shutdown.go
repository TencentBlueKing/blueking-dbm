package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// ShutdownParams 执行脚本初始化参数
type ShutdownParams struct {
}

// Shutdown 执行脚本原子任务   oracle用户执行
type Shutdown struct {
	BaseJob
	Params             *ShutdownParams
	ShutdownRunTimeCtx `json:"-"`
}

// ShutdownRunTimeCtx 运行时上下文
type ShutdownRunTimeCtx struct {
}

// NewShutdown new
func NewShutdown() jobruntime.JobRunner {
	return &Shutdown{}
}

// Init 初始化
func (e *Shutdown) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of Shutdown fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of Shutdown fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *Shutdown) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of Shutdown")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of Shutdown fail, error:%s", err)
		return fmt.Errorf("validate parameters of Shutdown fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *Shutdown) Name() string {
	return "shutdown"
}

// Run 执行函数
func (e *Shutdown) Run() error {
	e.Runtime.Logger.Info("start to shutdown listener")
	err := ShutdownListener()
	if err != nil {
		e.Runtime.Logger.Info("shutdown listener fail, skipped: %v", err)
	}
	isRunning, err := CheckListenerStatus()
	if err != nil {
		e.Runtime.Logger.Error("check listener status fail: %s", err)
		return err
	} else if isRunning {
		e.Runtime.Logger.Info("listener is running")
		return fmt.Errorf("listener is running, please check and shutdown listener manually")
	}
	e.Runtime.Logger.Info("shutdown listener success")

	e.Runtime.Logger.Info("start to shutdown instance")
	err = ShutdownInstance(false)
	if err != nil {
		e.Runtime.Logger.Error("shutdown instance fail: %s", err)
		return err
	}
	e.Runtime.Logger.Info("shutdown instance success")
	return nil

}

// ShutdownInstance 关闭实例
// 注意：shutdown immediate / shutdown abort 是 SQL*Plus 客户端命令，无法通过 OCI/godror 下发，
// 必须借助 `sqlplus / as sysdba` 执行，否则会返回 ORA-00900: invalid SQL statement。
func ShutdownInstance(force bool) error {
	shutdownSQL := consts.ShutdownImmediate
	err := common.ExecuteSqlplusAsSysdba(shutdownSQL)
	if err == nil {
		return nil
	}
	if !force {
		return fmt.Errorf("failed to execute shutdown command: %s error: %v", shutdownSQL, err)
	}
	shutdownSQL = consts.ShutdownAbort
	err = common.ExecuteSqlplusAsSysdba(shutdownSQL)
	if err != nil {
		return fmt.Errorf("failed to execute shutdown command: %s error: %v", shutdownSQL, err)
	}
	return nil
}
