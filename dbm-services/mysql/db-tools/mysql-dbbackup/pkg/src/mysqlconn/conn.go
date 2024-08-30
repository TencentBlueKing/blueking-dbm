// Package mysqlconn TODO
package mysqlconn

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"

	// mysql driver
	_ "github.com/go-sql-driver/mysql"
)

// InitConn create mysql connection
func InitConn(cfg *config.Public) (*sql.DB, error) {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/?parseTime=%t&loc=Local",
		cfg.MysqlUser, cfg.MysqlPasswd, cfg.MysqlHost, cfg.MysqlPort, true)
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		logger.Log.Error("can't create the connection to Mysql server:", err)
		return nil, err
	}
	if err := db.Ping(); err != nil {
		logger.Log.Error("The connection is dead:", err)
		return nil, err
	}
	return db, nil
}

// InitConnx create mysql connection of sqlx
func InitConnx(cfg *config.Public, ctx context.Context) (*sqlx.Conn, error) {
	if db, err := InitConn(cfg); err != nil {
		return nil, err
	} else {
		dbx := sqlx.NewDb(db, "mysql")
		return dbx.Connx(ctx)
	}
}

// GetSingleGlobalVar get single global variable
func GetSingleGlobalVar(variableName string, dbh *sql.DB) (val string, err error) {
	var varName, varValue string
	sqlStr := fmt.Sprintf("show global variables like '%s'", variableName)
	row := dbh.QueryRow(sqlStr)
	if err = row.Scan(&varName, &varValue); err != nil {
		return "", err
	}
	return varValue, nil
}

// SetGlobalVarAndReturnOrigin set global and return origin value
func SetGlobalVarAndReturnOrigin(variableName, varValue string, dbh *sql.DB) (originVal string, err error) {
	originValue, err := GetSingleGlobalVar(variableName, dbh)
	if err != nil {
		return "", err
	}
	err = SetSingleGlobalVar(variableName, varValue, dbh)
	return originValue, err
}

// SetSingleGlobalVar set global
func SetSingleGlobalVar(variableName, varValue string, dbh *sql.DB) error {
	var sqlStr = ""
	if _, e := cast.ToBoolE(varValue); e == nil {
		sqlStr = fmt.Sprintf("SET GLOBAL %s=%s", variableName, varValue)
	} else if _, e := cast.ToFloat64E(varValue); e == nil { // fix Incorrect argument type to variable
		sqlStr = fmt.Sprintf("SET GLOBAL %s=%s", variableName, varValue)
	} else {
		sqlStr = fmt.Sprintf("SET GLOBAL %s='%s'", variableName, varValue)
	}
	if _, err := dbh.Exec(sqlStr); err != nil {
		return err
	}
	return nil
}

