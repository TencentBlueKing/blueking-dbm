package dbloader

import (
	"fmt"
	"path/filepath"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// PhysicalLoader TODO
type PhysicalLoader struct {
	*LoaderUtil
	*Xtrabackup
}

// CreateConfigFile TODO
func (l *PhysicalLoader) CreateConfigFile() error {
	logger.Info("create loader config file")
	p := l.LoaderUtil

	// get my.cnf and socket
	cnfFileName := util.GetMyCnfFileName(p.TgtInstance.Port)
	cnfFile := &util.CnfFile{FileName: cnfFileName}
	if err := cnfFile.Load(); err != nil {
		logger.Info("get my.conf failed %v", cnfFileName)
		return errors.WithStack(err)
	}
	l.myCnf = cnfFile
	if p.TgtInstance.Socket == "" {
		p.TgtInstance.Socket = l.Xtrabackup.getSocketName() // x.myCnf.GetMySQLSocket()
		l.Xtrabackup.TgtInstance.Socket = l.Xtrabackup.getSocketName()
	}
	// create loader config file
	loaderConfig := config.PhysicalLoad{
		DefaultsFile:  cnfFileName, // l.Xtrabackup.myCnf.FileName
		MysqlLoadDir:  p.LoaderDir,
		IndexFilePath: p.IndexFilePath,
		CopyBack:      false,
		Threads:       4,
	}
	logger.Info("dbloader config file, %+v", loaderConfig)

	f := ini.Empty()
	section, err := f.NewSection("PhysicalLoad")
	if err != nil {
		return err
	}
	if err = section.ReflectFrom(&loaderConfig); err != nil {
		return err
	}
	cfgFilePath := filepath.Join(p.TaskDir, fmt.Sprintf("dbloader_%d.cfg", p.TgtInstance.Port))
	if err = f.SaveTo(cfgFilePath); err != nil {
		return errors.Wrap(err, "create config")
	}
	p.cfgFilePath = cfgFilePath
	logger.Info("tmp dbloader config file %s", p.cfgFilePath)
	return nil
}

// PreLoad TODO
func (l *PhysicalLoader) PreLoad() error {
	return nil
}

// Load 恢复数据
// 1. create config
// 2. stop mysqld / clean old dirs
// 3. loadbackup
// 4. fix privs / star mysqld
func (l *PhysicalLoader) Load() error {
	if err := l.CreateConfigFile(); err != nil {
		return err
	}
	if err := l.Xtrabackup.PreRun(); err != nil {
		return err
	}
	if err := l.loadBackup(); err != nil {
		return err
	}
	if err := l.Xtrabackup.PostRun(); err != nil {
		return err
	}
	return nil
}

func (l *PhysicalLoader) loadBackup() error {
	cmd := fmt.Sprintf(`cd %s && %s loadbackup --config %s |grep -v WARNING`, l.TaskDir, l.Client, l.cfgFilePath)
	logger.Info("dbLoader cmd: %s", cmd)
	stdStr, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		return errors.Wrap(err, stdStr)
	}
	return nil
}
