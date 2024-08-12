package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os/exec"
	"path"
)

func (c *MySQLCrondComp) Stop() (err error) {
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(
				`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "stop.sh"),
			),
		}...,
	)

	err = cmd.Run()
	if err != nil {
		logger.Error("stop mysql-crond failed: %s", err.Error())
		return err
	}
	logger.Info("stop mysql-crond success")
	return nil
}

// Start 启动进程
func (c *MySQLCrondComp) Start() (err error) {
	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.MySQLCrondInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}

	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c", // mysql 写死
			fmt.Sprintf(
				`%s -c %s`,
				path.Join(cst.MySQLCrondInstallPath, "start.sh"),
				path.Join(cst.MySQLCrondInstallPath, "runtime.yaml"),
			),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("start mysql-crond failed: %s", err.Error())
		return err
	}

	logger.Info("mysql-crond started")
	return nil
}
