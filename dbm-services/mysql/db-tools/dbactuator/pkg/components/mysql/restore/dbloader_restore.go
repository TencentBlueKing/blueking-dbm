package restore

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore/dbloader"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// DBLoader 使用 dbbackup-go loadbackup 进行恢复
type DBLoader struct {
	*RestoreParam

	taskDir      string // 依赖 BackupInfo.WorkDir ${work_dir}/doDr_${id}/${port}/
	targetDir    string // 备份解压后的目录，${taskDir}/backupBaseName/
	dbLoaderUtil *dbloader.LoaderUtil
	// dbLoader is interface
	dbLoader dbloader.DBBackupLoader
	// myCnf for physical backup
	myCnf *util.CnfFile
}

// Init load index file
func (m *DBLoader) Init() error {
	var err error
	/*
		if err = m.BackupInfo.GetBackupMetaFile(dbbackup.BACKUP_INDEX_FILE); err != nil {
			return err
		}
	*/
	cnfFileName := util.GetMyCnfFileName(m.TgtInstance.Port)
	cnfFile := &util.CnfFile{FileName: cnfFileName}
	if err = cnfFile.Load(); err != nil {
		logger.Info("get my.conf failed %v", cnfFileName)
		return errors.WithStack(err)
	} else {
		m.myCnf = cnfFile
		m.TgtInstance.Socket, err = m.myCnf.GetMySQLSocket()
		if err != nil {
			logger.Warn("fail to get mysqld socket: %s", cnfFileName)
		}
	}
	if err = m.BackupInfo.indexObj.ValidateFiles(); err != nil {
		return err
	}
	if err = m.initDirs(); err != nil {
		return err
	}
	return nil
}

// PreCheck TODO
func (m *DBLoader) PreCheck() error {
	toolset, err := tools.NewToolSetWithPick(tools.ToolDbbackupGo, tools.ToolQPress)
	if err != nil {
		return err
	}
	if err := m.Tools.Merge(toolset); err != nil {
		return err
	}
	// validateBackupInfo before run import
	if _, err := m.getChangeMasterPos(m.SrcInstance); err != nil {
		return err
	}
	// 工具可执行权限
	// 本地实例是否可联通
	return nil
}

// chooseDBBackupLoader 选择是 dbbackup-go 恢复是 logical or physical
func (m *DBLoader) chooseDBBackupLoader() error {
	dbloaderPath := m.Tools.MustGet(tools.ToolDbbackupGo)
	m.dbLoaderUtil = &dbloader.LoaderUtil{
		Client:        dbloaderPath,
		TgtInstance:   m.TgtInstance,
		IndexFilePath: m.BackupInfo.indexFilePath,
		IndexObj:      m.BackupInfo.indexObj,
		LoaderDir:     m.targetDir,
		TaskDir:       m.taskDir,
		EnableBinlog:  m.RestoreOpt.EnableBinlog,
	}
	// logger.Warn("validate dbLoaderUtil: %+v", m.dbLoaderUtil)
	if err := validate.GoValidateStruct(m.dbLoaderUtil, false, false); err != nil {
		return err
	}

	if m.backupType == cst.BackupTypeLogical {
		myloaderOpt := &dbloader.LoaderOpt{}
		copier.Copy(myloaderOpt, m.RestoreOpt)
		logger.Warn("myloaderOpt copied: %+v. src:%+v", myloaderOpt, m.RestoreOpt)
		m.dbLoader = &dbloader.LogicalLoader{
			LoaderUtil:  m.dbLoaderUtil,
			MyloaderOpt: myloaderOpt,
		}
	} else if m.backupType == cst.BackupTypePhysical {
		m.dbLoader = &dbloader.PhysicalLoader{
			LoaderUtil: m.dbLoaderUtil,
			Xtrabackup: &dbloader.Xtrabackup{
				TgtInstance:   m.dbLoaderUtil.TgtInstance,
				SrcBackupHost: m.dbLoaderUtil.IndexObj.BackupHost,
				QpressTool:    m.Tools.MustGet(tools.ToolQPress),
				LoaderDir:     m.targetDir,
			},
		}
	} else {
		return errors.Errorf("unknown backupType: %s", m.backupType)
	}
	logger.Info("recover backup_type=%s", m.backupType)
	return nil
}

