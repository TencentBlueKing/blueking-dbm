package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongo/db-tools/dbactuator/pkg/common"
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// DelUserConfParams 参数
type DelUserConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	InstanceType  string `json:"instanceType" validate:"required"`
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
	Username      string `json:"username" validate:"required"`
	AuthDb        string `json:"authDb"` // 为方便管理用户，验证库默认为admin库
}

// DelUser 添加分片到集群
type DelUser struct {
	BaseJob
	runtime       *jobruntime.JobGenericRuntime
	BinDir        string
	Mongo         string
	OsUser        string
	PrimaryIP     string
	PrimaryPort   int
	ScriptContent string
	ConfParams    *DelUserConfParams
}

// NewDelUser 实例化结构体
func NewDelUser() jobruntime.JobRunner {
	return &DelUser{}
}

// Name 获取原子任务的名字
func (d *DelUser) Name() string {
	return "delete_user"
}

// Run 运行原子任务
func (d *DelUser) Run() error {
	// 生成脚本内容
	if err := d.makeScriptContent(); err != nil {
		return err
	}

	// 执行js脚本
	if err := d.execScript(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (d *DelUser) Retry() uint {
	return 2
}

// Rollback 回滚
func (d *DelUser) Rollback() error {
	return nil
}

// Init 初始化
func (d *DelUser) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	d.runtime = runtime
	d.runtime.Logger.Info("start to init")
	d.BinDir = consts.UsrLocal
	d.Mongo = filepath.Join(d.BinDir, "mongodb", "bin", "mongo")
	d.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(d.runtime.PayloadDecoded), &d.ConfParams); err != nil {
		d.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of deleteUser fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of deleteUser fail by json.Unmarshal, error:%s", err)
	}

	// 获取primary信息
	if d.ConfParams.InstanceType == "mongos" {
		d.PrimaryIP = d.ConfParams.IP
		d.PrimaryPort = d.ConfParams.Port
	} else {
		info, err := common.AuthGetPrimaryInfo(d.Mongo, d.ConfParams.AdminUsername, d.ConfParams.AdminPassword,
			d.ConfParams.IP, d.ConfParams.Port)
		if err != nil {
			d.runtime.Logger.Error(fmt.Sprintf(
				"get primary db info of addUser fail, error:%s", err))
			return fmt.Errorf("get primary db info of addUser fail, error:%s", err)
		}
		getInfo := strings.Split(info, ":")
		d.PrimaryIP = getInfo[0]
		d.PrimaryPort, _ = strconv.Atoi(getInfo[1])
	}
	d.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := d.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (d *DelUser) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	d.runtime.Logger.Info("start to validate parameters of deleteUser")
	if err := validate.Struct(d.ConfParams); err != nil {
		d.runtime.Logger.Error(fmt.Sprintf("validate parameters of deleteUser fail, error:%s", err))
		return fmt.Errorf("validate parameters of deleteUser fail, error:%s", err)
	}
	d.runtime.Logger.Info("validate parameters of deleteUser successfully")
	return nil
}

// makeScriptContent 生成user配置内容
func (d *DelUser) makeScriptContent() error {
	d.runtime.Logger.Info("start to make deleteUser script content")
	// 判断验证db
	if d.ConfParams.AuthDb == "" {
		d.ConfParams.AuthDb = "admin"
	}

	// 获取mongo版本
	mongoName := "mongod"
	if d.ConfParams.InstanceType == "mongos" {
		mongoName = "mongos"
	}
	version, err := common.CheckMongoVersion(d.BinDir, mongoName)
	if err != nil {
		d.runtime.Logger.Error(fmt.Sprintf("check mongo version fail, error:%s", err))
		return fmt.Errorf("check mongo version fail, error:%s", err)
	}
	mainVersion, _ := strconv.Atoi(strings.Split(version, ".")[0])
	if mainVersion >= 3 {
		d.ScriptContent = strings.Join([]string{fmt.Sprintf("db.getMongo().getDB('%s')", d.ConfParams.AuthDb),
			fmt.Sprintf("dropUser('%s')", d.ConfParams.Username)}, ".")
		d.runtime.Logger.Info("make deleteUser script content successfully")
		return nil
	}
	d.ScriptContent = strings.Join([]string{fmt.Sprintf("db.getMongo().getDB('%s')", d.ConfParams.AuthDb),
		fmt.Sprintf("removeUser('%s')", d.ConfParams.Username)}, ".")
	d.runtime.Logger.Info("make deleteUser script content successfully")
	return nil
}

// execScript 执行脚本
func (d *DelUser) execScript() error {
	// 检查
	flag, err := common.AuthCheckUser(d.Mongo, d.ConfParams.AdminUsername, d.ConfParams.AdminPassword,
		d.PrimaryIP, d.PrimaryPort, d.ConfParams.AuthDb, d.ConfParams.Username)
	if err != nil {
		return err
	}
	if flag == false {
		d.runtime.Logger.Info(fmt.Sprintf("user:%s is not existed", d.ConfParams.Username))
		return nil
	}

	// 执行脚本
	d.runtime.Logger.Info("start to execute deleteUser script")
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\"",
		d.Mongo, d.ConfParams.AdminUsername, d.ConfParams.AdminPassword, d.PrimaryIP,
		d.PrimaryPort, d.ScriptContent)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		d.runtime.Logger.Error(fmt.Sprintf("execute addUser script fail, error:%s", err))
		return fmt.Errorf("execute addUser script fail, error:%s", err)
	}

	time.Sleep(2 * time.Second)

	// 检查
	flag, err = common.AuthCheckUser(d.Mongo, d.ConfParams.AdminUsername, d.ConfParams.AdminPassword,
		d.PrimaryIP, d.PrimaryPort, d.ConfParams.AuthDb, d.ConfParams.Username)
	if err != nil {
		return err
	}
	if flag == true {
		d.runtime.Logger.Error(fmt.Sprintf("delete user:%s fail, error:%s", d.ConfParams.Username, err))
		return fmt.Errorf("delete user:%s fail, error:%s", d.ConfParams.Username, err)
	}
	d.runtime.Logger.Info("execute deleteUser script successfully")
	return nil
}
