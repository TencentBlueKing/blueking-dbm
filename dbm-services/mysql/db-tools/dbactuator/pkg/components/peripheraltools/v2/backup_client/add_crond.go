package backup_client

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

func (c *BackupClientComp) AddCrond() (err error) {
	err = osutil.RemoveSystemCrontab("backup_client upload")
	if err != nil {
		logger.Error("remove old 'backup_client upload' crontab failed: %s", err.Error())
		return err
	}
	uploadCrontabCmd := fmt.Sprintf("%s addcrontab -u root >/dev/null", c.binPath)
	str, err := osutil.ExecShellCommand(false, uploadCrontabCmd)
	if err != nil {
		logger.Error(
			"failed add '%s' to crond: %s(%s)", uploadCrontabCmd, str, err.Error(),
		)
	}
	return err
}
