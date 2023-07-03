package native

import (
	"context"
	"database/sql"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// DbWorker TODO
type DbWorker struct {
	Dsn string
	Db  *sql.DB
}

// NewDbWorker TODO
func NewDbWorker(dsn string) (*DbWorker, error) {
	var err error
	dbw := &DbWorker{
		Dsn: dsn,
	}
	dbw.Db, err = sql.Open("mysql", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	// check connect with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := dbw.Db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("ping context failed, err:%w", err)
	}
	if err := dbw.Db.Ping(); err != nil {
		return nil, err
	}
	return dbw, nil
}

// NewDbWorkerNoPing mysql-proxy supports very few queries, which do not include PINGs
// In this case, we do not ping after a connection is built,
// and let the function caller to decide if the connection is healthy
func NewDbWorkerNoPing(host, user, password string) (*DbWorker, error) {
	var err error
	dbw := &DbWorker{
		Dsn: fmt.Sprintf("%s:%s@tcp(%s)/?timeout=5s&multiStatements=true", user, password, host),
	}
	dbw.Db, err = sql.Open("mysql", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	return dbw, nil
}

// Stop close connection
func (h *DbWorker) Stop() {
	if h.Db != nil {
		if err := h.Db.Close(); err != nil {
			logger.Warn("close db handler failed, err:%s", err.Error())
		}
	}
}

// Exec 执行任意sql，返回影响行数
func (h *DbWorker) Exec(query string, args ...interface{}) (int64, error) {
	ret, err := h.Db.Exec(query, args...)
	if err != nil {
		return 0, err
	}
	return ret.RowsAffected()
}

// ExecWithTimeout 执行任意sql，返回影响行数
// 超时
func (h *DbWorker) ExecWithTimeout(dura time.Duration, query string, args ...interface{}) (int64, error) {
	ctx := context.Background()
	ctx, cancel := context.WithTimeout(ctx, dura)
	defer cancel()
	ret, err := h.Db.ExecContext(ctx, query, args...)
	if err != nil {
		return 0, err
	}
	return ret.RowsAffected()
}

// ExecMore 执行一堆sql
func (h *DbWorker) ExecMore(sqls []string) (rowsAffectedCount int64, err error) {
	var c int64
	for _, args := range sqls {
		ret, err := h.Db.Exec(args)
		if err != nil {
			return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", args, err)
		}
		if c, err = ret.RowsAffected(); err != nil {
			return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", args, err)
		}
		rowsAffectedCount += c
	}
	return
}

// Queryx execute query use sqlx
func (h *DbWorker) Queryx(data interface{}, query string, args ...interface{}) error {
	logger.Info("Queryx:%s, args:%v", query, args)
	db := sqlx.NewDb(h.Db, "mysql")
	udb := db.Unsafe()
	if err := udb.Select(data, query, args...); err != nil {
		return fmt.Errorf("sqlx select failed, err:%w", err)
	}
	return nil
}

// Queryxs execute query use sqlx return Single column
func (h *DbWorker) Queryxs(data interface{}, query string) error {
	logger.Info("Queryxs:%s", query)
	db := sqlx.NewDb(h.Db, "mysql")
	udb := db.Unsafe()
	if err := udb.Get(data, query); err != nil {
		return err
	}
	return nil
}

// QueryOneColumn query one column rows to slice
func (h *DbWorker) QueryOneColumn(columnName string, query string) ([]string, error) {
	logger.Info("QueryOneColumn: %s, params:%v", query)
	if ret, err := h.Query(query); err != nil {
		return nil, err
	} else {
		colValues := []string{}
		if len(ret) > 0 {
			row0 := ret[0]
			if _, ok := row0[columnName]; !ok {
				return nil, errors.Errorf("column name %s not found", columnName)
			}
		}
		for _, row := range ret {
			colValues = append(colValues, cast.ToString(row[columnName]))
		}
		return colValues, nil
	}
}

// Query conv rows list to map
// 查询结果为空时，返回 not row found
func (h *DbWorker) Query(query string) ([]map[string]interface{}, error) {
	return h.QueryWithArgs(query)
}

// QueryWithArgs conv rows list to map
// 查询结果为空时，返回 not row found
func (h *DbWorker) QueryWithArgs(query string, args ...interface{}) ([]map[string]interface{}, error) {
	logger.Info("Query: %s, params:%v", query, args)
	var rows *sql.Rows
	var err error
	if len(args) <= 0 {
		rows, err = h.Db.Query(query)
	} else {
		rows, err = h.Db.Query(query, args)
	}
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := rows.Close(); err != nil {
			logger.Warn("close row failed, err:%s", err.Error())
		}
	}()
	// get all columns name
	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	values := make([]sql.RawBytes, len(columns))
	scanArgs := make([]interface{}, len(values))
	for i := range values {
		scanArgs[i] = &values[i]
	}
	result := make([]map[string]interface{}, 0)
	for rows.Next() {
		row := make(map[string]interface{})
		err = rows.Scan(scanArgs...)
		if err != nil {
			return nil, err
		}
		var value string
		for i, col := range values {
			if col == nil {
				value = "NULL"
			} else {
				value = string(col)
			}
			row[columns[i]] = value
		}
		result = append(result, row)
	}
	if err = rows.Err(); err != nil {
		return nil, err
	}
	if len(result) == 0 {
		return nil, fmt.Errorf(NotRowFound)
	}
	return result, nil
}

// QueryGlobalVariables TODO
func (h *DbWorker) QueryGlobalVariables() (map[string]string, error) {
	result := make(map[string]string)
	rows, err := h.Db.Query("SHOW GLOBAL VARIABLES")
	if err != nil {
		return result, err
	}
	defer rows.Close()
	for rows.Next() {
		var key, val string
		err := rows.Scan(&key, &val)
		if err != nil {
			continue
		}
		result[key] = val
	}
	return result, nil
}

// ExecuteAdminSql for example, flush binary logs; set global binlog_format=row;
func (h *DbWorker) ExecuteAdminSql(admSql string) error {
	_, err := h.Db.Exec(admSql)
	if err != nil {
		return err
	}
	return nil
}

// IsNotRowFound TODO
func (h *DbWorker) IsNotRowFound(err error) bool {
	return err.Error() == NotRowFound
}

// ShowSlaveStatus 返回结构化的查询show slave status
func (h *DbWorker) ShowSlaveStatus() (resp ShowSlaveStatusResp, err error) {
	err = h.Queryxs(&resp, "show slave status;")
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return ShowSlaveStatusResp{}, nil
		}
	}
	return
}

