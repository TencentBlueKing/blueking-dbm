package atommongodb

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
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
	runtime            *jobruntime.JobGenericRuntime
	BinDir             string
	DataDir            string
	DbpathDir          string
	Mongo              string
	OsUser             string // MongoDB安装在哪个用户下
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
	r.runtime.Logger.Info("mongo_restart Run: begin (onlyChangeParam=%v, instance=%s, port=%d)",
		r.ConfParams.OnlyChangeParam, r.ConfParams.InstanceType, r.ConfParams.Port)

	// 修改配置文件参数
	if r.ConfParams.OnlyChangeParam {
		r.runtime.Logger.Info("mongo_restart Run: step changeParam only (no restart)")
		if err := r.changeParam(); err != nil {
			return err
		}
		r.runtime.Logger.Info("mongo_restart Run: step changeParam only finished successfully")
		return nil
	}

	r.runtime.Logger.Info("mongo_restart Run: step changeParam before restart")
	if err := r.changeParam(); err != nil {
		return err
	}
	r.runtime.Logger.Info("mongo_restart Run: step changeParam finished successfully")

	// mongod的primary进行主备切换
	r.runtime.Logger.Info("mongo_restart Run: step RsStepDown")
	if err := r.RsStepDown(); err != nil {
		return err
	}
	r.runtime.Logger.Info("mongo_restart Run: step RsStepDown finished successfully")

	// 关闭服务
	r.runtime.Logger.Info("mongo_restart Run: step shutdown")
	if err := r.shutdown(); err != nil {
		return err
	}
	r.runtime.Logger.Info("mongo_restart Run: step shutdown finished successfully")

	// 启动服务
	r.runtime.Logger.Info("mongo_restart Run: step startup")
	if err := r.startup(); err != nil {
		return err
	}
	r.runtime.Logger.Info("mongo_restart Run: step startup finished successfully")

	r.runtime.Logger.Info("mongo_restart Run: all steps completed successfully")
	return nil
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
	// 获取安装参数
	r.runtime = runtime
	r.runtime.Logger.Info("start to init")
	r.BinDir = consts.GetMongoBinDir()
	r.DataDir = consts.GetMongoDataDir()
	r.OsUser = consts.GetProcessUser()
	r.OsGroup = consts.GetProcessUserGroup()
	r.Mongo = filepath.Join(r.BinDir, "mongodb", "bin", "mongo")

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		r.runtime.Logger.Error("get parameters of mongo restart fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of mongo restart fail by json.Unmarshal, error:%s", err)
	}

	// 设置各种路径
	strPort := strconv.Itoa(r.ConfParams.Port)
	r.DbpathDir = filepath.Join(r.DataDir, "mongodata", strPort, "db")
	r.AuthConfFilePath = filepath.Join(r.DataDir, "mongodata", strPort, "mongo.conf")
	r.NoAuthConfFilePath = filepath.Join(r.DataDir, "mongodata", strPort, "noauth.conf")
	r.runtime.Logger.Info("init successfully")

	// 安装前进行校验
	if err := r.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (r *MongoRestart) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	r.runtime.Logger.Info("start to validate parameters of restart")
	if err := validate.Struct(r.ConfParams); err != nil {
		r.runtime.Logger.Error("validate parameters of restart fail, error:%s", err)
		return fmt.Errorf("validate parameters of restart fail, error:%s", err)
	}
	r.runtime.Logger.Info("validate parameters of restart successfully")
	return nil
}

// changeParam 修改参数
func (r *MongoRestart) changeParam() error {
	if r.ConfParams.InstanceType == "mongos" &&
		r.ConfParams.MongoSConfDbOld != "" && r.ConfParams.MongoSConfDbNew != "" {
		if err := r.changeConfigDb(); err != nil {
			return err
		}
		return nil
	}
	if err := r.changeCacheSizeGB(); err != nil {
		return err
	}
	return nil
}

