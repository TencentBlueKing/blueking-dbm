package pkg

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"

	"gopkg.in/ini.v1"
)

func DumpDBSchema(ip string, port int, user, password, dbName string, uid string, isCtl bool) (string, error) {
	mysqldumpBasePath := cst.MysqldInstallPath
	if isCtl {
		mysqldumpBasePath = cst.TdbctlInstallPath
	}

	backupCharset := "utf8" // mysql 表结构编码都是用 utf8，可能跟表数据编码不一样
	_, backupDir, err := readBackupConfig(port)
	if err != nil {
		return "", err
	}

	outputFileName := fmt.Sprintf("%s_%d_%s_%s.sql", ip, port, dbName, uid)
	outputFilePath := filepath.Join(backupDir, outputFileName)

	err = os.Remove(outputFilePath)
	if err != nil && !os.IsNotExist(err) {
		return "", err
	}

	var dumper mysqlutil.Dumper
	dumper = &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			MySQLDumpOption: mysqlutil.MySQLDumpOption{
				DumpSchema:   true,
				NoCreateDb:   true,
				NoCreateTb:   false,
				DumpTrigger:  true,
				DumpRoutine:  true,
				DumpEvent:    true,
				AddDropTable: false,
			},
			DumpDir:      backupDir,
			DbBackupUser: user,
			DbBackupPwd:  password,
			Ip:           ip,
			Port:         port,
			Charset:      backupCharset,
			DumpCmdFile:  filepath.Join(mysqldumpBasePath, "bin", "mysqldump"),
			DbNames:      []string{dbName},
		},
		OutputfileName: outputFileName,
	}

	err = dumper.Dump()
	if err != nil {
		return "", err
	}

	return outputFilePath, nil
}

func readBackupConfig(port int) (string, string, error) {
	backupConfigPath := filepath.Join(
		cst.DbbackupGoInstallPath,
		fmt.Sprintf("dbbackup.%d.ini", port),
	)

	backupConfigContent, err := ini.Load(backupConfigPath)
	if err != nil {
		return "", "", err
	}

	var backupConfig config.BackupConfig
	err = backupConfigContent.MapTo(&backupConfig)
	if err != nil {

		return "", "", err
	}

	return backupConfig.Public.MysqlCharset, backupConfig.Public.BackupDir, nil
}
