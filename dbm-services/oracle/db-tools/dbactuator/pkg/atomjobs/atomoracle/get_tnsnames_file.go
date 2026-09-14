package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"os"

	"github.com/go-playground/validator/v10"
)

// GetTnsnamesFileParams 执行脚本初始化参数
type GetTnsnamesFileParams struct{}

// GetTnsnamesFile 执行脚本原子任务   oracle用户执行
type GetTnsnamesFile struct {
	BaseJob
	Params                    *GetTnsnamesFileParams
	GetTnsnamesFileRunTimeCtx `json:"-"`
}

// GetTnsnamesFileRunTimeCtx 运行时上下文
type GetTnsnamesFileRunTimeCtx struct {
	Content string `json:"content"`
}

// NewGetTnsnamesFile new
func NewGetTnsnamesFile() jobruntime.JobRunner {
	return &GetTnsnamesFile{}
}

// Init 初始化
func (e *GetTnsnamesFile) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of GetTnsnamesFile fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of GetTnsnamesFile fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *GetTnsnamesFile) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of GetTnsnamesFile")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of GetTnsnamesFile fail, error:%s", err)
		return fmt.Errorf("validate parameters of GetTnsnamesFile fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *GetTnsnamesFile) Name() string {
	return "get-tnsnames-file"
}

// Run 执行函数
func (e *GetTnsnamesFile) Run() error {
	if err := e.ReadTnsnamesFile(); err != nil {
		return err
	}
	if err := e.OutputCtx(); err != nil {
		return err
	}
	return nil
}

// ReadTnsnamesFile 读取tnsnames.ora文件内容
func (e *GetTnsnamesFile) ReadTnsnamesFile() error {
	oracleHome := os.Getenv("ORACLE_HOME")
	if oracleHome == "" {
		oracleHome = consts.DefaultOracleHome
	}
	file := oracleHome + "/network/admin/" + staticembed.TnsNamesFileName
	content, err := os.ReadFile(file)
	if err != nil {
		return fmt.Errorf("read file %s fail, error:%s", file, err)
	}
	e.Content = string(content)
	return nil
}

func (e *GetTnsnamesFile) OutputCtx() error {
	err := atomjobs.PrintOutputCtx(&e.Content)
	if err != nil {
		return err
	}
	return nil
}
