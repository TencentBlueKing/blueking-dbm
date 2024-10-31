package pkg

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func ImportDBSchema(ip string, port int, user, password, dbName, sqlFilePath string) error {
	backupCharset, _, err := readBackupConfig(port)
	if err != nil {
		return err
	}

	err = mysqlutil.ExecuteSqlAtLocal{
		IsForce:          true,
		Charset:          backupCharset,
		NeedShowWarnings: false,
		Host:             ip,
		Port:             port,
		User:             user,
		Password:         password,
	}.ExecuteSqlWithOutReport(
		sqlFilePath, []string{dbName},
	)

	return err
}
