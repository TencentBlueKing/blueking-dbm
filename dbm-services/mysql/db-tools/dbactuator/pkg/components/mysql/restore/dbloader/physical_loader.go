package dbloader

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/cmutil"
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
	// logger.Info("dbloader config file, %+v", loaderConfig) // 有密码打印

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
	// logger.Info("tmp dbloader config file %s", p.cfgFilePath) // 有密码打印
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
	// TODO 考虑把这个地方封装成独立的节点，可以单独重试
	if err := l.Xtrabackup.PostRun(); err != nil {
		return err
	}
	return nil
}

func (l *PhysicalLoader) loadBackup() error {
	cmd := fmt.Sprintf(`cd %s && %s loadbackup --config %s`, l.TaskDir, l.Client, l.cfgFilePath)
	logger.Info("dbLoader cmd: %s", cmd)
	errStr, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("physical dbbackup loadbackup stderr: ", errStr)
		// 尝试读取 myloader.log 里 CRITICAL 关键字
		_, errStr, _ = cmutil.ExecCommand(false, l.TaskDir, "grep", "-Ei 'CRITICAL|ERROR|FATAL'",
			"logs/xtrabackup_*.log", "| head -5 >&2")
		if len(strings.TrimSpace(errStr)) > 0 {
			logger.Info("head 5 error from", filepath.Join(l.TaskDir, "logs/xtrabackup_*.log"))
			logger.Error(errStr)
		}
		return errors.Wrap(err, errStr)
	}
	return nil
}
