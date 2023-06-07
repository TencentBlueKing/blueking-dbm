package mysql

import (
	"fmt"
	"os/exec"
	"path"

	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// BackupTruncateDatabaseComp TODO
type BackupTruncateDatabaseComp struct {
	GeneralParam *components.GeneralParam
	Params       BackupTruncateDatabaseParam
	BackupTruncateDatabaseCtx
}

// BackupTruncateDatabaseParam TODO
type BackupTruncateDatabaseParam struct {
	Host          string         `json:"host" validate:"required,ip"`
	Port          int            `json:"port" validate:"required,lt=65536,gte=3306"`
	DatabaseInfos []DatabaseInfo `json:"database_infos"`
}

// DatabaseInfo TODO
type DatabaseInfo struct {
	Old string `json:"old"`
	New string `json:"new"`
}

// DatabaseInfoCtx TODO
type DatabaseInfoCtx struct {
	DatabaseInfo
	SqlFile string `json:"sql_file"`
}

// BackupTruncateDatabaseCtx TODO
type BackupTruncateDatabaseCtx struct {
	dbConn           *native.DbWorker
	charset          string
	dumpCmd          string
	socket           string
	databaseInfosCtx []DatabaseInfoCtx
	uid              string
	backupDir        string
}

// Init TODO
func (c *BackupTruncateDatabaseComp) Init(uid string) (err error) {
	c.dbConn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
	}

	if c.socket, err = c.dbConn.ShowSocket(); err != nil {
		logger.Error("获取socket value 失败:%s", err.Error())
		return err
	}

	c.uid = uid
	return nil
}

// Precheck TODO
func (c *BackupTruncateDatabaseComp) Precheck() error {
	c.dumpCmd = path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	if !osutil.FileExist(c.dumpCmd) {
		return fmt.Errorf("dumpCmd：%s文件不存在", c.dumpCmd)
	}
	return nil
}

// ReadBackupConf TODO
func (c *BackupTruncateDatabaseComp) ReadBackupConf() error {
	dailyBackupConfPath := path.Join(
		cst.DbbackupGoInstallPath,
		fmt.Sprintf("dbbackup.%d.ini", c.Params.Port),
	)

	dailyConfigFile, err := ini.Load(dailyBackupConfPath)
	if err != nil {
		logger.Error("load %s failed: %s", dailyBackupConfPath, err.Error())
		return err
	}

	var backupConfig config.BackupConfig
	err = dailyConfigFile.MapTo(&backupConfig)
	if err != nil {
		logger.Error("map %s to struct failed: %s", dailyBackupConfPath, err.Error())
		return err
	}

	c.charset = backupConfig.Public.MysqlCharset
	c.backupDir = backupConfig.Public.BackupDir
	return nil
}

// DumpSchema TODO
func (c *BackupTruncateDatabaseComp) DumpSchema() error {
	for _, dbInfo := range c.Params.DatabaseInfos {
		oldDb := dbInfo.Old
		backupFileName := fmt.Sprintf(
			`truncate_dump_%s_%d_%s_%s.sql`,
			c.Params.Host,
			c.Params.Port,
			oldDb,
			c.uid,
		)

		var dumper mysqlutil.Dumper
		dumper = &mysqlutil.MySQLDumperTogether{
			MySQLDumper: mysqlutil.MySQLDumper{
				DumpDir:      c.backupDir,
				Ip:           c.Params.Host,
				Port:         c.Params.Port,
				DbBackupUser: c.GeneralParam.RuntimeAccountParam.AdminUser,
				DbBackupPwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
				DbNames:      []string{oldDb},
				DumpCmdFile:  c.dumpCmd,
				Charset:      c.charset,
				MySQLDumpOption: mysqlutil.MySQLDumpOption{
					NoData:       true,
					NoCreateDb:   true,
					NoCreateTb:   false,
					DumpTrigger:  true,
					DumpRoutine:  true,
					DumpEvent:    true,
					NeedUseDb:    false,
					AddDropTable: false,
				},
			},
			OutputfileName: backupFileName,
		}
		if err := dumper.Dump(); err != nil {
			logger.Error("dump failed: ", err.Error())
			return err
		}

		c.databaseInfosCtx = append(
			c.databaseInfosCtx, DatabaseInfoCtx{
				DatabaseInfo: dbInfo,
				SqlFile:      backupFileName,
			},
		)
	}

	return nil
}

