package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// ExecuteScriptConfParams 执行脚本初始化参数
type ExecuteScriptConfParams struct {
	App                 string   `json:"app" validate:"required"`
	TaskId              string   `json:"taskid" validate:"required"`
	IP                  string   `json:"ip" validate:"required"`
	Port                string   `json:"port" validate:"required"`
	ServiceName         string   `json:"servicename" validate:"required"`
	BlurDb              []string `json:"blurdb" validate:"required"`
	ManagerUser         string   `json:"manageruser" validate:"required"`
	ManagerUserPassword string   `json:"manageruserpassword" validate:"required"`
	ExecuteUserPassword string   `json:"executeuserpassword" validate:"required"`
	ScriptFiles         []string `json:"scriptfiles" validate:"required"`
}

// ExecuteScript 执行脚本原子任务   oracle用户执行
type ExecuteScript struct {
	BaseJob
	ConfParams          *ExecuteScriptConfParams
	ExecuteDir          string
	ExecuteScriptFormat string
	AllExecuteDb        []string
	ExecuteShellPath    []string
	ExecuteShellLogPath []string
	OsGroup             string
	ExecuteTimeOut      time.Duration
	ExecuteResultStatus map[string][]string
}

// NewExecuteScript new
func NewExecuteScript() jobruntime.JobRunner {
	return &ExecuteScript{
		ExecuteTimeOut: 24 * time.Hour,
		ExecuteResultStatus: map[string][]string{
			"successful": {},
			"fail":       {}},
	}
}