// changeConfigDb 修改mongoS的ConfigDb参数
func (r *MongoRestart) changeConfigDb() error {
	r.runtime.Logger.Info("start to change configDB value of config file")
	// 获取配置文件内容
	readAuthConfFileContent, _ := ioutil.ReadFile(r.AuthConfFilePath)
	readNoAuthConfFileContent, _ := ioutil.ReadFile(r.NoAuthConfFilePath)

	// 修改configDB配置
	yamlAuthMongoSConf := common.NewYamlMongoSConf()
	yamlNoAuthMongoSConf := common.NewYamlMongoSConf()
	_ = yaml.Unmarshal(readAuthConfFileContent, yamlAuthMongoSConf)
	_ = yaml.Unmarshal(readNoAuthConfFileContent, yamlNoAuthMongoSConf)
	yamlAuthMongoSConf.Sharding.ConfigDB = strings.Replace(yamlAuthMongoSConf.Sharding.ConfigDB,
		r.ConfParams.MongoSConfDbOld, r.ConfParams.MongoSConfDbNew, -1)
	yamlNoAuthMongoSConf.Sharding.ConfigDB = strings.Replace(yamlNoAuthMongoSConf.Sharding.ConfigDB,
		r.ConfParams.MongoSConfDbOld, r.ConfParams.MongoSConfDbNew, -1)
	authConfFileContent, _ := yamlAuthMongoSConf.GetConfContent()
	noAuthConfFileContent, _ := yamlNoAuthMongoSConf.GetConfContent()

	// 修改authConfFile
	authConfFile, err := os.OpenFile(r.AuthConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer authConfFile.Close()
	if err != nil {
		r.runtime.Logger.Error("create auth config file fail, error:%s", err)
		return fmt.Errorf("create auth config file fail, error:%s", err)
	}
	if _, err = authConfFile.WriteString(string(authConfFileContent)); err != nil {
		r.runtime.Logger.Error("change configDB value of auth config file write content fail, error:%s", err)
		return fmt.Errorf("change configDB value of auth config file write content fail, error:%s",
			err)
	}

	// 修改noAuthConfFile
	noAuthConfFile, err := os.OpenFile(r.NoAuthConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer noAuthConfFile.Close()
	if err != nil {
		r.runtime.Logger.Error("create no auth config file fail, error:%s", err)
		return fmt.Errorf("create no auth config file fail, error:%s", err)
	}
	if _, err = noAuthConfFile.WriteString(string(noAuthConfFileContent)); err != nil {
		r.runtime.Logger.Error("change configDB value of no auth config file write content fail, error:%s", err)
		return fmt.Errorf("change configDB value of no auth config file write content fail, error:%s",
			err)
	}
	r.runtime.Logger.Info("change configDB value of config file successfully")

	return nil
}

// changeCacheSizeGB 修改CacheSizeGB
func (r *MongoRestart) changeCacheSizeGB() error {
	if r.ConfParams.CacheSizeGB == 0 {
		return nil
	}

	// 检查mongo版本
	r.runtime.Logger.Info("start to check mongo version")
	version, err := common.CheckMongoVersion(r.BinDir, "mongod")
	if err != nil {
		r.runtime.Logger.Error("check mongo version fail, error:%s", err)
		return fmt.Errorf("check mongo version fail, error:%s", err)
	}
	mainVersion, _ := strconv.Atoi(strings.Split(version, ".")[0])
	r.runtime.Logger.Info("check mongo version successfully")

	if mainVersion >= 3 {
		r.runtime.Logger.Info("start to change CacheSizeGB value of config file")
		// 获取配置文件内容
		readAuthConfFileContent, _ := ioutil.ReadFile(r.AuthConfFilePath)
		readNoAuthConfFileContent, _ := ioutil.ReadFile(r.NoAuthConfFilePath)

		// 修改CacheSizeGB大小并写入文件
		yamlAuthConfFile := common.NewYamlMongoDBConf()
		yamlNoAuthConfFile := common.NewYamlMongoDBConf()
		_ = yaml.Unmarshal(readAuthConfFileContent, &yamlAuthConfFile)
		_ = yaml.Unmarshal(readNoAuthConfFileContent, &yamlNoAuthConfFile)
		if r.ConfParams.CacheSizeGB == 0 {
			return nil
		}
		if r.ConfParams.CacheSizeGB != yamlAuthConfFile.Storage.WiredTiger.EngineConfig.CacheSizeGB {
			yamlAuthConfFile.Storage.WiredTiger.EngineConfig.CacheSizeGB = r.ConfParams.CacheSizeGB
			yamlNoAuthConfFile.Storage.WiredTiger.EngineConfig.CacheSizeGB = r.ConfParams.CacheSizeGB
			authConfFileContent, _ := yamlAuthConfFile.GetConfContent()
			noAuthConfFileContent, _ := yamlNoAuthConfFile.GetConfContent()

			// 修改authConfFile
			authConfFile, err := os.OpenFile(r.AuthConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
			defer authConfFile.Close()
			if err != nil {
				r.runtime.Logger.Error("create auth config file fail, error:%s", err)
				return fmt.Errorf("create auth config file fail, error:%s", err)
			}
			if _, err = authConfFile.WriteString(string(authConfFileContent)); err != nil {
				r.runtime.Logger.Error("change CacheSizeGB value of auth config file write content fail, error:%s", err)
				return fmt.Errorf("change CacheSizeGB value of auth config file write content fail, error:%s",
					err)
			}

			// 修改noAuthConfFile
			noAuthConfFile, err := os.OpenFile(r.NoAuthConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
			defer noAuthConfFile.Close()
			if err != nil {
				r.runtime.Logger.Error("create no auth config file fail, error:%s", err)
				return fmt.Errorf("create no auth config file fail, error:%s", err)
			}
			if _, err = noAuthConfFile.WriteString(string(noAuthConfFileContent)); err != nil {
				r.runtime.Logger.Error("change CacheSizeGB value of no auth config file write content fail, error:%s", err)
				return fmt.Errorf("change CacheSizeGB value of no auth config file write content fail, error:%s",
					err)
			}
		}
		r.runtime.Logger.Info("change CacheSizeGB value of config file successfully")
	}
	return nil
}

// checkPrimary 检查该节点是否是primary
func (r *MongoRestart) checkPrimary() (bool, error) {
	r.runtime.Logger.Info("start to check if it is primary")
	var info string
	var err error
	// 安装时无需密码验证。安装成功后需要密码验证
	if r.ConfParams.AdminUsername != "" && r.ConfParams.AdminPassword != "" {
		info, err = common.AuthGetPrimaryInfo(r.Mongo, r.ConfParams.AdminUsername,
			r.ConfParams.AdminPassword, r.ConfParams.IP, r.ConfParams.Port)
	} else {
		info, err = common.NoAuthGetPrimaryInfo(r.Mongo,
			r.ConfParams.IP, r.ConfParams.Port)
	}
	if err != nil {
		// During rolling restart, a member may temporarily fail to resolve primary (election/network jitter).
		// In this case, treat it as "not primary" so restart can continue on this node.
		if strings.Contains(err.Error(), "get primary info timeout") {
			r.runtime.Logger.Warn("get primary info timeout, treat current node as non-primary and skip stepDown")
			return false, nil
		}
		r.runtime.Logger.Error("get primary info fail, error:%s", err)
		return false, fmt.Errorf("get primary info fail, error:%s", err)
	}
	if info == fmt.Sprintf("%s:%d", r.ConfParams.IP, r.ConfParams.Port) {
		return true, nil
	}
	r.runtime.Logger.Info("check if it is primary successfully")
	return false, nil
}

// RsStepDown  主备切换
func (r *MongoRestart) RsStepDown() error {
	if r.ConfParams.InstanceType != "mongos" {
		r.runtime.Logger.Info("start to check mongod service before rsStepDown")
		flag, _, err := common.CheckMongoService(r.ConfParams.Port)
		if err != nil {
			r.runtime.Logger.Error("check mongod service fail, error:%s", err)
			return fmt.Errorf("check mongod service fail, error:%s", err)
		}
		r.runtime.Logger.Info("check mongod service before rsStepDown successfully")
		if flag == false {
			return nil
		}

		// 检查是否是primary
		flag1, err := r.checkPrimary()
		r.runtime.Logger.Info("checkPrimary %s:%d primary=%v, error:%v", r.ConfParams.IP, r.ConfParams.Port, flag1, err)
		if err != nil {
			return err
		}
		if flag1 == true {
			r.runtime.Logger.Info("start to convert primary secondary db")
			// 安装时无需密码验证。安装成功后需要密码验证
			var flag2 bool
			if r.ConfParams.AdminUsername != "" && r.ConfParams.AdminPassword != "" {
				flag2, err = common.AuthRsStepDown(r.Mongo, r.ConfParams.IP, r.ConfParams.Port,
					r.ConfParams.AdminUsername, r.ConfParams.AdminPassword)
			} else {
				flag2, err = common.NoAuthRsStepDown(r.Mongo, r.ConfParams.IP, r.ConfParams.Port)
			}
			if err != nil {
				r.runtime.Logger.Error("convert primary secondary db fail, error:%s", err)
				return fmt.Errorf("convert primary secondary db fail, error:%s", err)
			}
			if flag2 == true {
				r.runtime.Logger.Info("convert primary secondary db successfully")
				return nil
			}
		}
	}

	return nil
}

// shutdown 关闭服务
func (r *MongoRestart) shutdown() error {
	// 检查服务是否存在
	r.runtime.Logger.Info("start to check %s service", r.ConfParams.InstanceType)
	result, _, err := common.CheckMongoService(r.ConfParams.Port)
	if err != nil {
		r.runtime.Logger.Error("check %s service fail, error:%s", r.ConfParams.InstanceType, err)
		return fmt.Errorf("check %s service fail, error:%s", r.ConfParams.InstanceType, err)
	}
	if result != true {
		r.runtime.Logger.Info("%s service has been close", r.ConfParams.InstanceType)
		return nil
	}
	r.runtime.Logger.Info("check %s service successfully", r.ConfParams.InstanceType)

	// 关闭服务
	r.runtime.Logger.Info("start to shutdown %s", r.ConfParams.InstanceType)
	if err = common.ShutdownMongoProcess(
		r.runtime.Logger,
		r.ConfParams.Port,
		30*time.Second,
		false,
	); err != nil {
		r.runtime.Logger.Error("shutdown %s fail, error:%s", r.ConfParams.InstanceType, err)
		return fmt.Errorf("shutdown %s fail, error:%s", r.ConfParams.InstanceType, err)
	}
	r.runtime.Logger.Info("shutdown %s successfully", r.ConfParams.InstanceType)
	return nil
}

// startup 开启服务
func (r *MongoRestart) startup() error {
	// 检查是否已有 mongod/mongos 监听（/proc/net/tcp{,6} + pid，任意本机地址含 127.0.0.1）
	r.runtime.Logger.Info("start to check %s listener on port %d", r.ConfParams.InstanceType, r.ConfParams.Port)
	pid, procName, err := common.GetMongoPidAndNameByPort(r.ConfParams.Port)
	if err != nil {
		r.runtime.Logger.Error("check %s listener fail, error:%s", r.ConfParams.InstanceType, err)
		return fmt.Errorf("check %s listener fail, error:%s", r.ConfParams.InstanceType, err)
	}
	if pid > 0 {
		r.runtime.Logger.Info("%s service already listening (pid=%d comm=%s)", r.ConfParams.InstanceType, pid, procName)
		return nil
	}
	r.runtime.Logger.Info("no %s TCP listener on port %d, will start process", r.ConfParams.InstanceType, r.ConfParams.Port)

	// 开启服务
	r.runtime.Logger.Info("start to startup %s", r.ConfParams.InstanceType)
	if err = common.StartMongoProcess(r.BinDir, r.ConfParams.Port, r.OsUser, r.ConfParams.Auth); err != nil {
		r.runtime.Logger.Error("startup %s fail, error:%s", r.ConfParams.InstanceType, err)
		return fmt.Errorf("startup %s fail, error:%s", r.ConfParams.InstanceType, err)
	}
	r.runtime.Logger.Info("startup %s successfully", r.ConfParams.InstanceType)
	return nil
}
