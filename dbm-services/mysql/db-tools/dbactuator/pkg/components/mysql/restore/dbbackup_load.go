package restore

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/filecontext"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore/dbbackup_loader"
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
	LogDir string `json:"-"`

	// taskDir 依赖 BackupInfo.WorkDir ${work_dir}/doDr_3306_1234567/
	taskDir string
	// untarDir  move-back: /data1/mysqldata/${root_id}/doDr_3306_1234567
	// copy-back: is taskDir
	untarDir string
	// 备份解压后的目录，${taskDir}/<backupBaseName>/
	targetDir string
	// dbLoader is interface
	dbLoader dbbackup_loader.DBBackupLoader
	// myCnf for physical backup
	myCnf *util.CnfFile
}

// SContext 全局共享变量，持久化，可传递到下一个节点
var SContext *filecontext.FileContext

// Init load index file
func (m *DBLoader) Init() error {
	// validateBackupInfo before run import
	// 重建模式，不需要 restore_opt 选项，但要校验位点信息
	// 回档模式，如果是备份记录回档则不需要位点，如果是需要基于 binlog 回档，则要检验位点信息
	if m.RestoreParam.RestoreOpt == nil {
		m.RestoreParam.RestoreOpt = &RestoreOpt{
			EnableBinlog:      false,
			WillRecoverBinlog: true,
			InitCommand:       "",
		}
	}

	if SContext == nil {
		SContext = filecontext.NewFileContext(fmt.Sprintf(
			"/tmp/dbloader_ctx_%d_%s.json", m.TgtInstance.Port, subcmd.GBaseOptions.RootId))
	}
	SContext.Set("untar_remove_original", false, false)
	SContext.Set("change_master", nil, false)
	SContext.Save()

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

	if m.RestoreParam.RestoreOpt.WillRecoverBinlog {
		if info, err := m.getChangeMasterPos(m.SrcInstance); err != nil {
			return err
		} else {
			SContext.Set("change_master", info, true)
		}
	}
	if m.RestoreParam.RestoreOpt.RecoverGrants {
		privFile := m.RestoreParam.indexObj.GetTarFileList("priv")
		if len(privFile) == 0 {
			return errors.Errorf("no priv file found in %s", m.RestoreParam.BackupDir)
		} else if f := filepath.Join(m.RestoreParam.BackupDir, privFile[0]); !cmutil.FileExists(f) {
			return errors.Errorf("priv file %s not found", privFile[0])
		} else {
			logger.Info("will recover grants file after finishing data restore: %s", f)
		}
	}
	// 工具可执行权限
	// 本地实例是否可联通
	return nil
}