// Init 初始化
func (e *ExecuteScript) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	e.Runtime = runtime
	e.Runtime.Logger.Info("start to init")
	e.OsUser = consts.GetProcessUser()
	e.OsGroup = consts.GetProcessUserGroup()
	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.ConfParams); err != nil {
		e.Runtime.Logger.Error(
			"get parameters of ExecuteScript fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of ExecuteScript fail by json.Unmarshal, error:%s", err)
	}
	// 执行目录
	e.ExecuteDir = filepath.Join(consts.PackageSavePath, e.ConfParams.TaskId)
	// 执行脚本的路径
	var scriptFilesPath []string
	for _, file := range e.ConfParams.ScriptFiles {
		scriptFilesPath = append(scriptFilesPath, "@"+filepath.Join(e.ExecuteDir, file))
	}
	e.ExecuteScriptFormat = strings.Join(scriptFilesPath, "\n")
	e.Runtime.Logger.Info("init successfully")

	// 进行校验
	if err := e.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (e *ExecuteScript) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of ExecuteScript")
	if err := validate.Struct(e.ConfParams); err != nil {
		e.Runtime.Logger.Error("validate parameters of ExecuteScript fail, error:%s", err)
		return fmt.Errorf("validate parameters of ExecuteScript fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *ExecuteScript) Name() string {
	return "execute_script"
}

// Run 执行函数
func (e *ExecuteScript) Run() error {
	// 获取db名
	if err := e.GetDbUserName(); err != nil {
		return err
	}
	// 创建执行脚本并授权
	if err := e.CreateExecuteScript(); err != nil {
		return err
	}
	// 执行脚本
	if err := e.ExecuteAllScript(); err != nil {
		return err
	}
	return nil
}

// GetDbUserName 获取准确的db用户名
func (e *ExecuteScript) GetDbUserName() error {
	e.Runtime.Logger.Info("start to get db username")
	var str string
	for i := 0; i < len(e.ConfParams.BlurDb); i++ {
		if i == 0 {
			str = fmt.Sprintf("username like :%d", i+1)
			continue
		}
		str = strings.Join([]string{str, fmt.Sprintf("username like :%d", i+1)}, " or ")
	}
	sql := strings.Join([]string{common.GetUserNameSql, str}, "")
	// 获取所有db名
	// []string装换成[]any
	var dbBlurName []any
	for _, db := range e.ConfParams.BlurDb {
		dbBlurName = append(dbBlurName, "%"+db+"%")
	}
	db, rows, err := common.GetInfoFromOracle(e.ConfParams.ManagerUser,
		e.ConfParams.ManagerUserPassword,
		e.ConfParams.IP,
		e.ConfParams.Port,
		e.ConfParams.ServiceName,
		sql,
		dbBlurName...,
	)
	if db != nil {
		defer db.Close()
	}
	if rows != nil {
		defer rows.Close()
	}
	if err != nil {
		e.Runtime.Logger.Error("get db username fail, error:%s", err)
		return fmt.Errorf("get db username fail, error:%s", err)
	}
	var username string
	for rows.Next() {
		rows.Scan(&username)
		e.AllExecuteDb = append(e.AllExecuteDb, username)
	}
	if len(e.AllExecuteDb) == 0 {
		e.Runtime.Logger.Error("get db username fail, error: db username %v doesn't exist ", e.ConfParams.BlurDb)
		return fmt.Errorf("get db username fail, error: db username %v doesn't exist ", e.ConfParams.BlurDb)
	}
	e.Runtime.Logger.Info("get db username successfully")
	return nil
}

// CreateExecuteScript 创建执行脚本
func (e *ExecuteScript) CreateExecuteScript() error {
	// 获取创建脚本路劲,日志路径，创建脚本 修改权限
	e.Runtime.Logger.Info("start to create execute shell script")
	for _, username := range e.AllExecuteDb {
		userShellName := strings.Join([]string{e.ConfParams.App, username, e.ConfParams.TaskId}, "-") + ".sh"
		userShellLogName := strings.Join([]string{e.ConfParams.App, username, e.ConfParams.TaskId}, "-") + ".log"
		// 执行shell完整路径
		userShellPath := filepath.Join(e.ExecuteDir, userShellName)
		e.Runtime.Logger.Info("username:%s shell script path:%s", username, e.ExecuteShellPath)
		e.ExecuteShellPath = append(e.ExecuteShellPath, userShellPath)
		// 执行日志完整路径
		userShellLogPath := filepath.Join(e.ExecuteDir, userShellLogName)
		e.Runtime.Logger.Info("username:%s shell script execute log path:%s", username, userShellLogPath)
		e.ExecuteShellLogPath = append(e.ExecuteShellLogPath, userShellLogPath)
		var info = make(map[string]string)
		info["{{logPath}}"] = userShellLogPath
		info["{{dbUser}}"] = username
		info["{{dbUserPassword}}"] = e.ConfParams.ExecuteUserPassword
		info["{{executeScriptFormat}}"] = e.ExecuteScriptFormat
		shellContent := common.ExecuteScriptTemplate
		shellContentPrintLog := common.ExecuteScriptTemplate
		for key, value := range info {
			shellContent = strings.Replace(shellContent, key, value, -1)
			if key != "{{dbUserPassword}}" {
				shellContentPrintLog = strings.Replace(shellContentPrintLog, key, value, -1)
			}
		}
		e.Runtime.Logger.Info("username:%s shell script content:%s", username, shellContentPrintLog)
		e.Runtime.Logger.Info("start to create %s shell script", username)
		if !util.FileExists(userShellPath) {
			if err := common.CreateFileAndChown(e.Runtime, userShellPath, []byte(shellContent), e.OsUser, e.OsGroup,
				0755); err != nil {
				e.Runtime.Logger.Error("create %s shell script fail,error:%s", username, err.Error())
				return fmt.Errorf("create %s shell script fail,error:%s", username, err.Error())
			}
		} else {
			// 先删除
			if err := os.Remove(userShellPath); err != nil {
				e.Runtime.Logger.Error("%s shell script exist,remove %s fail, error:%s", userShellPath, userShellPath, err.Error())
			}
			if err := common.CreateFileAndChown(e.Runtime, userShellPath, []byte(shellContent), e.OsUser, e.OsGroup,
				0755); err != nil {
				e.Runtime.Logger.Error("create %s shell script fail,error:%s", username, err.Error())
				return fmt.Errorf("create %s shell script fail,error:%s", username, err.Error())
			}
		}
		e.Runtime.Logger.Info("create %s shell script successfully", username)
	}
	e.Runtime.Logger.Info("create execute shell script successfully")
	return nil
}

// ExecuteAllScript 执行脚本
func (e *ExecuteScript) ExecuteAllScript() error {
	// 串行执行脚本
	for index, username := range e.AllExecuteDb {
		e.Runtime.Logger.Info("start to execute shell script:%s", e.ExecuteShellPath[index])
		shellCmd := fmt.Sprintf("sh %s", e.ExecuteShellPath[index])
		echoCmd := fmt.Sprintf("echo \"db_pkg_script_end\" >> %s", e.ExecuteShellLogPath[index])
		if _, err := util.RunBashCmd(shellCmd, "", nil, e.ExecuteTimeOut); err != nil {
			_, _ = util.RunBashCmd(echoCmd, "", nil, 10*time.Second)
			e.Runtime.Logger.Error("execute shell script:%s fail, error:%s", e.ExecuteShellPath[index], err.Error())
			// 截取报错日志
			lines, _ := util.GetLastLine(e.ExecuteShellLogPath[index], 10)
			e.Runtime.Logger.Error("execute shell script:%s fail, error log:%s", e.ExecuteShellPath[index], strings.Join(lines,
				"\n"))
			e.ExecuteResultStatus["fail"] = append(e.ExecuteResultStatus["fail"], username)
			continue
		}
		_, _ = util.RunBashCmd(echoCmd, "", nil, 10*time.Second)
		e.ExecuteResultStatus["successful"] = append(e.ExecuteResultStatus["successful"], username)
		e.Runtime.Logger.Info("execute shell script:%s successfully", e.ExecuteShellPath[index])
	}
	// 检查执行结果
	e.Runtime.Logger.Info("execute shell script result:")
	e.Runtime.Logger.Info("execute shell script success list:%s", e.ExecuteResultStatus["successful"])
	if len(e.ExecuteResultStatus["fail"]) > 0 {
		e.Runtime.Logger.Error("execute shell script fail list:%v", e.ExecuteResultStatus["fail"])
		return fmt.Errorf("execute shell script fail list:%v", e.ExecuteResultStatus["fail"])
	} else {
		e.Runtime.Logger.Info("execute shell script fail list:%v", e.ExecuteResultStatus["fail"])
	}
	return nil
}

// Retry times
func (e *ExecuteScript) Retry() uint {
	return 2
}

// Rollback rollback
func (e *ExecuteScript) Rollback() error {
	return nil
}
