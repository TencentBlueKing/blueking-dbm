// Package sqlserver TODO
/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package sqlserver

import (
	"context"
	"database/sql"
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"

	_ "github.com/denisenkom/go-mssqldb" // go-mssqldb TODO
	"github.com/jmoiron/sqlx"
)

// DbWorker TODO
type DbWorker struct {
	Dsn  string
	Db   *sql.DB
	Host string
	Port int
}

type InstanceInfo struct {
	ServerName string `db:"servername"`
	Hostname   string `db:"hostname"`
}

// execResult todo
type execResult struct {
	Msg      string `db:"msg"`
	ExitCode int    `db:"exitcode"`
}

// 定义连接状态的结构
type ProcessInfo struct {
	Spid        int            `db:"spid"`
	DbName      sql.NullString `db:"dbname"`
	Cmd         sql.NullString `db:"cmd"`
	Status      sql.NullString `db:"status"`
	ProgramName sql.NullString `db:"program_name"`
	Hostname    sql.NullString `db:"hostname"`
	LoginTime   sql.NullString `db:"login_time"`
}

func (p ProcessInfo) String() string {
	return fmt.Sprintf("spid=%d, db=%s, cmd=%s, status=%s, program=%s, host=%s, login_time=%s",
		p.Spid,
		osutil.NullStringValue(p.DbName),
		osutil.NullStringValue(p.Cmd),
		osutil.NullStringValue(p.Status),
		osutil.NullStringValue(p.ProgramName),
		osutil.NullStringValue(p.Hostname),
		osutil.NullStringValue(p.LoginTime))
}

// FormatProcessInfos formats process list as a pretty-printed ASCII table.
// title is an optional header describing the context (e.g. db name or instance addr).
// Returns a multi-line string suitable for direct logger output.
func FormatProcessInfos(title string, procs []ProcessInfo) string {
	if len(procs) == 0 {
		if title != "" {
			return fmt.Sprintf("[%s] no active business connections", title)
		}
		return "no active business connections"
	}
	// table headers
	headers := []string{"SPID", "DB", "CMD", "STATUS", "PROGRAM", "HOST", "LOGIN_TIME"}
	rows := make([][]string, 0, len(procs))
	for _, p := range procs {
		rows = append(rows, []string{
			fmt.Sprintf("%d", p.Spid),
			osutil.NullStringValue(p.DbName),
			osutil.NullStringValue(p.Cmd),
			osutil.NullStringValue(p.Status),
			osutil.NullStringValue(p.ProgramName),
			osutil.NullStringValue(p.Hostname),
			osutil.NullStringValue(p.LoginTime),
		})
	}
	// compute column widths
	widths := make([]int, len(headers))
	for i, h := range headers {
		widths[i] = len(h)
	}
	for _, row := range rows {
		for i, cell := range row {
			if l := len(cell); l > widths[i] {
				widths[i] = l
			}
		}
	}
	// build separator like +----+----+
	var sep strings.Builder
	sep.WriteByte('+')
	for _, w := range widths {
		sep.WriteString(strings.Repeat("-", w+2))
		sep.WriteByte('+')
	}
	sepLine := sep.String()

	formatRow := func(cells []string) string {
		var b strings.Builder
		b.WriteByte('|')
		for i, c := range cells {
			b.WriteString(fmt.Sprintf(" %-*s |", widths[i], c))
		}
		return b.String()
	}

	var out strings.Builder
	out.WriteByte('\n')
	if title != "" {
		out.WriteString(fmt.Sprintf("==== [%s] active connections: %d ====\n", title, len(procs)))
	} else {
		out.WriteString(fmt.Sprintf("==== active connections: %d ====\n", len(procs)))
	}
	out.WriteString(sepLine + "\n")
	out.WriteString(formatRow(headers) + "\n")
	out.WriteString(sepLine + "\n")
	for _, row := range rows {
		out.WriteString(formatRow(row) + "\n")
	}
	out.WriteString(sepLine)
	return out.String()
}

// LogProcessInfos prints process list in a pretty-printed table via logger.
// level: "info" | "warn" | "error" (default "info" when empty / unknown).
// title is optional; pass "" if not needed.
func LogProcessInfos(level string, title string, procs []ProcessInfo) {
	msg := FormatProcessInfos(title, procs)
	switch strings.ToLower(level) {
	case "error":
		logger.Error("%s", msg)
	case "warn", "warning":
		logger.Warn("%s", msg)
	default:
		logger.Info("%s", msg)
	}
}