// TotalDelayBinlogSize 获取Slave 延迟的总binlog size,total 单位byte
func (h *DbWorker) TotalDelayBinlogSize() (total int, err error) {
	maxbinlogsize_str, err := h.GetSingleGlobalVar("max_binlog_size")
	if err != nil {
		return -1, err
	}
	maxbinlogsize, err := strconv.Atoi(maxbinlogsize_str)
	if err != nil {
		return -1, err
	}
	var ss ShowSlaveStatusResp
	err = h.Queryxs(&ss, "show slave status;")
	if err != nil {
		return
	}
	masterBinIdx, err := getIndexFromBinlogFile(ss.MasterLogFile)
	if err != nil {
		return -1, err
	}
	relayBinIdx, err := getIndexFromBinlogFile(ss.RelayMasterLogFile)
	if err != nil {
		return -1, err
	}
	return (masterBinIdx-relayBinIdx)*maxbinlogsize + (ss.ExecMasterLogPos - ss.ReadMasterLogPos), nil
}

// getIndexFromBinlogFile TODO
// eg：fileName binlog20000.224712
// output: 224712
func getIndexFromBinlogFile(fileName string) (seq int, err error) {
	ss := strings.Split(fileName, ".")
	if len(ss) <= 0 {
		return -1, fmt.Errorf("empty after split . %s", fileName)
	}
	return strconv.Atoi(ss[1])
}

