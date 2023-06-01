package mysql

import (
	"fmt"
	"path"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"gopkg.in/ini.v1"
)

// FullBackupComp 基本结构
type FullBackupComp struct {
	GeneralParam *components.GeneralParam
	Params       *FullBackupParam
	tools        *tools.ToolSet
	FullBackupCtx
}

// FullBackupParam godoc
type FullBackupParam struct {
	Host string `json:"host"`
	Port int    `json:"port"`
	// Charset    string `json:"charset"`
	BackupType string `json:"backup_type"`
	FileTag    string `json:"file_tag"`
	BillId     string `json:"bill_id"`
}

// FullBackupCtx 上下文
type FullBackupCtx struct {
	backupGoDailyConfig *BackupGoConfig
	uid                 string
	cfgFilePath         string
	ReportStatusLog     string
	ReportResultLog     string
}

// Precheck 预检查
func (c *FullBackupComp) Precheck() (err error) {
	_, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.DbBackupUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.DbBackupPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect %s:%d failed:%s", c.Params.Host, c.Params.Port, err.Error())
		return err
	}

	c.tools, err = tools.NewToolSetWithPick(tools.ToolDbbackupGo)
	if err != nil {
		logger.Error("init toolset failed: %s", err.Error())
		return err
	}

	return nil
}

// Init 初始化
func (c *FullBackupComp) Init(uid string) (err error) {
	c.uid = uid

	configFile := path.Join(cst.DbbackupGoInstallPath, cst.DbbackupConfigFilename(c.Params.Port))
	if !osutil.FileExist(configFile) {
		err = fmt.Errorf("backup config file %s not found", configFile)
		logger.Error(err.Error())
		return err
	}

	cfg, err := ReadBackupConfigFile(configFile)
	if err != nil {
		logger.Error("read %s failed: %s", configFile, err.Error())
		return err
	}

	c.backupGoDailyConfig = cfg

	c.ReportResultLog = path.Join(
		c.backupGoDailyConfig.BackupParamPublic.ResultReportPath,
		fmt.Sprintf("dbareport_result_%d.log", c.Params.Port),
	)
	c.ReportStatusLog = path.Join(
		c.backupGoDailyConfig.BackupParamPublic.StatusReportPath,
		fmt.Sprintf("dbareport_status_%d.log", c.Params.Port),
	)
	return nil
}

// GenerateConfigFile 生成配置
func (c *FullBackupComp) GenerateConfigFile() (err error) {
	c.backupGoDailyConfig.BackupParamPublic.BackupType = c.Params.BackupType
	c.backupGoDailyConfig.BackupParamPublic.DataSchemaGrant = "ALL"
	c.backupGoDailyConfig.BackupParamPublic.BillId = c.Params.BillId
	c.backupGoDailyConfig.BackupParamBackupSystem.FileTag = c.Params.FileTag
	c.backupGoDailyConfig.BackupParamPublic.BackupTimeOut = ""

	// if strings.ToLower(c.Params.Charset) != "default" {
	//	c.backupGoDailyConfig.BackupParamPublic.MysqlCharset = strings.ToLower(c.Params.Charset)
	// }
	// c.backupGoDailyConfig.BackupParamPublic.BackupTimeOut ToDo 怎么搞

	f := ini.Empty()
	section, err := f.NewSection(c.backupGoDailyConfig.SectionStringPublic)
	if err != nil {
		logger.Error("new public section failed: %s", err.Error())
		return err
	}
	err = section.ReflectFrom(c.backupGoDailyConfig.BackupParamPublic)
	if err != nil {
		logger.Error("public section reflect failed: %s", err.Error())
		return err
	}

	section, err = f.NewSection(c.backupGoDailyConfig.SectionStringBackupSystem)
	if err != nil {
		logger.Error("new backup system section failed: %s", err.Error())
		return err
	}
	err = section.ReflectFrom(c.backupGoDailyConfig.BackupParamBackupSystem)
	if err != nil {
		logger.Error("backup system section reflect failed: %s", err.Error())
		return err
	}

	section, err = f.NewSection(c.backupGoDailyConfig.SectionStringLogical)
	if err != nil {
		logger.Error("new logical section failed: %s", err.Error())
		return err
	}
	err = section.ReflectFrom(c.backupGoDailyConfig.BackupParamLogical)
	if err != nil {
		logger.Error("logical section reflect failed: %s", err.Error())
		return err
	}

	c.cfgFilePath = path.Join("/tmp", fmt.Sprintf("dbbackup.%d.%s.ini", c.Params.Port, c.uid))

	err = f.SaveTo(c.cfgFilePath)
	if err != nil {
		logger.Error("save %s failed: %s", c.cfgFilePath, err.Error())
		return err
	}

	return nil
}

// DoBackup 执行
func (c *FullBackupComp) DoBackup() (err error) {
	// defer func() {
	//	_ = os.Remove(c.cfgFilePath)
	// }()

	cmd := fmt.Sprintf(
		"%s --configpath=%s --dumpbackup",
		c.tools.MustGet(tools.ToolDbbackupGo),
		c.cfgFilePath,
	)
	_, err = osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute %s failed: %s", cmd, err.Error())
		return err
	}
	return nil
}

// OutputBackupInfo 输出报告
func (c *FullBackupComp) OutputBackupInfo() error {
	res, err := GenerateReport(c.Params.BillId, c.ReportStatusLog, c.ReportResultLog)
	if err != nil {
		logger.Error("generate report failed: %s", err.Error())
		return err
	}

	err = components.PrintOutputCtx(res)
	if err != nil {
		logger.Error("print backup report info failed: %s.", err.Error())
		return err
	}

	return nil
}

// Example 例子
func (c *FullBackupComp) Example() interface{} {
	comp := FullBackupComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &FullBackupParam{
			Host: "127.0.0.1",
			Port: 20000,
			// Charset:    "default",
			BackupType: "LOGICAL",
			FileTag:    "MYSQL_FULL_BACKUP",
			BillId:     "123456",
		},
	}
	return comp
}
