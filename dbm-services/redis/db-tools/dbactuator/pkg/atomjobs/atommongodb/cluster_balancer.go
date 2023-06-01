package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// BalancerConfParams 参数
type BalancerConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	Open          bool   `json:"open"` // true：打开 false：关闭
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
}

// Balancer 添加分片到集群
type Balancer struct {
	runtime    *jobruntime.JobGenericRuntime
	BinDir     string
	Mongo      string
	OsUser     string
	ConfParams *BalancerConfParams
}

// NewBalancer 实例化结构体
func NewBalancer() jobruntime.JobRunner {
	return &Balancer{}
}

// Name 获取原子任务的名字
func (b *Balancer) Name() string {
	return "cluster_balancer"
}

// Run 运行原子任务
func (b *Balancer) Run() error {
	// 执行脚本
	if err := b.execScript(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (b *Balancer) Retry() uint {
	return 2
}

// Rollback 回滚
func (b *Balancer) Rollback() error {
	return nil
}

// Init 初始化
func (b *Balancer) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	b.runtime = runtime
	b.runtime.Logger.Info("start to init")
	b.BinDir = consts.UsrLocal
	b.Mongo = filepath.Join(b.BinDir, "mongodb", "bin", "mongo")
	b.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(b.runtime.PayloadDecoded), &b.ConfParams); err != nil {
		b.runtime.Logger.Error(
			"get parameters of clusterBalancer fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of clusterBalancer fail by json.Unmarshal, error:%s", err)
	}
	b.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := b.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (b *Balancer) checkParams() error {
	// 校验配置参数
	validate := validator.New()
	b.runtime.Logger.Info("start to validate parameters of clusterBalancer")
	if err := validate.Struct(b.ConfParams); err != nil {
		b.runtime.Logger.Error(fmt.Sprintf("validate parameters of clusterBalancer fail, error:%s", err))
		return fmt.Errorf("validate parameters of clusterBalancer fail, error:%s", err)
	}
	b.runtime.Logger.Info("validate parameters of clusterBalancer successfully")
	return nil
}

// execScript 执行脚本
func (b *Balancer) execScript() error {
	// 检查状态
	b.runtime.Logger.Info("start to get balancer status")
	result, err := common.CheckBalancer(b.OsUser, b.Mongo, b.ConfParams.IP, b.ConfParams.Port,
		b.ConfParams.AdminUsername, b.ConfParams.AdminPassword)
	if err != nil {
		b.runtime.Logger.Error("get cluster balancer status fail, error:%s", err)
		return fmt.Errorf("get cluster balancer status fail, error:%s", err)
	}
	flag, _ := strconv.ParseBool(result)
	b.runtime.Logger.Info("get balancer status successfully")
	if flag == b.ConfParams.Open {
		b.runtime.Logger.Info("balancer status has been %t", b.ConfParams.Open)
		os.Exit(0)
	}

	// 执行脚本
	var cmd string
	if b.ConfParams.Open == true {
		cmd = fmt.Sprintf(
			"su %s -c '%s -u %s -p %s --host %s --port %d --authenticationDatabase=admin --quiet --eval \"sh.startBalancer()\"'",
			b.OsUser, b.Mongo, b.ConfParams.AdminUsername, b.ConfParams.AdminPassword, b.ConfParams.IP, b.ConfParams.Port)
	} else {
		cmd = fmt.Sprintf(
			"su %s -c '%s -u %s -p %s --host %s --port %d --authenticationDatabase=admin --quiet --eval \"sh.stopBalancer()\"'",
			b.OsUser, b.Mongo, b.ConfParams.AdminUsername, b.ConfParams.AdminPassword, b.ConfParams.IP, b.ConfParams.Port)
	}
	b.runtime.Logger.Info("start to execute script")
	_, err = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
	if err != nil {
		b.runtime.Logger.Error("set cluster balancer status fail, error:%s", err)
		return fmt.Errorf("set cluster balancer status fail, error:%s", err)
	}
	b.runtime.Logger.Info("execute script successfully")

	// 检查状态
	b.runtime.Logger.Info("start to check balancer status")
	result, err = common.CheckBalancer(b.OsUser, b.Mongo, b.ConfParams.IP, b.ConfParams.Port,
		b.ConfParams.AdminUsername, b.ConfParams.AdminPassword)
	if err != nil {
		b.runtime.Logger.Error("get cluster balancer status fail, error:%s", err)
		return fmt.Errorf("get cluster balancer status fail, error:%s", err)
	}
	flag, _ = strconv.ParseBool(result)
	b.runtime.Logger.Info("check balancer status successfully")
	if flag == b.ConfParams.Open {
		b.runtime.Logger.Info("set balancer status:%t successfully", b.ConfParams.Open)
	}

	return nil
}