// ShowMasterStatus 返回结构化的查询show slave status
func (h *DbWorker) ShowMasterStatus() (resp MasterStatusResp, err error) {
	err = h.Queryxs(&resp, "show master status;")
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return MasterStatusResp{}, nil
		}
	}
	return
}

// ShowSlaveHosts 返回结构化的查询show slave hosts
func (h *DbWorker) ShowSlaveHosts() (resp []SlaveHostResp, err error) {
	err = h.Queryx(&resp, "show slave hosts;")
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return []SlaveHostResp{}, nil
		}
	}
	return
}

// SelectVersion 查询version
func (h *DbWorker) SelectVersion() (version string, err error) {
	err = h.Queryxs(&version, "select version() as version;")
	return
}

// SelectNow 获取实例的当前时间。不是获取机器的，因为可能存在时区不一样
func (h *DbWorker) SelectNow() (nowTime string, err error) {
	err = h.Queryxs(&nowTime, "select now() as not_time;")
	return
}

// GetBinlogDir 获取实例的 binlog_dir 和 binlog file prefix
// 从 mysqld 在线变量里获取失败，则从 my.cnf 里获取
func (h *DbWorker) GetBinlogDir(port int) (string, string, error) {
	cnfFile := util.CnfFile{}
	if logBinBasename, err := h.GetSingleGlobalVar("log_bin_basename"); err == nil {
		if logBinBasename != "" {
			binlogDir, namePrefix, err2 := cnfFile.ParseLogBinBasename(logBinBasename)
			if err2 == nil {
				return binlogDir, namePrefix, nil
			}
		}
	} else {
		logger.Warn("failed to get global variables log_bin_basename: %s", err.Error())
	}
	cnfFile.FileName = util.GetMyCnfFileName(port)
	if err := cnfFile.Load(); err != nil {
		return "", "", err
	} else {
		return cnfFile.GetBinLogDir()
	}
}

// ShowApplicationProcesslist 查询是否存在非系统用户的processlist
// 已经忽略了dbsysUsers
func (h *DbWorker) ShowApplicationProcesslist(sysUsers []string) (processLists []ShowProcesslistResp, err error) {
	users := append(sysUsers, dbSysUsers...)
	query, args, err := sqlx.In("select * from information_schema.processlist  where  User not in (?)", users)
	if err != nil {
		return nil, err
	}
	err = h.Queryx(&processLists, query, args...)
	return processLists, err
}

// SelectProcesslist TODO
func (h *DbWorker) SelectProcesslist(usersIn []string) (processList []SelectProcessListResp, err error) {
	query, args, err := sqlx.In("select * from information_schema.processlist where User in (?);", usersIn)
	if err != nil {
		return nil, err
	}
	if err := h.Queryx(&processList, query, args...); err != nil {
		return nil, err
	}
	return processList, nil
}

// SelectLongRunningProcesslist 查询Time > ? And state != 'Sleep'的processLists
func (h *DbWorker) SelectLongRunningProcesslist(time int) ([]SelectProcessListResp, error) {
	var userExcluded []string = []string{"'repl'", "'system user'", "'event_scheduler'"}
	var processList []SelectProcessListResp
	query, args, err := sqlx.In(
		"select * from information_schema.processlist where  Command <> 'Sleep' and Time > ? and User Not In (?)",
		time, userExcluded,
	)
	if err != nil {
		return nil, err
	}
	if err := h.Queryx(&processList, query, args...); err != nil {
		return nil, err
	}
	return processList, nil
}

// ShowOpenTables TODO
/*
ShowOpenTables
   show open tables;
   +---------------+---------------------------------------+--------+-------------+
   | Database      | Table                                 | In_use | Name_locked |
   +---------------+---------------------------------------+--------+-------------+
   | dbPrdsDevBak  | tb_app_max_bak                        |      0 |           0 |
*/
// 查询实例上被打开的表
// 忽略系统库
func (h *DbWorker) ShowOpenTables(sleepTime time.Duration) (openTables []ShowOpenTablesResp, err error) {
	if _, err = h.ExecWithTimeout(time.Second*5, "flush tables;"); err != nil {
		return nil, err
	}
	// wait a moment before check opened tables
	time.Sleep(sleepTime)
	db := sqlx.NewDb(h.Db, "mysql")
	udb := db.Unsafe()
	// show open tables WHERE `Database` not in
	inStr, _ := mysqlutil.UnsafeBuilderStringIn(DBSys, "'")
	sqlStr := fmt.Sprintf("show open tables where `Database` not in (%s)", inStr)
	if err := udb.Select(&openTables, sqlStr); err != nil {
		return nil, err
	}
	return openTables, nil
}

