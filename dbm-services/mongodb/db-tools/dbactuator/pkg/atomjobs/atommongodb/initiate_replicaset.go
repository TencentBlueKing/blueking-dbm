package atommongodb

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
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
	signalMu        sync.Mutex
	primarySignaled bool
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
	if i.ConfParams == nil {
		return fmt.Errorf("initiateReplicaset: ConfParams is nil")
	}

	// 如果任何一个成员上复制集已就绪，则跳过后续 initiate（不必再写脚本、执行 rs.initiate）。
	if i.checkIfAnyNodeInitialized() {
		i.runtime.Logger.Info("some node has been initialized, skip initiate replicaset")
		return nil
	}

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

	// checkStatus 轮询前先尝试一次获取 primary，降低初始化瞬时超时报错概率。
	primaryFound := i.tryFindPrimaryBeforeCheckStatus()

	// 检查状态
	if !primaryFound {
		go i.checkStatus()
	}

	// 获取状态
	if err := i.getStatus(); err != nil {
		return err
	}

	return nil
}

// checkIfAnyNodeInitialized 遍历 members，任一节点的 repl 已选举出属于本列表的 primary 即视为复制集已初始化。
func (i *InitiateReplicaset) checkIfAnyNodeInitialized() bool {
	for _, hp := range i.ConfParams.Ips {
		host, portStr, err := net.SplitHostPort(hp)
		if err != nil {
			i.runtime.Logger.Warn("checkIfAnyNodeInitialized: invalid member address %s, error:%s", hp, err)
			continue
		}
		port, err := strconv.Atoi(portStr)
		if err != nil {
			i.runtime.Logger.Warn("checkIfAnyNodeInitialized: invalid port in %s, error:%s", hp, err)
			continue
		}
		primary, err := common.InitiateReplicasetGetPrimaryInfo(i.Mongo, host, port)
		if err != nil {
			i.runtime.Logger.Warn("checkIfAnyNodeInitialized: probe member %s fail, error:%s", hp, err)
			continue
		}
		if primary == "" {
			continue
		}
		for _, member := range i.ConfParams.Ips {
			if member == primary {
				i.runtime.Logger.Info(
					"checkIfAnyNodeInitialized: replica set already up, primary:%s (probed via %s)", primary, hp)
				return true
			}
		}
	}
	return false
}

func (i *InitiateReplicaset) tryFindPrimaryBeforeCheckStatus() bool {
	i.runtime.Logger.Info("try to find primary before checkStatus")
	result, err := common.NoAuthGetPrimaryInfo(i.Mongo, i.ConfParams.IP, i.ConfParams.Port)
	if err != nil {
		i.runtime.Logger.Warn("pre-check primary lookup failed before checkStatus, error:%s", err)
		return false
	}
	if result == "" {
		i.runtime.Logger.Warn("pre-check primary lookup returned empty before checkStatus")
		return false
	}
	i.runtime.Logger.Info("pre-check found primary:%s before checkStatus", result)
	i.signalPrimaryReadyOnce()
	return true
}

