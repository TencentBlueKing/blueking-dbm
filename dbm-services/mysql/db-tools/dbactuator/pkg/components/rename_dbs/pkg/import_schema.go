package pkg

import (
	"path/filepath"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func ImportDBSchema(ip string, port int, user, password, dbName, sqlFilePath string) error {
	backupCharset, _, err := readBackupConfig(port)
	if err != nil {
		return err
	}

	// ErrFile 由 WorkDir + path.Base(sqlfile) 拼装，须与调用方 "{sqlFilePath}.{db}.err" 对齐
	workDir := filepath.Dir(sqlFilePath)
	sqlFile := filepath.Base(sqlFilePath)

	err = mysqlutil.ExecuteSqlAtLocal{
		IsForce:          true,
		Charset:          backupCharset,
		NeedShowWarnings: false,
		Host:             ip,
		Port:             port,
		User:             user,
		Password:         password,
		WorkDir:          workDir,
	}.ExecuteSqlWithOutReport(
		sqlFile, []string{dbName},
	)

	return err
}
