package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"time"

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
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("shutdown immediate failed: %v", err)
	}
	defer db.Close()

	query := `shutdown immediate`
	err = common.ExecuteOracle(db, query)
	if err != nil {
		return fmt.Errorf("shutdown immediate failed: %v", err)
	}

	cmd := []string{`lsnrctl stop`, `lsnrctl stop LISTENER1`}
	for _, c := range cmd {
		out, err := util.RunBashCmd(c, "", nil, 30*time.Second)
		if err != nil {
			e.Runtime.Logger.Warn("run cmd %s fail: %s", c, err)
			continue
		}
		e.Runtime.Logger.Info("run cmd %s success: %s", c, out)
	}
	return nil
}
