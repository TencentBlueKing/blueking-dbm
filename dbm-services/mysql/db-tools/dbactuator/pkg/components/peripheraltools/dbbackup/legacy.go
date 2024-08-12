package dbbackup

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
)

func (c *NewDbBackupComp) StageLegacyBackup() (err error) {
	bakInstallPath := c.installPath + "-backup"
	if _, err := os.Stat(c.installPath); !os.IsNotExist(err) {
		cmd := fmt.Sprintf("rm -rf %s; mv %s %s", bakInstallPath, c.installPath, bakInstallPath)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			err = fmt.Errorf("execute %s get an error:%s,%w", cmd, output, err)
			return err
		}
	}
	return
}
