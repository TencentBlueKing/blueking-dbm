package atomoracle

import (
	"database/sql"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-playground/validator/v10"
)

// SwitchLogParams 执行脚本初始化参数
type SwitchLogParams struct {
}

// SwitchLog 执行脚本原子任务   root用户执行
type SwitchLog struct {
	BaseJob
	Params              *SwitchLogParams
	SwitchLogRunTimeCtx `json:"-"`
}

type SwitchLogRunTimeCtx struct {
}

// NewSwitchLog new
func NewSwitchLog() jobruntime.JobRunner {
	return &SwitchLog{}
}

// Init 初始化
func (e *SwitchLog) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of SwitchLog fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of SwitchLog fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *SwitchLog) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of SwitchLog")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of SwitchLog fail, error:%s", err)
		return fmt.Errorf("validate parameters of SwitchLog fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *SwitchLog) Name() string {
	return "switch-log"
}

// Run 执行函数
func (e *SwitchLog) Run() error {
	e.Runtime.Logger.Info("start to switch log")
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer db.Close()
	err = SwitchLogfile(db)
	if err != nil {
		return fmt.Errorf("switch log file failed: %v", err)
	}
	e.Runtime.Logger.Info("switch log file successfully")
	time.Sleep(10 * time.Second)
	return nil
}

// SwitchLogfile 切换日志文件
func SwitchLogfile(db *sql.DB) error {
	err := common.ExecuteOracle(db, consts.SwitchLogfile)
	if err != nil {
		return fmt.Errorf("switch log file failed: %v", err)
	}
	return nil
}
