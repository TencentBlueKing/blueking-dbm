package atomsys

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs/atomoracle"
	"fmt"
	"os"
	"strings"
	"time"

	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
)

// OsOracleInit 系统初始化原子任务
type OsOracleInit struct {
	atomoracle.BaseJob
	OsGroup string
}

// NewOsOracleInit new
func NewOsOracleInit() jobruntime.JobRunner {
	return &OsOracleInit{}
}

// Init 初始化
func (o *OsOracleInit) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	o.Runtime = runtime
	o.Runtime.Logger.Info("start to init")
	o.OsUser = consts.GetProcessUser()
	o.OsGroup = consts.GetProcessUserGroup()
	o.Runtime.Logger.Info("init successfully")
	return nil
}

// Name 名字
func (o *OsOracleInit) Name() string {
	return "os_oracle_init"
}

// Run 执行函数
func (o *OsOracleInit) Run() error {
	// 获取初始化脚本
	o.Runtime.Logger.Info("start to make init script content")
	data := common.OracleShellInit
	data = strings.Replace(data, "{{user}}", o.OsUser, -1)
	data = strings.Replace(data, "{{group}}", o.OsGroup, -1)
	o.Runtime.Logger.Info("make init script content successfully")

	// 创建脚本文件
	o.Runtime.Logger.Info("start to create init script file")
	tmpScriptName := "/tmp/sysinit.sh"
	if err := os.WriteFile(tmpScriptName, []byte(data), 07555); err != nil {
		o.Runtime.Logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	o.Runtime.Logger.Info("create init script file successfully")

	// 执行脚本
	o.Runtime.Logger.Info("start to execute init script")
	_, err := util.RunBashCmd(tmpScriptName, "", nil, 30*time.Second)
	if err != nil {
		o.Runtime.Logger.Error("execute init script fail, error:%s", err)
		return fmt.Errorf("execute init script fail, error:%s", err)
	}
	o.Runtime.Logger.Info("execute init script successfully")
	return nil
}

// Retry times
func (o *OsOracleInit) Retry() uint {
	return 2
}

// Rollback rollback
func (o *OsOracleInit) Rollback() error {
	return nil
}