// GetSqlxDb TODO
func (h *DbWorker) GetSqlxDb() *sqlx.DB {
	return sqlx.NewDb(h.Db, "mysql")
}

// ShowServerCharset 查询version
func (h *DbWorker) ShowServerCharset() (charset string, err error) {
	return h.GetSingleGlobalVar("character_set_server")
}

// ShowSocket  获取当前实例的socket Value
//
//	@receiver h
//	@return socket
//	@return err
func (h *DbWorker) ShowSocket() (socket string, err error) {
	return h.GetSingleGlobalVar("socket")
}

// GetSingleGlobalVar TODO
func (h *DbWorker) GetSingleGlobalVar(varName string) (val string, err error) {
	var item MySQLGlobalVariableItem
	sqlstr := fmt.Sprintf("show global variables like '%s'", varName)
	if err = h.Queryxs(&item, sqlstr); err != nil {
		return "", err
	}
	return item.Value, nil
}

// SetSingleGlobalVarAndReturnOrigin set global and return origin value
func (h *DbWorker) SetSingleGlobalVarAndReturnOrigin(varName, varValue string) (val string, err error) {
	originValue, err := h.GetSingleGlobalVar(varName)
	if err != nil {
		return "", err
	}
	sqlstr := fmt.Sprintf("SET GLOBAL %s='%s'", varName, varValue)
	if err = h.ExecuteAdminSql(sqlstr); err != nil {
		return "", err
	}
	return originValue, nil
}

// SetSingleGlobalVar set global
func (h *DbWorker) SetSingleGlobalVar(varName, varValue string) error {
	sqlstr := fmt.Sprintf("SET GLOBAL %s='%s'", varName, varValue)
	if err := h.ExecuteAdminSql(sqlstr); err != nil {
		return err
	}
	return nil
}

// ShowDatabases 执行show database 获取所有的dbName
//
//	@receiver h
//	@return databases
//	@return err
func (h *DbWorker) ShowDatabases() (databases []string, err error) {
	err = h.Queryx(&databases, "show databases")
	return
}

// SelectDatabases 查询 databases
func (h *DbWorker) SelectDatabases(dbNameLike string) (databases []string, err error) {
	inStr, _ := mysqlutil.UnsafeBuilderStringIn(DBSys, "'")
	dbsSql := fmt.Sprintf("select SCHEMA_NAME from information_schema.SCHEMATA where SCHEMA_NAME not in (%s) ", inStr)
	if dbNameLike != "" {
		dbsSql += fmt.Sprintf(" and SCHEMA_NAME like '%s'", dbNameLike)
	}
	if databases, err = h.QueryOneColumn("SCHEMA_NAME", dbsSql); err != nil {
		if h.IsNotRowFound(err) {
			return nil, nil
		} else {
			return nil, err
		}
	}
	return databases, nil
}

// TableColumnDef TODO
type TableColumnDef struct {
	ColName string
	ColPos  string // int?
	ColType string
}

// TableSchema TODO
type TableSchema struct {
	DBName     string
	TableName  string
	DBTableStr string // dbX.tableY
	SchemaStr  string

	PrimaryKey []string
	UniqueKey  []string
	ColumnMap  map[string]TableColumnDef
}

