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

// StopListenerParams 执行脚本初始化参数
type StopListenerParams struct {
}

// StopListener 执行脚本原子任务   oracle用户执行
type StopListener struct {
	BaseJob
	Params                 *StopListenerParams
	StopListenerRunTimeCtx `json:"-"`
}

// StopListenerRunTimeCtx 运行时上下文
type StopListenerRunTimeCtx struct {
}

// NewStopListener new
func NewStopListener() jobruntime.JobRunner {
	return &StopListener{}
}

// Init 初始化
func (e *StopListener) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of StopListener fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of StopListener fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *StopListener) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of StopListener")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of StopListener fail, error:%s", err)
		return fmt.Errorf("validate parameters of StopListener fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *StopListener) Name() string {
	return "stop-listener"
}

// Run 执行函数
func (e *StopListener) Run() error {
	e.Runtime.Logger.Info("start to stop listener")
	err := ShutdownListener()
	if err != nil {
		e.Runtime.Logger.Info("StopListener listener fail, skipped: %v", err)
	}
	isRunning, err := CheckListenerStatus()
	if err != nil {
		e.Runtime.Logger.Error("check listener status fail: %s", err)
		return err
	} else if isRunning {
		e.Runtime.Logger.Info("listener is running")
		return fmt.Errorf("listener is running, please check and StopListener listener manually")
	}
	e.Runtime.Logger.Info("stop listener success")
	return nil

}

// ShutdownListener 关闭监听
func ShutdownListener() error {
	var errors error
	cmd := []string{`lsnrctl stop`, `lsnrctl stop LISTENER1`}
	for _, c := range cmd {
		_, err := util.RunBashCmd(c, "", nil, 30*time.Second)
		if err != nil {
			errors = fmt.Errorf("%v \n failed to execute command: %s error: %v", err, c, err)
			continue
		}
	}
	return errors
}

// CheckListenerStatus 检查监听状态
func CheckListenerStatus() (bool, error) {
	isRunning := false
	cmd := []string{`lsnrctl status`, `lsnrctl status LISTENER1`}
	for _, c := range cmd {
		_, err := util.RunBashCmd(c, "", nil, 30*time.Second)
		if err != nil {
			if strings.Contains(err.Error(), "No listener") {
				continue
			} else {
				return isRunning, fmt.Errorf("failed to execute command: %s error: %v", c, err)
			}
		}
		isRunning = true
	}
	return isRunning, nil
}
