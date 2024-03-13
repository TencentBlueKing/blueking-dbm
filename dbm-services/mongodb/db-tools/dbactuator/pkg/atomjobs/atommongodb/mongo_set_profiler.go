package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// SetProfilerConfParams 参数
type SetProfilerConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	DbName        string `json:"dbName" validate:"required"`
	Level         int    `json:"level" validate:"required"`
	ProfileSize   int    `json:"profileSize"` // 单位：GB
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
}

// SetProfiler 添加分片到集群
type SetProfiler struct {
	BaseJob
	runtime     *jobruntime.JobGenericRuntime
	BinDir      string
	Mongo       string
	OsUser      string
	PrimaryIP   string
	PrimaryPort int
	ConfParams  *SetProfilerConfParams
}

// NewSetProfiler 实例化结构体
func NewSetProfiler() jobruntime.JobRunner {
	return &SetProfiler{}
}

// Name 获取原子任务的名字
func (s *SetProfiler) Name() string {
	return "mongo_set_profiler"
}

// Run 运行原子任务
func (s *SetProfiler) Run() error {
	// 生成script内容
	if err := s.setProfileSize(); err != nil {
		return err
	}

	// 执行脚本生成结果文件
	if err := s.setProfileLevel(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (s *SetProfiler) Retry() uint {
	return 2
}

// Rollback 回滚
func (s *SetProfiler) Rollback() error {
	return nil
}

// Init 初始化
func (s *SetProfiler) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.runtime.Logger.Info("start to init")
	s.BinDir = consts.UsrLocal
	s.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		s.runtime.Logger.Error(
			"get parameters of setProfiler fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of setProfiler fail by json.Unmarshal, error:%s", err)
	}

	// 获取primary信息
	info, err := common.AuthGetPrimaryInfo(s.Mongo, s.ConfParams.AdminUsername, s.ConfParams.AdminPassword,
		s.ConfParams.IP, s.ConfParams.Port)
	if err != nil {
		s.runtime.Logger.Error("get primary db info fail, error:%s", err)
		return fmt.Errorf("get primary db info fail, error:%s", err)
	}
	sliceInfo := strings.Split(info, ":")
	s.PrimaryIP = sliceInfo[0]
	s.PrimaryPort, _ = strconv.Atoi(sliceInfo[1])

	// 获取各种目录
	s.Mongo = filepath.Join(s.BinDir, "mongodb", "bin", "mongo")
	s.runtime.Logger.Info("init successfully")

	// 进行校验
	if err = s.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (s *SetProfiler) checkParams() error {
	// 校验配置参数
	s.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	s.runtime.Logger.Info("start to validate parameters of deInstall")
	if err := validate.Struct(s.ConfParams); err != nil {
		s.runtime.Logger.Error("validate parameters of setProfiler fail, error:%s", err)
		return fmt.Errorf("validate parameters of setProfiler fail, error:%s", err)
	}
	s.runtime.Logger.Info("validate parameters successfully")
	return nil
}

// setProfileSize 设置profile大小
func (s *SetProfiler) setProfileSize() error {
	// 获取profile级别
	status, err := common.GetProfilingLevel(s.Mongo, s.ConfParams.IP, s.ConfParams.Port,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, s.ConfParams.DbName)
	if err != nil {
		s.runtime.Logger.Error("get profile level fail, error:%s", err)
		return fmt.Errorf("get profile level fail, error:%s", err)
	}
	if status != 0 {
		if err = common.SetProfilingLevel(s.Mongo, s.ConfParams.IP, s.ConfParams.Port, s.ConfParams.AdminUsername,
			s.ConfParams.AdminPassword, s.ConfParams.DbName, 0); err != nil {
			s.runtime.Logger.Error("set profile level 0 fail, error:%s", err)
			return fmt.Errorf("set profile level 0 fail, error:%s", err)
		}
	}

	// 删除profile.system
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"db.getMongo().getDB('%s').system.profile.drop()\"",
		s.Mongo, s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, s.ConfParams.IP, s.ConfParams.Port,
		s.ConfParams.DbName)
	if _, err = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		s.runtime.Logger.Error("delete system.profile fail, error:%s", err)
		return fmt.Errorf("set system.profile fail, error:%s", err)
	}

	// 设置profile.system
	s.runtime.Logger.Info("start to set system.profile size")
	profileSizeBytes := s.ConfParams.ProfileSize * 1024 * 1024 * 1024
	cmd = fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"db.getMongo().getDB('%s').createCollection('system.profile',{ capped: true, size:%d })\"",
		s.Mongo, s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, s.ConfParams.IP, s.ConfParams.Port,
		s.ConfParams.DbName, profileSizeBytes)
	if _, err = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		s.runtime.Logger.Error("set system.profile size fail, error:%s", err)
		return fmt.Errorf("set system.profile size fail, error:%s", err)
	}
	s.runtime.Logger.Info("set system.profile size successfully")
	return nil
}

// setProfileLevel 生成脚本内容
func (s *SetProfiler) setProfileLevel() error {
	s.runtime.Logger.Info("start to set profile level")
	if err := common.SetProfilingLevel(s.Mongo, s.ConfParams.IP, s.ConfParams.Port, s.ConfParams.AdminUsername,
		s.ConfParams.AdminPassword, s.ConfParams.DbName, s.ConfParams.Level); err != nil {
		s.runtime.Logger.Error("set profile level fail, error:%s", err)
		return fmt.Errorf("set profile level fail, error:%s", err)
	}
	s.runtime.Logger.Info("set profile level successfully")
	return nil
}
