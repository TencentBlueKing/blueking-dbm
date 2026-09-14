package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// ActivateStandbyParams 执行脚本初始化参数
type ActivateStandbyParams struct {
}

// ActivateStandby 执行脚本原子任务   oracle用户执行
type ActivateStandby struct {
	BaseJob
	Params                    *ActivateStandbyParams
	ActivateStandbyRunTimeCtx `json:"-"`
}

// ActivateStandbyRunTimeCtx 运行时上下文
type ActivateStandbyRunTimeCtx struct {
}

// NewActivateStandby new
func NewActivateStandby() jobruntime.JobRunner {
	return &ActivateStandby{}
}

// Init 初始化
func (e *ActivateStandby) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of ActivateStandby fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of ActivateStandby fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *ActivateStandby) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of ActivateStandby")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of ActivateStandby fail, error:%s", err)
		return fmt.Errorf("validate parameters of ActivateStandby fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *ActivateStandby) Name() string {
	return "activate-standby"
}

// Run 执行函数
func (e *ActivateStandby) Run() error {
	// 1. 取消日志应用
	if err := common.ExecuteSqlplusAsSysdba(consts.RecoverCancel); err != nil {
		e.Runtime.Logger.Error("%s execute failed: %v", consts.RecoverCancel, err)
		return fmt.Errorf("%s execute failed: %v", consts.RecoverCancel, err)
	}
	e.Runtime.Logger.Info("%s execute successfully", consts.RecoverCancel)

	// 2. 关闭实例
	if err := ShutdownInstance(true); err != nil {
		e.Runtime.Logger.Error("shutdown instance fail: %s", err)
		return err
	}
	e.Runtime.Logger.Info("shutdown instance success")

	// 3. mount 实例、激活备库、开启实例
	cmds := []string{
		consts.MountInstance,
		consts.ActivateStandbyDatabase,
		consts.OpenInstance,
	}
	for _, c := range cmds {
		if err := common.ExecuteSqlplusAsSysdba(c); err != nil {
			e.Runtime.Logger.Error("%s execute failed: %v", c, err)
			return fmt.Errorf("%s execute failed: %v", c, err)
		}
		e.Runtime.Logger.Info("%s execute successfully", c)
	}
	return nil
}
