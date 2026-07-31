package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

// RestartConfParams 重启进程参数
type RestartConfParams struct {
	IP              string `json:"ip" validate:"required"`
	Port            int    `json:"port" validate:"required"`
	InstanceType    string `json:"instanceType" validate:"required"` // mongos mongod
	Auth            bool   `json:"auth"`                             // true->auth false->noauth
	CacheSizeGB     int    `json:"cacheSizeGB"`                      // 可选，重启mongod的参数
	MongoSConfDbOld string `json:"mongoSConfDbOld"`                  // 可选，ip:port
	MongoSConfDbNew string `json:"mongoSConfDbNew"`                  // 可选，ip:port
	AdminUsername   string `json:"adminUsername"`
	AdminPassword   string `json:"adminPassword"`
	OnlyChangeParam bool   `json:"onlyChangeParam"` // 是否只改变db相关参数，不重启进程
}

// MongoRestart 重启mongo进程
type MongoRestart struct {
	BaseJob
	BinDir             string
	DataDir            string
	DbpathDir          string
	Mongo              string
	OsGroup            string
	ConfParams         *RestartConfParams
	AuthConfFilePath   string
	NoAuthConfFilePath string
}

// NewMongoRestart 实例化结构体
func NewMongoRestart() jobruntime.JobRunner {
	return &MongoRestart{}
}

// Name 获取原子任务的名字
func (r *MongoRestart) Name() string {
	return "mongo_restart"
}

// Run 运行原子任务
func (r *MongoRestart) Run() error {
	r.runtime.Logger.Info("mongo_restart begin (onlyChangeParam=%v, instance=%s, port=%d)",
		r.ConfParams.OnlyChangeParam, r.ConfParams.InstanceType, r.ConfParams.Port)

	if r.ConfParams.OnlyChangeParam {
		return r.runSteps([]stepFunc{{"changeParam", r.changeParam}})
	}
	return r.runSteps([]stepFunc{
		{"changeParam", r.changeParam},
		{"RsStepDown", r.RsStepDown},
		{"shutdown", r.shutdown},
		{"startup", r.startup},
	})
}

// Retry 重试
func (r *MongoRestart) Retry() uint {
	return 2
}

// Rollback 回滚
func (r *MongoRestart) Rollback() error {
	return nil
}

// Init 初始化
func (r *MongoRestart) Init(runtime *jobruntime.JobGenericRuntime) error {
	r.runtime = runtime
	r.runtime.Logger.Info("start to init")
	r.BinDir = consts.GetMongoBinDir()
	r.DataDir = consts.GetMongoDataDir()
	r.OsUser = consts.GetProcessUser()
	r.OsGroup = consts.GetProcessUserGroup()
	r.Mongo = filepath.Join(r.BinDir, "mongodb", "bin", "mongo")

	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		return errors.Wrap(err, "unmarshal mongo restart parameters")
	}

	strPort := strconv.Itoa(r.ConfParams.Port)
	r.DbpathDir = filepath.Join(r.DataDir, "mongodata", strPort, "db")
	r.AuthConfFilePath = filepath.Join(r.DataDir, "mongodata", strPort, "mongo.conf")
	r.NoAuthConfFilePath = filepath.Join(r.DataDir, "mongodata", strPort, "noauth.conf")
	r.runtime.Logger.Info("init successfully")
	return r.checkParams()
}

func (r *MongoRestart) checkParams() error {
	r.runtime.Logger.Info("start to validate parameters of restart")
	if err := validator.New().Struct(r.ConfParams); err != nil {
		return errors.Wrap(err, "validate restart parameters")
	}
	r.runtime.Logger.Info("validate parameters of restart successfully")
	return nil
}

func (r *MongoRestart) changeParam() error {
	if r.ConfParams.InstanceType == "mongos" &&
		r.ConfParams.MongoSConfDbOld != "" && r.ConfParams.MongoSConfDbNew != "" {
		return r.changeConfigDb()
	}
	return r.changeCacheSizeGB()
}

func (r *MongoRestart) writeConfPair(authContent, noAuthContent []byte) error {
	if err := os.WriteFile(r.AuthConfFilePath, authContent, DefaultPerm); err != nil {
		return errors.Wrap(err, "write auth config")
	}
	if err := os.WriteFile(r.NoAuthConfFilePath, noAuthContent, DefaultPerm); err != nil {
		return errors.Wrap(err, "write noauth config")
	}
	return nil
}

