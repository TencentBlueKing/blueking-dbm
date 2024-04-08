package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"

	"github.com/go-playground/validator/v10"
)

// StartProcessConfParams 开启进程参数
type StartProcessConfParams struct {
	IP           string `json:"ip" validate:"required"`
	Port         int    `json:"port" validate:"required"`
	InstanceType string `json:"instanceType" validate:"required"` // mongos mongod
	Auth         bool   `json:"auth"`                             // true->auth false->noauth
}

// MongoStartProcess 开启mongo进程
type MongoStartProcess struct {
	BaseJob
	runtime            *jobruntime.JobGenericRuntime
	BinDir             string
	DataDir            string
	DbpathDir          string
	Mongo              string
	OsUser             string // MongoDB安装在哪个用户下
	OsGroup            string
	ConfParams         *StartProcessConfParams
	AuthConfFilePath   string
	NoAuthConfFilePath string
}

// NewMongoStartProcess 实例化结构体
func NewMongoStartProcess() jobruntime.JobRunner {
	return &MongoStartProcess{}
}

// Name 获取原子任务的名字
func (s *MongoStartProcess) Name() string {
	return "mongo_start"
}

// Run 运行原子任务
func (s *MongoStartProcess) Run() error {
	// 启动服务
	if err := s.startup(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (s *MongoStartProcess) Retry() uint {
	return 2
}

// Rollback 回滚
func (s *MongoStartProcess) Rollback() error {
	return nil
}

// Init 初始化
func (s *MongoStartProcess) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.runtime.Logger.Info("start to init")
	s.BinDir = consts.UsrLocal
	s.DataDir = consts.GetMongoDataDir()
	s.OsUser = consts.GetProcessUser()
	s.OsGroup = consts.GetProcessUserGroup()
	s.Mongo = filepath.Join(s.BinDir, "mongodb", "bin", "mongo")

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of mongo restart fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of mongo restart fail by json.Unmarshal, error:%s", err)
	}

	// 设置各种路径
	strPort := strconv.Itoa(s.ConfParams.Port)
	s.DbpathDir = filepath.Join(s.DataDir, "mongodata", strPort, "db")
	s.AuthConfFilePath = filepath.Join(s.DataDir, "mongodata", strPort, "mongo.conf")
	s.NoAuthConfFilePath = filepath.Join(s.DataDir, "mongodata", strPort, "noauth.conf")
	s.runtime.Logger.Info("init successfully")

	// 安装前进行校验
	if err := s.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (s *MongoStartProcess) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	s.runtime.Logger.Info("start to validate parameters of restart")
	if err := validate.Struct(s.ConfParams); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("validate parameters of restart fail, error:%s", err))
		return fmt.Errorf("validate parameters of restart fail, error:%s", err)
	}
	s.runtime.Logger.Info("validate parameters of restart successfully")
	return nil
}

// startup 开启服务
func (s *MongoStartProcess) startup() error {
	// 检查服务是否存在
	s.runtime.Logger.Info("start to check %s service", s.ConfParams.InstanceType)
	result, _, err := common.CheckMongoService(s.ConfParams.Port)
	if err != nil {
		s.runtime.Logger.Error("check %s service fail, error:%s", s.ConfParams.InstanceType, err)
		return fmt.Errorf("check %s service fail, error:%s", s.ConfParams.InstanceType, err)
	}
	if result == true {
		s.runtime.Logger.Info("%s service has been open", s.ConfParams.InstanceType)
		return nil
	}
	s.runtime.Logger.Info("check %s service successfully", s.ConfParams.InstanceType)

	// 开启服务
	s.runtime.Logger.Info("start to startup %s", s.ConfParams.InstanceType)
	if err = common.StartMongoProcess(s.BinDir, s.ConfParams.Port, s.OsUser, s.ConfParams.Auth); err != nil {
		s.runtime.Logger.Error("startup %s fail, error:%s", s.ConfParams.InstanceType, err)
		return fmt.Errorf("startup %s fail, error:%s", s.ConfParams.InstanceType, err)
	}
	s.runtime.Logger.Info("startup %s successfully", s.ConfParams.InstanceType)
	return nil
}
