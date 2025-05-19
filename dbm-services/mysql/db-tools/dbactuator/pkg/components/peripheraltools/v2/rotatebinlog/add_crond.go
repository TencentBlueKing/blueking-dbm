package rotatebinlog

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func (c *MySQLRotateBinlogComp) AddCrond() (err error) {
	return AddCrond()
}

func AddCrond() (err error) {
	tl, err := tools.NewToolSetWithPick(tools.ToolMysqlRotatebinlog)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	err = osutil.RemoveSystemCrontab("rotate_logbin")
	if err != nil {
		logger.Error("remove old rotate_logbin crontab failed: %s", err.Error())
		return err
	}
	scheduleCmd := fmt.Sprintf("%s -c %s crond --add 2>/dev/null && chown -R mysql:mysql %s",
		tl.MustGet(tools.ToolMysqlRotatebinlog),
		filepath.Join(cst.MysqlRotateBinlogInstallPath, "main.yaml"),
		cst.MysqlRotateBinlogInstallPath,
	)
	str, err := osutil.ExecShellCommand(false, scheduleCmd)
	if err != nil {
		logger.Error(
			"failed to register mysql-rotatebinlog to crond: %s(%s)", str, err.Error(),
		)
	}
	return err
}