// changeConfigDb 修改mongoS的ConfigDb参数
func (r *MongoRestart) changeConfigDb() error {
	r.runtime.Logger.Info("start to change configDB value of config file")
	authRaw, err := os.ReadFile(r.AuthConfFilePath)
	if err != nil {
		return errors.Wrap(err, "read auth config")
	}
	noAuthRaw, err := os.ReadFile(r.NoAuthConfFilePath)
	if err != nil {
		return errors.Wrap(err, "read noauth config")
	}

	authConf := common.NewYamlMongoSConf()
	noAuthConf := common.NewYamlMongoSConf()
	if err = yaml.Unmarshal(authRaw, authConf); err != nil {
		return errors.Wrap(err, "unmarshal auth mongos config")
	}
	if err = yaml.Unmarshal(noAuthRaw, noAuthConf); err != nil {
		return errors.Wrap(err, "unmarshal noauth mongos config")
	}
	authConf.Sharding.ConfigDB = strings.Replace(authConf.Sharding.ConfigDB,
		r.ConfParams.MongoSConfDbOld, r.ConfParams.MongoSConfDbNew, -1)
	noAuthConf.Sharding.ConfigDB = strings.Replace(noAuthConf.Sharding.ConfigDB,
		r.ConfParams.MongoSConfDbOld, r.ConfParams.MongoSConfDbNew, -1)

	authOut, err := authConf.GetConfContent()
	if err != nil {
		return errors.Wrap(err, "render auth mongos config")
	}
	noAuthOut, err := noAuthConf.GetConfContent()
	if err != nil {
		return errors.Wrap(err, "render noauth mongos config")
	}
	if err = r.writeConfPair(authOut, noAuthOut); err != nil {
		return err
	}
	r.runtime.Logger.Info("change configDB value of config file successfully")
	return nil
}

// changeCacheSizeGB 修改CacheSizeGB
func (r *MongoRestart) changeCacheSizeGB() error {
	if r.ConfParams.CacheSizeGB == 0 {
		return nil
	}

	r.runtime.Logger.Info("start to check mongo version")
	version, err := common.CheckMongoVersion(r.BinDir, "mongod")
	if err != nil {
		return errors.Wrap(err, "check mongo version")
	}
	mainVersion, _ := strconv.Atoi(strings.Split(version, ".")[0])
	if mainVersion < 3 {
		return nil
	}

	r.runtime.Logger.Info("start to change CacheSizeGB value of config file")
	authRaw, err := os.ReadFile(r.AuthConfFilePath)
	if err != nil {
		return errors.Wrap(err, "read auth config")
	}
	noAuthRaw, err := os.ReadFile(r.NoAuthConfFilePath)
	if err != nil {
		return errors.Wrap(err, "read noauth config")
	}

	authConf := common.NewYamlMongoDBConf()
	noAuthConf := common.NewYamlMongoDBConf()
	if err = yaml.Unmarshal(authRaw, &authConf); err != nil {
		return errors.Wrap(err, "unmarshal auth mongod config")
	}
	if err = yaml.Unmarshal(noAuthRaw, &noAuthConf); err != nil {
		return errors.Wrap(err, "unmarshal noauth mongod config")
	}
	if r.ConfParams.CacheSizeGB == authConf.Storage.WiredTiger.EngineConfig.CacheSizeGB {
		r.runtime.Logger.Info("CacheSizeGB unchanged, skip write")
		return nil
	}

	authConf.Storage.WiredTiger.EngineConfig.CacheSizeGB = r.ConfParams.CacheSizeGB
	noAuthConf.Storage.WiredTiger.EngineConfig.CacheSizeGB = r.ConfParams.CacheSizeGB
	authOut, err := authConf.GetConfContent()
	if err != nil {
		return errors.Wrap(err, "render auth mongod config")
	}
	noAuthOut, err := noAuthConf.GetConfContent()
	if err != nil {
		return errors.Wrap(err, "render noauth mongod config")
	}
	if err = r.writeConfPair(authOut, noAuthOut); err != nil {
		return err
	}
	r.runtime.Logger.Info("change CacheSizeGB value of config file successfully")
	return nil
}

