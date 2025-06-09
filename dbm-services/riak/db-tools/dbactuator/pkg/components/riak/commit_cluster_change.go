// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"strings"
	"time"
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
		"riak-admin cluster status",
		"riak-admin transfers",
		"riak-admin transfer-limit",
		"riak-admin ring-status",
	}
	var info string
	for _, cmd := range cmds {
		time.Sleep(10 * time.Second)
		res, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			info = fmt.Sprintf("execute shell [%s] error: %s", cmd, err.Error())
			logger.Error(info)
			err = fmt.Errorf(info)
			return err
		}
		logger.Info("execute shell [%s] output:\n %s", cmd, res)
		// 指令执行失败，没有输出到stderr，而是输出到stdout，进一步检查stdout
		if cmd == "riak-admin cluster plan" && !strings.Contains(res, "Staged Changes") {
			info = "riak-admin cluster plan fail, check log"
			logger.Error(info)
			err = fmt.Errorf(info)
			return err
		}
		if cmd == "riak-admin cluster commit" && !strings.Contains(res, "Cluster changes committed") {
			info = "riak-admin cluster commit fail, check log"
			logger.Error(info)
			err = fmt.Errorf(info)
			return err
		}
	}
	logger.Info("commit cluster change success, begin to transfer data")
	return nil
}