// chooseDBBackupLoader 选择是 dbbackup-go 恢复是 logical or physical
func (m *DBLoader) chooseDBBackupLoader() error {
	dbloaderPath := m.Tools.MustGet(tools.ToolDbbackupGo)
	if m.RestoreOpt == nil {
		m.RestoreOpt = &RestoreOpt{
			EnableBinlog: false,
			InitCommand:  "",
		}
	}
	dbLoaderUtil := &dbbackup_loader.LoaderUtil{
		Client:        dbloaderPath,
		TgtInstance:   m.TgtInstance,
		IndexFilePath: m.BackupInfo.indexFilePath,
		IndexObj:      m.BackupInfo.indexObj,
		LoaderDir:     m.targetDir,
		TaskDir:       m.taskDir,
		BackupDir:     m.BackupDir,
		LogDir:        m.LogDir,
		EnableBinlog:  m.RestoreOpt.EnableBinlog,
		InitCommand:   m.RestoreOpt.InitCommand,
		RecoverGrants: m.RestoreParam.RestoreOpt.RecoverGrants,
	}
	// logger.Warn("validate dbLoaderUtil: %+v", m.dbLoaderUtil)
	if err := validate.GoValidateStruct(dbLoaderUtil, false); err != nil {
		return err
	}

	if m.backupType == cst.BackupTypeLogical {
		myloaderOpt := &dbbackup_loader.LoaderOpt{}
		copier.Copy(myloaderOpt, m.RestoreOpt)
		logger.Warn("myloaderOpt copied: %+v. src:%+v", myloaderOpt, m.RestoreOpt)
		m.dbLoader = &dbbackup_loader.LogicalLoader{
			LoaderUtil:  dbLoaderUtil,
			MyloaderOpt: myloaderOpt,
		}
	} else if m.backupType == cst.BackupTypePhysical {
		// include rocksdb, tokudb
		m.dbLoader = &dbbackup_loader.PhysicalLoader{
			LoaderUtil: dbLoaderUtil,
			Xtrabackup: &dbbackup_loader.Xtrabackup{
				TgtInstance:   dbLoaderUtil.TgtInstance,
				SrcBackupHost: dbLoaderUtil.IndexObj.BackupHost,
				QpressTool:    m.Tools.MustGet(tools.ToolQPress),
				LoaderDir:     m.targetDir,
				StorageType:   strings.ToLower(m.indexObj.StorageEngine),
				MySQLVersion:  m.BackupInfo.indexObj.MysqlVersion,
			},
			CopyBack:          m.RestoreOpt.PhysicalCopyBack,
			RenameOriginalDir: m.RestoreOpt.PhysicalRenameOriginalDir,
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
		cmutil.ExecCommand(false, "", "chown", "-R", "mysql:mysql", m.taskDir)
	}()

	// 做并发约束判断
	restoreDataLockFile, maxProcessNum := m.getConcurrencyInfo()
	fileLock, err := filecontext.NewIncrFile(restoreDataLockFile, maxProcessNum, 20*time.Second)
	if err != nil {
		return err
	}
	// 未解之谜：在 tlinux4 上这个打开，会导致 permission denied
	//_ = cmutil.ChownNotUsingExec(fileLock.GetContextFilePath(), "mysql", "mysql")
	logger.Info("using lock file %s", fileLock.GetContextFilePath())
	if err := fileLock.Incr(1); err != nil {
		return errors.WithMessage(err, "file lock incr failed")
	}
	defer fileLock.Done()

	logger.Info("开始解压 untarDir=%s", m.untarDir)
	if err := m.BackupInfo.indexObj.UntarFiles(m.untarDir, SContext); err != nil {
		return err
	} else if baseName := filepath.Base(m.targetDir); m.untarDir != m.taskDir {
		// 创建软连接到 taskDir 下，方便查看
		os.Symlink(m.targetDir, filepath.Join(m.taskDir, baseName))
	}

	// TODO 解压完，这里存档，避免重试时从头来过

	logger.Info("开始数据恢复 targetDir=%s", m.targetDir)
	if err := m.dbLoader.Load(); err != nil {
		// 导入失败了也打印位点，但不输出到上下文
		if changeMs, err := m.getChangeMasterPos(m.SrcInstance); err == nil {
			logger.Warn("change master pos: %+v", changeMs.GetSQL())
		}
		return errors.WithMessage(err, "dbactuator dbloaderData failed")
	}
	// 清理恢复中转目录：安全起见，只清理路径带 doDr_ 的目录
	if strings.Contains(m.targetDir, "doDr_") {
		if err := os.RemoveAll(m.targetDir); err != nil {
			logger.Warn("fail to remove old recover dir: %s. ignore %s", m.targetDir, err.Error())
			//return err
		}
	}
	// 进度存档
	SContext.Set("recover_data_success", true, true)

	if m.RestoreParam.SkipAfterLoad {
		logger.Info("skip PostLoad as requested, will be done by restore-dr-after")
	} else {
		logger.Info("running PostLoad now")
		if err := m.dbLoader.PostLoad(); err != nil {
			return err
		}
	}
	return nil
}

// ReturnChangeMaster TODO
func (m *DBLoader) ReturnChangeMaster() (*mysqlutil.ChangeMaster, error) {
	return m.getChangeMasterPos(m.SrcInstance)
}

// initDirs 如果 removeOld =  true，会删除当前任务目录下，之前的解压目录，可能是重试导致的废弃目录
func (m *DBLoader) initDirs(removeOld bool) error {
	if m.BackupInfo.WorkDir == "" {
		return errors.Errorf("work_dir %s should not be empty", m.WorkDir)
	}
	if m.WorkID == "" {
		m.WorkID = cmutil.NewTimestampString()
		//m.WorkID = subcmd.GBaseOptions.RootId
		//SContext.Set("work_id", m.WorkID, true)
	}

	untarDirSuffix := fmt.Sprintf("doDr_%d_%s", m.TgtInstance.Port, m.WorkID)
	m.taskDir = filepath.Join(m.WorkDir, untarDirSuffix)
	// 物理备份 targetDir 直接放在数据目录所在分区
	if untarDir2, _ := SContext.GetString("untar_dir"); untarDir2 != "" {
		m.untarDir = filepath.Join(untarDir2, untarDirSuffix)
		logger.Info("use untar dir from file context %s: %s", SContext.GetContextFilePath(), untarDir2)
	} else if m.BackupInfo.backupType == cst.BackupTypePhysical && !m.RestoreOpt.PhysicalCopyBack {
		// move-back directly by default
		// get mysql data root dir (not mysql datadir) to save untar files
		if instanceDataRootDir, err := m.myCnf.GetMySQLDataRootDir(); err != nil {
			logger.Warn("fail to get mysqld datadir: %s", m.myCnf.FileName)
		} else {
			if subcmd.GBaseOptions.RootId == "" {
				subcmd.GBaseOptions.RootId = cast.ToString(m.TgtInstance.Port)
			}
			// untarDir = /data1/mysqldata/[xyzrootid/doDr_20000_1234567]
			untarDirSuffix = fmt.Sprintf("%s/%s", subcmd.GBaseOptions.RootId, untarDirSuffix)
			m.untarDir = filepath.Join(filepath.Dir(instanceDataRootDir), untarDirSuffix)
			logger.Info("use untar dir under datadir: %s", instanceDataRootDir)
		}
	}
	if m.untarDir == "" {
		// untarDir = /data/dbbak/xyzrootid/[20000/doDr_20000_1234567]
		m.untarDir = m.taskDir
		logger.Info("use untar dir under workDir %s: %s", m.WorkDir)
	}
	if removeOld { // 删除旧目录
		timeNow := time.Now()
		// 只匹配 doDr_ 开头的目录，避免删
		searchUntarDir := fmt.Sprintf("%s/doDr_%d_*", filepath.Dir(m.untarDir), m.TgtInstance.Port)
		oldDirs, _ := filepath.Glob(searchUntarDir)
		for _, oldDir := range oldDirs {
			if dirInfo, err := os.Stat(oldDir); err == nil && dirInfo.IsDir() {
				if timeNow.Sub(dirInfo.ModTime()) > 1*time.Minute {
					logger.Warn("remove old recover work directory: %s", oldDir)
					cmutil.SafeRmDir(oldDir)
				}
			}
		}
	}

	if err := osutil.CheckAndMkdir("", m.taskDir); err != nil {
		return err
	}
	if err := osutil.CheckAndMkdir("", m.untarDir); err != nil {
		return err
	}
	if dirParts := strings.Split(m.untarDir, "/"); len(dirParts) >= 2 {
		dbbakDir := "/" + strings.Join(dirParts[:2], "/")
		osutil.ExecShellCommand(false, fmt.Sprintf("chown mysql:mysql %s", dbbakDir))
	}

	m.targetDir = filepath.Join(m.untarDir, m.BackupInfo.indexObj.GetBackupFileBasename())
	logger.Info("current recover work directory: %s", m.taskDir)
	logger.Info("current recover work untar directory: %s", m.untarDir)
	logger.Info("current recover work target directory: %s", m.targetDir)
	SContext.Set("task_dir", m.taskDir, false)
	SContext.Set("untar_dir", m.untarDir, false)
	err := SContext.Set("target_dir", m.targetDir, true)
	if err != nil {
		return err
	}

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

func (m *DBLoader) getConcurrencyInfo() (string, int) {
	restoreDataLockFile := "/tmp/mysql_restore_data.lock.yaml"
	threadsForOneInstance := 16 // cpu cores?

	cpuCores := 8
	if cpus, err := cmutil.GetCPUInfo(); err == nil {
		cpuCores = cpus.CoresLogical
	} else {
		logger.Warn("fail loader get cpu cores(use 8): ", err.Error())
	}
	if m.TotalThreads == 0 {
		m.TotalThreads = cpuCores
	}
	if cpuCores < threadsForOneInstance {
		// 避免低核机器 cpu 占用太高
		threadsForOneInstance = cpuCores
	} else if cpuCores >= 64 {
		// 这里影响的就是单机单实例的恢复速度，因为实例本身并不知道还有没有其他恢复进程。这里意思一下，单实例加大到 32
		threadsForOneInstance = 32
	}

	maxProcessNum := m.TotalThreads/threadsForOneInstance + 1
	return restoreDataLockFile, maxProcessNum
}
