package atomsys

import (
	"embed"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// SysInitMySQLScriptFileName 系统初始化脚本文件名
var SysInitMySQLScriptFileName = "sysinit_mysql.sh"

// SysInitMySQLScript embed调用
//
//go:embed sysinit_mysql.sh
var SysInitMySQLScript embed.FS

// SysInitParams 系统初始化参数
type SysInitParams struct {
	User     string `json:"user" validate:"required"`
	Password string `json:"password" validate:"required"`
}

// SysInit 系统初始化原子任务
type SysInit struct {
	runtime *jobruntime.JobGenericRuntime
	params  SysInitParams
}

// NewSysInit new
func NewSysInit() jobruntime.JobRunner {
	return &SysInit{}
}

// Init 初始化
func (job *SysInit) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m

	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v\n", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("Sys Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("Sys Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
	}
	return nil
}

// Name 名字
func (job *SysInit) Name() string {
	return "sysinit"
}

// Run 执行函数
func (job *SysInit) Run() (err error) {
	data, err := SysInitMySQLScript.ReadFile(SysInitMySQLScriptFileName)
	if err != nil {
		job.runtime.Logger.Error("read sysinit script failed %s", err.Error())
		return err
	}
	tmpScriptName := "/tmp/sysinit.sh"
	if err = ioutil.WriteFile(tmpScriptName, data, 07555); err != nil {
		job.runtime.Logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	_, err = util.RunBashCmd(tmpScriptName, "", nil, 30*time.Second)
	if err != nil {
		return
	}
	err = util.SetOSUserPassword(job.params.User, job.params.Password)
	if err != nil {
		return err
	}
	return nil
}

// Retry retry times
func (job *SysInit) Retry() uint {
	return 2
}

// Rollback rollback
func (job *SysInit) Rollback() error {
	return nil
}
