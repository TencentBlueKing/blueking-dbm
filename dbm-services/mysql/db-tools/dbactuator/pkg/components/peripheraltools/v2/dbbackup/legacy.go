package dbbackup

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
)

func (c *NewDbBackupComp) StageLegacyBackup() (err error) {
	bakInstallPath := cst.DbbackupGoInstallPath + "-backup"
	if _, err := os.Stat(cst.DbbackupGoInstallPath); !os.IsNotExist(err) {
		cmd := fmt.Sprintf("rm -rf %s; mv %s %s", bakInstallPath, cst.DbbackupGoInstallPath, bakInstallPath)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			err = fmt.Errorf("execute %s get an error:%s,%w", cmd, output, err)
			return err
		}
	}
	return
}