// SelectTables 查询 tables
// db=[db1,db2] tb=[tbl1,tbl2,tbl3]
// 从上面松散的信息中，获取真实的db.table，可能最终得到 db1.tbl1 db2.tbl2 db2.tbl3
func (h *DbWorker) SelectTables(dbNames, tbNames []string) (map[string]TableSchema, error) {
	queryStr :=
		"SELECT TABLE_SCHEMA,TABLE_NAME,TABLE_TYPE,TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_TYPE='BASE TABLE' "
	if len(dbNames) > 0 {
		if dbs, err := mysqlutil.UnsafeBuilderStringIn(dbNames, "'"); err != nil {
			return nil, err
		} else {
			queryStr += fmt.Sprintf(" AND TABLE_SCHEMA IN (%s)", dbs)
		}
	}
	if len(tbNames) > 0 {
		if tbs, err := mysqlutil.UnsafeBuilderStringIn(tbNames, "'"); err != nil {
			return nil, err
		} else {
			queryStr += fmt.Sprintf(" AND TABLE_NAME IN (%s)", tbs)
		}
	}

	result, err := h.Query(queryStr)
	if err != nil {
		return nil, err
	}
	tblSchemas := make(map[string]TableSchema)

	if len(result) > 0 {
		for _, row := range result {
			dbtbl := fmt.Sprintf(`%s.%s`, row["TABLE_SCHEMA"].(string), row["TABLE_NAME"].(string))
			tblSchemas[dbtbl] = TableSchema{
				DBName:     row["TABLE_SCHEMA"].(string),
				TableName:  row["TABLE_NAME"].(string),
				DBTableStr: dbtbl,
			}
		}

		return tblSchemas, nil
	}
	return nil, errors.New("table not found")
}

// ShowTables  获取指定库名下的所有表名
//
//	@receiver h
//	@receiver db
//	@return tables
//	@return err
func (h *DbWorker) ShowTables(db string) (tables []string, err error) {
	results, err := h.Query(fmt.Sprintf("show full tables from `%s`;", db))
	if err != nil {
		return
	}
	for _, row := range results {
		tableType, ok := row[TableType].(string)
		if !ok {
			return nil, fmt.Errorf("隐式转换失败%s", row[tableType])
		}
		// 仅仅获取表，忽略视图等
		if tableType != "BASE TABLE" {
			continue
		}
		dbCol := TablesInPrefix + db
		dbData, ok := row[dbCol].(string)
		if !ok {
			return nil, errors.New("GetTables:change result(dbData) to string fail")
		}
		tables = append(tables, dbData)
	}
	return tables, nil
}

// ShowEngines 返回执行 show engines;
//
//	@receiver h
//	@return engines
//	@return err
func (h *DbWorker) ShowEngines() (engines []ShowEnginesResp, err error) {
	err = h.Queryx(&engines, "show engines")
	return
}

// IsSupportTokudb 判断实例是否开启了Tokudb引擎
//
//	@receiver h
//	@return support
//	@return err
func (h *DbWorker) IsSupportTokudb() (support bool, err error) {
	engines, err := h.ShowEngines()
	if err != nil {
		return false, err
	}
	for _, engine := range engines {
		if engine.Engine == strings.ToUpper("Tokudb") && engine.Support != "NO" {
			return true, nil
		}
	}
	return false, nil
}

// IsEmptyInstance  判断实例是否是空实例 ps:过滤系统后
//
//	@receiver h
//	@return bool
func (h *DbWorker) IsEmptyInstance() bool {
	dbs, err := h.ShowDatabases()
	if err != nil {
		return false
	}
	return IsEmptyDB(dbs)
}

// GetUserHosts  获取MySQL 实例上的user,host
//
//	@receiver h
//	@return users
//	@return err
func (h *DbWorker) GetUserHosts() (users []UserHosts, err error) {
	err = h.Queryx(&users, "select user,host from mysql.user")
	return
}

// ShowPrivForUser 获取create user &&  grant user 语句
//
//	@receiver h
//	@receiver created  5.7 以上的版本需要show create user
//	@receiver userhost
//	@return grants
//	@return err
func (h *DbWorker) ShowPrivForUser(created bool, userhost string) (grants []string, err error) {
	if created {
		var createUserSQL string
		if err = h.Queryxs(&createUserSQL, fmt.Sprintf("show create user %s", userhost)); err != nil {
			return
		}
		grants = append(grants, createUserSQL)
	}
	var grantsSQL []string
	if err = h.Queryx(&grantsSQL, fmt.Sprintf("show grants for %s", userhost)); err != nil {
		return
	}
	grants = append(grants, grantsSQL...)
	return
}

