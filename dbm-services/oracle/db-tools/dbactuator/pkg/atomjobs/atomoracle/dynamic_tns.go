package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// DynamicTnsParams 执行脚本初始化参数
type DynamicTnsParams struct {
	SlaveHost         string `json:"slave_host" validate:"required"`
	SlavePort         int    `json:"slave_port" validate:"required"`
	OracleSID         string `json:"oracle_sid" validate:"required"`
	SlaveDbUniqueName string `json:"slave_db_unique_name" validate:"required"`
}

// DynamicTns 执行脚本原子任务   root用户执行
type DynamicTns struct {
	BaseJob
	Params               *DynamicTnsParams
	DynamicTnsRunTimeCtx `json:"-"`
}

// DynamicTnsRunTimeCtx 运行时上下文
type DynamicTnsRunTimeCtx struct {
}

// NewDynamicTns new
func NewDynamicTns() jobruntime.JobRunner {
	return &DynamicTns{}
}

// Init 初始化
func (e *DynamicTns) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of DynamicTns fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of DynamicTns fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *DynamicTns) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of DynamicTns")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of DynamicTns fail, error:%s", err)
		return fmt.Errorf("validate parameters of DynamicTns fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *DynamicTns) Name() string {
	return "dynamic-tns"
}

// Run 执行函数
func (e *DynamicTns) Run() error {
	if err := e.ConfigTnsNames(); err != nil {
		return err
	}
	return nil
}

// ConfigTnsNames 配置tnsnames.ora
func (e *DynamicTns) ConfigTnsNames() error {
	return ConfigTnsNames(e.Runtime.Logger, e.Params.SlaveDbUniqueName,
		e.Params.SlaveHost, e.Params.SlavePort, e.Params.OracleSID)
}
