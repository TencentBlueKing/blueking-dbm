package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// AddConfParams 参数
type AddConfParams struct {
	IP            string            `json:"ip" validate:"required"`
	Port          int               `json:"port" validate:"required"`
	AdminUsername string            `json:"adminUsername" validate:"required"`
	AdminPassword string            `json:"adminPassword" validate:"required"`
	Shards        map[string]string `json:"shard" validate:"required"` // key->clusterId,value->ip:port,ip:port  不包含隐藏节点
}

// AddShardToCluster 添加分片到集群
type AddShardToCluster struct {
	runtime         *jobruntime.JobGenericRuntime
	BinDir          string
	Mongo           string
	OsUser          string
	ConfFilePath    string
	ConfFileContent string
	ConfParams      *AddConfParams
}

// NewAddShardToCluster 实例化结构体
func NewAddShardToCluster() jobruntime.JobRunner {
	return &AddShardToCluster{}
}

// Name 获取原子任务的名字
func (a *AddShardToCluster) Name() string {
	return "add_shard_to_cluster"
}

// Run 运行原子任务
func (a *AddShardToCluster) Run() error {
	// 获取配置内容
	if err := a.makeConfContent(); err != nil {
		return err
	}

	// 生成js脚本
	if err := a.createAddShardToClusterScript(); err != nil {
		return err
	}

	// 执行js脚本
	if err := a.execScript(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (a *AddShardToCluster) Retry() uint {
	return 2
}

// Rollback 回滚
func (a *AddShardToCluster) Rollback() error {
	return nil
}

// Init 初始化
func (a *AddShardToCluster) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	a.runtime = runtime
	a.runtime.Logger.Info("start to init")
	a.BinDir = consts.UsrLocal
	a.Mongo = filepath.Join(a.BinDir, "mongodb", "bin", "mongo")
	a.ConfFilePath = filepath.Join("/", "tmp", "addShardToCluster.js")
	a.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(a.runtime.PayloadDecoded), &a.ConfParams); err != nil {
		a.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err)
	}
	a.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := a.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (a *AddShardToCluster) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	a.runtime.Logger.Info("start to validate parameters of addShardToCluster")
	if err := validate.Struct(a.ConfParams); err != nil {
		a.runtime.Logger.Error(fmt.Sprintf("validate parameters of addShardToCluster fail, error:%s", err))
		return fmt.Errorf("validate parameters of addShardToCluster fail, error:%s", err)
	}
	a.runtime.Logger.Info("validate parameters of addShardToCluster successfully")
	return nil
}

// makeConfContent 生成配置内容
func (a *AddShardToCluster) makeConfContent() error {
	a.runtime.Logger.Info("start to make config content of addShardToCluster")
	var shards []string
	for key, value := range a.ConfParams.Shards {
		shards = append(shards, strings.Join([]string{key, "/", value}, ""))
	}

	for _, v := range shards {
		a.ConfFileContent += strings.Join([]string{"sh.addShard(\"", v, "\")\n"}, "")
	}
	a.runtime.Logger.Info("make config content of addShardToCluster successfully")
	return nil
}

// createAddShardToClusterScript 生成js脚本
func (a *AddShardToCluster) createAddShardToClusterScript() error {
	a.runtime.Logger.Info("start to create addShardToCluster script")
	confFile, err := os.OpenFile(a.ConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer confFile.Close()
	if err != nil {
		a.runtime.Logger.Error(
			fmt.Sprintf("create script file of addShardToCluster fail, error:%s", err))
		return fmt.Errorf("create script file of addShardToCluster fail, error:%s", err)
	}

	if _, err = confFile.WriteString(a.ConfFileContent); err != nil {
		a.runtime.Logger.Error(
			fmt.Sprintf("create script file of addShardToCluster write content fail, error:%s",
				err))
		return fmt.Errorf("create script file of addShardToCluster write content fail, error:%s",
			err)
	}
	a.runtime.Logger.Info("create addShardToCluster script successfully")
	return nil
}

// checkShard 检查shard是否已经加入到cluster中
func (a *AddShardToCluster) checkShard() (bool, error) {
	a.runtime.Logger.Info("start to check shard")
	cmd := fmt.Sprintf(
		"su %s -c '%s -u %s -p %s --host %s --port %d --quiet --authenticationDatabase=admin --eval \"db.getMongo().getDB(\\\"config\\\").shards.find()\" admin'",
		a.OsUser, a.Mongo, a.ConfParams.AdminUsername, a.ConfParams.AdminPassword, a.ConfParams.IP, a.ConfParams.Port)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
	if err != nil {
		a.runtime.Logger.Error(fmt.Sprintf("get shard info fail, error:%s", err))
		return false, fmt.Errorf("get shard info fail, error:%s", err)
	}
	result = strings.Replace(result, "\n", "", -1)
	if result == "" {
		a.runtime.Logger.Info("check shard successfully")
		return false, nil
	}

	for k, _ := range a.ConfParams.Shards {

		if strings.Contains(result, k) {
			continue
		}

		return false, fmt.Errorf("add shard %s fail", k)
	}
	a.runtime.Logger.Info("check shard successfully")
	return true, nil
}

// execScript 执行脚本
func (a *AddShardToCluster) execScript() error {
	// 检查
	flag, err := a.checkShard()
	if err != nil {
		return err
	}
	if flag == true {
		a.runtime.Logger.Info(fmt.Sprintf("shards have been added"))
		// 删除脚本
		if err = a.removeScript(); err != nil {
			return err
		}

		return nil
	}

	// 执行脚本
	a.runtime.Logger.Info("start to execute addShardToCluster script")
	cmd := fmt.Sprintf("su %s -c '%s -u %s -p %s --host %s --port %d --authenticationDatabase=admin --quiet  %s'",
		a.OsUser, a.Mongo, a.ConfParams.AdminUsername, a.ConfParams.AdminPassword, a.ConfParams.IP, a.ConfParams.Port,
		a.ConfFilePath)
	if _, err = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		a.runtime.Logger.Error(fmt.Sprintf("execute addShardToCluster script fail, error:%s", err))
		return fmt.Errorf("execute addShardToCluster script fail, error:%s", err)
	}
	a.runtime.Logger.Info("execute addShardToCluster script successfully")

	// time.Sleep(15 * time.Second)

	// 检查
	flag, err = a.checkShard()
	if err != nil {
		return err
	}
	if flag == false {
		a.runtime.Logger.Error(fmt.Sprintf("add shard fail, error:%s", err))
		return fmt.Errorf("add shard fail, error:%s", err)
	}

	// 删除脚本
	if err = a.removeScript(); err != nil {
		return err
	}

	return nil
}

// removeScript 删除脚本
func (a *AddShardToCluster) removeScript() error {
	// 删除脚本
	a.runtime.Logger.Info("start to remove addShardToCluster script")
	if err := common.RemoveFile(a.ConfFilePath); err != nil {
		a.runtime.Logger.Error(fmt.Sprintf("remove addShardToCluster script fail, error:%s", err))
		return fmt.Errorf("remove addShardToCluster script fail, error:%s", err)
	}
	a.runtime.Logger.Info("remove addShardToCluster script successfully")
	return nil
}
