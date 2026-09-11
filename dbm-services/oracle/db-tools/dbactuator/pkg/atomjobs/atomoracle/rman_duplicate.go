package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// RmanDuplicateParams 执行脚本初始化参数
type RmanDuplicateParams struct {
	AvailableNumber    int     `json:"available_number" validate:"required"`
	MasterDbUniqueName string  `json:"master_db_unique_name" validate:"required"`
	SlaveDbUniqueName  string  `json:"slave_db_unique_name" validate:"required"`
	RealMaster         bool    `json:"real_master"`
	Account            Account `json:"account" validate:"required"`
}

// RmanErrorKeywords rman 日志中若出现下列关键字（大写比较）则判定为失败
var RmanErrorKeywords = []string{"RMAN-", "ERROR", "ORA-"}

// Account 数据库账号信息
type Account struct {
	Username string `json:"username" validate:"required"`
	Password string `json:"password" validate:"required"`
}

// RmanDuplicate 执行脚本原子任务   root用户执行
type RmanDuplicate struct {
	BaseJob
	Params                  *RmanDuplicateParams
	RmanDuplicateRunTimeCtx `json:"-"`
}

type RmanDuplicateRunTimeCtx struct {
}

// NewRmanDuplicate new
func NewRmanDuplicate() jobruntime.JobRunner {
	return &RmanDuplicate{}
}

// Init 初始化
func (e *RmanDuplicate) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of RmanDuplicate fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of RmanDuplicate fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *RmanDuplicate) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of RmanDuplicate")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of RmanDuplicate fail, error:%s", err)
		return fmt.Errorf("validate parameters of RmanDuplicate fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *RmanDuplicate) Name() string {
	return "rman-duplicate"
}

// Run 执行函数
func (e *RmanDuplicate) Run() error {
	e.Runtime.Logger.Info("start to rman duplicate")

	tplBytes, err := e.loadTemplate()
	if err != nil {
		return err
	}
	content := e.renderScript(tplBytes)
	scriptPath, logPath, err := e.writeScript(content)
	if err != nil {
		return err
	}
	if err = e.executeScript(scriptPath, logPath); err != nil {
		return err
	}
	e.waitAfterDuplicate()
	defer e.maskPasswordInScript(scriptPath)
	return nil
}

// loadTemplate 根据 RealMaster 选择并读取内嵌的 rman 脚本模板
func (e *RmanDuplicate) loadTemplate() ([]byte, error) {
	var (
		tplBytes []byte
		err      error
		tplName  string
	)
	if e.Params.RealMaster {
		tplName = staticembed.RMANDuplicateSlowlyScriptFileName
		tplBytes, err = staticembed.RMANDuplicateSlowlyScript.ReadFile(tplName)
	} else {
		tplName = staticembed.RMANDuplicateScriptFileName
		tplBytes, err = staticembed.RMANDuplicateScript.ReadFile(tplName)
	}
	if err != nil {
		e.Runtime.Logger.Error("read embedded %s fail, error:%s", tplName, err)
		return nil, fmt.Errorf("read embedded %s fail, error:%s", tplName, err)
	}
	return tplBytes, nil
}

// renderScript 根据入参替换 shell 模板中的占位符，生成实际脚本内容
func (e *RmanDuplicate) renderScript(tplBytes []byte) string {
	return strings.NewReplacer(
		consts.RmanPlaceholderPassword, e.Params.Account.Password,
		consts.RmanPlaceholderMaster, e.Params.MasterDbUniqueName,
		consts.RmanPlaceholderSlave, e.Params.SlaveDbUniqueName,
		consts.RmanPlaceholderAvailableNumber, strconv.Itoa(e.Params.AvailableNumber),
	).Replace(string(tplBytes))
}

// writeScript 生成脚本文件，返回 scriptPath 和 logPath
func (e *RmanDuplicate) writeScript(content string) (string, string, error) {
	timestamp := time.Now().Format(consts.RmanTimestampLayout)
	scriptPath := fmt.Sprintf(consts.RmanScriptNamePattern, timestamp)
	logPath := fmt.Sprintf(consts.RmanLogNamePattern, timestamp)

	if err := os.WriteFile(scriptPath, []byte(content), consts.RmanScriptPerm); err != nil {
		e.Runtime.Logger.Error("write script %s fail, error:%s", scriptPath, err)
		return "", "", fmt.Errorf("write script %s fail, error:%s", scriptPath, err)
	}
	e.Runtime.Logger.Info("generate script %s successfully", scriptPath)
	return scriptPath, logPath, nil
}

// executeScript 执行生成的 rman 脚本，并根据日志判定是否成功
func (e *RmanDuplicate) executeScript(scriptPath, logPath string) error {
	// 执行生成的脚本并将输出追加到对应日志
	shellCmd := fmt.Sprintf("./%s >> %s 2>&1", scriptPath, logPath)
	e.Runtime.Logger.Info("start to execute cmd: %s", shellCmd)
	if _, err := util.RunBashCmd(shellCmd, "", nil, consts.RmanScriptTimeout); err != nil {
		// 截取报错日志
		lines, _ := util.GetLastLine(logPath, consts.RmanLogTailLines)
		e.Runtime.Logger.Error("execute rman duplicate fail, error:%s, tail log:\n%s",
			err, strings.Join(lines, "\n"))
		return fmt.Errorf("execute rman duplicate fail, error:%s", err)
	}
	if ok, err := CheckRMANLog(logPath); !ok {
		e.Runtime.Logger.Error("check rman log fail, error:%s", err)
		return err
	}
	return nil
}

// waitAfterDuplicate rman duplicate 完成后 sleep 60 秒
func (e *RmanDuplicate) waitAfterDuplicate() {
	e.Runtime.Logger.Info("sleep 60 seconds begin")
	time.Sleep(60 * time.Second)
	e.Runtime.Logger.Info("sleep 60 seconds done")
	e.Runtime.Logger.Info("rman duplicate successfully")
}

// maskPasswordInScript 脚本执行完后，将脚本文件中的明文密码脱敏，避免密码长期驻留磁盘。
func (e *RmanDuplicate) maskPasswordInScript(scriptPath string) {
	data, rerr := os.ReadFile(scriptPath)
	if rerr != nil {
		e.Runtime.Logger.Warn("read script %s for masking password fail, error:%s", scriptPath, rerr)
		return
	}
	masked := strings.ReplaceAll(string(data), e.Params.Account.Password, consts.RmanPasswordMask)
	if werr := os.WriteFile(scriptPath, []byte(masked), consts.RmanScriptPerm); werr != nil {
		e.Runtime.Logger.Warn("mask password in script %s fail, error:%s", scriptPath, werr)
		return
	}
	e.Runtime.Logger.Info("mask password in script %s successfully", scriptPath)
}

// CheckRMANLog 检查整个 rman 日志文件，若包含 RMAN- / error / ORA- 关键字则认为失败
func CheckRMANLog(logPath string) (bool, error) {
	data, err := os.ReadFile(logPath)
	if err != nil {
		return false, fmt.Errorf("read rman log %s fail, error:%s", logPath, err)
	}
	content := strings.ToUpper(string(data))
	for _, kw := range RmanErrorKeywords {
		if strings.Contains(content, kw) {
			return false, fmt.Errorf(
				"rman duplicate fail, log %s contains keyword %q",
				logPath, kw)
		}
	}
	return true, nil
}
