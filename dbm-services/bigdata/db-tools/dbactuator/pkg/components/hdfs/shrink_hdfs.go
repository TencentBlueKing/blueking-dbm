package hdfs

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/hdfsutil"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// UpdateDfsHostParams TODO
type UpdateDfsHostParams struct {
	DataNodeHosts string `json:"data_node_hosts"  validate:"required"`
	ConfFile      string `json:"conf_file"  validate:"required"`
	Operation     string `json:"operation"  validate:"required"`
}

// UpdateDfsHostService TODO
type UpdateDfsHostService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params *UpdateDfsHostParams

	RollBackContext rollback.RollBackObjects
}

// UpdateDfsHost TODO
func (i *UpdateDfsHostService) UpdateDfsHost() (err error) {

	dnHostArr := strings.Split(i.Params.DataNodeHosts, ",")
	if i.Params.Operation == Add {
		for _, dnHost := range dnHostArr {
			executeCmd := fmt.Sprintf("echo \"%s\" >> %s", dnHost, i.Params.ConfFile)
			if _, err = osutil.ExecShellCommand(false, executeCmd); err != nil {
				logger.Error("%s execute failed, %v", executeCmd, err)
			}
		}
	} else if i.Params.Operation == Remove {
		for _, dnHost := range dnHostArr {
			executeCmd := fmt.Sprintf("sed -i '/^%s$/d' %s", dnHost, i.Params.ConfFile)
			if _, err = osutil.ExecShellCommand(false, executeCmd); err != nil {
				logger.Error("%s execute failed, %v", executeCmd, err)
			}
		}
	}
	logger.Info("update dfs hosts successfully")
	return nil
}

const (
	// CheckDecommissionRetryTimes 检查 DataNode 退役进度的最大轮询次数。
	// 单次执行最多轮询 10 次，最多发生 9 次等待，配合 CheckDecommissionWaitTime=5min，
	// 总等待时长上限约 45 分钟（外加每轮 hdfs CLI 与 HTTP 请求耗时），控制在作业平台单次脚本执行超时（3600s）以内，
	// 避免被作业平台强杀导致真实失败原因丢失。
	// 超过上限后本 actor 返回失败，由人工在 dbm 流程上重试；本检查为只读操作，可安全重复执行。
	CheckDecommissionRetryTimes = 10
	// CheckDecommissionWaitTime 每次轮询之间的等待时间
	CheckDecommissionWaitTime = 5 * time.Minute
	// DataNodeStateDecommissioned NameNode JMX 中表示 DataNode 已退役完成的 adminState 取值
	DataNodeStateDecommissioned = "Decommissioned"
)

// CheckDecommissionParams TODO
type CheckDecommissionParams struct {
	Host          string `json:"host" validate:"required,ip"`
	DataNodeHosts string `json:"data_node_hosts"  validate:"required"`
	DataNodePort  int    `json:"data_node_port"`
	HttpPort      int    `json:"http_port"  validate:"required"`
	Version       string `json:"version"  validate:"required"`
	Password      string `json:"password"`
}

// CheckDecommissionService TODO
type CheckDecommissionService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *CheckDecommissionParams
	RollBackContext rollback.RollBackObjects
}

// CheckDatanodeDecommission 循环检查 DataNode 节点退役进度，直到退役完成或超过最大重试次数。
// 每次调用 checkDatanodeDecommissionOnce 判断是否完成；
// 未完成且后面仍有重试机会时，等待 CheckDecommissionWaitTime 后继续重试，最多检查 CheckDecommissionRetryTimes 次。
func (c *CheckDecommissionService) CheckDatanodeDecommission() (err error) {
	logger.Info("start checking DataNode decommission progress, max retry %d times, interval %s",
		CheckDecommissionRetryTimes, CheckDecommissionWaitTime)

	for i := 0; i < CheckDecommissionRetryTimes; i++ {
		done, checkErr := c.checkDatanodeDecommissionOnce()
		if checkErr != nil {
			// request or parse error, return immediately without retry
			logger.Error("check DataNode decommission progress failed: %s", checkErr.Error())
			return checkErr
		}
		if done {
			logger.Info("Datanode Decommission completed")
			return nil
		}

		if i < CheckDecommissionRetryTimes-1 {
			logger.Info("Datanode is still decommissioning, check %d/%d not finished, wait %s and retry",
				i+1, CheckDecommissionRetryTimes, CheckDecommissionWaitTime)
			time.Sleep(CheckDecommissionWaitTime)
		}
	}

	return fmt.Errorf("datanode decommission still not finished after %d attempts", CheckDecommissionRetryTimes)
}

