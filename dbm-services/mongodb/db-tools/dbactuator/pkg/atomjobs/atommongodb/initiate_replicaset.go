package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// InitConfParams 参数
type InitConfParams struct {
	IP        string          `json:"ip" validate:"required"`
	Port      int             `json:"port" validate:"required"`
	App       string          `json:"app" validate:"required"`
	SetId     string          `json:"setId" validate:"required"`
	ConfigSvr bool            `json:"configSvr"`                    // shardsvr  configsvr
	Ips       []string        `json:"ips" validate:"required"`      // ip:port
	Priority  map[string]int  `json:"priority" validate:"required"` // key->ip:port,value->priority
	Hidden    map[string]bool `json:"hidden" validate:"required"`   // key->ip:port,value->hidden(true or false)
}

// InitiateReplicaset 复制集初始化
type InitiateReplicaset struct {
	BaseJob
	runtime         *jobruntime.JobGenericRuntime
	BinDir          string
	Mongo           string
	OsUser          string
	ConfFilePath    string
	ConfFileContent string
	ConfParams      *InitConfParams
	ClusterId       string
	StatusChan      chan int
}

// NewInitiateReplicaset 实例化结构体
func NewInitiateReplicaset() jobruntime.JobRunner {
	return &InitiateReplicaset{}
}

// Name 获取原子任务的名字
func (i *InitiateReplicaset) Name() string {
	return "init_replicaset"
}

// Run 运行原子任务
func (i *InitiateReplicaset) Run() error {
	// 获取配置内容
	if err := i.makeConfContent(); err != nil {
		return err
	}

	// 生成js脚本
	if err := i.createInitiateReplicasetScript(); err != nil {
		return err
	}

	// 执行js脚本
	if err := i.execScript(); err != nil {
		return err
	}

	// 检查状态
	go i.checkStatus()

	// 获取状态
	if err := i.getStatus(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (i *InitiateReplicaset) Retry() uint {
	return 2
}

// Rollback 回滚
func (i *InitiateReplicaset) Rollback() error {
	return nil
}

// Init 初始化
func (i *InitiateReplicaset) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	i.runtime = runtime
	i.runtime.Logger.Info("start to init")
	i.BinDir = consts.UsrLocal
	i.Mongo = filepath.Join(i.BinDir, "mongodb", "bin", "mongo")
	i.OsUser = consts.GetProcessUser()
	i.ConfFilePath = filepath.Join("/", "tmp", "initiateReplicaset.js")
	i.StatusChan = make(chan int, 1)

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(i.runtime.PayloadDecoded), &i.ConfParams); err != nil {
		i.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err)
	}
	i.ClusterId = strings.Join([]string{i.ConfParams.App, i.ConfParams.SetId}, "-")
	i.runtime.Logger.Info("init successfully")

	// 进行校验
	if err := i.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (i *InitiateReplicaset) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	i.runtime.Logger.Info("start to validate parameters of initiateReplicaset")
	if err := validate.Struct(i.ConfParams); err != nil {
		i.runtime.Logger.Error(fmt.Sprintf("validate parameters of initiateReplicaset fail, error:%s", err))
		return fmt.Errorf("validate parameters of initiateReplicaset fail, error:%s", err)
	}
	i.runtime.Logger.Info("validate parameters of initiateReplicaset successfully")
	return nil
}

// makeConfContent 获取配置内容
func (i *InitiateReplicaset) makeConfContent() error {
	i.runtime.Logger.Info("start to make config content of initiateReplicaset")
	jsonConfReplicaset := common.NewJsonConfReplicaset()
	jsonConfReplicaset.Id = i.ClusterId
	for index, value := range i.ConfParams.Ips {
		member := common.NewMember()
		member.Id = index
		member.Host = i.ConfParams.Ips[index]
		member.Priority = i.ConfParams.Priority[value]
		member.Hidden = i.ConfParams.Hidden[value]
		jsonConfReplicaset.Members = append(jsonConfReplicaset.Members, member)
	}
	jsonConfReplicaset.ConfigSvr = i.ConfParams.ConfigSvr

	var err error
	confJson, err := json.Marshal(jsonConfReplicaset)
	if err != nil {
		i.runtime.Logger.Error(
			fmt.Sprintf("config content of initiateReplicaset json Marshal fial, error:%s", err))
		return fmt.Errorf("config content of initiateReplicaset json Marshal fial, error:%s", err)
	}
	i.ConfFileContent = strings.Join([]string{"var config=",
		string(confJson), "\n", "rs.initiate(config)\n"}, "")
	i.runtime.Logger.Info("make config content of initiateReplicaset successfully")
	return nil
}