// ModifyFile TODO
func (c *BackupTruncateDatabaseComp) ModifyFile() error {
	for _, dbInfoCtx := range c.databaseInfosCtx {
		sqlFilePath := path.Join(c.backupDir, dbInfoCtx.SqlFile)
		cmd := exec.Command("sed", "-i", "-e", `s/CREATE TABLE/CREATE TABLE IF NOT EXISTS/g`, sqlFilePath)
		r, err := cmd.CombinedOutput()
		if err != nil {
			logger.Error("replace %s failed: %s(%s)", sqlFilePath, string(r), err.Error())
		}
	}
	return nil
}

// CleanNewDB TODO
func (c *BackupTruncateDatabaseComp) CleanNewDB() error {
	for _, dbInfoCtx := range c.databaseInfosCtx {
		rows, err := c.dbConn.Query(
			fmt.Sprintf(
				"select table_name from information_schema.views where table_schema='%s'",
				dbInfoCtx.New,
			),
		)
		if err != nil && !c.dbConn.IsNotRowFound(err) {
			logger.Error(err.Error())
			return err
		}
		for _, row := range rows {
			viewName, ok := row["table_name"]
			if !ok {
				err = fmt.Errorf("转换 %s 失败", row["table_name"])
				logger.Error(err.Error())
				return err
			}
			_, err = c.dbConn.Exec(fmt.Sprintf("drop view if exists `%s`.`%s`", dbInfoCtx.New, viewName))
			if err != nil {
				logger.Error(err.Error())
				return err
			}
		}

		rows, err = c.dbConn.Query(
			fmt.Sprintf(
				"select trigger_name from information_schema.triggers where trigger_schema='%s'",
				dbInfoCtx.New,
			),
		)
		if err != nil && !c.dbConn.IsNotRowFound(err) {
			logger.Error(err.Error())
			return err
		}
		for _, row := range rows {
			triggerName, ok := row["trigger_name"]
			if !ok {
				err = fmt.Errorf("转换 %s 失败", row["trigger_name"])
				logger.Error(err.Error())
				return err
			}
			_, err = c.dbConn.Exec(fmt.Sprintf("drop trigger if exists `%s`.`%s`", dbInfoCtx.New, triggerName))
			if err != nil {
				logger.Error(err.Error())
				return err
			}
		}

		rows, err = c.dbConn.Query(
			fmt.Sprintf(
				"select event_name from information_schema.events where event_schema='%s'",
				dbInfoCtx.New,
			),
		)
		if err != nil && !c.dbConn.IsNotRowFound(err) {
			logger.Error(err.Error())
			return err
		}
		for _, row := range rows {
			eventName, ok := row["event_name"]
			if !ok {
				err = fmt.Errorf("转换 %s 失败", row["event_name"])
				logger.Error(err.Error())
				return err
			}
			_, err = c.dbConn.Exec(fmt.Sprintf("drop event if exists `%s`.`%s`", dbInfoCtx.New, eventName))
			if err != nil {
				logger.Error(err.Error())
				return err
			}
		}

		rows, err = c.dbConn.Query(
			fmt.Sprintf(
				"select routine_name, routine_type from information_schema.routines where ROUTINE_SCHEMA='%s'",
				dbInfoCtx.New,
			),
		)
		if err != nil && !c.dbConn.IsNotRowFound(err) {
			logger.Error(err.Error())
			return err
		}
		for _, row := range rows {
			routineName, ok := row["routine_name"]
			if !ok {
				err = fmt.Errorf("转换 %s 失败", row["routine_name"])
				logger.Error(err.Error())
				return err
			}
			routineType, ok := row["routine_type"]
			if !ok {
				err = fmt.Errorf("转换 %s 失败", row["routine_type"])
				logger.Error(err.Error())
				return err
			}
			_, err = c.dbConn.Exec(fmt.Sprintf("drop %s if exists `%s`.`%s`", routineType, dbInfoCtx.New, routineName))
			if err != nil {
				logger.Error(err.Error())
				return err
			}
		}
	}
	return nil
}

// ImportSchema TODO
func (c *BackupTruncateDatabaseComp) ImportSchema() error {
	for _, dbInfoCtx := range c.databaseInfosCtx {
		err := mysqlutil.ExecuteSqlAtLocal{
			IsForce:          false,
			Charset:          c.charset,
			NeedShowWarnings: false,
			Host:             c.Params.Host,
			Port:             c.Params.Port,
			Socket:           c.socket,
			User:             c.GeneralParam.RuntimeAccountParam.AdminUser,
			Password:         c.GeneralParam.RuntimeAccountParam.AdminPwd,
			WorkDir:          c.backupDir,
		}.ExcuteSqlByMySQLClient(dbInfoCtx.SqlFile, []string{dbInfoCtx.New})
		if err != nil {
			logger.Error("导入 %s 到 %s 失败", dbInfoCtx.SqlFile, dbInfoCtx.New)
			return err
		}
	}
	return nil
}
