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
	"fmt"
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
	Dsn string
	Db  *sql.DB
}

type InstanceInfo struct {
	ServerName string `db:"servername"`
	Hostname   string `db:"hostname"`
}

// 定义连接状态的结构
type ProcessInfo struct {
	Spid        int    `db:"spid"`
	DbName      string `db:"dbname"`
	Cmd         string `db:"cmd"`
	Status      string `db:"status"`
	ProgramName string `db:"program_name"`
	Hostname    string `db:"hostname"`
	LoginTime   string `db:"login_time"`
}

// NewDbWorker 初始化SQLserver实例对象
func NewDbWorker(user string, pass string, server string, port int) (dbw *DbWorker, err error) {
	dsn := fmt.Sprintf(
		"server=%s;port=%d;user id=%s;password=%s;database=master;encrypt=disable;collation=utf8mb4_unicode_ci",
		server, port, user, pass,
	)
	dbw = &DbWorker{
		Dsn: dsn,
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
func (h *DbWorker) Exec(query string, args ...interface{}) (int64, error) {
	ret, err := h.Db.Exec(query, args...)
	if err != nil {
		return 0, err
	}
	return ret.RowsAffected()
}

// ExecMore 执行一堆sql
// 会在同一个连接里执行
// 空元素会跳过
func (h *DbWorker) ExecMore(sqls []string) (rowsAffectedCount int64, err error) {
	var c int64
	db, err := h.Db.Conn(context.Background())
	if err != nil {
		return 0, err
	}
	defer db.Close()
	for _, sqlStr := range sqls {
		if strings.TrimSpace(sqlStr) == "" {
			continue
		}
		ret, err := db.ExecContext(context.Background(), sqlStr)
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
	db := sqlx.NewDb(h.Db, "mssql")
	udb := db.Unsafe()
	if err := udb.Select(data, query, args...); err != nil {
		logger.Info("Queryx:%s, args:%v", query, args)
		return fmt.Errorf("sqlx select failed, err:%w", err)
	}
	return nil
}

// Queryxs execute query use sqlx return Single row
func (h *DbWorker) Queryxs(data interface{}, query string) error {
	// logger.Info("Queryxs:%s", query)
	db := sqlx.NewDb(h.Db, "mssql")
	udb := db.Unsafe()
	if err := udb.Get(data, query); err != nil {
		return err
	}
	return nil
}

// ShowDatabases 执行show database 获取所有的dbName
// 正常情况值遍历可读写以及状态为running 的 业务数据库列表
func (h *DbWorker) ShowDatabases() (databases []string, err error) {
	cmd := "select name from sys.databases where is_read_only=0 and state=0 " +
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
	cmd := "SELECT name from sys.availability_groups;"
	err = h.Queryxs(&name, cmd)
	return
}

// CheckDBProcessExist 判断db是否存在相关请求
func (h *DbWorker) CheckDBProcessExist(dbName string) bool {
	var procinfos []ProcessInfo
	checkCmd := fmt.Sprintf("select spid, DB_NAME(dbid) as dbname ,cmd, status, program_name,hostname, login_time"+
		" from master.sys.sysprocesses where dbid >4  and dbid = DB_ID('%s') order by login_time desc;", dbName)
	if err := h.Queryx(&procinfos, checkCmd); err != nil {
		logger.Error("check-db-process failed %v", err)
		return false
	}
	if len(procinfos) == 0 {
		// 没有返回异常db列表则正常退出
		return true
	}
	// 异常退出
	for _, info := range procinfos {
		logger.Error("process:[%+v]", info)
	}
	return false
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
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_LOG',@enabled=0",
	}
	if _, err := h.ExecMore(cmds); err != nil {
		log := fmt.Sprintf("disable backup jobs failed %v", err)
		if isForce {
			return fmt.Errorf(log)
		} else {
			logger.Warn(log)
		}
	}
	return nil
}

// DisableBackupJob 启动备份JOB
func (h *DbWorker) EnableBackupJob() (err error) {
	cmds := []string{
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_FULL',@enabled=1;",
		"exec msdb.dbo.sp_update_job @job_name='TC_BACKUP_LOG',@enabled=1",
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
		DECLARE @Login sysname;
		SELECT @Login=name FROM sys.syslogins WHERE isntuser=1 and name like '%%sqlserver'
		EXEC sp_addsrvrolemember @Login, 'sysadmin'
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
			"restore database %s from disk='%s' with file = 1, %s",
			dbname, fullBakFile, restoreMode,
		)
	} else {
		restoreSQL = fmt.Sprintf(
			"restore database %s from disk='%s' with file = 1, %s, %s",
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
func (h *DbWorker) DBRestoreForLogBackup(dbname string, logBakFile string, restoreMode string) error {

	restoreSQL := fmt.Sprintf(
		"restore log %s from disk='%s' with file = 1, %s",
		dbname, logBakFile, restoreMode,
	)

	logger.Info("execute restore log-backup-sql: %s", restoreSQL)
	if _, err := h.Exec(restoreSQL); err != nil {
		return fmt.Errorf("restore sql failed %v", err)
	}
	return nil

}

// GetTableListOnDB 在db匹配符合的表列表
func (h *DbWorker) GetTableListOnDB(
	dbName string,
	intentionRegex []string,
	ignoreRegex []string) (realTables []string, err error) {

	var allTables []string
	getTablesSQL := fmt.Sprintf("select name from [%s].[sys].[tables]", dbName)
	logger.Info("get table list: %s", getTablesSQL)

	if err = h.Queryx(&allTables, getTablesSQL); err != nil {
		return realTables, fmt.Errorf("get table failed %v", err)
	}
	if len(allTables) == 0 {
		// 如果数据库没有数据表，则正常返回
		return realTables, nil
	}
	// 获取匹配到表列表
	intentionTables, err := util.DbMatch(allTables, util.ChangeToMatch(intentionRegex))
	if err != nil {
		return realTables, err
	}
	// 获取匹配到忽略表列表
	ignoreTables, err := util.DbMatch(allTables, util.ChangeToMatch(ignoreRegex))
	if err != nil {
		return realTables, err
	}
	// 获取最终需要匹配到的表
	realTables = util.FilterOutStringSlice(intentionTables, ignoreTables)
	return

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
		return fmt.Errorf("this version [%s] is not supported", sqlVersion)
	}
	for _, filename := range filenames {
		cmd := fmt.Sprintf(
			"& '%s' -S \"127.0.0.1,%d\" -C -d %s -f %d -b -i %s",
			cmdSql, port, dbName, charsetNO, filename,
		)
		fmt.Println(cmd)
		if ret, err := osutil.StandardPowerShellCommand(cmd); err != nil {
			logger.Error("exec sql script failed %s, result: %s ", err.Error(), ret)
			return err
		}
		logger.Info("exec sql script success  [%d:%s]", port, filename)
	}

	return nil
}