type DefaultPathInfo struct {
	DefaultDataPath string `db:"Default_Data_Path"`
	DefaultLogPath  string `db:"Default_Log_Path"`
}

// CSVExportOptions CSV导出选项
type CSVExportOptions struct {
	FileName   string // 文件名
	Directory  string // 导出目录
	WithHeader bool   // 是否包含表头
	Encoding   string // 文件编码
	AutoName   bool   // 是否自动生成文件名
}

// DefaultExportOptions 默认导出选项
func DefaultExportOptions() *CSVExportOptions {
	return &CSVExportOptions{
		WithHeader: true,
		Encoding:   "utf-8",
		AutoName:   true,
		Directory:  "./exports",
	}
}

// NewDbWorker 初始化SQLserver实例对象
func NewDbWorker(user string, pass string, server string, port int) (dbw *DbWorker, err error) {
	if strings.TrimSpace(user) == "" || strings.TrimSpace(pass) == "" {
		return nil, fmt.Errorf("user or pass is null, check")
	}
	dsn := fmt.Sprintf(
		"server=%s;port=%d;user id=%s;password=%s;database=master;encrypt=disable;collation=utf8mb4_unicode_ci",
		server, port, user, pass,
	)
	dbw = &DbWorker{
		Dsn:  dsn,
		Host: server,
		Port: port,
	}
	dbw.Db, err = sql.Open("sqlserver", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	// check connect with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := dbw.Db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("ping context failed, err:%w", err)
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
func (h *DbWorker) Exec(sql string, args ...interface{}) (int64, error) {
	sqls := []string{sql}
	return h.ExecMore(sqls)
}

// ExecMore 执行一堆sql
// 会在同一个连接里执行
func (h *DbWorker) ExecMore(sqls []string) (rowsAffectedCount int64, err error) {
	var c int64
	var db *sqlx.DB
	// 插入execute命令
	baseSQL := "EXECUTE AS login='sa';"
	db, err = sqlx.Connect("mssql", h.Dsn)
	if err != nil {
		return 0, fmt.Errorf("connect db failed, err:%w", err)
	}
	defer db.Close()
	sqlStr := strings.Join(sqls, ";")
	ret, err := db.Exec(fmt.Sprintf("%s %s", baseSQL, sqlStr))
	if err != nil {
		return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", sqlStr, err)
	}
	if c, err = ret.RowsAffected(); err != nil {
		return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", sqlStr, err)
	}
	rowsAffectedCount += c
	return
}

// ExecMoreNoSA 执行一堆sql，没有sa权限下
func (h *DbWorker) ExecMoreNoSA(sqls []string) (rowsAffectedCount int64, err error) {
	var c int64
	var db *sqlx.DB
	// 插入execute命令
	db, err = sqlx.Connect("mssql", h.Dsn)
	if err != nil {
		return 0, fmt.Errorf("connect db failed, err:%w", err)
	}
	defer db.Close()
	for _, sqlStr := range sqls {
		if strings.TrimSpace(sqlStr) == "" {
			continue
		}
		ret, err := db.Exec(sqlStr)
		if err != nil {
			return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", sqlStr, err)
		}
		if c, err = ret.RowsAffected(); err != nil {
			return rowsAffectedCount, fmt.Errorf("exec %s failed,err:%w", sqlStr, err)
		}
		rowsAffectedCount += c
	}
	return
}

// Queryx execute query use sqlx
func (h *DbWorker) Queryx(data interface{}, query string, args ...interface{}) error {
	db, err := sqlx.Connect("mssql", h.Dsn)
	if err != nil {
		return fmt.Errorf("connect db failed, err:%w", err)
	}
	defer db.Close()
	udb := db.Unsafe()
	if err := udb.Select(data, query, args...); err != nil {
		logger.Error("Queryx:%s, args:%v", query, args)
		return fmt.Errorf("sqlx select failed, err:%w", err)
	}
	return nil
}

// Queryxs execute query use sqlx return Single row
func (h *DbWorker) Queryxs(data interface{}, query string) error {
	db, err := sqlx.Connect("mssql", h.Dsn)
	if err != nil {
		return fmt.Errorf("connect db failed, err:%w", err)
	}
	defer db.Close()
	udb := db.Unsafe()
	if err := udb.Get(data, query); err != nil {
		return err
	}
	return nil
}

func (h *DbWorker) ExportToCSVWithSelect(query string) (string, error) {
	db, err := sqlx.Connect("mssql", h.Dsn)
	if err != nil {
		return "", fmt.Errorf("connect db failed, err:%w", err)
	}
	defer db.Close()
	udb := db.Unsafe()
	var results []map[string]interface{}
	if err := udb.Select(&results, query); err != nil {
		return "", fmt.Errorf("查询失败: %v", err)
	}

	// 使用默认选项导出
	options := DefaultExportOptions()
	options.AutoName = true
	options.WithHeader = true

	return h.ExportToCSVFile(results, options)
}

// ShowDatabases 执行show database 获取所有的dbName, 不包括系统数据库、异常的库、以及快照库
// 正常情况值遍历可读写以及状态为running 的 业务数据库列表
func (h *DbWorker) ShowDatabases() (databases []string, err error) {
	cmd := "select name from sys.databases where is_read_only=0 and state=0 " +
		"and name not in ('msdb', 'master', 'model', 'tempdb', 'Monitor');"
	err = h.Queryx(&databases, cmd)
	return
}

// ShowDatabases 执行show database 获取所有的dbName, 不包括系统数据库、异常的库
// 正常情况值遍历可读写以及状态为running 的 业务数据库列表
func (h *DbWorker) ShowDatabasesIncludeSnapshots() (databases []string, err error) {
	cmd := "select name from sys.databases where state=0 " +
		"and name not in ('msdb', 'master', 'model', 'tempdb', 'Monitor');"
	err = h.Queryx(&databases, cmd)
	return
}

// GetVersion 获取实例的版本信息
func (h *DbWorker) GetVersion() (version string, err error) {
	cmd := "select SUBSTRING(@@VERSION, 1, CHARINDEX('-', @@VERSION) - 2) AS VersionInfo;"
	err = h.Queryxs(&version, cmd)
	return
}

// GetGroupName 获取Alwayson的group name
func (h *DbWorker) GetGroupName() (name string, err error) {
	cmd := "SELECT name from master.sys.availability_groups;"
	err = h.Queryxs(&name, cmd)
	return
}

// GetGroupName 获取实例在Alwayson的角色
func (h *DbWorker) GetRoleInAlwaysOn() (role int, err error) {
	cmd := "select role from master.sys.dm_hadr_availability_replica_states where is_local = 1;"
	err = h.Queryxs(&role, cmd)
	return
}

// GetDefaultPath 获取实例默认数据目录路径
func (h *DbWorker) GetDefaultPath() (getpath []DefaultPathInfo, err error) {
	err = h.Queryx(&getpath, cst.GET_PATH_SQL)
	return
}

// GetDefaultPath 获取实例默例行全量备份的路径
func (h *DbWorker) GetFullBackupPath() (getpath sql.NullString, err error) {
	cmd := "select [FULL_BACKUP_PATH] from [Monitor].[dbo].[APP_SETTING]"
	err = h.Queryxs(&getpath, cmd)
	return
}

// GetDefaultPath 获取实例默例行全量备份的路径
func (h *DbWorker) GetLogBackupPath() (getpath sql.NullString, err error) {
	cmd := "select [LOG_BACKUP_PATH] from [Monitor].[dbo].[APP_SETTING]"
	err = h.Queryxs(&getpath, cmd)
	return
}

// GetClusterDomain 获取实例所在的集群域名
func (h *DbWorker) GetClusterDomain() (cluster_domain sql.NullString, err error) {
	cmd := "select [CLUSTER_DOMAIN] from [Monitor].[dbo].[APP_SETTING]"
	err = h.Queryxs(&cluster_domain, cmd)
	return
}

// GetInstanceRole 获取实例在DBM的角色信息
func (h *DbWorker) GetInstanceRole() (role sql.NullString, err error) {
	cmd := "select [ROLE] from [Monitor].[dbo].[APP_SETTING]"
	err = h.Queryxs(&role, cmd)
	return
}

// CheckDBProcessExist 判断db是否存在相关请求
// 这里会顺便kill掉ssms的连接
func (h *DbWorker) CheckDBProcessExist(dbName string) bool {
	var procinfos []ProcessInfo
	var killCmd []string
	isNoErr := true
	checkCmd := fmt.Sprintf("select spid, DB_NAME(dbid) as dbname ,cmd, status, program_name,hostname, login_time"+
		" from master.sys.sysprocesses where dbid >4  and dbid = DB_ID('%s') and lastwaittype != 'PARALLEL_REDO_WORKER_WAIT_WORK' "+
		" order by login_time desc;", dbName)
	if err := h.Queryx(&procinfos, checkCmd); err != nil {
		logger.Error("check-db-process failed %v", err)
		return false
	}
	if len(procinfos) == 0 {
		// 没有返回异常db列表则正常退出
		return true
	}
	// 区分可自动 kill 的 SSMS 连接 与 业务连接
	var ssmsProcs, bizProcs []ProcessInfo
	for _, info := range procinfos {
		if strings.Contains(info.ProgramName.String, "Microsoft SQL Server Management Studio") {
			ssmsProcs = append(ssmsProcs, info)
			killCmd = append(killCmd, fmt.Sprintf("kill %d", info.Spid))
		} else {
			bizProcs = append(bizProcs, info)
			isNoErr = false
		}
	}
	if len(ssmsProcs) > 0 {
		LogProcessInfos("warn", fmt.Sprintf("db:%s SSMS connections will be killed", dbName), ssmsProcs)
	}
	if len(bizProcs) > 0 {
		LogProcessInfos("error", fmt.Sprintf("db:%s business connections", dbName), bizProcs)
	}
	if !isNoErr {
		return false
	}
	if _, err := h.ExecMore(killCmd); err != nil {
		logger.Error(fmt.Sprintf("kill process failed %v", err))
		return false
	}
	return true
}

// GetServerNameAndInstanceName 获取实例的相关信息
func (h *DbWorker) GetServerNameAndInstanceName() (info []InstanceInfo, err error) {

	cmd := "SELECT CAST(SERVERPROPERTY('ServerName') AS sysname) as servername, " +
		"case when CAST(SERVERPROPERTY('ServerName') AS sysname) " +
		"like '%\\%' then substring(CAST(SERVERPROPERTY('ServerName') AS sysname)," +
		"0,charindex('\\',CAST(SERVERPROPERTY('ServerName') AS sysname))) " +
		"else CAST(SERVERPROPERTY('ServerName') AS sysname) end as hostname"

	err = h.Queryx(&info, cmd)
	return
}

// DisableBackupJob 禁止备份JOB
func (h *DbWorker) DisableBackupJob(isForce bool) (err error) {
	cmds := []string{
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_FULL',@enabled=0;",
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_LOG',@enabled=0;",
	}
	if _, err := h.ExecMore(cmds); err != nil {
		if isForce {
			return fmt.Errorf("disable backup jobs failed %v", err)
		}
		logger.Warn("disable backup jobs failed %v", err)
	}
	return nil
}

// DisableBackupJob 启动备份JOB
func (h *DbWorker) EnableBackupJob() (err error) {
	cmds := []string{
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_FULL',@enabled=1;",
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_LOG',@enabled=1;",
	}
	if _, err := h.ExecMore(cmds); err != nil {
		return fmt.Errorf("enable backup jobs failed %v", err)
	}
	return nil
}

// EnableEndPoint 启动endpoint配置
func (h *DbWorker) EnableEndPoint(end_port int) (err error) {
	cmd := fmt.Sprintf(
		`IF EXISTS(select 1 from [master].[sys].[database_mirroring_endpoints] where name='endpoint_mirroring') 
			DROP ENDPOINT [endpoint_mirroring]
		CREATE ENDPOINT [endpoint_mirroring] STATE=STARTED AS TCP (LISTENER_PORT = %d, LISTENER_IP = ALL) 
		FOR DATA_MIRRORING (ROLE = PARTNER, AUTHENTICATION = WINDOWS NEGOTIATE, ENCRYPTION = REQUIRED ALGORITHM AES);
		`, end_port)

	if _, err := h.Exec(cmd); err != nil {
		return fmt.Errorf("enable endpoint failed %v", err)
	}
	return nil
}

// CreateLoginUser 定义添加账号
func (h *DbWorker) CreateLoginUser(userName string, pwd string, loginRole string) (err error) {
	cmd := fmt.Sprintf(cst.EXEC_INIT_LOGIN_SQL, userName, pwd, loginRole)
	if _, err := h.Exec(cmd); err != nil {
		return fmt.Errorf("create login [%s] failed %v", userName, err)
	}
	return nil
}

// CreateLoginUserWithSid 定义添加账号, 指定SID
func (h *DbWorker) CreateLoginUserWithSid(userName string, pwd string, loginRole string, sid string) (err error) {
	cmd := fmt.Sprintf(cst.EXEC_INIT_LOGIN_WITH_SID_SQL, userName, pwd, loginRole, sid)
	if _, err := h.Exec(cmd); err != nil {
		return fmt.Errorf("create login with sid [%s] failed %v", userName, err)
	}
	return nil
}

// CreateLoginUser 初始化账号添加权限，统一给db_owner
func (h *DbWorker) AddPriv(dbname string, userName string) (err error) {
	cmd := fmt.Sprintf(cst.EXEC_INIT_PRIV_SQL, dbname, userName)
	if _, err := h.Exec(cmd); err != nil {
		return fmt.Errorf("add priv login [%s] in db [%s] failed %v", userName, dbname, err)
	}
	return nil
}

// 操作全量恢复命令
func (h *DbWorker) DBRestoreForFullBackup(dbname string, fullBakFile string, move string, restoreMode string) error {
	var restoreSQL string
	if move == "" {
		restoreSQL = fmt.Sprintf(
			"restore database [%s] from disk='%s' with file = 1, %s , NOUNLOAD,  REPLACE,  STATS = 5",
			dbname, fullBakFile, restoreMode,
		)
	} else {
		restoreSQL = fmt.Sprintf(
			"restore database [%s] from disk='%s' with file = 1, %s, %s, NOUNLOAD,  REPLACE,  STATS = 5",
			dbname, fullBakFile, move, restoreMode,
		)

	}
	logger.Info("execute restore full-backup-sql: %s", restoreSQL)
	if _, err := h.Exec(restoreSQL); err != nil {
		return fmt.Errorf("restore sql failed %v", err)
	}
	return nil

}

// 操作日志备份恢复命令
func (h *DbWorker) DBRestoreForLogBackup(dbname string, logBakFile string, restoreMode string, restoreTime string) error {
	var restoreSQL string
	if restoreTime != "" {
		restoreSQL = fmt.Sprintf(
			"restore log [%s] from disk='%s' with file = 1, %s, STOPAT = N'%s'",
			dbname, logBakFile, restoreMode, restoreTime,
		)
	} else {
		restoreSQL = fmt.Sprintf(
			"restore log [%s] from disk='%s' with file = 1, %s",
			dbname, logBakFile, restoreMode,
		)
	}

	logger.Info("execute restore log-backup-sql: %s", restoreSQL)
	if _, err := h.Exec(restoreSQL); err != nil {
		return fmt.Errorf("restore sql failed %v", err)
	}
	return nil

}

// TableSchema 表的 schema/table 名信息
type TableSchema struct {
	SchemaName string `db:"schema_name"`
	TableName  string `db:"table_name"`
}

// FKRelation 外键关系（parent → referenced）
//   - Parent 表是"引用方"，其上定义了 FK 列
//   - Referenced 表是"被引用方"，被 FK 指向
type FKRelation struct {
	FKName       string `db:"fk_name"`
	ParentSchema string `db:"parent_schema"`
	ParentTable  string `db:"parent_table"`
	RefSchema    string `db:"ref_schema"`
	RefTable     string `db:"ref_table"`
}

// GetFKRelationsOnDB 拉取指定数据库下所有用户表的外键关系
func (h *DbWorker) GetFKRelationsOnDB(dbName string) ([]FKRelation, error) {
	var rs []FKRelation
	getSQL := fmt.Sprintf(cst.LIST_FKS_ON_DB_SQL, dbName)
	if err := h.Queryx(&rs, getSQL); err != nil {
		return nil, fmt.Errorf("get fk-relations on db [%s] failed: %v", dbName, err)
	}
	return rs, nil
}

// SchemaBoundRef schema-bound 对象（视图/UDF 等）对表的引用
type SchemaBoundRef struct {
	Referencing string `db:"referencing"` // 引用方（schema-bound 对象）
	Referenced  string `db:"referenced"`  // 被引用方（表）
}

// GetSchemaBoundRefsOnDB 拉取数据库内所有 schema-bound 对象对用户表的引用
// 用于 DROP TABLE 前的预检查，避免被 SQL Server 抛 3729 错误
func (h *DbWorker) GetSchemaBoundRefsOnDB(dbName string) ([]SchemaBoundRef, error) {
	var rs []SchemaBoundRef
	getSQL := fmt.Sprintf(cst.LIST_SCHEMABOUND_REFS_SQL, dbName)
	if err := h.Queryx(&rs, getSQL); err != nil {
		return nil, fmt.Errorf("get schema-bound refs on db [%s] failed: %v", dbName, err)
	}
	return rs, nil
}

// GetTableListOnDB 在db匹配符合的表列表，返回包含 schema 信息的表列表
// 匹配/忽略规则均按表名（不含 schema）作正则匹配，与历史行为保持一致
func (h *DbWorker) GetTableListOnDB(
	dbName string,
	intentionRegex []string,
	ignoreRegex []string) (realTables []TableSchema, err error) {

	var allTables []TableSchema
	getTablesSQL := fmt.Sprintf(
		`SELECT t.name AS table_name, s.name AS schema_name
FROM [%s].sys.tables t
JOIN [%s].sys.schemas s ON s.schema_id = t.schema_id
WHERE t.is_ms_shipped = 0`,
		dbName, dbName,
	)
	logger.Info("get table list: %s", getTablesSQL)

	if err = h.Queryx(&allTables, getTablesSQL); err != nil {
		return realTables, fmt.Errorf("get table failed %v", err)
	}
	if len(allTables) == 0 {
		// 如果数据库没有数据表，则正常返回
		return realTables, nil
	}
	// 抽取表名用于正则匹配
	allTableNames := make([]string, 0, len(allTables))
	for _, t := range allTables {
		allTableNames = append(allTableNames, t.TableName)
	}
	// 获取匹配到表列表
	intentionTables, err := util.DbMatch(allTableNames, util.ChangeToMatch(intentionRegex))
	if err != nil {
		return realTables, err
	}
	// 获取匹配到忽略表列表
	ignoreTables, err := util.DbMatch(allTableNames, util.ChangeToMatch(ignoreRegex))
	if err != nil {
		return realTables, err
	}
	// 获取最终需要匹配到的表名集合
	finalTableNames := util.FilterOutStringSlice(intentionTables, ignoreTables)
	if len(finalTableNames) == 0 {
		return realTables, nil
	}
	finalSet := make(map[string]struct{}, len(finalTableNames))
	for _, n := range finalTableNames {
		finalSet[n] = struct{}{}
	}
	// 回填 schema 信息
	for _, t := range allTables {
		if _, ok := finalSet[t.TableName]; ok {
			realTables = append(realTables, t)
		}
	}
	return

}

// ExportToCSVFile 将结果导出到CSV文件
func (h *DbWorker) ExportToCSVFile(results []map[string]interface{}, options *CSVExportOptions) (string, error) {
	if options == nil {
		options = DefaultExportOptions()
	}

	// 生成文件名
	fileName, err := h.generateFileName(options)
	if err != nil {
		return "", fmt.Errorf("生成文件名失败: %v", err)
	}

	// 确保目录存在
	if err := os.MkdirAll(options.Directory, 0755); err != nil {
		return "", fmt.Errorf("创建目录失败: %v", err)
	}

	// 创建文件
	filePath := filepath.Join(options.Directory, fileName)
	file, err := os.Create(filePath)
	if err != nil {
		return "", fmt.Errorf("创建文件失败: %v", err)
	}
	defer file.Close()

	// 写入CSV内容
	if err := h.writeCSVToFile(file, results, options); err != nil {
		return "", fmt.Errorf("写入CSV失败: %v", err)
	}

	logger.Info("成功导出CSV文件: %s", filePath)
	return filePath, nil
}

// generateFileName 生成文件名
func (h *DbWorker) generateFileName(options *CSVExportOptions) (string, error) {
	if options.FileName != "" {
		// 确保有.csv扩展名
		if !strings.HasSuffix(strings.ToLower(options.FileName), ".csv") {
			options.FileName += ".csv"
		}
		return options.FileName, nil
	}

	if options.AutoName {
		// 自动生成文件名：export_YYYYMMDD_HHMMSS.csv
		timestamp := time.Now().Format("20060102_150405")
		return fmt.Sprintf("export_%s.csv", timestamp), nil
	}

	return "", fmt.Errorf("未指定文件名且未启用自动命名")
}

// writeCSVToFile 写入CSV到文件
func (h *DbWorker) writeCSVToFile(file *os.File, results []map[string]interface{}, options *CSVExportOptions) error {
	writer := csv.NewWriter(file)
	defer writer.Flush()

	if len(results) == 0 {
		// 如果结果为空且需要表头，创建空文件或只包含表头
		if options.WithHeader {
			// 可以在这里添加空表头逻辑 todo
		}
		return nil
	}

	// 获取列名
	columns := h.getColumnNames(results)

	// 写入表头
	if options.WithHeader {
		if err := writer.Write(columns); err != nil {
			return fmt.Errorf("写入表头失败: %v", err)
		}
	}

	// 写入数据行
	for _, result := range results {
		record := make([]string, len(columns))
		for i, col := range columns {
			if val := result[col]; val == nil {
				record[i] = "NULL"
			} else {
				record[i] = fmt.Sprintf("%v", val)
			}
		}

		if err := writer.Write(record); err != nil {
			return fmt.Errorf("写入数据行失败: %v", err)
		}
	}

	return writer.Error()
}

// getColumnNames 获取列名
func (h *DbWorker) getColumnNames(results []map[string]interface{}) []string {
	if len(results) == 0 {
		return []string{}
	}

	columns := make([]string, 0, len(results[0]))
	for col := range results[0] {
		columns = append(columns, col)
	}
	return columns
}

// GetCmdSql 获取sqlcmd的路径
func GetCmdSql(sqlVersion string) (string, error) {
	var cmdSql string
	switch {
	case strings.Contains(sqlVersion, "2008"):
		cmdSql = cst.SQLCMD_2008
	case strings.Contains(sqlVersion, "2012"):
		cmdSql = cst.SQLCMD_2012
	case strings.Contains(sqlVersion, "2014"):
		cmdSql = cst.SQLCMD_2014
	case strings.Contains(sqlVersion, "2016"):
		cmdSql = cst.SQLCMD_2016
	case strings.Contains(sqlVersion, "2017"):
		cmdSql = cst.SQLCMD_2017
	case strings.Contains(sqlVersion, "2019"):
		cmdSql = cst.SQLCMD_2019
	case strings.Contains(sqlVersion, "2022"):
		cmdSql = cst.SQLCMD_2022
	default:
		return cmdSql, fmt.Errorf("this version [%s] is not supported", sqlVersion)
	}
	return cmdSql, nil
}

// ExecLocalSQLFile TODO
// 调用本地的sqlcmd执行本地sql脚本，识别smss的语法（主要是go语法）
// 适配sql脚本执行、初始化等相关大脚本操作
// 目前执行sql脚本出现错误则异常退出
func ExecLocalSQLFile(sqlVersion string, dbName string, charsetNO int, filenames []string, port int) error {
	var cmdSql string
	if charsetNO == 0 {
		charsetNO = 936
	}
	cmdSql, err := GetCmdSql(sqlVersion)
	if err != nil {
		return err
	}
	for _, filename := range filenames {
		var ret string
		var err error
		cmd := fmt.Sprintf(
			"& '%s' -S \"127.0.0.1,%d\" -C -I -d %s -f %d -b -i %s",
			cmdSql, port, dbName, charsetNO, filename,
		)
		logger.Info("exec cmd: %s", cmd)
		if ret, err = osutil.StandardPowerShellCommand(cmd); err != nil {
			logger.Error("the db [%s] exec sql script failed %s, result: %s ", dbName, err.Error(), ret)
			return err
		}
		logger.InfoNotForAi("exec result: %s", ret)
		logger.Info("ths db [%s] exec sql script success  [%d:%s]", dbName, port, filename)
	}

	return nil
}

// ExecLocalSQLFileForSa 基于 sa 账号执行本地 sql 脚本
// 逻辑与 ExecLocalSQLFile 一致，区别在于：
//  1. 使用 -U/-P 通过 sa 等账号进行认证，而非 Windows 集成认证
//  2. 无论是正常日志还是错误日志，均对密码进行屏蔽（xxx）
func ExecLocalSQLFileForSa(
	sqlVersion string,
	dbName string,
	charsetNO int,
	filenames []string,
	port int,
	userName string,
	pwd string,
) error {
	var cmdSql string
	if charsetNO == 0 {
		charsetNO = 936
	}
	cmdSql, err := GetCmdSql(sqlVersion)
	if err != nil {
		return err
	}
	// mask 用于对任意字符串屏蔽密码明文
	mask := func(s string) string {
		if pwd == "" {
			return s
		}
		return strings.Replace(s, pwd, "xxx", -1)
	}
	for _, filename := range filenames {
		var ret string
		var err error
		cmd := fmt.Sprintf(
			"& '%s' -S \"127.0.0.1,%d\" -C -I -d %s -f %d -b -i %s -U '%s' -P '%s'",
			cmdSql, port, dbName, charsetNO, filename, userName, pwd,
		)
		logger.Info("exec cmd: %s", mask(cmd))
		if ret, err = osutil.StandardPowerShellCommand(cmd); err != nil {
			logger.Error("the db [%s] exec sql script failed %s, result: %s ",
				dbName, mask(err.Error()), mask(ret))
			return fmt.Errorf("%s", mask(err.Error()))
		}
		logger.InfoNotForAi("exec result: %s", mask(ret))
		logger.Info("ths db [%s] exec sql script success  [%d:%s]", dbName, port, filename)
	}

	return nil
}

// ExecLocalSQLFileForDataExport 执行本地sql脚本，导出数据
func ExecLocalSQLFileForDataExport(
	cluster_domain string,
	sqlVersion string,
	dbName string,
	filenames []string,
	port int,
	userName string,
	pwd string,
) ([]string, error) {

	var cmdSql string
	var outPutFiles []string
	cmdSql, err := GetCmdSql(sqlVersion)
	if err != nil {
		return outPutFiles, err
	}
	for _, filename := range filenames {
		var ret string
		var err error
		outPutFile := strings.Replace(filename, ".sql", fmt.Sprintf("_%s_%d_%s.csv", cluster_domain, port, dbName), -1)
		outPutFiles = append(outPutFiles, outPutFile)
		cmd := fmt.Sprintf(
			"$output = & '%s' -S '127.0.0.1,%d' -C -I -d %s -f %d -b -i %s -U '%s' -P '%s' -s ',' -W 2>&1;"+
				" if ($LASTEXITCODE -ne 0) { Write-Error ($output -join \"`n\"); exit $LASTEXITCODE }"+
				" else { $output | Out-File -FilePath '%s' -Encoding UTF8 }",
			cmdSql, port, dbName, 936, filename, userName, pwd, outPutFile,
		)

		logger.Info("exec cmd: %s", strings.Replace(cmd, pwd, "xxx", -1))
		if ret, err = osutil.StandardPowerShellCommand(cmd); err != nil {
			sanitizedErr := fmt.Errorf("the db [%s] exec sql script failed %s, result: %s ", dbName, strings.Replace(err.Error(), pwd, "xxx", -1), ret)
			return outPutFiles, sanitizedErr
		}
		logger.InfoNotForAi("exec result: %s", ret)
		logger.Info("ths db [%s] exec sql select script success  [%d:%s]", dbName, port, filename)
	}

	return outPutFiles, nil
}

// exec_switch_sp todo
func ExecSwitchSP(db *DbWorker, spName string, paramStr string) error {
	cmd := fmt.Sprintf(cst.EXEC_SWITCH_SP_TMEP_SQL, spName, paramStr)
	logger.Info(cmd)
	var ret []execResult
	if err := db.Queryx(&ret, cmd); err != nil {
		logger.Error("exec %s failed", spName)
		return err
	}
	if ret[0].ExitCode != 1 {
		logger.Error("exec %s failed", spName)
		return fmt.Errorf(ret[0].Msg)
	}
	logger.Info(ret[0].Msg)
	return nil
}
