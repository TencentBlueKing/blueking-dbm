package dbbackup_loader

import (
	"context"
	"fmt"
	"path/filepath"
	"time"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/filecontext"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// PhysicalLoader TODO
type PhysicalLoader struct {
	// LoaderUtil logical and physical 通用参数
	*LoaderUtil
	*Xtrabackup
	CopyBack          bool
	RenameOriginalDir bool
	ctx               *filecontext.FileContext
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
	l.Xtrabackup.myCnf = cnfFile
	if p.TgtInstance.Socket == "" {
		p.TgtInstance.Socket = l.Xtrabackup.getSocketName() // x.myCnf.GetMySQLSocket()
		l.Xtrabackup.TgtInstance.Socket = l.Xtrabackup.getSocketName()
	}
	// create loader config file
	loaderConfig := config.PhysicalLoad{
		DefaultsFile:  cnfFileName, // l.Xtrabackup.myCnf.FileName
		MysqlLoadDir:  p.LoaderDir,
		IndexFilePath: p.IndexFilePath,
		CopyBack:      l.CopyBack,
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
	cfgFilePath := filepath.Join(p.TaskDir, fmt.Sprintf("dbloader_%d.ini", p.TgtInstance.Port))
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

// PostLoad TODO
func (l *PhysicalLoader) PostLoad() (err error) {
	// 这里主要是提示用户如果跳过，跳过了后面那些步骤
	logger.Warn("PhysicalLoader post load steps: "+
		"[RepairPrivilegesForNormalUser, "+
		"recoverGrants(%v), "+
		"repairNonSysMyIsamTables, "+
		"commonPostLoad(global_backup,remove_backup_file)]",
		l.RecoverGrants)
	// 判断可连接性后，再继续。连接会在后面用到
	l.Xtrabackup.dbWorker, err = l.Xtrabackup.TgtInstance.Conn()
	if err != nil {
		return err
	}
	defer l.Xtrabackup.dbWorker.Stop()

	logger.Warn("[step-1/4] PhysicalLoader post load: repair normal user's privileges")
	if err := l.Xtrabackup.RepairPrivilegesForNormalUser(); err != nil {
		return errors.WithMessage(err, "RepairPrivilegesForNormalUser")
	}

	logger.Warn("[step-2/4] PhysicalLoader post load: recoverGrants")
	if l.RecoverGrants {
		privFiles := l.IndexObj.GetTarFileList("priv")
		if err := recoverGrant(l.LoaderUtil.TgtInstance, privFiles, l.LoaderUtil.BackupDir); err != nil {
			return errors.WithMessagef(err, "restore-dr recover grants")
		}
	}

	logger.Warn("[step-3/4] PhysicalLoader post load: repairNonSysMyIsamTables")
	err = cmutil.WithPeriodicLogging("修复非系统MyISAM表", func(ctx context.Context) error {
		return l.Xtrabackup.RepairNonSysMyIsamTables(ctx)
	}, time.Minute, 12*time.Hour, logger.Default())
	if err != nil {
		return err
	}

	logger.Warn("[step-4/4] PhysicalLoader post load: commonPostLoad")
	if err := l.LoaderUtil.commonPostLoad(l.LoaderUtil.BackupDir); err != nil {
		return err
	}
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
	if err := l.Xtrabackup.stopAndClean(l.RenameOriginalDir); err != nil {
		return err
	}
	if err := l.loadBackup(); err != nil {
		return err
	}
	logger.Info("change datadir owner user and group")

	// 调整目录属主
	if err := l.Xtrabackup.ChangeDirOwner(); err != nil {
		return err
	}

	logger.Warn("PhysicalLoader run repairSysAndStart")
	if err := l.Xtrabackup.repairSysAndStart(); err != nil {
		return err
	}
	return nil
}

func (l *PhysicalLoader) loadBackup() error {
	loadCmd := fmt.Sprintf(`cd %s && %s loadbackup --config %s`, l.TaskDir, l.Client, l.cfgFilePath)
	if l.LogDir != "" {
		loadCmd += fmt.Sprintf(" --log-dir %s", l.LogDir)
	}
	logger.Info("dbLoader cmd: %s", loadCmd)
	errStr, err := osutil.ExecShellCommand(false, loadCmd)
	if err != nil {
		logger.Error("physical dbbackup loadbackup stderr: ", errStr)
		return errors.WithMessage(err, errStr)
	}
	return nil
}
