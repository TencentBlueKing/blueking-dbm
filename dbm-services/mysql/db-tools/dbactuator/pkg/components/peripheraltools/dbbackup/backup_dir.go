package dbbackup

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
)

func (c *NewDbBackupComp) InitBackupDir() (err error) {
	if c.Params.UntarOnly {
		logger.Info("untar_only=true do not need InitBackupDir")
		return nil
	}
	backupdir := c.Params.Configs["Public"]["BackupDir"]
	if _, err := os.Stat(backupdir); os.IsNotExist(err) {
		logger.Warn("backup dir %s is not exist. will make it", backupdir)
		cmd := fmt.Sprintf("mkdir -p %s", backupdir)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			return fmt.Errorf("execute [%s] get an error:%s,%w", cmd, output, err)
		}
	}
	cmd := fmt.Sprintf("chown -R mysql.mysql %s", backupdir)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		return fmt.Errorf("execute [%s] get an error:%s,%w", cmd, output, err)
	}
	return
}
