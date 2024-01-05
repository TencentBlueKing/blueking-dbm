package restore

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// MLoad TODO
type MLoad struct {
	*RestoreParam

	taskDir   string // 依赖 BackupInfo.WorkDir ${work_dir}/doDr_${id}/${port}/
	targetDir string // 备份解压后的目录，${taskDir}/backupBaseName/
	mloadUtil MLoadParam
	dbWorker  *native.DbWorker // TgtInstance
}

// Init TODO
func (m *MLoad) Init() error {
	var err error
	logger.Info("mload infoObj:%+v file=%s", m.BackupInfo.infoObj, m.BackupInfo.infoFilePath)
	if err = m.BackupInfo.infoObj.ValidateFiles(); err != nil {
		return err
	}
	if err = m.initDirs(); err != nil {
		return err
	}
	// 本地实例是否可联通
	m.dbWorker, err = m.TgtInstance.Conn()
	if err != nil {
		return errors.Wrap(err, "目标实例连接失败")
	}
	return nil
}

// PreCheck TODO
func (m *MLoad) PreCheck() error {
	toolset, err := tools.NewToolSetWithPick(tools.ToolMload)
	if err != nil {
		return err
	}
	if err := m.Tools.Merge(toolset); err != nil {
		return err
	}
	// 工具可执行权限
	return nil
}

// Start TODO
func (m *MLoad) Start() error {
	mloadPath := m.Tools.MustGet(tools.ToolMload)
	m.mloadUtil = MLoadParam{
		Client:            mloadPath,
		Host:              m.TgtInstance.Host,
		Port:              m.TgtInstance.Port,
		User:              m.TgtInstance.User,
		Password:          m.TgtInstance.Pwd,
		Charset:           m.BackupInfo.infoObj.Charset,
		PathList:          []string{m.targetDir},
		TaskDir:           m.taskDir,
		db:                m.dbWorker,
		checkMLoadProcess: true,
		WithOutBinlog:     true,
	}
	if m.RestoreOpt != nil {
		o := m.RestoreOpt
		if !m.RestoreOpt.WillRecoverBinlog {
			// schema/data 一起导入
			m.mloadUtil.flagApartSchemaData = false
		} else {
			if len(o.Databases)+len(o.Tables)+len(o.IgnoreDatabases)+len(o.IgnoreTables) == 0 {
				// schema/data 一起全部导入, recover-binlog quick_mode只能false
				logger.Info("no filter: import schema and data together, recover-binlog need quick_mode=false")
				m.mloadUtil.flagApartSchemaData = false
			} else if m.RestoreOpt.SourceBinlogFormat != "ROW" {
				logger.Info("binlog_format!=row: import schema and data together, recover-binlog need quick_mode=false")
				// 指定 filter databases/tables（或者指定无效）,导入数据时，必须全部导入 schema 和 data.恢复时也恢复全量 binlog,即 quick_mode=false
				m.mloadUtil.flagApartSchemaData = false
			} else { // 存在 filter 且 binlog_format=row
				logger.Info("import full-schema and specific-data apart, recover-binlog filter depends on its quick_mode")
				m.mloadUtil.Databases = o.Databases
				m.mloadUtil.Tables = o.Tables
				m.mloadUtil.IgnoreDatabases = o.IgnoreDatabases
				m.mloadUtil.IgnoreTables = o.IgnoreTables
				// 1. schema全部导入，data 指定导入, 2. schema/data 一起部分导入, 但后续 recover-binlog 的错误概率可能变高
				// recover-binlog 有 quick_mode 控制是恢复全量 binlog 还是恢复指定库表 binlog (event_query_handler=error)
				m.mloadUtil.flagApartSchemaData = true
			}
		}
	}

	if err := validate.GoValidateStruct(m.mloadUtil, false, false); err != nil {
		return err
	}
	logger.Info("mload params %+v", m)
	if err := m.BackupInfo.infoObj.UntarFiles(m.taskDir); err != nil {
		return err
	}
	// 针对空库，可能备份了 infodba_schema，导入时忽略掉
	if cmutil.FileExists(filepath.Join(m.targetDir, native.INFODBA_SCHEMA)) {
		m.mloadUtil.IgnoreDatabases = append(m.mloadUtil.IgnoreDatabases, native.INFODBA_SCHEMA)
	}
	if err := m.mloadUtil.Run(); err != nil {
		return errors.Wrap(err, "mloadData failed")
	}
	return nil
}

// WaitDone TODO
func (m *MLoad) WaitDone() error {
	return nil
}

// PostCheck TODO
func (m *MLoad) PostCheck() error {
	return nil
}

// ReturnChangeMaster TODO
func (m *MLoad) ReturnChangeMaster() (*mysqlutil.ChangeMaster, error) {
	return m.getChangeMasterPos(m.SrcInstance)
}

func (m *MLoad) initDirs() error {
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
	/*
		if m.backupBaseName == "" {
			return errors.Errorf("backup file baseName [%s] error", m.backupBaseName)
		}
	*/
	//m.targetDir = fmt.Sprintf("%s/%s", m.taskDir, m.backupBaseName)
	m.targetDir = fmt.Sprintf("%s/%s", m.taskDir, m.BackupInfo.infoObj.GetMetafileBasename())
	return nil
}

// getChangeMasterPos godoc
// srcMaster -> srcSlave
//
//	|-> tgtMaster -> tgtSlave
//
// tgtMaster 始终指向 srcMaster host,port
func (m *MLoad) getChangeMasterPos(masterInst native.Instance) (*mysqlutil.ChangeMaster, error) {
	// -- CHANGE MASTER TO
	// -- CHANGE SLAVE TO
	backupPosFile := "DUMP.BEGIN.sql.gz"
	cmd := fmt.Sprintf("zcat %s/%s |grep 'CHANGE '", m.targetDir, backupPosFile)
	out, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		return nil, err
	}
	changeSqls := cmutil.SplitAnyRune(out, "\n")
	if len(changeSqls) == 2 {
		// backupRole := DBRoleSlave
	}
	var changeSql string
	// 在 slave 上备份，会同时有 CHANGE MASTER, CHANGE SLAVE
	reChangeMaster := regexp.MustCompile(`(?i:CHANGE MASTER TO)`)
	// reChangeSlave := regexp.MustCompile(`(?i:CHANGE SLAVE TO)`)   // 在 master 上备份，只有 CHANGE SLAVE
	for _, sql := range changeSqls {
		if reChangeMaster.MatchString(sql) {
			sql = strings.ReplaceAll(sql, "--", "")
			changeSql = sql
			break
		}
	}
	cm := &mysqlutil.ChangeMaster{ChangeSQL: changeSql}
	if err := cm.ParseChangeSQL(); err != nil {
		return nil, errors.Wrap(err, changeSql)
	}
	cm.MasterHost = masterInst.Host
	cm.MasterPort = masterInst.Port
	return cm, nil
}
