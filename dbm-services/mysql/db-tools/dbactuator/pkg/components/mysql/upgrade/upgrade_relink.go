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
	// tar mysql new version  package
	var stderr, oldlink string
	if stderr, err = osutil.StandardShellCommand(false, fmt.Sprintf("tar -axf %s -C %s", m.Params.GetAbsolutePath(),
		cst.UsrLocal)); err != nil {
		logger.Error("tar mysql new version package failed %s,stderr%s", err.Error(), stderr)
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
		logger.Error("tar mysql new version package failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	return err
}

// RelinkTdbctl relink tdbctl
/**
 * @description: 重新链接tdbctl
 * @return {*}
 */
func (m *MysqlUpgradeRelinkComp) RelinkTdbctl() (err error) {
	// tar tdbctl new version package
	var stderr, oldLink string
	if stderr, err = osutil.StandardShellCommand(false, fmt.Sprintf("tar -axf %s -C %s", m.Params.GetAbsolutePath(),
		cst.UsrLocal)); err != nil {
		logger.Error("tar tdbctl new version package failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	fi, err := os.Lstat(cst.TdbctlInstallPath)
	if err != nil {
		logger.Error("read /usr/local/tdbctl dir info failed %s", err.Error())
		return err
	}
	sc := ""
	newLink := m.Params.GePkgBaseName()
	switch mode := fi.Mode(); {
	case mode.IsDir():
		bakDir := fmt.Sprintf("mysql_%s", time.Now().Format(cst.TimeLayoutDir))
		sc = fmt.Sprintf("cd %s && mv tdbctl %s && ln -s %s tdbctl ",
			cst.UsrLocal, bakDir, newLink)
		logger.Info("move tdbctl dir to %s", bakDir)
	case mode&os.ModeSymlink != 0:
		oldLink, err = os.Readlink(cst.MysqldInstallPath)
		if err != nil {
			logger.Error("get old tdbctl link failed %s", err.Error())
			return err
		}
		logger.Info("tdbctl old link is %s", oldLink)
		sc = fmt.Sprintf("cd %s && unlink tdbctl && ln -s %s tdbctl ",
			cst.UsrLocal, newLink)
	default:
		return fmt.Errorf("file %s is not a dir or symlink", cst.MysqldInstallPath)
	}
	if stderr, err = osutil.StandardShellCommand(false, sc); err != nil {
		logger.Error("tar tdbctl new version package failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	return err
}
