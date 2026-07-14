package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/go-playground/validator/v10"
)

const (
	defaultTargetRsProtocolVersion = 1
	minFcvForRsProtocolUpgrade     = 3.6
)

// UpgradeRsProtocolParams 升级副本集 replication protocol version 参数
type UpgradeRsProtocolParams struct {
	IP                    string `json:"ip" validate:"required"`
	Port                  int    `json:"port" validate:"required"`
	InstanceType          string `json:"instanceType" validate:"required"` // mongod / mongos
	AdminUsername         string `json:"adminUsername" validate:"required"`
	AdminPassword         string `json:"adminPassword" validate:"required"`
	TargetProtocolVersion int    `json:"targetProtocolVersion"`
}

// MongoUpgradeRsProtocol 在 MongoDB 4.0 升级前将 protocolVersion 从 0 升到 1
type MongoUpgradeRsProtocol struct {
	BaseJob
	runtime    *jobruntime.JobGenericRuntime
	BinDir     string
	Mongo      string
	ExecIP     string
	ExecPort   int
	ConfParams *UpgradeRsProtocolParams
}

// NewMongoUpgradeRsProtocol 实例化结构体
func NewMongoUpgradeRsProtocol() jobruntime.JobRunner {
	return &MongoUpgradeRsProtocol{}
}

// Name 获取原子任务的名字
func (v *MongoUpgradeRsProtocol) Name() string {
	return "mongo_upgrade_rs_protocol"
}

func (p *UpgradeRsProtocolParams) targetProtocolVersion() int {
	if p.TargetProtocolVersion <= 0 {
		return defaultTargetRsProtocolVersion
	}
	return p.TargetProtocolVersion
}

func fcvAtLeast(fcv string, min float64) (bool, error) {
	fcvVal, err := strconv.ParseFloat(fcv, 64)
	if err != nil {
		return false, fmt.Errorf("parse fcv %q: %w", fcv, err)
	}
	return fcvVal >= min, nil
}

// Run 运行原子任务
func (v *MongoUpgradeRsProtocol) Run() error {
	if v.ConfParams.InstanceType != "mongod" {
		v.runtime.Logger.Info(
			"skip mongo_upgrade_rs_protocol: instanceType=%s (replica set protocol upgrade applies to mongod only)",
			v.ConfParams.InstanceType,
		)
		return nil
	}

	target := v.ConfParams.targetProtocolVersion()
	rsOp := common.NewRsOp()
	primaryInst := common.NewInstance(
		v.ExecIP, v.ExecPort, v.ConfParams.AdminUsername, v.ConfParams.AdminPassword, "mongod",
	)

	conf, err := rsOp.GetRsConf(primaryInst)
	if err != nil {
		v.runtime.Logger.Error("get rs config fail, error:%s", err)
		return fmt.Errorf("get rs config fail: %w", err)
	}
	current := conf.Config.ProtocolVersion
	if current >= target {
		v.runtime.Logger.Info(
			"skip mongo_upgrade_rs_protocol: protocolVersion=%d already >= target=%d (set=%s)",
			current, target, conf.Config.Id,
		)
		return nil
	}

	fcv, err := common.GetFCV(v.Mongo, v.ExecIP, v.ExecPort, v.ConfParams.AdminUsername, v.ConfParams.AdminPassword)
	if err != nil {
		v.runtime.Logger.Error("get fcv before protocol upgrade fail, error:%s", err)
		return fmt.Errorf("get fcv before protocol upgrade fail: %w", err)
	}
	ok, err := fcvAtLeast(fcv, minFcvForRsProtocolUpgrade)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf(
			"fcv %s must be >= %.1f before upgrading replication protocol to %d",
			fcv, minFcvForRsProtocolUpgrade, target,
		)
	}

	v.runtime.Logger.Info(
		"upgrade replication protocolVersion for set=%s: %d -> %d (fcv=%s)",
		conf.Config.Id, current, target, fcv,
	)
	conf.Config.ProtocolVersion = target
	out, err := rsOp.ReConfig(primaryInst, &conf.Config, 120)
	if err != nil {
		v.runtime.Logger.Error("replSetReconfig protocolVersion fail, error:%s", err)
		return fmt.Errorf("replSetReconfig protocolVersion fail: %w", err)
	}
	if out.Ok != 1 {
		return fmt.Errorf("replSetReconfig protocolVersion failed: ok=%d", out.Ok)
	}

	verifyConf, err := rsOp.GetRsConf(primaryInst)
	if err != nil {
		return fmt.Errorf("verify rs config after protocol upgrade fail: %w", err)
	}
	if verifyConf.Config.ProtocolVersion < target {
		return fmt.Errorf(
			"protocolVersion still %d after reconfig, expected >= %d",
			verifyConf.Config.ProtocolVersion, target,
		)
	}
	v.runtime.Logger.Info(
		"upgrade replication protocolVersion successfully for set=%s: protocolVersion=%d",
		verifyConf.Config.Id, verifyConf.Config.ProtocolVersion,
	)
	return nil
}

