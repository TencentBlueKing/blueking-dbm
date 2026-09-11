package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// StartListenerParams 执行脚本初始化参数
type StartListenerParams struct {
}

// StartListener 执行脚本原子任务   oracle用户执行
type StartListener struct {
	BaseJob
	Params                  *StartListenerParams
	StartListenerRunTimeCtx `json:"-"`
}

// StartListenerRunTimeCtx 运行时上下文
type StartListenerRunTimeCtx struct {
}

// NewStartListener new
func NewStartListener() jobruntime.JobRunner {
	return &StartListener{}
}

// Init 初始化
func (e *StartListener) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of StartListener fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of StartListener fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *StartListener) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of StartListener")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of StartListener fail, error:%s", err)
		return fmt.Errorf("validate parameters of StartListener fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *StartListener) Name() string {
	return "start-listener"
}

// Run 执行函数
func (e *StartListener) Run() error {
	cmd := []string{`lsnrctl stop`, `lsnrctl start`, `lsnrctl status`}
	for _, c := range cmd {
		out, err := util.RunBashCmd(c, "", nil, 30*time.Second)
		if strings.Contains(c, "stop") {
			continue
		}
		if err != nil {
			e.Runtime.Logger.Error("run cmd %s fail: %s", c, err)
			return fmt.Errorf("run cmd %s fail: %s", c, err)
		}
		if !strings.Contains(out, "The command completed successfully") {
			return fmt.Errorf("no [success] key in ouput: %s, cmd: %s", out, c)
		}
		e.Runtime.Logger.Info("run cmd %s successfully, output:\n%s", c, out)
	}
	return nil
}
