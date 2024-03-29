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

// RestartComp TODO
type RestartComp struct {
	Params            *RestartParam `json:"extend"`
	RestartRunTimeCtx `json:"-"`
}

// RestartParam TODO
type RestartParam struct {
}

// RestartRunTimeCtx 运行时上下文
type RestartRunTimeCtx struct {
}

// Restart 启动
func (i *RestartComp) Restart() error {
	cmd := "riak restart"
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		// 当节点已经关闭，restart会失败，尝试start
		logger.Info("restart failed, try to start")
		errStart := Start()
		if errStart != nil {
			// 返回restart的报错
			return err
		} else {
			return nil
		}
	}
	time.Sleep(time.Minute)
	logger.Info("restart riak success")
	return nil
}
