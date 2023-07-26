// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"time"
)

// StopComp TODO
type StopComp struct {
	Params         *StopParam `json:"extend"`
	StopRunTimeCtx `json:"-"`
}

// StopParam TODO
type StopParam struct {
}

// StopRunTimeCtx 运行时上下文
type StopRunTimeCtx struct {
}

// Stop 关闭
func (i *StopComp) Stop() error {
	// 关闭实例
	cmd := "riak stop"
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		return fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
	}
	time.Sleep(time.Minute)
	logger.Info("stop riak node complete")
	return nil
}
