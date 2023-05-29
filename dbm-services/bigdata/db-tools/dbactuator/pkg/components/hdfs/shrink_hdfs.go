package hdfs

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"
	"strings"

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

// CheckDecommissionParams TODO
type CheckDecommissionParams struct {
	Host          string `json:"host" validate:"required,ip"`
	DataNodeHosts string `json:"data_node_hosts"  validate:"required"`
	DataNodePort  int    `json:"data_node_port"`
	HttpPort      int    `json:"http_port"  validate:"required"`
	Version       string `json:"version"  validate:"required"`
	HaproxyPasswd string `json:"haproxy_passwd"`
}

// CheckDecommissionService TODO
type CheckDecommissionService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *CheckDecommissionParams
	RollBackContext rollback.RollBackObjects
}

// CheckDatanodeDecommission TODO
func (c *CheckDecommissionService) CheckDatanodeDecommission() (err error) {

	urlFormat := "http://root:%s@%s:%d/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo"
	responseBody, err := util.HttpGet(fmt.Sprintf(urlFormat, c.Params.HaproxyPasswd, c.Params.Host, c.Params.HttpPort))
	if err != nil {
		return err
	}
	var beans map[string][]NameNodeInfoBean
	if err = json.Unmarshal(responseBody, &beans); err != nil {
		logger.Error("transfer response to json failed", err.Error())
		return err
	}
	nameNodeInfoBean := beans["beans"][0]
	logger.Debug("LiveNodesStr is [%s]", nameNodeInfoBean.LiveNodesStr)
	logger.Debug("DeadNodesStr is [%s]", nameNodeInfoBean.DeadNodesStr)

	var liveNodeMap DataNodeMap
	var deadNodeMap DataNodeMap
	if err = json.Unmarshal([]byte(nameNodeInfoBean.LiveNodesStr), &liveNodeMap); err != nil {
		logger.Error("transfer LiveNodesStr to json failed", err.Error())
		return err
	}
	if err = json.Unmarshal([]byte(nameNodeInfoBean.DeadNodesStr), &deadNodeMap); err != nil {
		logger.Error("transfer DeadNodesStr to json failed", err.Error())
		return err
	}
	dnHostArr := strings.Split(c.Params.DataNodeHosts, ",")
	logger.Debug("len dnHostArr is %d", len(dnHostArr))
	datanodeDetail := make(DataNodeMap, len(dnHostArr))
	result := true
	for _, dnHost := range dnHostArr {
		if value, ok := liveNodeMap[dnHost]; ok {
			logger.Debug("node %s is in liveNodes")
			if value.AdminState == "Decommissioned" {
				value.Decommissioned = true
			} else {
				result = false
			}
			datanodeDetail[dnHost] = value
		} else if value, ok := deadNodeMap[dnHost]; ok {
			logger.Debug("node %s is in deadNodes")
			datanodeDetail[dnHost] = value
		}
	}
	if result {
		logger.Info("Datanode Decommission completed")
		return nil
	} else {
		logger.Error("Datanode Decommissioning")
		return errors.New("Datanode Decommissioning")
	}
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
