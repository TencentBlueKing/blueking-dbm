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

// AddUserConfParams 参数
type AddUserConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	InstanceType  string `json:"instanceType" validate:"required"`
	Username      string `json:"username" validate:"required"`
	Password      string `json:"password" validate:"required"`
	AdminUsername string `json:"adminUsername"`
	AdminPassword string `json:"adminPassword"`
	AuthDb        string `json:"authDb"` // 为方便管理用户，验证库默认为admin库
	DbsPrivileges []struct {
		Db         string   `json:"db"`
		Privileges []string `json:"privileges"`
	} `json:"dbsPrivileges"` // 业务库 以及权限 [{"db":xxx,"privileges":[xxx,xxx]}]
}

// AddUser 添加分片到集群
type AddUser struct {
	BaseJob
	runtime       *jobruntime.JobGenericRuntime
	BinDir        string
	Mongo         string
	PrimaryIP     string
	PrimaryPort   int
	OsUser        string
	ScriptContent string
	ConfParams    *AddUserConfParams
}

// NewAddUser 实例化结构体
func NewAddUser() jobruntime.JobRunner {
	return &AddUser{}
}

// Name 获取原子任务的名字
func (u *AddUser) Name() string {
	return "add_user"
}

// Run 运行原子任务
func (u *AddUser) Run() error {
	// 生成脚本内容
	if err := u.makeScriptContent(); err != nil {
		return err
	}

	// 执行js脚本
	if err := u.execScript(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (u *AddUser) Retry() uint {
	return 2
}

// Rollback 回滚
func (u *AddUser) Rollback() error {
	return nil
}

// Init 初始化
func (u *AddUser) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	u.runtime = runtime
	u.runtime.Logger.Info("start to init")
	u.BinDir = consts.UsrLocal
	u.Mongo = filepath.Join(u.BinDir, "mongodb", "bin", "mongo")
	u.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(u.runtime.PayloadDecoded), &u.ConfParams); err != nil {
		u.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of addUser fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of addUser fail by json.Unmarshal, error:%s", err)
	}

	// 获取primary信息
	if u.ConfParams.InstanceType == "mongos" {
		u.PrimaryIP = u.ConfParams.IP
		u.PrimaryPort = u.ConfParams.Port
	} else {
		var info string
		var err error
		// 安装时无需密码验证。安装成功后需要密码验证
		if u.ConfParams.AdminUsername != "" && u.ConfParams.AdminPassword != "" {
			info, err = common.AuthGetPrimaryInfo(u.Mongo, u.ConfParams.AdminUsername,
				u.ConfParams.AdminPassword, u.ConfParams.IP, u.ConfParams.Port)
			if err != nil {
				u.runtime.Logger.Error(fmt.Sprintf(
					"get primary db info of addUser fail, error:%s", err))
				return fmt.Errorf("get primary db info of addUser fail, error:%s", err)
			}
			getInfo := strings.Split(info, ":")
			u.PrimaryIP = getInfo[0]
			u.PrimaryPort, _ = strconv.Atoi(getInfo[1])
		}
	}
	u.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := u.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (u *AddUser) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	u.runtime.Logger.Info("start to validate parameters of addUser")
	if err := validate.Struct(u.ConfParams); err != nil {
		u.runtime.Logger.Error(fmt.Sprintf("validate parameters of addUser fail, error:%s", err))
		return fmt.Errorf("validate parameters of addUser fail, error:%s", err)
	}
	u.runtime.Logger.Info("validate parameters of addUser successfully")
	return nil
}

