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

// NodeHiddenParams 参数
type NodeHiddenParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	HiddenIP      string `json:"hiddenip" validate:"required"`
	HiddenPort    int    `json:"hiddenport" validate:"required"`
	Hidden        bool   `json:"hidden"` // true：隐藏 false：不隐藏
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
}

// NodeHidden 节点隐藏
type NodeHidden struct {
	BaseJob
	runtime      *jobruntime.JobGenericRuntime
	BinDir       string
	Mongo        string
	OsUser       string
	ConfParams   *NodeHiddenParams
	PrimaryIP    string
	PrimaryPort  int
	HiddenHost   string
	HiddenStatus bool
}

// NewNodeHidden 实例化结构体
func NewNodeHidden() jobruntime.JobRunner {
	return &NodeHidden{}
}

// Name 获取原子任务的名字
func (n *NodeHidden) Name() string {
	return "mongod_node_hidden"
}

// Run 运行原子任务
func (n *NodeHidden) Run() error {
	// 执行脚本
	if err := n.execScript(); err != nil {
		return err
	}
	return nil
}

// Retry 重试
func (n *NodeHidden) Retry() uint {
	return 2
}

// Rollback 回滚
func (n *NodeHidden) Rollback() error {
	return nil
}

// Init 初始化
func (n *NodeHidden) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取参数
	n.runtime = runtime
	n.runtime.Logger.Info("start to init")
	n.BinDir = consts.UsrLocal
	n.Mongo = filepath.Join(n.BinDir, "mongodb", "bin", "mongo")
	n.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(n.runtime.PayloadDecoded), &n.ConfParams); err != nil {
		n.runtime.Logger.Error(
			"get parameters of nodeHidden fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of nodeHidden fail by json.Unmarshal, error:%s", err)
	}

	// 获取 primary 信息
	primaryInfo, err := common.AuthGetPrimaryInfo(n.Mongo, n.ConfParams.AdminUsername,
		n.ConfParams.AdminPassword,
		n.ConfParams.IP, n.ConfParams.Port)
	if err != nil {
		n.runtime.Logger.Error("init get primary info fail, error:%s", err)
		return fmt.Errorf("init get primary info fail, error:%s", err)
	}
	n.PrimaryIP = strings.Split(primaryInfo, ":")[0]
	n.PrimaryPort, _ = strconv.Atoi(strings.Split(primaryInfo, ":")[1])
	// 隐藏的 host
	n.HiddenHost = strings.Join([]string{n.ConfParams.HiddenIP, strconv.Itoa(n.ConfParams.HiddenPort)}, ":")

	n.runtime.Logger.Info("init successfully")

	// 进行校验
	if err = n.checkParams(); err != nil {
		return err
	}
	return nil
}

// checkParams 校验参数
func (n *NodeHidden) checkParams() error {
	// 校验配置参数
	validate := validator.New()
	n.runtime.Logger.Info("start to validate parameters of nodeHidden")
	if err := validate.Struct(n.ConfParams); err != nil {
		n.runtime.Logger.Error(fmt.Sprintf("validate parameters of nodeHidden fail, error:%s", err))
		return fmt.Errorf("validate parameters of nodeHidden fail, error:%s", err)
	}
	n.runtime.Logger.Info("validate parameters of nodeHidden successfully")
	return nil
}

// checkHidden 检查 hidden
func (n *NodeHidden) checkHidden() error {
	n.runtime.Logger.Info("start to check %s hidden status", n.HiddenHost)
	flag, _, _, hidden, _, _, err := common.GetNodeInfo(n.Mongo, n.PrimaryIP, n.PrimaryPort,
		n.ConfParams.AdminUsername, n.ConfParams.AdminPassword, n.ConfParams.HiddenIP, n.ConfParams.HiddenPort)
	if err != nil {
		n.runtime.Logger.Error("get %s hidden status fail, error:%s", n.HiddenHost, err)
		return fmt.Errorf("get %s hidden status fail, error:%s", n.HiddenHost, err)
	}
	n.HiddenStatus = hidden

	// 判断n.HiddenHost 是否存在
	if flag {
		n.runtime.Logger.Info("%s hidden current status is %t", n.HiddenHost, n.HiddenStatus)
	} else {
		n.runtime.Logger.Error("%s is not existed", n.HiddenHost)
		return fmt.Errorf("%s is not existed", n.HiddenHost)
	}
	n.runtime.Logger.Info("check %s hidden status successfully", n.HiddenHost)
	return nil
}

// execScript 执行脚本
func (n *NodeHidden) execScript() error {
	// 检查节点状态
	if err := n.checkHidden(); err != nil {
		return err
	}
	if n.HiddenStatus == n.ConfParams.Hidden {
		n.runtime.Logger.Info("%s hidden current status is %t, nothing to do", n.HiddenHost, n.HiddenStatus)
		return nil
	}
	// 编写脚本
	var script string
	n.runtime.Logger.Info("start to create script")
	if n.ConfParams.Hidden == true {
		script = strings.Replace(common.NodeHiddenTrueScript, "{{host}}", n.HiddenHost, -1)
		script = strings.Replace(script, "{{hidden}}", strconv.FormatBool(n.ConfParams.Hidden), -1)
	} else {
		script = strings.Replace(common.NodeHiddenFalseScript, "{{host}}", n.HiddenHost, -1)
		script = strings.Replace(script, "{{hidden}}", strconv.FormatBool(n.ConfParams.Hidden), -1)
	}
	n.runtime.Logger.Info("script content:\n%s", script)
	n.runtime.Logger.Info("create script successfully")

	// 执行脚本
	n.runtime.Logger.Info("start to execute script")
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\"",
		n.Mongo, n.ConfParams.AdminUsername, n.ConfParams.AdminPassword, n.PrimaryIP, n.PrimaryPort, script)
	_, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		n.runtime.Logger.Error("set %s hidden status:%t fail, error:%s", n.HiddenHost, n.ConfParams.Hidden, err)
		return fmt.Errorf("set %s hidden status:%t fail, error:%s", n.HiddenHost, n.ConfParams.Hidden, err)
	}

	n.runtime.Logger.Info("execute script successfully")

	// 间隔 5 秒
	time.Sleep(time.Second * 5)
	// 检查设置是否成功
	if err = n.checkHidden(); err != nil {
		return err
	}
	if n.HiddenStatus != n.ConfParams.Hidden {
		n.runtime.Logger.Error("%s set hidden status:%t fail, current status is %t", n.HiddenHost, n.ConfParams.Hidden,
			n.HiddenStatus)
		return fmt.Errorf("%s set hidden status:%t fail, current status is %t", n.HiddenHost, n.ConfParams.Hidden,
			n.HiddenStatus)
	}
	n.runtime.Logger.Info("set %s hidden status:%t successfully", n.HiddenHost, n.ConfParams.Hidden)
	return nil
}