// Retry 重试
func (v *MongoUpgradeRsProtocol) Retry() uint {
	return 2
}

// Init 初始化
func (v *MongoUpgradeRsProtocol) Init(runtime *jobruntime.JobGenericRuntime) error {
	v.runtime = runtime
	v.runtime.Logger.Info("start to init mongo_upgrade_rs_protocol")
	v.BinDir = consts.GetMongoBinDir()
	v.Mongo = filepath.Join(v.BinDir, "mongodb", "bin", "mongo")

	if err := json.Unmarshal([]byte(v.runtime.PayloadDecoded), &v.ConfParams); err != nil {
		v.runtime.Logger.Error("unmarshal mongo_upgrade_rs_protocol payload fail, error:%s", err)
		return fmt.Errorf("unmarshal mongo_upgrade_rs_protocol payload fail: %w", err)
	}
	v.ExecIP = v.ConfParams.IP
	v.ExecPort = v.ConfParams.Port
	if v.ConfParams.InstanceType == "mongod" {
		info, err := common.AuthGetPrimaryInfo(
			v.Mongo, v.ConfParams.AdminUsername, v.ConfParams.AdminPassword, v.ConfParams.IP, v.ConfParams.Port,
		)
		if err != nil {
			v.runtime.Logger.Error("get primary for protocol upgrade fail, error:%s", err)
			return fmt.Errorf("get primary for protocol upgrade fail: %w", err)
		}
		if info == "" {
			const msg = "get primary for protocol upgrade fail: empty primary address"
			v.runtime.Logger.Error("%s", msg)
			return fmt.Errorf("%s", msg)
		}
		parts := strings.Split(info, ":")
		if len(parts) != 2 {
			v.runtime.Logger.Error("get primary for protocol upgrade fail: invalid primary address %q", info)
			return fmt.Errorf("get primary for protocol upgrade fail: invalid primary address %q", info)
		}
		v.ExecIP = parts[0]
		portVal, err := strconv.Atoi(parts[1])
		if err != nil {
			v.runtime.Logger.Error("get primary for protocol upgrade fail: invalid port in %q, error:%s", info, err)
			return fmt.Errorf("get primary for protocol upgrade fail: invalid port in %q: %w", info, err)
		}
		v.ExecPort = portVal
	}

	validate := validator.New()
	if err := validate.Struct(v.ConfParams); err != nil {
		v.runtime.Logger.Error("validate mongo_upgrade_rs_protocol params fail, error:%s", err)
		return fmt.Errorf("validate mongo_upgrade_rs_protocol params fail: %w", err)
	}
	v.runtime.Logger.Info("init mongo_upgrade_rs_protocol successfully, exec=%s:%d", v.ExecIP, v.ExecPort)
	return nil
}
