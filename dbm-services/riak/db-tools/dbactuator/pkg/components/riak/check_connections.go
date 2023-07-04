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

	"golang.org/x/exp/slog"
)

// CheckConnectionsComp TODO
type CheckConnectionsComp struct {
	Params                     *CheckConnectionsParam `json:"extend"`
	CheckConnectionsRunTimeCtx `json:"-"`
}

// CheckConnectionsParam TODO
type CheckConnectionsParam struct {
}

// CheckConnectionsRunTimeCtx 运行时上下文
type CheckConnectionsRunTimeCtx struct {
}

// CheckConnections 集群数据搬迁进度检查
func (i *CheckConnectionsComp) CheckConnections() error {
	cmd := fmt.Sprintf(`netstat -anpl|grep %d | grep "beam.smp" | grep -E -v '0.0.0.0:*'`, cst.DefaultProtobufPort)
	res, err := osutil.ExecShellCommand(false, cmd)
	// 没有连接
	if err != nil {
		slog.Info("check success, no connection")
		return nil
	}
	logger.Error("execute shell [%s] connections: %s", cmd, res)
	err = fmt.Errorf("execute shell [%s] connections: %s", cmd, res)
	return err
}
