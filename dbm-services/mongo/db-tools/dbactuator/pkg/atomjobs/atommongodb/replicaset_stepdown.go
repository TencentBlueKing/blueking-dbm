package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"

	"dbm-services/mongo/db-tools/dbactuator/pkg/common"
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// StepDownConfParams 参数
type StepDownConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
}

// StepDown 添加分片到集群
type StepDown struct {
	BaseJob
	runtime     *jobruntime.JobGenericRuntime
	BinDir      string
	Mongo       string
	OsUser      string
	PrimaryIP   string
	PrimaryPort int
	ConfParams  *StepDownConfParams
}

// NewStepDown 实例化结构体
func NewStepDown() jobruntime.JobRunner {
	return &StepDown{}
}

// Name 获取原子任务的名字
func (s *StepDown) Name() string {
	return "replicaset_stepdown"
}

// Run 运行原子任务
func (s *StepDown) Run() error {
	// 执行主备切换
	if err := s.execStepDown(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (s *StepDown) Retry() uint {
	return 2
}

// Rollback 回滚
func (s *StepDown) Rollback() error {
	return nil
}

// Init 初始化
func (s *StepDown) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.runtime.Logger.Info("start to init")
	s.BinDir = consts.UsrLocal
	s.Mongo = filepath.Join(s.BinDir, "mongodb", "bin", "mongo")
	s.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of stepDown fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of stepDown fail by json.Unmarshal, error:%s", err)
	}

	// 获取primary信息
	info, err := common.AuthGetPrimaryInfo(s.Mongo, s.ConfParams.AdminUsername, s.ConfParams.AdminPassword,
		s.ConfParams.IP, s.ConfParams.Port)
	if err != nil {
		s.runtime.Logger.Error(fmt.Sprintf(
			"get primary db info of stepDown fail, error:%s", err))
		return fmt.Errorf("get primary db info of stepDown fail, error:%s", err)
	}
	getInfo := strings.Split(info, ":")
	s.PrimaryIP = getInfo[0]
	s.PrimaryPort, _ = strconv.Atoi(getInfo[1])

	// 进行校验
	s.runtime.Logger.Info("start to validate parameters")
	if err = s.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (s *StepDown) checkParams() error {
	// 校验配置参数
	validate := validator.New()
	s.runtime.Logger.Info("start to validate parameters of deleteUser")
	if err := validate.Struct(s.ConfParams); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("validate parameters of deleteUser fail, error:%s", err))
		return fmt.Errorf("validate parameters of deleteUser fail, error:%s", err)
	}
	return nil
}

// execStepDown 执行切换
func (s *StepDown) execStepDown() error {
	s.runtime.Logger.Info("start to convert primary secondary db")
	flag, err := common.AuthRsStepDown(s.Mongo, s.PrimaryIP, s.PrimaryPort, s.ConfParams.AdminUsername,
		s.ConfParams.AdminPassword)
	if err != nil {
		s.runtime.Logger.Error("convert primary secondary db fail, error:%s", err)
		return fmt.Errorf("convert primary secondary db fail, error:%s", err)
	}
	if flag == true {
		s.runtime.Logger.Info("convert primary secondary db successfully")
		return nil
	}

	return nil
}
