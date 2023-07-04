// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

// CommitClusterChangeComp TODO
type CommitClusterChangeComp struct {
	Params *CommitClusterChangeParam `json:"extend"`
}

// CommitClusterChangeParam TODO
type CommitClusterChangeParam struct {
	Nodes *[]string `json:"nodes" validate:"required"`
}

// CommitClusterChange 提交集群变化
func (i *CommitClusterChangeComp) CommitClusterChange() error {
	cmds := []string{
		"riak-admin cluster plan",
		"riak-admin cluster commit",
		"riak-admin transfers",
		"riak-admin transfer-limit",
		"riak-admin ring-status",
		"riak-admin cluster status",
	}
	for _, cmd := range cmds {
		res, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			logger.Error("execute shell [%s] error: %s", cmd, err.Error())
			err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
			return err
		} else {
			logger.Info("execute shell [%s] output:\n %s", cmd, res)
		}
	}
	logger.Info("commit cluster change success, begin to transfer data")
	return nil
}
