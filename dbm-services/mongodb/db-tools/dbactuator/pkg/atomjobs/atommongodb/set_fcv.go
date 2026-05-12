package atommongodb

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// SetFCVConfParams 设置FCV参数
type SetFCVConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	OldFCV        string `json:"old_fcv" validate:"required"`
	NewFCV        string `json:"new_fcv" validate:"required"`
	InstanceType  string `json:"instanceType" validate:"required"` // mongos mongod
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
}

// MongoSetFCV 设置FCV
type MongoSetFCV struct {
	BaseJob
	runtime    *jobruntime.JobGenericRuntime
	BinDir     string
	Mongo      string
	ExecIP     string
	ExecPort   int
	ConfParams *SetFCVConfParams
}

// NewMongoSetFCV 实例化结构体
func NewMongoSetFCV() jobruntime.JobRunner {
	return &MongoSetFCV{}
}

// Name 获取原子任务的名字
func (v *MongoSetFCV) Name() string {
	return "mongo_set_fcv"
}

// Run 运行原子任务
func (v *MongoSetFCV) Run() error {
	// 检查老FCV参数
	if err := v.checkOldFCV(); err != nil {
		return err
	}

	// 设置FCV参数
	if err := v.setParam(); err != nil {
		return err
	}

	// 检查新FCV参数
	if err := v.checkNewFCV(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (v *MongoSetFCV) Retry() uint {
	return 2
}

// Rollback 回滚
func (v *MongoSetFCV) Rollback() error {
	return nil
}

// Init 初始化
func (v *MongoSetFCV) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	v.runtime = runtime
	v.runtime.Logger.Info("start to init")
	v.BinDir = consts.GetMongoBinDir()
	v.Mongo = filepath.Join(v.BinDir, "mongodb", "bin", "mongo")

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(v.runtime.PayloadDecoded), &v.ConfParams); err != nil {
		v.runtime.Logger.Error("get parameters of mongo restart fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of setting fcv fail by json.Unmarshal, error:%w", err)
	}
	v.ExecIP = v.ConfParams.IP
	v.ExecPort = v.ConfParams.Port
	if v.ConfParams.InstanceType == "mongod" {
		// 获取primary信息
		info, err := common.AuthGetPrimaryInfo(v.Mongo, v.ConfParams.AdminUsername, v.ConfParams.AdminPassword,
			v.ConfParams.IP, v.ConfParams.Port)
		if err != nil {
			v.runtime.Logger.Error("get primary db info of setting fcv fail, error:%s", err)
			return fmt.Errorf("get primary db info of setting fcv fail, error:%w", err)
		}
		// 判断info是否为null
		if info == "" {
			const msg = "get primary db info of setting fcv fail: empty primary address"
			v.runtime.Logger.Error("%s", msg)
			return fmt.Errorf("%s", msg)
		}
		getInfo := strings.Split(info, ":")
		v.ExecIP = getInfo[0]
		v.ExecPort, _ = strconv.Atoi(getInfo[1])
	}

	v.runtime.Logger.Info("init successfully")

	// 安装前进行校验
	if err := v.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (v *MongoSetFCV) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	v.runtime.Logger.Info("start to validate parameters of setting fcv")
	if err := validate.Struct(v.ConfParams); err != nil {
		v.runtime.Logger.Error("validate parameters of setting fcv fail, error:%s", err)
		return fmt.Errorf("validate parameters of setting fcv fail, error:%w", err)
	}
	v.runtime.Logger.Info("validate parameters of setting fcv successfully")
	return nil
}

// checkOldFCV 检查老的FCV的值
func (v *MongoSetFCV) checkOldFCV() error {
	v.runtime.Logger.Info("start to check old fcv parameter")
	fcv, err := common.GetFCV(v.Mongo, v.ExecIP, v.ExecPort, v.ConfParams.AdminUsername, v.ConfParams.AdminPassword)
	if err != nil {
		v.runtime.Logger.Error("get old fcv of %s fail, error:%v", v.ExecIP, err)
		return fmt.Errorf("get old fcv of %s fail: %w", v.ExecIP, err)
	}
	if fcv != v.ConfParams.OldFCV {
		v.runtime.Logger.Error("current fcv is not equal to old fcv: %s, expected: %s", fcv, v.ConfParams.OldFCV)
		return fmt.Errorf("current fcv is not equal to old fcv: %s, expected: %s", fcv, v.ConfParams.OldFCV)
	}
	v.runtime.Logger.Info("check old fcv parameter successfully, current: %s, expected: %s", fcv, v.ConfParams.OldFCV)
	return nil
}

// checkNewFCV 检查老的FCV的值
func (v *MongoSetFCV) checkNewFCV() error {
	v.runtime.Logger.Info("start to check new fcv parameter")
	fcv, err := common.GetFCV(v.Mongo, v.ExecIP, v.ExecPort, v.ConfParams.AdminUsername, v.ConfParams.AdminPassword)
	if err != nil {
		v.runtime.Logger.Error("get new fcv of %s fail, error:%v", v.ExecIP, err)
		return fmt.Errorf("get new fcv of %s fail: %w", v.ExecIP, err)
	}
	if fcv != v.ConfParams.NewFCV {
		v.runtime.Logger.Error("current fcv is not equal to new fcv: %s, expected: %s", fcv, v.ConfParams.NewFCV)
		return fmt.Errorf("current fcv is not equal to new fcv: %s, expected: %s", fcv, v.ConfParams.NewFCV)
	}
	v.runtime.Logger.Info("check new fcv parameter successfully, current: %s, expected: %s", fcv, v.ConfParams.NewFCV)
	return nil
}

// setParam 设置FCV参数
func (v *MongoSetFCV) setParam() error {
	v.runtime.Logger.Info("start to set fcv parameter")
	setFcv := common.SetFcv{}
	setFcv.SetFeatureCompatibilityVersion = v.ConfParams.NewFCV
	fcvFloat64, _ := strconv.ParseFloat(v.ConfParams.NewFCV, 64)
	if fcvFloat64 >= 7 {
		setFcv.Confirm = true
	}
	setFcvByte, err := json.Marshal(setFcv)
	if err != nil {
		v.runtime.Logger.Error("marshal setFcv fail, error:%s", err)
		return fmt.Errorf("marshal setFcv fail: %w", err)
	}
	evalScript := "db.adminCommand(" + string(setFcvByte) + ")"
	_, err = mycmd.New(
		v.Mongo,
		"-u", v.ConfParams.AdminUsername,
		"-p", mycmd.Password(v.ConfParams.AdminPassword),
		"--host", v.ExecIP,
		"--port", strconv.Itoa(v.ExecPort),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", evalScript,
		"admin",
	).Run(120 * time.Second)
	if err != nil {
		v.runtime.Logger.Error("set fcv parameter fail, error:%v", err)
		return fmt.Errorf("set fcv parameter fail: %w", err)
	}
	v.runtime.Logger.Info("set fcv parameter successfully")
	return nil
}