// CheckSlaveReplStatus TODO
// 检查从库的同步状态是否Ok
func (h *DbWorker) CheckSlaveReplStatus(fn func() (resp ShowSlaveStatusResp, err error)) (err error) {
	return util.Retry(
		util.RetryConfig{Times: 10, DelayTime: 1},
		func() error {
			ss, err := fn()
			if err != nil {
				return err
			}
			if !ss.ReplSyncIsOk() {
				return fmt.Errorf("主从同步状态异常,IoThread:%s,SqlThread:%s", ss.SlaveIORunning, ss.SlaveSQLRunning)
			}
			if !ss.SecondsBehindMaster.Valid {
				return fmt.Errorf("SecondsBehindMaster Val Is Null")
			}
			if ss.SecondsBehindMaster.Int64 > 5 {
				return fmt.Errorf("SecondsBehindMaster Great Than 10 Sec")
			}
			return nil
		},
	)
}

// MySQLVarsCompare MySQL 实例参数差异对比
// referInsConn 参照实例的是连接
// h 对比的实例
func (h *DbWorker) MySQLVarsCompare(referInsConn *DbWorker, checkVars []string) (err error) {
	referVars, err := referInsConn.QueryGlobalVariables()
	if err != nil {
		return err
	}
	compareVars, err := h.QueryGlobalVariables()
	if err != nil {
		return err
	}
	return compareDbVariables(referVars, compareVars, checkVars)
}

func compareDbVariables(referVars, compareVars map[string]string, checkVars []string) (err error) {
	var errMsg []string
	for _, varName := range checkVars {
		referV, r_ok := referVars[varName]
		compareV, c_ok := compareVars[varName]
		// 如果存在某个key,在某个节点查询不就输出waning
		if !(r_ok && c_ok) {
			continue
		}
		if strings.Compare(referV, compareV) != 0 {
			errMsg = append(errMsg, fmt.Sprintf("存在差异： 变量名:%s Master:%s,Slave:%s", varName, referV, compareV))
		}
	}
	if len(errMsg) > 0 {
		return fmt.Errorf(strings.Join(errMsg, "\n"))
	}
	return nil
}

// ResetSlave TODO
// reset slave
func (h *DbWorker) ResetSlave() (err error) {
	_, err = h.Exec("reset slave /*!50516 all */;")
	return
}

// StopSlave TODO
// reset slave
func (h *DbWorker) StopSlave() (err error) {
	_, err = h.ExecWithTimeout(time.Second*30, "stop slave;")
	return
}

// Grants TODO
type Grants struct {
	User  string
	Host  string
	Privs []string
}

// TableType TODO
const TableType = "Table_type"

// TablesInPrefix TODO
const TablesInPrefix = "Tables_in_"

// GetTableUniqueKeys 本地获取表的 unique key
func (h *DbWorker) GetTableUniqueKeys(dbtable string) (uniqKeys map[string][]string, err1 error) {
	sqlKeys := fmt.Sprintf(`SHOW INDEX FROM %s WHERE Key_name='PRIMARY'`, dbtable)
	result, err := h.Query(sqlKeys)
	uniqKeys = make(map[string][]string)
	if err != nil && !strings.Contains(err.Error(), "not row found") {
		return nil, fmt.Errorf("GetTableUniqueKeysRemote fail,error:%s", err.Error())
	} else if len(result) > 0 {
		var pKey []string
		for _, row := range result {
			pKey = append(pKey, row["Column_name"].(string))
		}
		uniqKeys["PRIMARY"] = pKey
	} else { // no primary key defined, check unique key
		sqlKeys = fmt.Sprintf(`SHOW INDEX FROM %s WHERE Non_unique=0`, dbtable)
		result, err := h.Query(sqlKeys)
		if err != nil {
			return nil, fmt.Errorf("GetTableUniqueKeysRemote fail,error:%s", err.Error())
		} else if len(result) == 0 {
			return nil, fmt.Errorf(`No PRIMARY or UNIQUE key found on table %s `, dbtable)
		} else {
			for _, row := range result {
				Key_name := row["Key_name"].(string)
				if _, ok := uniqKeys[Key_name]; ok {
					uniqKeys[Key_name] = append(uniqKeys[Key_name], row["Column_name"].(string))
				} else {
					var uKey []string
					uKey = append(uKey, row["Column_name"].(string))
					uniqKeys[Key_name] = uKey
				}
			}
		}
	}
	return uniqKeys, nil
}

