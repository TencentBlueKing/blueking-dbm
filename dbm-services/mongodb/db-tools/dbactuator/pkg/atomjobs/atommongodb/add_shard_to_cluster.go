package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// AddConfParams 参数
type AddConfParams struct {
	IP            string            `json:"ip" validate:"required"`
	Port          int               `json:"port" validate:"required"`
	AdminUsername string            `json:"adminUsername" validate:"required"`
	AdminPassword string            `json:"adminPassword" validate:"required"`
	Shards        map[string]string `json:"shards" validate:"required"` // key->clusterId,value->ip:port,ip:port  不包含隐藏节点
}

// AddShardToCluster 添加分片到集群
type AddShardToCluster struct {
	BaseJob
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
	a.BinDir = consts.GetMongoBinDir()
	mongoBin, err := common.ResolveMongoShellBin(a.BinDir)
	if err != nil {
		a.runtime.Logger.Error("resolve mongo shell fail, error:%s", err)
		return fmt.Errorf("resolve mongo shell fail, error:%s", err)
	}
	a.Mongo = mongoBin
	a.ConfFilePath = filepath.Join("/", "tmp", "addShardToCluster.js")
	a.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(a.runtime.PayloadDecoded), &a.ConfParams); err != nil {
		a.runtime.Logger.Error("get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err)
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
		a.runtime.Logger.Error("validate parameters of addShardToCluster fail, error:%s", err)
		return fmt.Errorf("validate parameters of addShardToCluster fail, error:%s", err)
	}
	a.runtime.Logger.Info("validate parameters of addShardToCluster successfully")
	return nil
}

// makeConfContent 生成配置内容。set_id 形如 {cluster}-s1，按分片序号排序，避免 map 随机顺序和 s10 排在 s2 前面。
func (a *AddShardToCluster) makeConfContent() error {
	a.runtime.Logger.Info("start to make config content of addShardToCluster")
	keys := make([]string, 0, len(a.ConfParams.Shards))
	for key := range a.ConfParams.Shards {
		keys = append(keys, key)
	}
	sort.Slice(keys, func(i, j int) bool {
		return shardSetIDLess(keys[i], keys[j])
	})

	var shards []string
	for _, key := range keys {
		shards = append(shards, strings.Join([]string{key, "/", a.ConfParams.Shards[key]}, ""))
	}

	for _, v := range shards {
		a.ConfFileContent += strings.Join([]string{"sh.addShard(\"", v, "\")\n"}, "")
	}
	a.runtime.Logger.Info("make config content of addShardToCluster successfully")
	return nil
}

// shardSetIDLess 按 set_id 末尾的 -s<序号> 比较；没有序号时退回字符串顺序。
func shardSetIDLess(a, b string) bool {
	ai, aok := shardSetIndex(a)
	bi, bok := shardSetIndex(b)
	if aok && bok && ai != bi {
		return ai < bi
	}
	return a < b
}

func shardSetIndex(setID string) (int, bool) {
	i := strings.LastIndex(setID, "-s")
	if i < 0 || i+2 >= len(setID) {
		return 0, false
	}
	n, err := strconv.Atoi(setID[i+2:])
	if err != nil || n <= 0 {
		return 0, false
	}
	return n, true
}

// createAddShardToClusterScript 生成js脚本
func (a *AddShardToCluster) createAddShardToClusterScript() error {
	a.runtime.Logger.Info("start to create addShardToCluster script")
	confFile, err := os.OpenFile(a.ConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer confFile.Close()
	if err != nil {
		a.runtime.Logger.Error("create script file of addShardToCluster fail, error:%s", err)
		return fmt.Errorf("create script file of addShardToCluster fail, error:%s", err)
	}

	if _, err = confFile.WriteString(a.ConfFileContent); err != nil {
		a.runtime.Logger.Error("create script file of addShardToCluster write content fail, error:%s", err)
		return fmt.Errorf("create script file of addShardToCluster write content fail, error:%s",
			err)
	}
	a.runtime.Logger.Info("create addShardToCluster script successfully")
	return nil
}

// checkShard 检查shard是否已经加入到cluster中
func (a *AddShardToCluster) checkShard(result string) bool {
	a.runtime.Logger.Info("start to check shard")
	if result == "" {
		return false
	}
	var flag bool
	for k, _ := range a.ConfParams.Shards {
		if strings.Contains(result, k) {
			flag = true
			continue
		}
		flag = false
		a.runtime.Logger.Error("shard:%s not belongs to cluster", k)
		return flag
	}
	a.runtime.Logger.Info("check shard successfully")
	return flag
}

// execScript 执行脚本
func (a *AddShardToCluster) execScript() error {
	// 获取shard信息
	result, err := common.GetShardInfo(
		a.Mongo, a.ConfParams.IP, a.ConfParams.Port, a.ConfParams.AdminUsername, a.ConfParams.AdminPassword)
	if err != nil {
		a.runtime.Logger.Error("get shard info fail, error:%s", err)
		return fmt.Errorf("get shard info fail, error:%s", err)
	}
	// 检查
	flag := a.checkShard(result)
	if flag == true {
		a.runtime.Logger.Info("shards have been added")
		// 删除脚本
		if err = a.removeScript(); err != nil {
			return err
		}
		return nil
	}

	// 执行脚本
	a.runtime.Logger.Info("start to execute addShardToCluster script")
	if _, err = mycmd.New(
		a.Mongo,
		"-u", a.ConfParams.AdminUsername,
		"-p", mycmd.Password(a.ConfParams.AdminPassword),
		"--host", a.ConfParams.IP,
		"--port", strconv.Itoa(a.ConfParams.Port),
		"--authenticationDatabase=admin",
		"--quiet",
		a.ConfFilePath,
	).Run(1800 * time.Second); err != nil {
		a.runtime.Logger.Error("execute addShardToCluster script fail, error:%s", err)
		return fmt.Errorf("execute addShardToCluster script fail, error:%s", err)
	}
	a.runtime.Logger.Info("execute addShardToCluster script successfully")

	time.Sleep(5 * time.Second)

	// 获取 shard 信息
	result, err = common.GetShardInfo(
		a.Mongo, a.ConfParams.IP, a.ConfParams.Port, a.ConfParams.AdminUsername, a.ConfParams.AdminPassword)
	if err != nil {
		a.runtime.Logger.Error("get shard info fail, error:%s", err)
		return fmt.Errorf("get shard info fail, error:%s", err)
	}
	// 检查
	flag = a.checkShard(result)
	if flag == false {
		a.runtime.Logger.Error("add shards fail")
		return fmt.Errorf("add shards fail")
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
		a.runtime.Logger.Error("remove addShardToCluster script fail, error:%s", err)
		return fmt.Errorf("remove addShardToCluster script fail, error:%s", err)
	}
	a.runtime.Logger.Info("remove addShardToCluster script successfully")
	return nil
}
