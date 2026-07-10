package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path"

	"github.com/go-playground/validator/v10"
)

// GetPasswordFileParams 执行脚本初始化参数
type GetPasswordFileParams struct{}

// GetPasswordFile 执行脚本原子任务   oracle用户执行
type GetPasswordFile struct {
	BaseJob
	Params                    *GetPasswordFileParams
	GetPasswordFileRunTimeCtx `json:"-"`
}

// GetPasswordFileRunTimeCtx 运行时上下文
type GetPasswordFileRunTimeCtx struct {
	Content string `json:"content"`
}

// NewGetPasswordFile new
func NewGetPasswordFile() jobruntime.JobRunner {
	return &GetPasswordFile{}
}

// Init 初始化
func (e *GetPasswordFile) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of GetPasswordFile fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of GetPasswordFile fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *GetPasswordFile) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of GetPasswordFile")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of GetPasswordFile fail, error:%s", err)
		return fmt.Errorf("validate parameters of GetPasswordFile fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *GetPasswordFile) Name() string {
	return "get-password-file"
}

// Run 执行函数
func (e *GetPasswordFile) Run() error {
	if err := e.GetPasswordFile(); err != nil {
		return err
	}
	if err := e.OutputCtx(); err != nil {
		return err
	}
	return nil
}

// GetPasswordFile 获取密码文件内容
func (e *GetPasswordFile) GetPasswordFile() error {
	oracleHome := os.Getenv("ORACLE_HOME")
	if oracleHome == "" {
		oracleHome = consts.DefaultOracleHome
	}
	oracleSID := os.Getenv("ORACLE_SID")
	if oracleSID == "" {
		return fmt.Errorf("ORACLE_SID is not set")
	}
	orapw := path.Join(oracleHome, "dbs", "orapw"+oracleSID)
	content, err := os.ReadFile(orapw)
	if err != nil {
		return fmt.Errorf("read orapw %s fail, error:%s", orapw, err.Error())
	}
	// orapw 是二进制文件（Oracle 密码文件），base64 编码穿越 JSON 通道，
	// 否则 json.Marshal 会把非法 UTF-8 字节替换成 U+FFFD，导致上传后内容损坏。
	e.Content = base64.StdEncoding.EncodeToString(content)
	// e.Content = string(content)
	return nil
}

func (e *GetPasswordFile) OutputCtx() error {
	err := atomjobs.PrintOutputCtx(&e.Content)
	if err != nil {
		return err
	}
	return nil
}
