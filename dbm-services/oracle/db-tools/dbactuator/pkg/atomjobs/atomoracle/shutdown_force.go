package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// ShutdownForceParams 执行脚本初始化参数
type ShutdownForceParams struct {
}

// ShutdownForce 执行脚本原子任务   oracle用户执行
type ShutdownForce struct {
	BaseJob
	Params                  *ShutdownForceParams
	ShutdownForceRunTimeCtx `json:"-"`
}

// ShutdownForceRunTimeCtx 运行时上下文
type ShutdownForceRunTimeCtx struct {
}

// NewShutdownForce new
func NewShutdownForce() jobruntime.JobRunner {
	return &ShutdownForce{}
}

// Init 初始化
func (e *ShutdownForce) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of ShutdownForce fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of ShutdownForce fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *ShutdownForce) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of ShutdownForce")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of ShutdownForce fail, error:%s", err)
		return fmt.Errorf("validate parameters of ShutdownForce fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *ShutdownForce) Name() string {
	return "shutdown-force"
}

// Run 执行函数
func (e *ShutdownForce) Run() error {
	// 关闭监听
	e.Runtime.Logger.Info("start to shutdown listener")
	err := ShutdownListener()
	if err != nil {
		e.Runtime.Logger.Info("shutdown listener fail, skipped: %v", err)
	}
	// 检查监听状态
	isRunning, err := CheckListenerStatus()
	if err != nil {
		e.Runtime.Logger.Error("check listener status fail: %s", err)
		return err
	} else if isRunning {
		e.Runtime.Logger.Info("listener is running")
		return fmt.Errorf("listener is running, please check and shutdown listener manually")
	}
	e.Runtime.Logger.Info("shutdown listener success")

	// 尝试切换日志
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer db.Close()
	err = SwitchLogfile(db)
	if err != nil {
		e.Runtime.Logger.Info("switch log fail, skipped: %v", err)
	} else {
		e.Runtime.Logger.Info("switch log success")
	}

	// 关闭实例
	e.Runtime.Logger.Info("start to shutdown instance")
	err = ShutdownInstance(true)
	if err != nil {
		e.Runtime.Logger.Error("shutdown instance fail: %s", err)
		return err
	}
	e.Runtime.Logger.Info("shutdown instance success")

	return nil
}