// signalPrimaryReadyOnce 向 StatusChan 发送就绪信号，可重入：仅发送一次，且避免阻塞（channel 已满时跳过）。
func (i *InitiateReplicaset) signalPrimaryReadyOnce() {
	i.signalMu.Lock()
	defer i.signalMu.Unlock()
	if i.primarySignaled {
		return
	}
	select {
	case i.StatusChan <- 1:
		i.primarySignaled = true
		i.runtime.Logger.Info("replica set primary ready signal sent")
	default:
		i.runtime.Logger.Warn("replica set primary ready signal skipped (channel busy or already signaled)")
	}
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
	i.BinDir = consts.GetMongoBinDir()
	i.Mongo = filepath.Join(i.BinDir, "mongodb", "bin", "mongo")
	i.OsUser = consts.GetProcessUser()
	i.StatusChan = make(chan int, 1)
	i.primarySignaled = false

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(i.runtime.PayloadDecoded), &i.ConfParams); err != nil {
		i.runtime.Logger.Error(
			"get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of initiateReplicaset fail by json.Unmarshal, error:%s", err)
	}
	i.ClusterId = i.ConfParams.SetId
	i.ConfFilePath = filepath.Join("/", "tmp", fmt.Sprintf("%s_initiateReplicaset.js", i.ClusterId))
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
		i.runtime.Logger.Error("validate parameters of initiateReplicaset fail, error:%s", err)
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
	localMember := fmt.Sprintf("%s:%d", i.ConfParams.IP, i.ConfParams.Port)
	for index, value := range i.ConfParams.Ips {
		member := common.NewMember()
		member.Id = index
		member.Host = value
		prio := i.ConfParams.Priority[value]
		// 提高当前执行节点的 priority，避免因 ips 数组顺序与执行节点不一致时选主错误。
		if value == localMember {
			prio++
		}
		member.Priority = prio
		member.Hidden = i.ConfParams.Hidden[value]
		jsonConfReplicaset.Members = append(jsonConfReplicaset.Members, member)
	}
	jsonConfReplicaset.ConfigSvr = i.ConfParams.ConfigSvr

	var err error
	confJson, err := json.Marshal(jsonConfReplicaset)
	if err != nil {
		i.runtime.Logger.Error(
			"config content of initiateReplicaset json Marshal fail, error:%s", err)
		return fmt.Errorf("config content of initiateReplicaset json Marshal fail, error:%s", err)
	}
	i.ConfFileContent = strings.Join([]string{"var config=",
		string(confJson), "\n", "rs.initiate(config)\n"}, "")
	i.runtime.Logger.Info("config content:\n%s", i.ConfFileContent)
	i.runtime.Logger.Info("make config content of initiateReplicaset successfully")
	return nil
}

// createInitiateReplicasetScript 生成js脚本
func (i *InitiateReplicaset) createInitiateReplicasetScript() error {
	i.runtime.Logger.Info("start to create initiateReplicaset script")
	confFile, err := os.OpenFile(i.ConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	if err != nil {
		i.runtime.Logger.Error(
			"create script file of initiateReplicaset open fail, error:%s", err)
		return fmt.Errorf("create script file of initiateReplicaset open fail, error:%s", err)
	}
	defer confFile.Close()

	if _, err = confFile.WriteString(i.ConfFileContent); err != nil {
		i.runtime.Logger.Error(
			"create script file of initiateReplicaset write content fail, error:%s", err)
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
		i.runtime.Logger.Error("get initiateReplicaset primary info fail, error:%s", err)
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
			i.runtime.Logger.Warn("check replicaset status fail, retrying, error:%s", err)
			time.Sleep(2 * time.Second)
			continue
		}
		if result != "" {
			i.signalPrimaryReadyOnce()
			return
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

		i.signalPrimaryReadyOnce()
		return nil
	}

	// 执行脚本
	i.runtime.Logger.Info("start to execute initiateReplicaset script")
	cmd := fmt.Sprintf("%s --host %s --port %d --quiet %s",
		i.Mongo, "127.0.0.1", i.ConfParams.Port, i.ConfFilePath)
	if _, err = util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second); err != nil {
		i.runtime.Logger.Error("execute initiateReplicaset script fail, error:%s", err)
		return fmt.Errorf("execute initiateReplicaset script fail, error:%s", err)
	}
	i.runtime.Logger.Info("execute initiateReplicaset script successfully")
	return nil
}

// getStatus 检查复制集状态，是否创建成功
func (i *InitiateReplicaset) getStatus() error {
	timeout := time.After(10 * time.Minute)
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
		case <-timeout:
			return fmt.Errorf("initiate replicaset timeout: no primary elected within 10 minutes")
		default:
			time.Sleep(200 * time.Millisecond)
		}
	}
}

// removeScript 删除脚本
func (i *InitiateReplicaset) removeScript() error {
	// 删除脚本
	i.runtime.Logger.Info("start to remove initiateReplicaset script")
	if err := common.RemoveFile(i.ConfFilePath); err != nil {
		i.runtime.Logger.Error("remove initiateReplicaset script fail, error:%s", err)
		return fmt.Errorf("remove initiateReplicaset script fail, error:%s", err)
	}
	i.runtime.Logger.Info("remove initiateReplicaset script successfully")

	return nil
}
