package dbbackup

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"path/filepath"
)

func (c *NewDbBackupComp) DeployBinary() (err error) {
	if err = c.Params.Medium.Check(); err != nil {
		return err
	}
	cmd := fmt.Sprintf(
		"tar zxf %s -C %s && mkdir -p %s &&  chown -R mysql.mysql %s", c.Params.Medium.GetAbsolutePath(),
		filepath.Dir(c.installPath), filepath.Join(c.installPath, "logs"), c.installPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}

func (c *NewDbBackupComp) ChownGroup() (err error) {
	// run dbbackup migrateold
	_, errStr, err := cmutil.ExecCommandReturnBytes(
		false,
		c.installPath,
		filepath.Join(c.installPath, "dbbackup"),
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
		filepath.Dir(c.installPath), c.installPath, c.installPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}