// MysqlSingleColumnQuery Send query to mysql, and query result should contain only one column
func MysqlSingleColumnQuery(queryStr string, dbh *sql.DB) ([]string, error) {
	var resArray []string
	var res string
	rows, err := dbh.Query(queryStr)
	if err != nil {
		logger.Log.Error("can't send query to Mysql server , error :", err)
		return resArray, err
	}
	defer rows.Close()
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

func GetBinlogFormat(dbh *sql.DB) (string, string) {
	binlogFormat, _ := GetSingleGlobalVar("binlog_format", dbh)
	binlogRowImage, _ := GetSingleGlobalVar("binlog_row_image", dbh)
	return binlogFormat, binlogRowImage
}

// GetStorageEngine Get the storage engine from mysql server, to lower
func GetStorageEngine(dbh *sql.DB) (string, error) {
	version, err := MysqlSingleColumnQuery("select @@default_storage_engine", dbh)
	if err != nil {
		logger.Log.Error("can't get default storage_engine, error :", err)
		return "", err
	}

	return strings.ToLower(version[0]), nil
}

// GetDataDir get datadir from mysql server
// if failed, try to get datadir from my.cnf -- todo not implemented
func GetDataDir(dbh *sql.DB, myCnfPath string) (string, error) {
	dataDir, err := MysqlSingleColumnQuery("select @@datadir", dbh)
	if err != nil {
		logger.Log.Error("can't select @@datadir, error :", err)
		return "", err
	}
	return dataDir[0], nil
}

// GetDatabases show databases like
// like == ” means all
func GetDatabases(like string, dbh *sql.DB) ([]string, error) {
	sqlStr := fmt.Sprintf("show databases like %s", mysqlcomm.UnsafeEqual(like, "'"))
	if like == "" {
		sqlStr = "show databases"
	}
	databases, err := MysqlSingleColumnQuery(sqlStr, dbh)
	return databases, err
}

// TestEngineTablesNum 判断指定的标引擎数量，是否超过允许值
// 注意，这里是为了避免 count information_schema.tables 全表，导致打开所有表
// 比如 MyISAM, 10, 返回 true 表示 myisam 表的数量超过 10个，false表示少于 10个
// 已经剔除系统库。 greaterThenNum >= (99999) cst.SkipMyisamTableMaxValue 表示不检查
func TestEngineTablesNum(engine string, greaterThenNum int, dbh *sql.DB) (bool, error) {
	if greaterThenNum >= cst.SkipMyisamTableMaxValue {
		return false, nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	sqlStr := fmt.Sprintf(
		`SELECT table_schema, table_name FROM information_schema.tables `+
			`WHERE table_schema not in (%s) AND engine = %s AND TABLE_TYPE ='BASE TABLE' LIMIT %d`,
		mysqlcomm.UnsafeIn(native.DBSys, "'"), mysqlcomm.UnsafeEqual(engine, "'"), greaterThenNum+1,
	)
	if res, err := dbh.QueryContext(ctx, sqlStr); err != nil {
		return false, errors.WithMessage(err, "test engine tables count")
	} else {
		defer res.Close()
		rowsCount := 0
		for res.Next() {
			rowsCount += 1
		}
		if rowsCount > greaterThenNum {
			return true, nil
		}
		return false, nil
	}
}

// GetMysqlCharset Get charset of mysql server
func GetMysqlCharset(dbh *sql.DB) ([]string, error) {
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
func ShowMysqlSlaveStatus(db *sql.DB) (masterHost string, masterPort int, err error) {
	rows, err := db.Query("show slave status")
	if err != nil {
		logger.Log.Error("failed to query show slave status, err: ", err)
		return masterHost, masterPort, err
	}
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		logger.Log.Error("failed to return column names, err: ", err)
		return masterHost, masterPort, err
	}
	index := make([]interface{}, len(cols))
	data := make([]sql.NullString, len(cols))
	for i := range index {
		index[i] = &data[i]
	}

	for rows.Next() {
		err := rows.Scan(index...)
		if err != nil {
			logger.Log.Error("scan failed: ", err)
			return "", 0, err
		}

		for k, v := range data {
			if strings.ToUpper(cols[k]) == "MASTER_HOST" {
				masterHost = v.String
			}
			if strings.ToUpper(cols[k]) == "MASTER_PORT" {
				masterPort = cast.ToInt(v.String)
			}
		}
	}
	return masterHost, masterPort, nil
}

type ShowMasterStatus struct {
	File            string `db:"File"`
	Position        int64  `db:"Position"`
	ExecutedGtidSet string `db:"Executed_Gtid_Set"`
	BinlogDoDB      string `db:"Binlog_Do_DB"`
	BinlogIgnoreDB  string `db:"Binlog_Ignore_DB"`
}

func ShowMysqlMasterStatus(ftwrl bool, db *sql.DB) (status *ShowMasterStatus, err error) {
	if ftwrl {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if _, err := db.ExecContext(ctx, "flush table with read lock"); err != nil {
			return nil, errors.WithMessage(err, "flush table to get binlog position")
		} else {
			defer func() {
				_, _ = db.ExecContext(ctx, "unlock tables", 5*time.Second)
			}()
		}
	}
	var result = ShowMasterStatus{}
	dbx := sqlx.NewDb(db, "mysql")
	if err := dbx.Get(&result, "show master status"); err != nil {
		return nil, err
	}
	return &result, nil
}

func StartSlaveThreads(ioThread, sqlThread bool, db *sql.DB) error {
	var err error
	if ioThread {
		if _, err = db.Exec("START SLAVE io_thread"); err != nil {
			return err
		}
	}
	if sqlThread {
		if _, err = db.Exec("START SLAVE sql_thread"); err != nil {
			return err
		}
	}
	return nil
}

// IsPrimaryCtl check tc_is_primary
func IsPrimaryCtl(dbw *DbWorker) (bool, error) {
	sqlStr := fmt.Sprintf(`tdbctl get primary`)
	var SERVER_NAME, HOST string
	var PORT, IS_THIS_SERVER int
	err := dbw.Db.QueryRow(sqlStr).Scan(&SERVER_NAME, &HOST, &PORT, &IS_THIS_SERVER)
	if err != nil {
		return false, errors.WithMessage(err, "query 'tdbctl get primary'")
	}
	if IS_THIS_SERVER == 1 {
		return true, nil
	}
	return false, nil
}

//// MysqlUptime mysql uptime in seconds
//func MysqlUptime(db *sqlx.DB) (int, error) {
//	sqlStr := fmt.Sprintf(`show global status like 'uptime'`)
//	var Variable_name string
//	var Value int
//	err := db.QueryRow(sqlStr).Scan(&Variable_name, &Value)
//	if err != nil {
//		return 0, errors.WithMessage(err, sqlStr)
//	}
//	return Value, nil
//}

// IsPrimarySpider spider is primary when tdbctl is primary
// dbw is spider inst
func IsPrimarySpider(spiderInst InsObject) (bool, error) {
	instCtl := GetTdbctlInst(spiderInst)
	dbwCtl, err := instCtl.Conn()
	if err != nil {
		return false, errors.WithMessagef(err, "connect tdbctl port %d", instCtl.Port)
	}
	defer dbwCtl.Close()
	isPrimary, err := IsPrimaryCtl(dbwCtl)
	return isPrimary, err
}

// GetTdbctlInst build tdbctl instance with spider port + 1000
func GetTdbctlInst(spiderInst InsObject) InsObject {
	ctlInst := InsObject{
		Host: spiderInst.Host,
		Port: mysqlcomm.GetTdbctlPortBySpider(spiderInst.Port),
		User: spiderInst.User,
		Pwd:  spiderInst.Pwd,
	}
	return ctlInst
}

// IsSpiderNode TODO
func IsSpiderNode(db *sql.DB) (tspider bool, tdbctl bool, err error) {
	sqlStr := "select version()"
	var serverVersion string
	if err := db.QueryRow(sqlStr).Scan(&serverVersion); err != nil {
		return false, false, err
	} else {
		if strings.Contains(serverVersion, "tspider") {
			return true, false, nil
		}
		if strings.Contains(serverVersion, "tdbctl") {
			return false, true, nil
		}
	}
	return false, false, nil
}

//// HasSpiderEngine TODO
//func HasSpiderEngine(db *sqlx.DB) (bool, error) {
//	sqlStr := "show engines"
//	type tableEngine struct {
//		engine  string
//		support string
//	}
//	var engines []*tableEngine
//	if err := db.QueryRow(sqlStr).Scan(&engines); err != nil {
//		return false, err
//	} else {
//		for _, row := range engines {
//			if row.engine == "SPIDER" && row.support == "YES" {
//				return true, nil
//			}
//		}
//	}
//	return false, nil
//}
