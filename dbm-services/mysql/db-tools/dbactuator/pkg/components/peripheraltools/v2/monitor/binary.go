package monitor

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"path/filepath"
)

func DeployBinary(medium *components.Medium) (err error) {
	err = os.MkdirAll(cst.MySQLMonitorInstallPath, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}

	err = os.MkdirAll(
		filepath.Join(cst.MySQLMonitorInstallPath, "context"),
		0755)
	if err != nil {
		logger.Error("mkdir context failed: %s", err.Error())
		return err
	}

	err = os.MkdirAll(
		filepath.Join(cst.MySQLMonitorInstallPath, "scenes"),
		0755)
	if err != nil {
		logger.Error("mkdir scenes failed: %s", err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		medium.GetAbsolutePath(), cst.MySQLMonitorInstallPath,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress monitor pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.MySQLMonitorInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.MySQLMonitorInstallPath, err.Error())
		return err
	}

	chownCmd = fmt.Sprintf(`chown -R mysql %s/context`, cst.MySQLMonitorInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown context to mysql failed: %s", err.Error())
		return err
	}

	chownCmd = fmt.Sprintf(`chown -R mysql %s/scenes`, cst.MySQLMonitorInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown scenes to mysql failed: %s", err.Error())
		return err
	}

	chmodCmd := fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.MySQLMonitorInstallPath, "pt-config-diff"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod pt-config-diff failed: %s", err.Error())
		return err
	}

	chmodCmd = fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.MySQLMonitorInstallPath, "pt-summary"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod pt-summary failed: %s", err.Error())
		return err
	}

	chmodCmd = fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.MySQLMonitorInstallPath, "mysql-monitor"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod mysql-monitor failed: %s", err.Error())
		return err
	}
	return nil
}

//func (c *MySQLMonitorComp) DeployBinary() (err error) {
//	return DeployBinary(&c.Params.Medium)
//}
