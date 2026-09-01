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
	logger.Info("get active namenode host, nameservices is %s", clusterName)
	// 1. hdfs getconf -confKey dfs.ha.namenodes.${clusterName} 获取NN列表
	nnIds, err := HdfsGetConf("dfs.ha.namenodes." + clusterName)
	if err != nil {
		logger.Error("get namenode list of %s failed, %s", clusterName, err.Error())
		return "", err
	}
	logger.Info("namenode ids of %s are [%s]", clusterName, nnIds)
	nnList := strings.Split(nnIds, ",")
	activeNnId := ""
	for _, nn := range nnList {
		state, err := GetServiceState(nn)
		if err != nil {
			logger.Error("get service state of namenode %s.%s failed, %s", clusterName, nn, err.Error())
			continue
		}
		logger.Info("namenode %s state is %s", nn, state)
		if state == "active" {
			activeNnId = nn
			break
		}
	}
	if util.IsEmpty(activeNnId) {
		logger.Error("no active namenode found in nameservices %s", clusterName)
		return "", errors.New("no one nn is active")
	}
	logger.Info("active namenode id is %s", activeNnId)
	confName := fmt.Sprintf("dfs.namenode.rpc-address.%s.%s", clusterName, activeNnId)
	confValue, err := HdfsGetConf(confName)
	if err != nil {
		logger.Error("get conf %s failed, %s", confName, err.Error())
		return "", err
	}
	// 与 GetActiveNNWithoutClusterName 保持一致：HdfsGetConf 成功但返回空串时必须显式造错，
	// 否则 strings.Split("", ":")[0] 会把空 host 静默传给调用方，掩盖真实的配置缺失。
	if util.IsEmpty(confValue) {
		logger.Error("conf %s is empty", confName)
		return "", fmt.Errorf("conf %s is empty", confName)
	}
	return strings.Split(confValue, ":")[0], nil
}

// GetActiveNNWithoutClusterName 获取当前主NN节点的域名, 不通过集群名, 兼容flow修改前参数
func GetActiveNNWithoutClusterName() (string, error) {
	clusterName, err := HdfsGetConf("dfs.nameservices")
	if err != nil {
		logger.Error("get conf dfs.nameservices failed, %s", err.Error())
		return "", err
	}
	// HdfsGetConf 成功但返回空字符串时，必须显式造错，避免把空 host 静默传给调用方；
	// 否则上游会拿着空 host 去拼 JMX URL（http://root:xxx@:port/...），最终报出的
	// "connection refused / no such host" 会掩盖 "dfs.nameservices 未配置" 这个真实根因。
	if util.IsEmpty(clusterName) {
		logger.Error("conf dfs.nameservices is empty, hdfs client may be misconfigured")
		return "", errors.New("conf dfs.nameservices is empty")
	}
	logger.Info("get conf dfs.nameservices is %s", clusterName)
	return GetActiveNameNodeHost(clusterName)
}