// makeScriptContent 生成user配置内容
func (u *AddUser) makeScriptContent() error {
	u.runtime.Logger.Info("start to make script content")
	user := common.NewMongoUser()
	user.User = u.ConfParams.Username
	user.Pwd = u.ConfParams.Password

	// 判断验证db
	if u.ConfParams.AuthDb == "" {
		u.ConfParams.AuthDb = "admin"
	}

	for _, dbPrivileges := range u.ConfParams.DbsPrivileges {
		for _, privilege := range dbPrivileges.Privileges {
			role := common.NewMongoRole()
			role.Role = privilege
			role.Db = dbPrivileges.Db
			user.Roles = append(user.Roles, role)
		}
	}

	content, err := user.GetContent()
	if err != nil {
		u.runtime.Logger.Error(fmt.Sprintf("make config content of addUser fail, error:%s", err))
		return fmt.Errorf("make config content of addUser fail, error:%s", err)
	}
	// content = strings.Replace(content, "\"", "\\\"", -1)

	// 获取mongo版本
	mongoName := "mongod"
	if u.ConfParams.InstanceType == "mongos" {
		mongoName = "mongos"
	}
	version, err := common.CheckMongoVersion(u.BinDir, mongoName)
	if err != nil {
		u.runtime.Logger.Error(fmt.Sprintf("check mongo version fail, error:%s", err))
		return fmt.Errorf("check mongo version fail, error:%s", err)
	}
	mainVersion, _ := strconv.Atoi(strings.Split(version, ".")[0])
	if mainVersion >= 3 {
		u.ScriptContent = strings.Join([]string{"db",
			fmt.Sprintf("createUser(%s)", content)}, ".")
		u.runtime.Logger.Info("make script content successfully")
		return nil
	}
	u.ScriptContent = strings.Join([]string{"db",
		fmt.Sprintf("addUser(%s)", content)}, ".")
	u.runtime.Logger.Info("make script content successfully")

	return nil
}

// checkUser 检查用户是否存在
func (u *AddUser) checkUser() (bool, error) {
	var flag bool
	var err error
	time.Sleep(time.Second * 3)
	// 安装时检查管理用户是否存在无需密码验证。安装后检查业务用户是否存在需密码验证
	if u.ConfParams.AdminUsername != "" && u.ConfParams.AdminPassword != "" {
		flag, err = common.AuthCheckUser(u.Mongo, u.ConfParams.AdminUsername, u.ConfParams.AdminPassword,
			u.PrimaryIP, u.PrimaryPort, u.ConfParams.AuthDb, u.ConfParams.Username)
	} else {
		flag, err = common.AuthCheckUser(u.Mongo, u.ConfParams.Username, u.ConfParams.Password,
			u.ConfParams.IP, u.ConfParams.Port, u.ConfParams.AuthDb, u.ConfParams.Username)
	}
	return flag, err
}

// execScript 执行脚本
func (u *AddUser) execScript() error {
	var cmd string
	if u.ConfParams.AdminUsername != "" && u.ConfParams.AdminPassword != "" {
		// 检查用户是否存在
		flag, err := u.checkUser()
		if err != nil {
			return err
		}
		if flag == true {
			u.runtime.Logger.Info("user:%s has been existed", u.ConfParams.Username)
			return nil
		}
		cmd = fmt.Sprintf(
			"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval '%s' %s",
			u.Mongo, u.ConfParams.AdminUsername, u.ConfParams.AdminPassword, u.PrimaryIP, u.PrimaryPort,
			u.ScriptContent, u.ConfParams.AuthDb)
	} else if u.ConfParams.AdminUsername == "" && u.ConfParams.AdminPassword == "" {
		// 复制集初始化后，马上创建db管理员用户，需要等3秒
		time.Sleep(time.Second * 3)
		cmd = fmt.Sprintf(
			"%s  --host %s --port %d  --quiet --eval '%s' %s",
			u.Mongo, "127.0.0.1", u.ConfParams.Port, u.ScriptContent, u.ConfParams.AuthDb)
		if u.ConfParams.AdminUsername != "" && u.ConfParams.AdminPassword != "" {

		}
	}

	// 执行脚本
	u.runtime.Logger.Info("start to execute addUser script")
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		u.runtime.Logger.Error("execute addUser script fail, error:%s", err)
		return fmt.Errorf("execute addUser script fail, error:%s", err)
	}
	u.runtime.Logger.Info("execute addUser script successfully")

	// 检查用户是否存在
	flag, err := u.checkUser()
	if err != nil {
		return err
	}
	if flag == false {
		u.runtime.Logger.Error("add user:%s fail, error:%s", u.ConfParams.Username, err)
		return fmt.Errorf("add user:%s fail, error:%s", u.ConfParams.Username, err)
	}

	return nil
}
