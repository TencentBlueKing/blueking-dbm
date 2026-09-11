package atomoracle

import (
	"database/sql"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/go-playground/validator/v10"
)

// RealTimeApplyParams 执行脚本初始化参数
type RealTimeApplyParams struct {
	RedoLogGroupNum int `json:"redo_log_group_num"`
	RedoLogMaxSize  int `json:"redo_log_max_size"`
}

// RealTimeApply 执行脚本原子任务   oracle用户执行
type RealTimeApply struct {
	BaseJob
	Params                  *RealTimeApplyParams
	RealTimeApplyRunTimeCtx `json:"-"`
}

// RealTimeApplyRunTimeCtx 运行时上下文
type RealTimeApplyRunTimeCtx struct {
}

// NewRealTimeApply new
func NewRealTimeApply() jobruntime.JobRunner {
	return &RealTimeApply{}
}

// Init 初始化
func (e *RealTimeApply) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of RealTimeApply fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of RealTimeApply fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *RealTimeApply) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of RealTimeApply")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of RealTimeApply fail, error:%s", err)
		return fmt.Errorf("validate parameters of RealTimeApply fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *RealTimeApply) Name() string {
	return "real-time-apply"
}

// Run 执行函数
func (e *RealTimeApply) Run() error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer db.Close()
	if err = StopSyncAndOpenInstance(db); err != nil {
		return err
	}
	if err = e.CheckStandbyRedo(db); err != nil {
		return err
	}
	if err = UseRealTimeApply(db); err != nil {
		return err
	}
	return nil
}

// StopSyncAndOpenInstance 停止同步并打开实例
func StopSyncAndOpenInstance(db *sql.DB) error {
	query := `alter database recover managed standby database cancel`
	err := common.ExecuteOracle(db, query)
	if err != nil {
		// ORA-16136: Managed Standby Recovery not active
		// 当前实例并未在跑 redo apply，对"停止同步"的目标来说等价于成功，忽略即可。
		if !strings.Contains(err.Error(), "ORA-16136") {
			return fmt.Errorf("stop standby apply failed: %v", err)
		}
	}

	query = `alter database open read only`
	err = common.ExecuteOracle(db, query)
	if err != nil {
		if strings.Contains(err.Error(), "ORA-01531") {
			return nil
		}
		return fmt.Errorf("open database failed: %v", err)
	}
	return nil
}

// CheckStandbyRedo 检查 standby redo 日志配置
func (e *RealTimeApply) CheckStandbyRedo(db *sql.DB) error {
	var standbyLogGroupNum, standbyLogMaxSize int
	if err := common.QueryOracle(db, consts.RedoLogSize, func(rows *sql.Rows) error {
		return rows.Scan(&standbyLogGroupNum, &standbyLogMaxSize)
	}); err != nil {
		return err
	}
	if standbyLogGroupNum < e.Params.RedoLogGroupNum {
		return fmt.Errorf("standby log group num is less than redo log group num")
	}
	if standbyLogMaxSize < e.Params.RedoLogMaxSize {
		return fmt.Errorf("standby log max size is less than redo log max size")
	}
	return nil
}

// UseRealTimeApply 实时应用 redo 日志
func UseRealTimeApply(db *sql.DB) error {
	query := `alter database recover managed standby database using current logfile disconnect`
	err := common.ExecuteOracle(db, query)
	if err != nil {
		return fmt.Errorf("real time apply failed: %v", err)
	}
	return nil
}
