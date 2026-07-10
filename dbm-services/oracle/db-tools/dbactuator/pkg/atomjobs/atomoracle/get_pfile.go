package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/go-playground/validator/v10"
)

// GetPfileParams 执行脚本初始化参数
type GetPfileParams struct{}

// GetPfile 执行脚本原子任务   oracle用户执行
type GetPfile struct {
	BaseJob
	Params             *GetPfileParams
	GetPfileRunTimeCtx `json:"-"`
}

// GetPfileRunTimeCtx 运行时上下文
type GetPfileRunTimeCtx struct {
	Content string `json:"content"`
}

// NewGetPfile new
func NewGetPfile() jobruntime.JobRunner {
	return &GetPfile{}
}

// Init 初始化
func (e *GetPfile) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of GetPfile fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of GetPfile fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *GetPfile) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of GetPfile")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of GetPfile fail, error:%s", err)
		return fmt.Errorf("validate parameters of GetPfile fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *GetPfile) Name() string {
	return "get-pfile"
}

// Run 执行函数
func (e *GetPfile) Run() error {
	if err := e.CreatePfile(); err != nil {
		return err
	}
	if err := e.OutputCtx(); err != nil {
		return err
	}
	return nil
}

// CreatePfile 创建pfile文件，并将pfile文件内容读取到 e.Pfile 中
func (e *GetPfile) CreatePfile() error {
	pfile := fmt.Sprintf("/tmp/init%s.ora", time.Now().Format("20060102_150405"))
	vsql := fmt.Sprintf("CREATE PFILE='%s' FROM SPFILE", pfile)
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(vsql)
	if err != nil {
		return err
	}
	content, err := os.ReadFile(pfile)
	if err != nil {
		return fmt.Errorf("read pfile %s fail, error:%s", pfile, err)
	}
	e.Content = string(content)
	return nil
}

func (e *GetPfile) OutputCtx() error {
	err := atomjobs.PrintOutputCtx(&e.Content)
	if err != nil {
		return err
	}
	return nil
}
