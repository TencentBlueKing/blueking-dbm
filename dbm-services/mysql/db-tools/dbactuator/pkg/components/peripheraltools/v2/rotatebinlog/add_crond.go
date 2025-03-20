package rotatebinlog

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func (c *MySQLRotateBinlogComp) AddCrond() (err error) {
	err = osutil.RemoveSystemCrontab("rotate_logbin")
	if err != nil {
		logger.Error("remove old rotate_logbin crontab failed: %s", err.Error())
		return err
	}
	scheduleCmd := fmt.Sprintf("%s -c %s crond --add 2>/dev/null && chown -R mysql.mysql %s",
		c.binPath, c.configFile, c.installPath)
	str, err := osutil.ExecShellCommand(false, scheduleCmd)
	if err != nil {
		logger.Error(
			"failed to register mysql-rotatebinlog to crond: %s(%s)", str, err.Error(),
		)
	}
	return err
}
