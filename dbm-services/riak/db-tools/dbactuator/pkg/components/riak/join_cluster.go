// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

// JoinClusterComp TODO
type JoinClusterComp struct {
	Params                *JoinClusterParam `json:"extend"`
	JoinClusterRunTimeCtx `json:"-"`
}

// JoinClusterParam TODO
type JoinClusterParam struct {
	DistributedCookie *string `json:"distributed_cookie" validate:"required"`
	RingSize          *string `json:"ring_size" validate:"required"`
	BaseNode          *string `json:"base_node"  validate:"required"`
}

// JoinClusterRunTimeCtx 运行时上下文
type JoinClusterRunTimeCtx struct {
	LocalIp string
}

// PreCheck 预检查
func (i *JoinClusterComp) PreCheck() error {
	var err error
	i.LocalIp, err = osutil.GetLocalIP()
	if err != nil {
		logger.Error("get local ip error: %s", err.Error())
		return err
	}
	config := map[string]string{
		"nodename":                   fmt.Sprintf("riak@%s", i.LocalIp),
		"listener.http.internal":     fmt.Sprintf("%s:%d", i.LocalIp, cst.DefaultHttpPort),
		"listener.protobuf.internal": fmt.Sprintf("%s:%d", i.LocalIp, cst.DefaultProtobufPort),
		"ring_size":                  *i.Params.RingSize,
		"distributed_cookie":         *i.Params.DistributedCookie,
	}
	err = CheckStatus(config, i.LocalIp)
	if err != nil {
		logger.Info("CheckRiakStatus error: %s", err.Error())
		return err
	}
	logger.Info("riak node status check success")
	return nil
}

// JoinCluster 节点加入集群
func (i *JoinClusterComp) JoinCluster() error {
	cmd := fmt.Sprintf("riak-admin cluster join riak@%s", *i.Params.BaseNode)
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	logger.Info("join cluster success")
	return nil
}
