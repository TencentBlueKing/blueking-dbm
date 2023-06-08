package precheck

import (
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// CheckCharset Check Mysql server charset
func CheckCharset(cnf *parsecnf.CnfShared) error {
	if strings.ToLower(cnf.BackupType) != "logical" {
		return nil
	}
	confCharset := cnf.MysqlCharset
	var superCharset string
	dbh, err := mysqlconn.InitConn(cnf)
	if err != nil {
		return err
	}
	defer dbh.Close()

	version, verErr := mysqlconn.GetMysqlVersion(dbh)
	if verErr != nil {
		return verErr
	}
	if strings.Compare(util.VersionParser(version), "005005003") == -1 { // mysql_version <5.5.3
		superCharset = "utf8"
	} else {
		superCharset = "utf8mb4"
	}
	if confCharset != "binary" && confCharset != superCharset && strings.ToUpper(cnf.DataSchemaGrant) == "ALL" {
		var goodCharset = []string{"latin1", "utf8", "utf8mb4"}

		serverCharset, err := mysqlconn.GetMysqlCharset(cnf, dbh)
		for i := 0; i < len(serverCharset); i++ {
			grep := false
			for j := 0; j < len(goodCharset); j++ {
				if serverCharset[i] == goodCharset[j] {
					grep = true
				}
			}
			if !grep {
				superCharset = "binary"
			}
		}

		if err != nil {
			logger.Log.Warn("get_server_data_charsets query failed,use super charset")
			cnf.MysqlCharset = superCharset
		} else if len(serverCharset) > 1 {
			logger.Log.Warn("found multi character sets on server ")
			cnf.MysqlCharset = superCharset
		} else if len(serverCharset) == 1 {
			cnf.MysqlCharset = serverCharset[0]
			if serverCharset[0] != confCharset {
				logger.Log.Warn("backup config charset:'%s' and server charset '%s' are not the same."+
					" You shoud use %s to backup,please modify config charset to remove this warning",
					confCharset, serverCharset[0], serverCharset[0])
			}
		} else {
			tableNum := common.GetTableNum(cnf.MysqlPort)
			if tableNum > 1000 {
				cnf.MysqlCharset = superCharset
				logger.Log.Warn("too much table, tableNum is %d,check server charset failed,"+
					"use super charset:%s to backup.", tableNum, superCharset)
			}
		}
	}
	logger.Log.Info("use character set:", cnf.MysqlCharset, "  to backup")
	return nil
}
