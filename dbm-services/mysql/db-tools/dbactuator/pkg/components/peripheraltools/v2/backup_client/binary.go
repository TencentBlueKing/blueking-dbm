package backup_client

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

func (c *BackupClientComp) DeployBinary() (err error) {
	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), "/usr/local",
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress backup_client pkg failed: %s", err.Error())
		return err
	}
	chownCmd := fmt.Sprintf(`chown -R root.root %s && chmod +x %s`, c.installPath, c.binPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to root failed: %s", c.installPath, err.Error())
		return err
	}
	return nil
}
