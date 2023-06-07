package mysql

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"encoding/json"
	"fmt"
	"math/rand"
	"path"
	"strings"
	"time"

	"gopkg.in/ini.v1"
)

const MachineTypeBackend = "backend"
const MachineTypeSingle = "single"
const MachineTypeSpider = "spider"
const MachineTypeRemote = "remote"

// BackupDatabaseTableComp struct
type BackupDatabaseTableComp struct {
	Params           *BackupDatabaseTableParam `json:"extend"`
	BackupRunTimeCtx `json:"-"`
	tools            *tools.ToolSet
}

// BackupDatabaseTableParam struct
type BackupDatabaseTableParam struct {
	Host        string `json:"host" validate:"required,ip"`
	Port        int    `json:"port" validate:"required,lt=65536,gte=3306"`
	MachineType string `json:"machine_type" validate:"required"`
	Regex       string `json:"regex" validate:"required"`
	BackupId    string `json:"backup_id" validate:"required"`
	BillId      string `json:"bill_id" validate:"required"`
}

// BackupRunTimeCtx 运行时上下文
type BackupRunTimeCtx struct {
	BackupDir        string
	StatusReportPath string
	ResultReportPath string
	ConfPath         string
	RandNum          string
}

// Report struct
type Report struct {
	ReportResult []ReportResult `json:"report_result"`
	ReportStatus ReportStatus   `json:"report_status"`
}

// BackupGoConfig 备份配置文件
type BackupGoConfig struct {
	SectionStringPublic       string
	BackupParamPublic         *dbbackup.CnfShared
	SectionStringBackupSystem string
	BackupParamBackupSystem   *dbbackup.CnfBackupClient
	SectionStringLogical      string
	BackupParamLogical        *dbbackup.CnfLogicalBackup
}

// ReportStatus ReportStatus
type ReportStatus struct {
	BackupId   string `json:"backup_id"`
	BillId     string `json:"bill_id"`
	Status     string `json:"status"`
	ReportTime string `json:"report_time"`
}

// ReportResult result
type ReportResult struct {
	BackupId             string `json:"backup_id"`
	BkBizId              string `json:"bk_biz_id"`
	BillId               string `json:"bill_id"`
	BkCloudId            string `json:"bk_cloud_id"`
	TimeZone             string `json:"time_zone"`
	ClusterAddress       string `json:"cluster_address"`
	MysqlHost            string `json:"mysql_host"`
	MysqlPort            int    `json:"mysql_port"`
	MasterHost           string `json:"master_host"`
	MasterPort           int    `json:"master_port"`
	FileName             string `json:"file_name"`
	BackupBeginTime      string `json:"backup_begin_time"`
	BackupEndTime        string `json:"backup_end_time"`
	DataSchemaGrant      string `json:"data_schema_grant"`
	BackupType           string `json:"backup_type"`
	ConsistentBackupTime string `json:"consistent_backup_time"`
	MysqlRole            string `json:"mysql_role"`
	FileSize             int64  `json:"file_size"`
	FileType             string `json:"file_type"`
	TaskId               string `json:"task_id"`
}

// Precheck 检查备份工具是否存在
func (c *BackupDatabaseTableComp) Precheck() (err error) {
	c.tools, err = tools.NewToolSetWithPick(tools.ToolDbbackupGo)
	if err != nil {
		logger.Error("init toolset failed: %s", err.Error())
		return err
	}
	c.BackupDir = cst.DbbackupGoInstallPath
	return nil
}

