package upgrade

import (
	"fmt"
	"os"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

type MysqlUpgradeRelinkComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       MysqlUpgradeRelinkParam  `json:"extend"`
}

type MysqlUpgradeRelinkParam struct {
	Host string `json:"host" validate:"required,ip"`
	components.Medium
}

func (m *MysqlUpgradeRelinkComp) RelinkMysql() (err error) {
	// tar mysql new version  packege
	var stderr, oldlink string
	if stderr, err = osutil.StandardShellCommand(false, fmt.Sprintf("tar -axf %s -C %s", m.Params.GetAbsolutePath(),
		cst.UsrLocal)); err != nil {
		logger.Error("tar mysql new version packege failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	fi, err := os.Lstat(cst.MysqldInstallPath)
	if err != nil {
		logger.Error("read /usr/local/mysql dir info failed %s", err.Error())
		return err
	}
	sc := ""
	newlink := m.Params.GePkgBaseName()
	switch mode := fi.Mode(); {
	case mode.IsDir():
		bakdir := fmt.Sprintf("mysql_%s", time.Now().Format(cst.TimeLayoutDir))
		sc = fmt.Sprintf("cd %s && mv mysql %s && ln -s %s mysql ",
			cst.UsrLocal, bakdir, newlink)
		logger.Info("move mysql dir to %s", bakdir)
	case mode&os.ModeSymlink != 0:
		oldlink, err = os.Readlink(cst.MysqldInstallPath)
		if err != nil {
			logger.Error("get old mysql link failed %s", err.Error())
			return err
		}
		logger.Info("mysql old link is %s", oldlink)
		sc = fmt.Sprintf("cd %s && unlink mysql && ln -s %s mysql ",
			cst.UsrLocal, newlink)
	default:
		return fmt.Errorf("file %s is not a dir or symlink", cst.MysqldInstallPath)
	}
	if stderr, err = osutil.StandardShellCommand(false, sc); err != nil {
		logger.Error("tar mysql new version packege failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	return err
}
