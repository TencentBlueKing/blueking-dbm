package rotatebinlog

import (
	"fmt"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func (c *MySQLRotateBinlogComp) RunMigrateOld() (err error) {
	cmdArgs := []string{"migrate-old", "-c", c.configFile}
	_, stdErr, err := cmutil.ExecCommand(false, c.installPath, c.binPath, cmdArgs...)

	chownCmd := fmt.Sprintf(`chown -R mysql.mysql %s ; mkdir -p %s ;chown -R mysql.mysql %s`, c.installPath,
		cst.DBAReportBase, cst.DBAReportBase)
	_, err = osutil.ExecShellCommand(false, chownCmd)

	if err != nil {
		logger.Error("migrate-old failed: ", err.Error(), stdErr)
		//return errors.WithMessagef(err, "run migrate-old failed:%s", stdErr)
	} else {
		logger.Info("migrate-old success")
	}
	return nil
}