// CreateBackupConfigFile 生成配置
func (c *BackupDatabaseTableComp) CreateBackupConfigFile() error {
	ts := time.Now().UnixNano()
	rand.Seed(ts)
	r := rand.Intn(100)
	c.RandNum = fmt.Sprintf("%d%d", ts, r)

	// 3306端口 dbbackup.3306.ini
	dailyBackupConfPath := path.Join(c.BackupDir, fmt.Sprintf("dbbackup.%d.ini", c.Params.Port))

	dailyConf, err := c.ReadDailyBackupConfigFile(dailyBackupConfPath)
	if err != nil {
		logger.Error("读取备份配置文件%s失败:%s", dailyBackupConfPath, err.Error())
		return err
	}
	err = c.ModifyNewBackupConfigFile(dailyConf)
	if err != nil {
		logger.Error("生成库表备份配置文件%s失败:%s", c.ConfPath, err.Error())
		return err
	}
	err = c.WriteToConfigFile(dailyConf)
	if err != nil {
		logger.Error("生成库表备份配置文件%s失败:%s", c.ConfPath, err.Error())
		return err
	}
	return nil
}

// WriteToConfigFile 写配置
func (c *BackupDatabaseTableComp) WriteToConfigFile(config *BackupGoConfig) error {
	c.ConfPath = path.Join(cst.BK_PKG_INSTALL_PATH, fmt.Sprintf("dbactuator-%s", c.Params.BillId),
		fmt.Sprintf("dbbackup.%d.%s.ini", c.Params.Port, c.RandNum))
	file := ini.Empty()
	mysqlSection, err := file.NewSection(config.SectionStringPublic)
	if err != nil {
		logger.Error("new section failed:%s", err.Error())
		return err
	}
	err = mysqlSection.ReflectFrom(config.BackupParamPublic)
	if err != nil {
		logger.Error("public section ReflectFrom failed:%s", err.Error())
		return err
	}

	mysqlSection, err = file.NewSection(config.SectionStringBackupSystem)
	if err != nil {
		logger.Error("new section failed:%s", err.Error())
		return err
	}
	err = mysqlSection.ReflectFrom(config.BackupParamBackupSystem)
	if err != nil {
		logger.Error("backup system section ReflectFrom failed:%s", err.Error())
		return err
	}

	mysqlSection, err = file.NewSection(config.SectionStringLogical)
	if err != nil {
		logger.Error("new section failed:%s", err.Error())
		return err
	}
	err = mysqlSection.ReflectFrom(config.BackupParamLogical)
	if err != nil {
		logger.Error("logical section ReflectFrom failed:%s", err.Error())
		return err
	}

	err = file.SaveTo(c.ConfPath)
	if err != nil {
		logger.Error("config file save failed:%s", err.Error())
		return err
	}
	return nil
}

// ReadDailyBackupConfigFile 读取日常备份配置文件
func (c *BackupDatabaseTableComp) ReadDailyBackupConfigFile(vPath string) (*BackupGoConfig, error) {
	cnf, err := ReadBackupConfigFile(vPath)
	if err != nil {
		return cnf, err
	}

	c.ResultReportPath = path.Join(
		cnf.BackupParamPublic.ResultReportPath, fmt.Sprintf(
			"dbareport_result_%d.log",
			c.Params.Port,
		),
	)
	c.StatusReportPath = path.Join(
		cnf.BackupParamPublic.StatusReportPath, fmt.Sprintf(
			"dbareport_status_%d.log",
			c.Params.Port,
		),
	)

	return cnf, err
}

// ReadBackupConfigFile 读取备份配置文件
func ReadBackupConfigFile(path string) (*BackupGoConfig, error) {
	publicConf := new(dbbackup.CnfShared)
	logicalConf := new(dbbackup.CnfLogicalBackup)
	backupSystemConf := new(dbbackup.CnfBackupClient)

	file, err := ini.Load(path)
	if err != nil {
		return nil, err
	}
	// config.SectionStrings()[0]:DEFAULT
	err = file.Section(file.SectionStrings()[1]).StrictMapTo(publicConf)
	if err != nil {
		return nil, err
	}
	err = file.Section(file.SectionStrings()[2]).StrictMapTo(backupSystemConf)
	if err != nil {
		return nil, err
	}
	err = file.Section(file.SectionStrings()[3]).StrictMapTo(logicalConf)
	if err != nil {
		return nil, err
	}

	return &BackupGoConfig{
		file.SectionStrings()[1], publicConf,
		file.SectionStrings()[2], backupSystemConf,
		file.SectionStrings()[3], logicalConf,
	}, nil
}

