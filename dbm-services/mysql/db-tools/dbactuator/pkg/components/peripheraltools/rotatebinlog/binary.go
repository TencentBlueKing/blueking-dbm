package rotatebinlog

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"path/filepath"
)

func (c *MySQLRotateBinlogComp) DeployBinary() (err error) {
	err = os.MkdirAll(filepath.Join(c.installPath, "logs"), 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", c.installPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), cst.MYSQL_TOOL_INSTALL_PATH,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress rotatebinlog pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql.mysql %s && chmod +x %s`, c.installPath, c.binPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", c.installPath, err.Error())
		return err
	}

	return nil
}
