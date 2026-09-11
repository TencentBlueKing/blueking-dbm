package atomoracle

import (
	"database/sql"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// RealMasterParams 执行脚本初始化参数
type RealMasterParams struct {
}

// RealMaster 执行脚本原子任务   oracle用户执行
type RealMaster struct {
	BaseJob
	Params               *RealMasterParams
	RealMasterRunTimeCtx `json:"-"`
}

// RealMasterRunTimeCtx 运行时上下文
type RealMasterRunTimeCtx struct {
}

// NewRealMaster new
func NewRealMaster() jobruntime.JobRunner {
	return &RealMaster{}
}

// Init 初始化
func (e *RealMaster) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of RealMaster fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of RealMaster fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *RealMaster) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of RealMaster")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of RealMaster fail, error:%s", err)
		return fmt.Errorf("validate parameters of RealMaster fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *RealMaster) Name() string {
	return "real-master"
}

// Run 执行函数
func (e *RealMaster) Run() error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer db.Close()
	if err = RealMasterCheck(db); err != nil {
		return err
	}
	return nil
}

func RealMasterCheck(db *sql.DB) error {
	var databaseRole string
	if err := db.QueryRow(consts.DatabaseRole).Scan(&databaseRole); err != nil {
		return fmt.Errorf("query database role failed: %v", err)
	}
	if databaseRole != "PRIMARY" {
		return fmt.Errorf("database role is not primary, got: %s", databaseRole)
	}
	return nil
}
