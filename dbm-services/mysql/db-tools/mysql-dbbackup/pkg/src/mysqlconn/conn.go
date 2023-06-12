// Package mysqlconn TODO
package mysqlconn

import (
	"database/sql"
	"fmt"
	"strings"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	// mysql driver
	_ "github.com/go-sql-driver/mysql"
)

// InitConn create mysql connection
func InitConn(connCnf *parsecnf.CnfShared) (*sql.DB, error) {
	dbh := strings.Join([]string{connCnf.MysqlUser, ":", connCnf.MysqlPasswd, "@tcp(",
		connCnf.MysqlHost, ":", connCnf.MysqlPort, ")/"}, "")
	DB, err := sql.Open("mysql", dbh)
	if err != nil {
		logger.Log.Error("can't create the connection to Mysql server %v\n", err)
		return nil, err
	}

	if err := DB.Ping(); err != nil {
		logger.Log.Error("The connection is dead %v\n", err)
		return nil, err
	}
	return DB, nil
}

// MysqlSingleColumnQuery Send query to mysql, and query result should contain only one column
func MysqlSingleColumnQuery(query_str string, dbh *sql.DB) ([]string, error) {
	var resArray []string
	var res string
	rows, err := dbh.Query(query_str)
	if err != nil {
		logger.Log.Error("can't send query to Mysql server , error :", err)
		return resArray, err
	}
	for rows.Next() {
		err := rows.Scan(&res)
		if err != nil {
			logger.Log.Error("can't scan query result, error :", err)
			return resArray, err
		}
		resArray = append(resArray, res)
	}
	return resArray, nil
}

// GetMysqlVersion Get the server version of mysql
func GetMysqlVersion(dbh *sql.DB) (string, error) {
	version, err := MysqlSingleColumnQuery("select version()", dbh)
	if err != nil {
		logger.Log.Error("can't select mysql version , error :", err)
		return "", err
	}
	return version[0], nil
}

// GetStorageEngine Get the storage engine from mysql server
func GetStorageEngine(dbh *sql.DB) (string, error) {
	version, err := MysqlSingleColumnQuery("select @@default_storage_engine", dbh)
	if err != nil {
		logger.Log.Error("can't get default storage_engine, error :", err)
		return "", err
	}
	return version[0], nil
}

// GetMysqlCharset Get charset of mysql server
func GetMysqlCharset(connCnf *parsecnf.CnfShared, dbh *sql.DB) ([]string, error) {
	var mysqlCharsets []string
	serverCharset, err := MysqlSingleColumnQuery("select @@character_set_server", dbh)
	if err != nil {
		logger.Log.Error("can't select mysql server charset , error :", err)
		return mysqlCharsets, err
	}
	mysqlCharsets = append(mysqlCharsets, serverCharset...)

	// column charset
	columnCharset, err := MysqlSingleColumnQuery(
		"select distinct CHARACTER_SET_NAME from INFORMATION_SCHEMA.COLUMNS"+
			" where CHARACTER_SET_NAME is not null and"+
			" table_schema not in ('performance_schema','information_schema','mysql','test','db_infobase')", dbh)
	if err != nil {
		logger.Log.Error("can't select mysql column charset , error :", err)
		return mysqlCharsets, err
	}
	mysqlCharsets = append(mysqlCharsets, columnCharset...)

	// table charset
	tableCharset, err := MysqlSingleColumnQuery(
		"select distinct TABLE_COLLATION from information_schema.tables where"+
			" TABLE_COLLATION is not null and"+
			" table_schema not in ('performance_schema','information_schema','mysql','test','db_infobase')", dbh)
	if err != nil {
		logger.Log.Error("can't select mysql table charset , error :", err)
		return mysqlCharsets, err
	}
	mysqlCharsets = append(mysqlCharsets, tableCharset...)

	// database charset
	databaseCharset, err := MysqlSingleColumnQuery(
		"select distinct DEFAULT_CHARACTER_SET_NAME from information_schema.SCHEMATA"+
			" where DEFAULT_CHARACTER_SET_NAME is not null and"+
			" schema_name not in ('performance_schema','information_schema','mysql','test','db_infobase')", dbh)
	if err != nil {
		logger.Log.Error("can't select mysql database charset , error :", err)
		return mysqlCharsets, err
	}
	mysqlCharsets = append(mysqlCharsets, databaseCharset...)
	return mysqlCharsets, nil
}

