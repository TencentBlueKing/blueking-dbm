package dbbackup

import (
	"fmt"
	"os"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func (c *NewDbBackupComp) InitBackupDir() (err error) {
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
	return c.initReportDir()
}

func (c *NewDbBackupComp) initReportDir() (err error) {
	// redis 会污染 /home/mysql/dbareport，建立成软连
	if isLink, _ := cmutil.IsSymLinkFile(cst.DBAReportBase); isLink {
		_ = os.Remove(cst.DBAReportBase)
	}
	reportDir := c.Params.Configs["Public"]["ReportPath"]
	if _, err := os.Stat(reportDir); os.IsNotExist(err) {
		err := os.MkdirAll(reportDir, 0755)
		if err != nil {
			return errors.WithMessagef(err, "execute [mkdir -p %s]", reportDir)
		}
	}
	cmd := fmt.Sprintf("chown -R mysql.mysql %s", reportDir)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		return fmt.Errorf("execute [%s] get an error:%s,%w", cmd, output, err)
	}
	return
}
