package atomoracle

import (
	"database/sql"
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/go-playground/validator/v10"
)

// GetConfigParams 执行脚本初始化参数
type GetConfigParams struct {
	SlaveHost string `json:"slave_host" validate:"required"`
}

// GetConfig 执行脚本原子任务   oracle用户执行
type GetConfig struct {
	BaseJob
	Params              *GetConfigParams
	GetConfigRunTimeCtx `json:"-"`
}

// GetConfigRunTimeCtx 运行时上下文
type GetConfigRunTimeCtx struct {
	Pathes             []string `json:"pathes"`
	LogArchiveConfig   string   `json:"log_archive_config"`
	AvailableNumber    int      `json:"available_number"`
	MasterDbUniqueName string   `json:"master_db_unique_name"`
	SlaveDbUniqueName  string   `json:"slave_db_unique_name"`
	RedoLogGroupNum    int      `json:"redo_log_group_num"`
	RedoLogMaxSize     int      `json:"redo_log_max_size"`
	CFSSN              string   `json:"cf_ssn"`
	CFSchema           string   `json:"cf_schema"`
	OracleSID          string   `json:"oracle_sid"`
	OracleHome         string   `json:"oracle_home"`
	ServiceNames       string   `json:"service_names"`
	DatabaseRole       string   `json:"database_role"`
	RealMaster         bool     `json:"real_master"`
}

// NewGetConfig new
func NewGetConfig() jobruntime.JobRunner {
	return &GetConfig{}
}

// Init 初始化
func (e *GetConfig) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of GetConfig fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of GetConfig fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *GetConfig) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of GetConfig")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of GetConfig fail, error:%s", err)
		return fmt.Errorf("validate parameters of GetConfig fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *GetConfig) Name() string {
	return "get-config"
}

// Run 执行函数
func (e *GetConfig) Run() error {
	if err := e.GetEnvConfig(); err != nil {
		return err
	}
	if err := e.GetPathes(); err != nil {
		return err
	}
	if err := e.GetInstanceConfig(); err != nil {
		return err
	}
	if err := e.GetRedoLogConfig(); err != nil {
		return err
	}
	if err := e.OutputCtx(); err != nil {
		return err
	}
	return nil
}

// GetPathes 获取Oracle的文件路径
func (e *GetConfig) GetPathes() error {
	var err error
	e.Pathes, err = common.QueryOraclePaths()
	if err != nil {
		return err
	}
	return nil
}

// GetInstanceConfig 获取实例的配置
func (e *GetConfig) GetInstanceConfig() error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return err
	}
	defer db.Close()
	// 查询项列表：每一项对应一条 SQL 及其结果写入的目标字段
	queries := []struct {
		sql  string
		dest any
	}{
		{consts.LogArchiveConfig, &e.LogArchiveConfig},
		{consts.AvailableNumber, &e.AvailableNumber},
		{consts.DbUniqueName, &e.MasterDbUniqueName},
		{consts.ServiceNames, &e.ServiceNames},
		{consts.DatabaseRole, &e.DatabaseRole},
	}
	for _, q := range queries {
		dest := q.dest
		if err = common.QueryOracle(db, q.sql, func(rows *sql.Rows) error {
			return rows.Scan(dest)
		}); err != nil {
			return err
		}
	}

	if err != nil {
		e.Runtime.Logger.Error("append dg config member fail, error:%s", err)
		return fmt.Errorf("append dg config member fail, error:%s", err)
	}

	e.SlaveDbUniqueName = fmt.Sprintf("%s_DR_%s",
		e.OracleSID, strings.ReplaceAll(e.Params.SlaveHost, ".", "_"))
	if e.DatabaseRole == "PRIMARY" {
		e.RealMaster = true
	} else {
		e.RealMaster = false
	}
	return nil
}

// GetRedoLogConfig 采集 redo log 的组数及最大大小
func (e *GetConfig) GetRedoLogConfig() error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return err
	}
	defer db.Close()
	if err = common.QueryOracle(db, consts.RedoLogSize, func(rows *sql.Rows) error {
		return rows.Scan(&e.RedoLogGroupNum, &e.RedoLogMaxSize)
	}); err != nil {
		return err
	}
	return nil
}

// GetEnvConfig 获取环境变量配置
func (e *GetConfig) GetEnvConfig() error {
	e.CFSSN = os.Getenv("CF_SSN")
	e.CFSchema = os.Getenv("CF_SCHEMA")
	e.OracleHome = os.Getenv("ORACLE_HOME")
	if e.OracleHome == "" {
		e.OracleHome = consts.DefaultOracleHome
	}
	e.OracleSID = os.Getenv("ORACLE_SID")
	if e.OracleSID == "" {
		return fmt.Errorf("ORACLE_SID is not set")
	}
	return nil
}

func (e *GetConfig) OutputCtx() error {
	err := atomjobs.PrintOutputCtx(&e.GetConfigRunTimeCtx)
	if err != nil {
		return err
	}
	return nil
}
