package backupexe

import (
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
)

// ExecuteBackup execute dump backup command
func ExecuteBackup(cnf *config.BackupConfig) error {
	// get mysql version from mysql server, and then set env variables
	db, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()
	versionStr, err := mysqlconn.GetMysqlVersion(db)
	if err != nil {
		return err
	}
	if envErr := SetEnv(cnf.Public.BackupType, versionStr); envErr != nil {
		return envErr
	}
	mysqlVersion, isOfficial := util.VersionParser(versionStr)
	XbcryptBin = GetXbcryptBin(mysqlVersion, isOfficial)

	dumper, err := BuildDumper(cnf)
	if err != nil {
		return err
	}
	if err := dumper.initConfig(versionStr); err != nil {
		return err
	}

	// needn't set timeout for slave
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave || cnf.Public.BackupTimeOut == "" {
		if err = dumper.Execute(false); err != nil {
			return err
		}
	} else {
		if err = dumper.Execute(true); err != nil {
			return err
		}
	}
	return nil
}
