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
	"strings"

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
	localIp, err := osutil.GetLocalIP()
	if err != nil {
		logger.Error("get local ip error: %s", err.Error())
		return err
	}
	// 剔除蓝鲸监控的探活进程
	cmd := fmt.Sprintf(`netstat -anpl|grep ':%d' | grep "beam.smp" | grep -E -v '0.0.0.0:*'`, cst.DefaultProtobufPort)
	cmd = fmt.Sprintf(`%s | awk '{ if (index($5,"%s:") == 0) { print $0 } }' `, cmd, localIp)
	res, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		errInfo := fmt.Sprintf("execute [ %s ] error: %s", cmd, err.Error())
		slog.Error(errInfo)
		return fmt.Errorf(errInfo)
	}
	content := strings.Replace(res, " ", "", -1)
	content = strings.Replace(res, "\n", "", -1)
	if content == "" {
		slog.Info("check success, no connection")
		return nil
	}
	logger.Error("execute shell [%s] connections: %s", cmd, res)
	err = fmt.Errorf("execute shell [%s] connections: %s", cmd, res)
	return err
}
