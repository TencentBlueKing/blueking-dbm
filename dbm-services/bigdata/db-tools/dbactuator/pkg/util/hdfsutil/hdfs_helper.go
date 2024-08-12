package hdfsutil

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"strings"

	"github.com/pkg/errors"
)

// HdfsGetConf HDFS获取配置
func HdfsGetConf(confName string) (string, error) {
	return osutil.ExecShellCommand(false,
		fmt.Sprintf("hdfs getconf -confKey %s | xargs echo -n", confName))
}

// GetServiceState 获取NameNode服务状态(主/备)
func GetServiceState(serviceId string) (string, error) {
	return osutil.ExecShellCommand(false,
		fmt.Sprintf("hdfs haadmin -getServiceState %s | xargs echo -n", serviceId))
}

// GetActiveNameNodeHost 获取当前主NN节点的域名
func GetActiveNameNodeHost(clusterName string) (string, error) {
	logger.Info("clusterName is %s", clusterName)
	// 1. hdfs getconf -confKey dfs.ha.namenodes.${clusterName} 获取NN列表
	nnIds, err := HdfsGetConf("dfs.ha.namenodes." + clusterName)
	if err != nil {
		logger.Error("get nn list failed, %s", clusterName, err.Error())
		return "", err
	}
	logger.Info("get conf result is %s", nnIds)
	nnList := strings.Split(nnIds, ",")
	activeNnId := ""
	for _, nn := range nnList {
		logger.Info("bianli nn id is %s", nn)
		state, err := GetServiceState(nn)
		logger.Info("nn id %s, state is %s", nn, state)
		if err != nil {
			logger.Error("get service state failed, %s %s", clusterName, nn, err.Error())
		} else if state == "active" {
			activeNnId = nn
			break
		}
	}
	if util.IsEmpty(activeNnId) {
		logger.Error("no one nn is active, %s", clusterName)
		return "", errors.New("no one nn is active")
	} else {
		logger.Info("activeNnId is %s", activeNnId)
		confName := fmt.Sprintf("dfs.namenode.rpc-address.%s.%s", clusterName, activeNnId)
		confValue, err := HdfsGetConf(confName)
		if err != nil {
			logger.Error("get active nn host conf failed, confName is %s", confName, err.Error())
			return "", err
		} else {
			return strings.Split(confValue, ":")[0], nil
		}
	}
}

// GetActiveNNWithoutClusterName 获取当前主NN节点的域名, 不通过集群名, 兼容flow修改前参数
func GetActiveNNWithoutClusterName() (string, error) {
	clusterName, err := HdfsGetConf("dfs.nameservices")
	logger.Info("enter this way")
	if err != nil || util.IsEmpty(clusterName) {
		return "", err
	} else {
		logger.Info("GetActiveNNWithoutClusterName %s", clusterName)
		return GetActiveNameNodeHost(clusterName)
	}
}
