package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"os/exec"
	"path"
	"time"
)

func (c *MySQLCrondComp) AddKeepAlive() (err error) {
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(
				`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "add_keep_alive.sh"),
			),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("add mysql-crond keep alive crontab failed: %s", err.Error())
		return err
	}
	logger.Info("add mysql-crond keep alive crontab success")
	return nil
}

func (c *MySQLCrondComp) RemoveKeepAlive() (err error) {
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(
				`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "remove_keep_alive.sh"),
			),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("remove mysql-crond keep alive crontab failed: %s", err.Error())
		return err
	}
	logger.Info("remove mysql-crond keep alive crond success")

	time.Sleep(1 * time.Minute) //确保现在在跑的周期完成
	return nil
}
