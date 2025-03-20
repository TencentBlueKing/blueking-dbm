package dbbackup

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"path/filepath"
)

func DeployBinary(medium *components.Medium) (err error) {
	if err = medium.Check(); err != nil {
		return err
	}

	cmd := fmt.Sprintf(
		"tar zxf %s -C %s && mkdir -p %s &&  chown -R mysql.mysql %s",
		medium.GetAbsolutePath(),
		filepath.Dir(cst.DbbackupGoInstallPath),
		filepath.Join(cst.DbbackupGoInstallPath, "logs"),
		cst.DbbackupGoInstallPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return ChownGroup()
}

func ChownGroup() (err error) {
	// run dbbackup migrateold
	_, errStr, err := cmutil.ExecCommandReturnBytes(
		false,
		cst.DbbackupGoInstallPath,
		filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"),
		"migrateold",
	)
	if err != nil {
		logger.Info("run dbbackup migrateold failed: %s", errStr)
		//we ignore this error
	} else {
		logger.Info("run dbbackup migrateold success")
	}

	cmd := fmt.Sprintf(
		" chown -R mysql.mysql %s ; chmod +x %s/*.sh ; chmod +x %s/dbbackup",
		filepath.Dir(cst.DbbackupGoInstallPath), cst.DbbackupGoInstallPath, cst.DbbackupGoInstallPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}

func (c *NewDbBackupComp) ChownGroup() (err error) {
	return ChownGroup()
}