// Start TODO
func (m *DBLoader) Start() error {
	if err := m.chooseDBBackupLoader(); err != nil {
		return err
	}
	if err := m.dbLoader.PreLoad(); err != nil {
		return err
	}

	logger.Info("dbloader params %+v", m)
	if m.taskDir == "" {
		return errors.Errorf("dbloader taskDir error")
	}
	if err := m.BackupInfo.indexObj.UntarFiles(m.taskDir); err != nil {
		return err
	}

	if err := m.dbLoader.Load(); err != nil {
		return errors.Wrap(err, "dbloaderData failed")
	}
	return nil
}

// WaitDone TODO
func (m *DBLoader) WaitDone() error {
	return nil
}

// PostCheck TODO
func (m *DBLoader) PostCheck() error {
	return nil
}

// ReturnChangeMaster TODO
func (m *DBLoader) ReturnChangeMaster() (*mysqlutil.ChangeMaster, error) {
	return m.getChangeMasterPos(m.SrcInstance)
}

func (m *DBLoader) initDirs() error {
	if m.BackupInfo.WorkDir == "" {
		return errors.Errorf("work_dir %s should not be empty", m.WorkDir)
	}
	if m.WorkID == "" {
		m.WorkID = newTimestampString()
	}
	m.taskDir = fmt.Sprintf("%s/doDr_%s/%d", m.WorkDir, m.WorkID, m.TgtInstance.Port)
	if err := osutil.CheckAndMkdir("", m.taskDir); err != nil {
		return err
	}
	if m.BackupInfo.backupBaseName == "" {
		return errors.Errorf("backup file baseName [%s] error", m.BackupInfo.backupBaseName)
	}
	m.targetDir = fmt.Sprintf("%s/%s", m.taskDir, m.backupBaseName)
	return nil
}

// getChangeMasterPos godoc
// srcMaster -> srcSlave
//
//	|-> tgtMaster -> tgtSlave
//
// masterInst is instance you want to change master to it
func (m *DBLoader) getChangeMasterPos(masterInst native.Instance) (*mysqlutil.ChangeMaster, error) {
	logger.Info("metadata: %+v", m.indexObj.BinlogInfo)
	masterInfo := m.indexObj.BinlogInfo.ShowMasterStatus
	slaveInfo := m.indexObj.BinlogInfo.ShowSlaveStatus
	if masterInfo == nil || masterInfo.BinlogFile == "" {
		return nil, errors.New("no master info found in metadata")
	}
	if masterInst.Host == "" || masterInst.Port == 0 { // 说明不关注备份位点信息
		return &mysqlutil.ChangeMaster{}, nil
	}
	// 如果备份文件的源实例，就是当前恢复要change master to 的实例，直接用 MasterStatus info
	if masterInfo.MasterHost == masterInst.Host && masterInfo.MasterPort == masterInst.Port {
		// if m.BackupInfo.backupHost == masterInst.Host && m.BackupInfo.backupPort == masterInst.Port {
		cm := &mysqlutil.ChangeMaster{
			MasterLogFile:   masterInfo.BinlogFile,
			MasterLogPos:    cast.ToInt64(masterInfo.BinlogPos),
			ExecutedGtidSet: masterInfo.Gtid,

			MasterHost: masterInst.Host,
			MasterPort: masterInst.Port,
		}
		return cm, nil
	} else if slaveInfo == nil || slaveInfo.BinlogFile == "" {
		// 说明是在 Master 的备份，如果发生互切/迁移，这个备份会是无效的
		return nil, errors.New("this backup is illegal because I cannot find the binlog pos for current master")
	}
	// 用的是 slave 的备份，change master to it's master
	if slaveInfo.MasterHost != "" && slaveInfo.MasterHost != masterInst.Host {
		logger.Warn(
			"metadata show slave host=%s:%d != change to master host=%s:%d",
			slaveInfo.MasterHost, slaveInfo.MasterPort, masterInst.Host, masterInst.Port)
	}
	cm := &mysqlutil.ChangeMaster{
		MasterLogFile:   slaveInfo.BinlogFile,
		MasterLogPos:    cast.ToInt64(slaveInfo.BinlogPos),
		ExecutedGtidSet: slaveInfo.Gtid,
		MasterHost:      masterInst.Host,
		MasterPort:      masterInst.Port,
	}
	return cm, nil
}