// ShowMysqlSlaveStatus Show the slave status of mysql server
// if server is master, return local ip:port
func ShowMysqlSlaveStatus(connCnf *parsecnf.CnfShared) (masterHost string, masterPort int, err error) {
	dbh, err := InitConn(connCnf)
	if err != nil {
		return masterHost, masterPort, err
	}
	defer dbh.Close()
	rows, err := dbh.Query("show slave status")
	if err != nil {
		logger.Log.Error("failed to query show slave status, err: ", err)
		return masterHost, masterPort, err
	}
	cols, err := rows.Columns()
	if err != nil {
		logger.Log.Error("failed to return column names, err: ", err)
		return masterHost, masterPort, err
	}
	index := make([]interface{}, len(cols))
	data := make([]string, len(cols))
	for i := range index {
		index[i] = &data[i]
	}

	for rows.Next() {
		rows.Scan(index...)

		for k, v := range data {
			if strings.ToUpper(cols[k]) == "MASTER_HOST" {
				masterHost = v
			}
			if strings.ToUpper(cols[k]) == "MASTER_PORT" {
				masterPort = cast.ToInt(v)
			}
		}
	}
	if masterHost == "" && strings.ToLower(connCnf.MysqlRole) == cst.RoleMaster {
		masterHost = connCnf.MysqlHost
	}
	if masterPort == 0 && strings.ToLower(connCnf.MysqlRole) == cst.RoleMaster {
		masterPort = cast.ToInt(connCnf.MysqlPort)
	}

	return masterHost, masterPort, nil
}

// IsPrimaryCtl check tc_is_primary
func IsPrimaryCtl(dbw *DbWorker) (bool, error) {
	sqlStr := fmt.Sprintf(`select @@tc_is_primary`)
	var val int
	err := dbw.Db.QueryRow(sqlStr).Scan(&val)
	if err != nil {
		return false, errors.WithMessage(err, "query tc_is_primary from tdbctl")
	}
	if val == 1 {
		return true, nil
	}
	return false, nil
}

// MysqlUptime mysql uptime in seconds
func MysqlUptime(db *sqlx.DB) (int, error) {
	sqlStr := fmt.Sprintf(`show global status like 'uptime'`)
	var Variable_name string
	var Value int
	err := db.QueryRow(sqlStr).Scan(&Variable_name, &Value)
	if err != nil {
		return 0, errors.WithMessage(err, sqlStr)
	}
	return Value, nil
}

// IsPrimarySpider spider is primary when tdbctl is primary
// dbw is spider inst
func IsPrimarySpider(instSpider InsObject) (bool, error) {
	instCtl := InsObject{
		Host: instSpider.Host,
		Port: instSpider.Port + 1000, // tdbctl port = spider_port + 1000
		User: instSpider.User,
		Pwd:  instSpider.Pwd,
	}
	dbwCtl, err := instCtl.Conn()
	if err != nil {
		return false, errors.WithMessagef(err, "connect tdbctl port %d", instCtl.Port)
	}
	defer dbwCtl.Close()
	isPrimary, err := IsPrimaryCtl(dbwCtl)
	return isPrimary, err
}

// IsSpiderNode TODO
func IsSpiderNode(db *sqlx.DB) (bool, error) {
	sqlStr := "select version()"
	var serverVersion string
	if err := db.QueryRow(sqlStr).Scan(&serverVersion); err != nil {
		return false, err
	} else {
		if strings.Contains(serverVersion, "tspider") {
			return true, nil
		}
	}
	return false, nil
}

// HasSpiderEngine TODO
func HasSpiderEngine(db *sqlx.DB) (bool, error) {
	sqlStr := "show engines"
	type tableEngine struct {
		engine  string
		support string
	}
	var engines []*tableEngine
	if err := db.QueryRow(sqlStr).Scan(&engines); err != nil {
		return false, err
	} else {
		for _, row := range engines {
			if row.engine == "SPIDER" && row.support == "YES" {
				return true, nil
			}
		}
	}
	return false, nil
}