// ModifyNewBackupConfigFile 修改临时配置文件
func (c *BackupDatabaseTableComp) ModifyNewBackupConfigFile(config *BackupGoConfig) error {
	config.BackupParamPublic.BackupType = "Logical"
	config.BackupParamPublic.BackupTimeOut = ""
	config.BackupParamPublic.BillId = c.Params.BillId
	config.BackupParamPublic.BackupId = c.Params.BackupId
	config.BackupParamLogical.Regex = c.Params.Regex
	if c.Params.MachineType == MachineTypeBackend || c.Params.MachineType == MachineTypeSingle ||
		c.Params.MachineType == MachineTypeRemote {
		config.BackupParamPublic.DataSchemaGrant = "data,schema"
	} else if c.Params.MachineType == MachineTypeSpider {
		config.BackupParamPublic.DataSchemaGrant = "schema"
	} else {
		err := fmt.Errorf("not matched machine type:%s", c.Params.MachineType)
		logger.Error(err.Error())
		return err
	}
	timeStr := time.Now().Format("20060102_150405")
	backupTo := path.Join(
		config.BackupParamPublic.BackupDir, fmt.Sprintf(
			"%s_%s_%s", "backupDatabaseTable",
			timeStr, c.RandNum,
		),
	)

	cmd := fmt.Sprintf("mkdir -p %s", backupTo)
	if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
		logger.Error("创建备份目录%s 失败:%s", cmd, err.Error())
		return err
	}

	config.BackupParamPublic.BackupDir = backupTo
	return nil
}

// DoBackup 执行备份
func (c *BackupDatabaseTableComp) DoBackup() error {
	cmd := fmt.Sprintf(
		"%s dumpbackup --config=%s",
		c.tools.MustGet(tools.ToolDbbackupGo),
		c.ConfPath,
	)
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute %s failed: %s", cmd, err.Error())
		return err
	}
	logger.Info("backup cmd: %s", cmd)
	return nil
}

// OutputBackupInfo 输出备份报告
func (c *BackupDatabaseTableComp) OutputBackupInfo() error {
	res, err := GenerateReport(c.Params.BillId, c.StatusReportPath, c.ResultReportPath)
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

// GenerateReport 生成报告
func GenerateReport(billId string, statusLogFile string, resultLogFile string) (*Report, error) {
	var res Report
	var status []ReportStatus
	var result []ReportResult

	cmd := fmt.Sprintf(`grep '"bill_id":"%s"' %s`, billId, statusLogFile)
	out, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute %s failed: %s.", cmd, err.Error())
		return nil, err
	}

	out = strings.ReplaceAll(out, "\n", ",")
	out = strings.Trim(out, ",")
	out = fmt.Sprintf("%s%s%s", "[", out, "]")
	err = json.Unmarshal([]byte(out), &status)
	if err != nil {
		logger.Error("get backup report status unmarshal failed: %s.", err.Error())
		return nil, err
	}

	last := len(status) - 1
	res.ReportStatus = status[last]
	if res.ReportStatus.Status != "Success" {
		err := fmt.Errorf("report status is not Success: %s", res.ReportStatus)
		logger.Error(err.Error())
		return nil, err
	}

	cmd = fmt.Sprintf(`grep '"backup_id":"%s"' %s`, res.ReportStatus.BackupId, resultLogFile)

	out, err = osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute %s failed: %s.", cmd, err.Error())
		return nil, err
	}
	out = strings.ReplaceAll(out, "\n", ",")
	out = strings.Trim(out, ",")
	out = fmt.Sprintf("%s%s%s", "[", out, "]")
	err = json.Unmarshal([]byte(out), &result)
	if err != nil {
		logger.Error("get backup report result unmarshal failed: %s.", err.Error())
		return nil, err
	}
	res.ReportResult = result
	return &res, nil
}
