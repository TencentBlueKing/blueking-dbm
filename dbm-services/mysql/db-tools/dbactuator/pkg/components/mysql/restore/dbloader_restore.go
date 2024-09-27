package restore

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore/dbloader"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// DBLoader 使用 dbbackup-go loadbackup 进行恢复
type DBLoader struct {
	*RestoreParam

	taskDir      string // 依赖 BackupInfo.WorkDir ${work_dir}/doDr_${id}/${port}/
	targetDir    string // 备份解压后的目录，${taskDir}/<backupBaseName>/
	LogDir       string `json:"-"`
	dbLoaderUtil *dbloader.LoaderUtil
	// dbLoader is interface
	dbLoader dbloader.DBBackupLoader
	// myCnf for physical backup
	myCnf *util.CnfFile
}

// Init load index file
func (m *DBLoader) Init() error {
	var err error
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

	if err = m.initDirs(true); err != nil {
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
	// 重建模式，不需要 restore_opt 选项，但要校验位点信息
	// 回档模式，如果是备份记录回档则不需要位点，如果是需要基于 binlog 回档，则要检验位点信息
	if m.RestoreParam.RestoreOpt == nil {
		m.RestoreParam.RestoreOpt = &RestoreOpt{
			EnableBinlog:      false,
			WillRecoverBinlog: true,
		}
	}
	if m.RestoreParam.RestoreOpt.WillRecoverBinlog {
		if _, err := m.getChangeMasterPos(m.SrcInstance); err != nil {
			return err
		}
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
		LogDir:        m.LogDir,
		//EnableBinlog:  m.RestoreOpt.EnableBinlog,
	}
	if m.RestoreOpt == nil {
		m.RestoreOpt = &RestoreOpt{
			EnableBinlog: false,
		}
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

// Start 执行导入
// 选择logical / physical tool
// 恢复前操作：比如build filter
// 解压 untar
// 恢复数据
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
	defer func() {
		cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", m.taskDir)
	}()
	logger.Info("开始解压 taskDir=%s", m.taskDir)
	if err := m.BackupInfo.indexObj.UntarFiles(m.taskDir, false); err != nil {
		return err
	}
	logger.Info("开始数据恢复 targetDir=%s", m.targetDir)
	if err := m.dbLoader.Load(); err != nil {
		return errors.WithMessage(err, "dbactuator dbloaderData failed")
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
	if m.RestoreParam.RestoreOpt != nil && m.RestoreParam.RestoreOpt.WillRecoverBinlog { //
		return m.getChangeMasterPos(m.SrcInstance)
	} else {
		return &mysqlutil.ChangeMaster{}, nil
	}
}

// initDirs 如果 removeOld =  true，会删除当前任务目录下，之前的解压目录，可能是重试导致的废弃目录
func (m *DBLoader) initDirs(removeOld bool) error {
	if m.BackupInfo.WorkDir == "" {
		return errors.Errorf("work_dir %s should not be empty", m.WorkDir)
	}
	if m.WorkID == "" {
		m.WorkID = newTimestampString()
	}
	if removeOld { // 删除旧目录
		timeNow := time.Now()
		oldDirs, _ := filepath.Glob(fmt.Sprintf("%s/doDr_*", m.WorkDir))
		for _, oldDir := range oldDirs {
			if dirInfo, err := os.Stat(oldDir); err == nil && dirInfo.IsDir() {
				if timeNow.Sub(dirInfo.ModTime()) > 1*time.Minute {
					logger.Warn("remove old recover work directory: ", oldDirs)
					_ = os.RemoveAll(oldDir)
				}
			}
		}
	}

	m.taskDir = fmt.Sprintf("%s/doDr_%s/%d", m.WorkDir, m.WorkID, m.TgtInstance.Port)
	if err := osutil.CheckAndMkdir("", m.taskDir); err != nil {
		return err
	}
	m.targetDir = m.BackupInfo.indexObj.GetTargetDir(m.taskDir)
	logger.Info("current recover work directory: %s", m.taskDir)
	logger.Info("current recover work target directory: %s", m.targetDir)
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
	if masterInst.Host == "" || masterInst.Port == 0 { // 说明不关注备份位点信息
		return &mysqlutil.ChangeMaster{}, nil
	}
	if masterInfo == nil || masterInfo.BinlogFile == "" {
		return nil, errors.New("no master info found in metadata")
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
		return nil, errors.Errorf("this backup is illegal because I cannot find the binlog pos for current master "+
			"%s:%d", masterInst.Host, masterInst.Port)
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