// GetTableUniqueKeyBest 从更多个 unique key 返回最优的唯一键
func GetTableUniqueKeyBest(uniqKeys map[string][]string) []string {
	if _, ok := uniqKeys["PRIMARY"]; ok {
		return uniqKeys["PRIMARY"]
	} else {
		// 或者列最少的unique key // 获取 not null unique key
		var uniqKeyBest []string
		var colCnt int = 9999
		for _, v := range uniqKeys {
			if len(v) <= colCnt {
				colCnt = len(v)
				uniqKeyBest = v
			}
		}
		return uniqKeyBest
	}
}

// GetTableColumns get table column info
func GetTableColumns(dbworker *DbWorker, dbName, tblName string) (map[string]TableSchema, error) {
	// tblSchemas = {"dbX.tableY": {"a": {"name":"a", "pos":"1", "type":"int"}}}
	/*
		queryStr := fmt.Sprintf("SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,DATA_TYPE,COLUMN_TYPE " +
			"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA =%s AND TABLE_NAME = %s" +
			" ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION asc", dbName, tblName)
	*/
	queryStr := fmt.Sprintf(
		"SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,DATA_TYPE,COLUMN_TYPE " +
			"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA =? AND TABLE_NAME = ? " +
			"ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION asc",
	)
	result, err := dbworker.QueryWithArgs(queryStr, dbName, tblName)
	// todo 这里的err没有正确捕捉到，比如sql执行错误
	if err != nil {
		return nil, err
	}

	dbtbl := fmt.Sprintf(`%s.%s`, dbName, tblName)
	tblSchemas := make(map[string]TableSchema)
	if len(result) > 0 {
		tblColumns := make(map[string]TableColumnDef)
		for _, row := range result {
			colDef := TableColumnDef{
				ColName: row["COLUMN_NAME"].(string),
				ColPos:  row["ORDINAL_POSITION"].(string),
				ColType: row["DATA_TYPE"].(string),
			}
			tblColumns[row["COLUMN_NAME"].(string)] = colDef
		}
		tblSchemas[dbtbl] = TableSchema{
			ColumnMap: tblColumns,
		}
		return tblSchemas, nil
	}
	return nil, errors.New("table not found")
}

// GetTableColumnList TODO
func GetTableColumnList(dbworker *DbWorker, dbName, tblName string) ([]string, error) {
	// tblSchemas = {"dbX.tableY": {"a": {"name":"a", "pos":"1", "type":"int"}}}
	/*
		queryStr := fmt.Sprintf("SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,DATA_TYPE,COLUMN_TYPE " +
			"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA =%s AND TABLE_NAME = %s" +
			" ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION asc", dbName, tblName)
	*/
	queryStr := fmt.Sprintf(
		"SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,DATA_TYPE,COLUMN_TYPE " +
			"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA =? AND TABLE_NAME = ? " +
			"ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION asc",
	)
	result, err := dbworker.QueryWithArgs(queryStr, dbName, tblName)
	// todo 这里的err没有正确捕捉到，比如sql执行错误
	if err != nil {
		return nil, err
	}
	var columnList []string
	if len(result) > 0 {
		for _, row := range result {
			columnList = append(columnList, row["COLUMN_NAME"].(string))
		}
		return columnList, nil
	}
	return nil, errors.New("table not found")
}
