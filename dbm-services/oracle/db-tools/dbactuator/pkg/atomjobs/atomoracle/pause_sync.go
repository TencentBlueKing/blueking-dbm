package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// PauseSyncParams 执行脚本初始化参数
type PauseSyncParams struct {
	AvailableNumber    int     `json:"available_number" validate:"required"`
	MasterDbUniqueName string  `json:"master_db_unique_name" validate:"required"`
	Account            Account `json:"account" validate:"required"`
}

// PauseSync 执行脚本原子任务   oracle用户执行
type PauseSync struct {
	BaseJob
	Params              *PauseSyncParams
	PauseSyncRunTimeCtx `json:"-"`
}

// PauseSyncRunTimeCtx 运行时上下文
type PauseSyncRunTimeCtx struct {
}

// NewPauseSync new
func NewPauseSync() jobruntime.JobRunner {
	return &PauseSync{}
}

// Init 初始化
func (e *PauseSync) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of PauseSync fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of PauseSync fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *PauseSync) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of PauseSync")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of PauseSync fail, error:%s", err)
		return fmt.Errorf("validate parameters of PauseSync fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *PauseSync) Name() string {
	return "pause-sync"
}

// Run 执行函数
func (e *PauseSync) Run() error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer db.Close()

	dbMaster, err := common.OpenOracleWithTns(e.Params.Account.Username, e.Params.Account.Password,
		e.Params.MasterDbUniqueName, true)
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer dbMaster.Close()

	query := fmt.Sprintf("ALTER SYSTEM SET log_archive_dest_state_%d='DEFER' SCOPE=BOTH", e.Params.AvailableNumber)
	err = common.ExecuteOracle(dbMaster, query)
	if err != nil {
		return fmt.Errorf("%s failed: %v", query, err)
	}

	query = `alter database recover managed standby database cancel`
	err = common.ExecuteOracle(db, query)
	if err != nil {
		return fmt.Errorf("stop standby apply failed: %v", err)
	}
	return nil
}
