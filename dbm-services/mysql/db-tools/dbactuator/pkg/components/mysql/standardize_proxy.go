package mysql

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

type StandardizeProxyComp struct {
	//GeneralParam *components.GeneralParam `json:"general"`
	//Params *
}

func (c *StandardizeProxyComp) ClearOldCrontab() error {
	err := osutil.RemoveUserCrontab("mysql")
	if err != nil {
		logger.Error("clear mysql crontab failed: %s", err.Error())
	} else {
		logger.Info("clear mysql crontab success")
	}
	return nil
}