// createInitiateReplicasetScript 生成js脚本
func (i *InitiateReplicaset) createInitiateReplicasetScript() error {
	i.runtime.Logger.Info("start to create initiateReplicaset script")
	confFile, err := os.OpenFile(i.ConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer confFile.Close()
	if err != nil {
		i.runtime.Logger.Error(
			fmt.Sprintf("create script file of initiateReplicaset json Marshal fail, error:%s", err))
		return fmt.Errorf("create script file of initiateReplicaset json Marshal fail, error:%s", err)
	}

	if _, err = confFile.WriteString(i.ConfFileContent); err != nil {
		i.runtime.Logger.Error(
			fmt.Sprintf("create script file of initiateReplicaset write content fail, error:%s",
				err))
		return fmt.Errorf("create script file of initiateReplicaset write content fail, error:%s",
			err)
	}
	i.runtime.Logger.Info("create initiateReplicaset script successfully")
	return nil
}

// getPrimaryInfo 检查状态
func (i *InitiateReplicaset) getPrimaryInfo() (bool, error) {
	i.runtime.Logger.Info("start to check replicaset status")
	result, err := common.InitiateReplicasetGetPrimaryInfo(i.Mongo, i.ConfParams.IP, i.ConfParams.Port)
	if err != nil {
		i.runtime.Logger.Error(fmt.Sprintf("get initiateReplicaset primary info fail, error:%s", err))
		return false, fmt.Errorf("get initiateReplicaset primary info fail, error:%s", err)
	}
	i.runtime.Logger.Info("check replicaset status successfully")
	for _, v := range i.ConfParams.Ips {
		if v == result {
			return true, nil
		}
	}

	return false, nil
}

// checkStatus 检查复制集状态
func (i *InitiateReplicaset) checkStatus() {
	for {
		result, err := common.NoAuthGetPrimaryInfo(i.Mongo, i.ConfParams.IP, i.ConfParams.Port)
		if err != nil {
			i.runtime.Logger.Error("check replicaset status fail, error:%s", err)
			fmt.Sprintf("check replicaset status fail, error:%s\n", err)
			panic(fmt.Sprintf("check replicaset status fail, error:%s\n", err.Error()))
		}
		if result != "" {
			i.StatusChan <- 1
		}
		time.Sleep(2 * time.Second)
	}
}

// execScript 执行脚本
func (i *InitiateReplicaset) execScript() error {
	// 检查
	flag, err := i.getPrimaryInfo()
	if err != nil {
		return err
	}
	if flag == true {
		i.runtime.Logger.Info("replicaset has been initiated")
		if err = i.removeScript(); err != nil {
			return err
		}

		return nil
	}

	// 执行脚本
	i.runtime.Logger.Info("start to execute initiateReplicaset script")
	cmd := fmt.Sprintf("%s --host %s --port %d --quiet %s",
		i.Mongo, "127.0.0.1", i.ConfParams.Port, i.ConfFilePath)
	if _, err = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		i.runtime.Logger.Error("execute initiateReplicaset script fail, error:%s", err)
		return fmt.Errorf("execute initiateReplicaset script fail, error:%s", err)
	}
	i.runtime.Logger.Info("execute initiateReplicaset script successfully")
	return nil
}

// getStatus 检查复制集状态，是否创建成功
func (i *InitiateReplicaset) getStatus() error {
	for {
		select {
		case status := <-i.StatusChan:
			if status == 1 {
				i.runtime.Logger.Info("initiate replicaset successfully")
				// 删除脚本
				if err := i.removeScript(); err != nil {
					return err
				}
				return nil
			}
		default:

		}
	}
}

// removeScript 删除脚本
func (i *InitiateReplicaset) removeScript() error {
	// 删除脚本
	i.runtime.Logger.Info("start to remove initiateReplicaset script")
	if err := common.RemoveFile(i.ConfFilePath); err != nil {
		i.runtime.Logger.Error(fmt.Sprintf("remove initiateReplicaset script fail, error:%s", err))
		return fmt.Errorf("remove initiateReplicaset script fail, error:%s", err)
	}
	i.runtime.Logger.Info("remove initiateReplicaset script successfully")

	return nil
}