// mongoListenPid 按 pid+端口判定 mongod/mongos 是否在听。
func (r *MongoRestart) mongoListenPid() (pid int, procName string, err error) {
	pid, procName, err = common.GetMongoPidAndNameByPort(r.ConfParams.Port)
	if err != nil {
		return 0, "", errors.Wrapf(err, "check %s listener on port %d", r.ConfParams.InstanceType, r.ConfParams.Port)
	}
	return pid, procName, nil
}

func (r *MongoRestart) hasAdminAuth() bool {
	return r.ConfParams.AdminUsername != "" && r.ConfParams.AdminPassword != ""
}

// checkPrimary 检查该节点是否是primary
func (r *MongoRestart) checkPrimary() (bool, error) {
	r.runtime.Logger.Info("start to check if it is primary")
	info, err := common.GetPrimaryInfo(r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
		r.ConfParams.IP, r.ConfParams.Port)
	if err != nil {
		// Rolling restart: election/network jitter may timeout; treat as non-primary and continue.
		if strings.Contains(err.Error(), "get primary info timeout") {
			r.runtime.Logger.Warn("get primary info timeout, treat current node as non-primary and skip stepDown")
			return false, nil
		}
		return false, errors.Wrap(err, "get primary info")
	}
	isPrimary := info == fmt.Sprintf("%s:%d", r.ConfParams.IP, r.ConfParams.Port)
	r.runtime.Logger.Info("checkPrimary %s:%d primary=%v", r.ConfParams.IP, r.ConfParams.Port, isPrimary)
	return isPrimary, nil
}

// RsStepDown 主备切换
func (r *MongoRestart) RsStepDown() error {
	if r.ConfParams.InstanceType == "mongos" {
		return nil
	}

	pid, _, err := r.mongoListenPid()
	if err != nil {
		return err
	}
	if pid == 0 {
		r.runtime.Logger.Info("mongod not running before rsStepDown, skip")
		return nil
	}

	isPrimary, err := r.checkPrimary()
	if err != nil || !isPrimary {
		return err
	}

	r.runtime.Logger.Info("start to stepDown primary")
	var switched bool
	if r.hasAdminAuth() {
		switched, err = common.AuthRsStepDown(r.Mongo, r.ConfParams.IP, r.ConfParams.Port,
			r.ConfParams.AdminUsername, r.ConfParams.AdminPassword)
	} else {
		switched, err = common.NoAuthRsStepDown(r.Mongo, r.ConfParams.IP, r.ConfParams.Port)
	}
	if err != nil {
		return errors.Wrap(err, "rs.stepDown")
	}
	if switched {
		r.runtime.Logger.Info("stepDown primary successfully")
	}
	return nil
}

// shutdown 关闭服务
func (r *MongoRestart) shutdown() error {
	pid, procName, err := r.mongoListenPid()
	if err != nil {
		return err
	}
	if pid == 0 {
		r.runtime.Logger.Info("%s already stopped", r.ConfParams.InstanceType)
		return nil
	}
	r.runtime.Logger.Info("shutdown %s (pid=%d comm=%s)", r.ConfParams.InstanceType, pid, procName)
	if err = common.ShutdownMongoProcess(r.runtime.Logger, r.ConfParams.Port, 30*time.Second, false); err != nil {
		return errors.Wrapf(err, "shutdown %s", r.ConfParams.InstanceType)
	}
	r.runtime.Logger.Info("shutdown %s successfully", r.ConfParams.InstanceType)
	return nil
}

// startup 开启服务
func (r *MongoRestart) startup() error {
	pid, procName, err := r.mongoListenPid()
	if err != nil {
		return err
	}
	if pid > 0 {
		r.runtime.Logger.Info("%s already listening (pid=%d comm=%s)", r.ConfParams.InstanceType, pid, procName)
		return nil
	}

	r.runtime.Logger.Info("startup %s on port %d", r.ConfParams.InstanceType, r.ConfParams.Port)
	if err = common.StartMongoProcess(r.BinDir, r.ConfParams.Port, r.OsUser, r.ConfParams.Auth); err != nil {
		return errors.Wrapf(err, "startup %s", r.ConfParams.InstanceType)
	}
	r.runtime.Logger.Info("startup %s successfully", r.ConfParams.InstanceType)
	return nil
}
