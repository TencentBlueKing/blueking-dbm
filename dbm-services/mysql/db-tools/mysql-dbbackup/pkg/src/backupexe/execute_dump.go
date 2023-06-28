package backupexe

import (
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
)

// ExecuteBackup execute dump backup command
func ExecuteBackup(cnf *config.BackupConfig) error {
	if envErr := SetEnv(); envErr != nil {
		return envErr
	}

	dumper, err := BuildDumper(cnf)
	if err != nil {
		return err
	}

	if err := dumper.initConfig(); err != nil {
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
