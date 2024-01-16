package atomsys

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/atomjobs/atommongodb"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"dbm-services/mongo/db-tools/dbactuator/pkg/common"
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// OsMongoInitConfParams 系统初始化参数
type OsMongoInitConfParams struct {
	User     string `json:"user" validate:"required"`
	Password string `json:"password" validate:"required"`
}

// OsMongoInit 系统初始化原子任务
type OsMongoInit struct {
	atommongodb.BaseJob
	runtime    *jobruntime.JobGenericRuntime
	ConfParams *OsMongoInitConfParams
	OsUser     string
	OsGroup    string
}

// NewOsMongoInit new
func NewOsMongoInit() jobruntime.JobRunner {
	return &OsMongoInit{}
}

// Init 初始化
func (o *OsMongoInit) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	o.runtime = runtime
	o.runtime.Logger.Info("start to init")
	o.OsUser = consts.GetProcessUser()
	o.OsGroup = consts.GetProcessUserGroup()
	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(o.runtime.PayloadDecoded), &o.ConfParams); err != nil {
		o.runtime.Logger.Error(
			"get parameters of mongoOsInit fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of mongoOsInit fail by json.Unmarshal, error:%s", err)
	}
	o.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := o.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (o *OsMongoInit) checkParams() error {
	// 校验配置参数
	o.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	o.runtime.Logger.Info("start to validate parameters of deInstall")
	if err := validate.Struct(o.ConfParams); err != nil {
		o.runtime.Logger.Error("validate parameters of mongoOsInit fail, error:%s", err)
		return fmt.Errorf("validate parameters of mongoOsInit fail, error:%s", err)
	}
	o.runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (o *OsMongoInit) Name() string {
	return "os_mongo_init"
}

// Run 执行函数
func (o *OsMongoInit) Run() error {
	// 获取初始化脚本
	o.runtime.Logger.Info("start to make init script content")
	data := common.MongoShellInit
	data = strings.Replace(data, "{{user}}", o.OsUser, -1)
	data = strings.Replace(data, "{{group}}", o.OsGroup, -1)
	o.runtime.Logger.Info("make init script content successfully")

	// 创建脚本文件
	o.runtime.Logger.Info("start to create init script file")
	tmpScriptName := "/tmp/sysinit.sh"
	if err := os.WriteFile(tmpScriptName, []byte(data), 07555); err != nil {
		o.runtime.Logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	o.runtime.Logger.Info("create init script file successfully")

	// 执行脚本
	o.runtime.Logger.Info("start to execute init script")
	_, err := util.RunBashCmd(tmpScriptName, "", nil, 30*time.Second)
	if err != nil {
		o.runtime.Logger.Error("execute init script fail, error:%s", err)
		return fmt.Errorf("execute init script fail, error:%s", err)
	}
	o.runtime.Logger.Info("execute init script successfully")
	// 设置用户名密码
	o.runtime.Logger.Info("start to set user:%s password", o.OsUser)
	err = util.SetOSUserPassword(o.ConfParams.User, o.ConfParams.Password)
	o.runtime.Logger.Info("set user:%s password successfully", o.OsUser)
	if err != nil {
		return err
	}
	return nil
}

// Retry times
func (o *OsMongoInit) Retry() uint {
	return 2
}

// Rollback rollback
func (o *OsMongoInit) Rollback() error {
	return nil
}
