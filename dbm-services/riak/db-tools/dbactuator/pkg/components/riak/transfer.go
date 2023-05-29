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

// TransferComp TODO
type TransferComp struct {
	Params             *TransferParam `json:"extend"`
	TransferRunTimeCtx `json:"-"`
}

// TransferParam TODO
type TransferParam struct {
	AutoStop *bool `json:"auto_stop"  validate:"required"`
}

// TransferRunTimeCtx 运行时上下文
type TransferRunTimeCtx struct {
}

// Transfer 集群数据搬迁进度检查
func (i *TransferComp) Transfer() error {
	cmd := "riak-admin transfers"
	cnt := 1
	logger.Info("check transfer status every 10s")
	for true {
		res, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			if *i.Params.AutoStop == true && strings.Contains(err.Error(), "Node did not respond to ping!") {
				logger.Info(err.Error())
				break
			} else {
				logger.Error("execute shell [%s] error: %s", cmd, err.Error())
				err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
				return err
			}
		}
		if strings.Contains(res, "No transfers active") {
			break
		}
		logger.Info("%d check, transfering data...", cnt)
		time.Sleep(10 * time.Second)
		cnt++
	}
	logger.Info("riak cluster transfer data complete")
	return nil
}