// checkDatanodeDecommissionOnce 单次检查 DataNode 节点退役进度。
// 返回值：
//   - done == true 表示 data_node_hosts 中所有节点均已退役完成（AdminState=Decommissioned 或已从 liveNodes 中消失）；
//   - done == false && err == nil 表示仍有节点处于退役中，调用方应继续重试；
//   - err != nil 表示请求/解析等异常，调用方应中止重试并返回错误。
func (c *CheckDecommissionService) checkDatanodeDecommissionOnce() (done bool, err error) {
	// 获取当前 Active NameNode 域名，用于直连 NN Web 接口查询 DataNode 退役进度
	visitHost, err := hdfsutil.GetActiveNNWithoutClusterName()
	if err != nil {
		logger.Error("get active NameNode host failed, %s", err.Error())
		return false, err
	}

	urlFormat := "http://root:%s@%s:%d/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo"
	responseBody, err := util.HttpGet(fmt.Sprintf(urlFormat, c.Params.Password, visitHost, c.Params.HttpPort))
	if err != nil {
		return false, err
	}
	var beans map[string][]NameNodeInfoBean
	if err = json.Unmarshal(responseBody, &beans); err != nil {
		logger.Error("transfer response to json failed, %s", err.Error())
		return false, err
	}
	// 同时覆盖两种异常：JSON 里没有 beans 字段（nil slice）与 "beans": []（长度 0 的非 nil slice）。
	// 前者可能是接口结构变更；后者可能是接口异常/主备切换瞬间——两者都不应直接访问 [0] 引发 panic。
	if len(beans["beans"]) == 0 {
		logger.Error("namenode jmx response has empty beans")
		return false, errors.New("namenode jmx response has empty beans")
	}
	nameNodeInfoBean := beans["beans"][0]
	logger.Debug("LiveNodesStr is [%s]", nameNodeInfoBean.LiveNodesStr)
	logger.Debug("DeadNodesStr is [%s]", nameNodeInfoBean.DeadNodesStr)

	var liveNodeMap DataNodeMap
	var deadNodeMap DataNodeMap
	if err = json.Unmarshal([]byte(nameNodeInfoBean.LiveNodesStr), &liveNodeMap); err != nil {
		logger.Error("transfer LiveNodesStr to json failed, %s", err.Error())
		return false, err
	}
	if err = json.Unmarshal([]byte(nameNodeInfoBean.DeadNodesStr), &deadNodeMap); err != nil {
		logger.Error("transfer DeadNodesStr to json failed, %s", err.Error())
		return false, err
	}
	dnHostArr := strings.Split(c.Params.DataNodeHosts, ",")
	logger.Info("check decommission progress of %d datanodes", len(dnHostArr))
	result := true
	for _, dnHost := range dnHostArr {
		if value, ok := liveNodeMap[dnHost]; ok {
			if value.AdminState == DataNodeStateDecommissioned {
				logger.Info("datanode %s is in liveNodes, adminState is %s, decommission finished",
					dnHost, value.AdminState)
			} else {
				logger.Info("datanode %s is in liveNodes, adminState is %s, still decommissioning",
					dnHost, value.AdminState)
				result = false
			}
		} else if _, ok := deadNodeMap[dnHost]; ok {
			logger.Info("datanode %s is in deadNodes, decommission finished", dnHost)
		} else {
			logger.Info("datanode %s is in neither liveNodes nor deadNodes, decommission finished", dnHost)
		}
	}
	return result, nil
}

// DataNodeMap TODO
type DataNodeMap map[string]DataNodeStruct

// DataNodeStruct TODO
type DataNodeStruct struct {
	InfoAddr       string `json:"infoAddr"`
	AdminState     string `json:"adminState"`
	TransferAddr   string `json:"xferaddr"`
	Decommissioned bool   `json:"decommissioned"`
}

// NameNodeInfoBean TODO
type NameNodeInfoBean struct {
	LiveNodesStr            string `json:"LiveNodes"`
	DeadNodesStr            string `json:"DeadNodes"`
	DecommissioningNodesStr string `json:"DecomNodes"`
}

// CheckDecommissionResult TODO
type CheckDecommissionResult struct {
	Result bool        `json:"result"`
	Detail DataNodeMap `json:"detail"`
}

// RefreshNodesParams TODO
type RefreshNodesParams struct {
	Host string `json:"host" validate:"required,ip"`
}

// RefreshNodesService TODO
type RefreshNodesService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *RefreshNodesParams
	RollBackContext rollback.RollBackObjects
}

// RefreshNodes TODO
func (r *RefreshNodesService) RefreshNodes() (err error) {
	execCommand := fmt.Sprintf("su - %s -c \"hdfs dfsadmin -refreshNodes\"", r.ExecuteUser)
	// 不检查是否执行成功
	if _, err := osutil.ExecShellCommand(false, execCommand); err != nil {
		logger.Error("[%s] execute failed, %v", execCommand, err)
	}
	return nil
}
