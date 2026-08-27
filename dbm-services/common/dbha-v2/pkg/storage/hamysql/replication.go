/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hamysql

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/go-pubpkg/cmutil"

	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"
)

const (
	// mysql84Version is the first version that removed the legacy replication terminology.
	mysql84Version = "8.4.0"

	// AutoPositionOmit emits no AUTO_POSITION clause.
	AutoPositionOmit = -1
	// AutoPositionOff emits MASTER_AUTO_POSITION = 0.
	AutoPositionOff = 0
	// AutoPositionOn emits MASTER_AUTO_POSITION = 1.
	AutoPositionOn = 1

	// GetPublicKeyAuto lets ChangeReplicationTo decide by server version (emitted on MySQL >= 8.4).
	GetPublicKeyAuto = 0
	// GetPublicKeyOff never emits the GET_MASTER/SOURCE_PUBLIC_KEY clause.
	GetPublicKeyOff = 1
	// GetPublicKeyOn always emits GET_MASTER/SOURCE_PUBLIC_KEY = 1.
	GetPublicKeyOn = 2
)

// mysqlStringEscaper escapes a value for inclusion in a single-quoted MySQL string literal.
var mysqlStringEscaper = strings.NewReplacer("\\", "\\\\", "'", "\\'")

// ReplSource carries the replication source coordinates for building a CHANGE MASTER statement.
type ReplSource struct {
	Host         string
	Port         int
	User         string
	Password     string
	LogFile      string
	LogPos       uint64
	AutoPosition int
	// GetPublicKey controls GET_MASTER/SOURCE_PUBLIC_KEY emission; zero value means auto by server version.
	GetPublicKey int
}

// ReplStatements holds the replication statements in the naming the connected server accepts.
type ReplStatements struct {
	ShowSlaveStatus  string
	ShowMasterStatus string
	StartSlave       string
	StopSlave        string
	ResetSlaveAll    string
}

// ReplicationStatus represents MySQL slave status information.
// SecondsBehindMaster stays NULL (Valid=false) when the server reports NULL
// (replication not connected); callers must check Valid before using the value.
type ReplicationStatus struct {
	SlaveIOState               string        `gorm:"column:Slave_IO_State"                json:"Slave_IO_State"`
	MasterHost                 string        `gorm:"column:Master_Host"                   json:"Master_Host"`
	MasterUser                 string        `gorm:"column:Master_User"                   json:"Master_User"`
	MasterPort                 int           `gorm:"column:Master_Port"                   json:"Master_Port"`
	ConnectRetry               int           `gorm:"column:Connect_Retry"                 json:"Connect_Retry"`
	MasterLogFile              string        `gorm:"column:Master_Log_File"               json:"Master_Log_File"`
	ReadMasterLogPos           uint64        `gorm:"column:Read_Master_Log_Pos"           json:"Read_Master_Log_Pos"`
	RelayLogFile               string        `gorm:"column:Relay_Log_File"                json:"Relay_Log_File"`
	RelayLogPos                uint64        `gorm:"column:Relay_Log_Pos"                 json:"Relay_Log_Pos"`
	RelayMasterLogFile         string        `gorm:"column:Relay_Master_Log_File"         json:"Relay_Master_Log_File"`
	SlaveIORunning             string        `gorm:"column:Slave_IO_Running"              json:"Slave_IO_Running"`
	SlaveSQLRunning            string        `gorm:"column:Slave_SQL_Running"             json:"Slave_SQL_Running"`
	ReplicateDoDB              string        `gorm:"column:Replicate_Do_DB"               json:"Replicate_Do_DB"`
	ReplicateIgnoreDB          string        `gorm:"column:Replicate_Ignore_DB"           json:"Replicate_Ignore_DB"`
	ReplicateDoTable           string        `gorm:"column:Replicate_Do_Table"            json:"Replicate_Do_Table"`
	ReplicateIgnoreTable       string        `gorm:"column:Replicate_Ignore_Table"        json:"Replicate_Ignore_Table"`
	ReplicateWildDoTable       string        `gorm:"column:Replicate_Wild_Do_Table"       json:"Replicate_Wild_Do_Table"`
	ReplicateWildIgnoreTable   string        `gorm:"column:Replicate_Wild_Ignore_Table"   json:"Replicate_Wild_Ignore_Table"`
	LastErrno                  int           `gorm:"column:Last_Errno"                    json:"Last_Errno"`
	LastError                  string        `gorm:"column:Last_Error"                    json:"Last_Error"`
	SkipCounter                int           `gorm:"column:Skip_Counter"                  json:"Skip_Counter"`
	ExecMasterLogPos           uint64        `gorm:"column:Exec_Master_Log_Pos"           json:"Exec_Master_Log_Pos"`
	RelayLogSpace              uint64        `gorm:"column:Relay_Log_Space"               json:"Relay_Log_Space"`
	UntilCondition             string        `gorm:"column:Until_Condition"               json:"Until_Condition"`
	UntilLogFile               string        `gorm:"column:Until_Log_File"                json:"Until_Log_File"`
	UntilLogPos                uint64        `gorm:"column:Until_Log_Pos"                 json:"Until_Log_Pos"`
	MasterSSLAllowed           string        `gorm:"column:Master_SSL_Allowed"            json:"Master_SSL_Allowed"`
	MasterSSLCAFile            string        `gorm:"column:Master_SSL_CA_File"            json:"Master_SSL_CA_File"`
	MasterSSLCAPath            string        `gorm:"column:Master_SSL_CA_Path"            json:"Master_SSL_CA_Path"`
	MasterSSLCert              string        `gorm:"column:Master_SSL_Cert"               json:"Master_SSL_Cert"`
	MasterSSLCipher            string        `gorm:"column:Master_SSL_Cipher"             json:"Master_SSL_Cipher"`
	MasterSSLKey               string        `gorm:"column:Master_SSL_Key"                json:"Master_SSL_Key"`
	SecondsBehindMaster        sql.NullInt64 `gorm:"column:Seconds_Behind_Master"         json:"Seconds_Behind_Master"`
	MasterSSLVerifyServerCert  string        `gorm:"column:Master_SSL_Verify_Server_Cert" json:"Master_SSL_Verify_Server_Cert"`
	LastIOErrno                int           `gorm:"column:Last_IO_Errno"                 json:"Last_IO_Errno"`
	LastIOError                string        `gorm:"column:Last_IO_Error"                 json:"Last_IO_Error"`
	LastSQLErrno               int           `gorm:"column:Last_SQL_Errno"                json:"Last_SQL_Errno"`
	LastSQLError               string        `gorm:"column:Last_SQL_Error"                json:"Last_SQL_Error"`
	ReplicateIgnoreServerIDs   string        `gorm:"column:Replicate_Ignore_Server_Ids"   json:"Replicate_Ignore_Server_Ids"`
	MasterServerID             uint64        `gorm:"column:Master_Server_Id"              json:"Master_Server_Id"`
	MasterUUID                 string        `gorm:"column:Master_UUID"                   json:"Master_UUID"`
	MasterInfoFile             string        `gorm:"column:Master_Info_File"              json:"Master_Info_File"`
	SqlDelay                   uint64        `gorm:"column:SQL_Delay"                     json:"SQL_Delay"`
	SqlRemainingDelay          string        `gorm:"column:SQL_Remaining_Delay"           json:"SQL_Remaining_Delay"`
	SlaveSqlRunningState       string        `gorm:"column:Slave_SQL_Running_State"       json:"Slave_SQL_Running_State"`
	MasterRetryCount           int           `gorm:"column:Master_Retry_Count"            json:"Master_Retry_Count"`
	MasterBind                 string        `gorm:"column:Master_Bind"                   json:"Master_Bind"`
	LastIoErrorTimestamp       string        `gorm:"column:Last_IO_Error_Timestamp"       json:"Last_IO_Error_Timestamp"`
	LastSqlErrorTimestamp      string        `gorm:"column:Last_SQL_Error_Timestamp"      json:"Last_SQL_Error_Timestamp"`
	MasterSSLCrl               string        `gorm:"column:Master_SSL_Crl"                json:"Master_SSL_Crl"`
	MasterSSLCrlpath           string        `gorm:"column:Master_SSL_Crlpath"            json:"Master_SSL_Crlpath"`
	RetrievedGtidSet           string        `gorm:"column:Retrieved_Gtid_Set"            json:"Retrieved_Gtid_Set"`
	ExecutedGtidSet            string        `gorm:"column:Executed_Gtid_Set"             json:"Executed_Gtid_Set"`
	AutoPosition               string        `gorm:"column:Auto_Position"                 json:"Auto_Position"`
	ReplicateWildParallelTable string        `gorm:"column:Replicate_Wild_Parallel_Table" json:"Replicate_Wild_Parallel_Table"`

	// MySQL 8.4 replica-named columns; normalized back into the legacy fields by Normalize.
	SourceHost          string        `gorm:"column:Source_Host"           json:"-"`
	SourcePort          int           `gorm:"column:Source_Port"           json:"-"`
	SourceLogFile       string        `gorm:"column:Source_Log_File"       json:"-"`
	ReadSourceLogPos    uint64        `gorm:"column:Read_Source_Log_Pos"   json:"-"`
	RelaySourceLogFile  string        `gorm:"column:Relay_Source_Log_File" json:"-"`
	ExecSourceLogPos    uint64        `gorm:"column:Exec_Source_Log_Pos"   json:"-"`
	ReplicaIORunning    string        `gorm:"column:Replica_IO_Running"    json:"-"`
	ReplicaSQLRunning   string        `gorm:"column:Replica_SQL_Running"   json:"-"`
	SecondsBehindSource sql.NullInt64 `gorm:"column:Seconds_Behind_Source" json:"-"`
	SourceServerID      uint64        `gorm:"column:Source_Server_Id"      json:"-"`
}

// Normalize copies MySQL 8.4 replica-named columns back into the legacy fields;
// legacy values win, NULL/negative replica values never overwrite.
func (s *ReplicationStatus) Normalize() {
	if s.MasterHost == "" && s.SourceHost != "" {
		s.MasterHost = s.SourceHost
	}
	if s.MasterPort == 0 && s.SourcePort != 0 {
		s.MasterPort = s.SourcePort
	}
	if s.MasterLogFile == "" && s.SourceLogFile != "" {
		s.MasterLogFile = s.SourceLogFile
	}
	if s.ReadMasterLogPos == 0 && s.ReadSourceLogPos != 0 {
		s.ReadMasterLogPos = s.ReadSourceLogPos
	}
	if s.RelayMasterLogFile == "" && s.RelaySourceLogFile != "" {
		s.RelayMasterLogFile = s.RelaySourceLogFile
	}
	if s.ExecMasterLogPos == 0 && s.ExecSourceLogPos != 0 {
		s.ExecMasterLogPos = s.ExecSourceLogPos
	}
	if s.SlaveIORunning == "" && s.ReplicaIORunning != "" {
		s.SlaveIORunning = s.ReplicaIORunning
	}
	if s.SlaveSQLRunning == "" && s.ReplicaSQLRunning != "" {
		s.SlaveSQLRunning = s.ReplicaSQLRunning
	}
	if !s.SecondsBehindMaster.Valid && s.SecondsBehindSource.Valid && s.SecondsBehindSource.Int64 >= 0 {
		s.SecondsBehindMaster = s.SecondsBehindSource
	}
	if s.MasterServerID == 0 && s.SourceServerID != 0 {
		s.MasterServerID = s.SourceServerID
	}
}

// MasterStatusInfo represents MySQL master status information.
type MasterStatusInfo struct {
	File            string `gorm:"column:File"              json:"File"`
	Position        uint64 `gorm:"column:Position"          json:"Position"`
	BinlogDoDB      string `gorm:"column:Binlog_Do_DB"      json:"Binlog_Do_DB"`
	BinlogIgnoreDB  string `gorm:"column:Binlog_Ignore_DB"  json:"Binlog_Ignore_DB"`
	ExecutedGtidSet string `gorm:"column:Executed_Gtid_Set" json:"Executed_Gtid_Set"`
}

// UseReplicaNamingByVersion reports whether a server version string requires the MySQL 8.4
// replica statement naming (SHOW REPLICA STATUS etc.). MariaDB-family servers never do.
func UseReplicaNamingByVersion(version string) bool {
	if strings.Contains(strings.ToLower(version), "mariadb") {
		return false
	}
	return cmutil.MySQLVersionCompare(version, mysql84Version) >= 0
}

// ReplStatements resolves the replication statements for the connected server version (cached).
func (db *GormDB) ReplStatements(ctx context.Context) (*ReplStatements, error) {
	useReplica, err := db.UseReplicaNaming(ctx)
	if err != nil {
		return nil, err
	}
	if useReplica {
		return &ReplStatements{
			ShowSlaveStatus:  "SHOW REPLICA STATUS",
			ShowMasterStatus: "SHOW BINARY LOG STATUS",
			StartSlave:       "START REPLICA",
			StopSlave:        "STOP REPLICA",
			ResetSlaveAll:    "RESET REPLICA ALL",
		}, nil
	}
	return &ReplStatements{
		ShowSlaveStatus:  "SHOW SLAVE STATUS",
		ShowMasterStatus: "SHOW MASTER STATUS",
		StartSlave:       "START SLAVE",
		StopSlave:        "STOP SLAVE",
		ResetSlaveAll:    "RESET SLAVE /*!50516 ALL */",
	}, nil
}

// ChangeReplicationSQL builds a CHANGE MASTER TO statement, or its MySQL 8.4 form
// CHANGE REPLICATION SOURCE TO when useReplica is true. The keyword is chosen up front so
// literal values (password, host, log file) are never rewritten by string replacement.
func ChangeReplicationSQL(useReplica bool, src ReplSource) string {
	stmt, kw := "CHANGE MASTER TO", "MASTER"
	if useReplica {
		stmt, kw = "CHANGE REPLICATION SOURCE TO", "SOURCE"
	}

	var b strings.Builder
	b.WriteString(stmt + " ")
	fmt.Fprintf(&b, "%s_HOST = '%s', %s_PORT = %d", kw, mysqlStringEscaper.Replace(src.Host), kw, src.Port)
	if src.User != "" {
		fmt.Fprintf(&b, ", %s_USER = '%s', %s_PASSWORD = '%s'", kw, mysqlStringEscaper.Replace(src.User),
			kw, mysqlStringEscaper.Replace(src.Password))
	}
	if src.LogFile != "" {
		fmt.Fprintf(&b, ", %s_LOG_FILE = '%s', %s_LOG_POS = %d", kw, mysqlStringEscaper.Replace(src.LogFile),
			kw, src.LogPos)
	}
	if src.AutoPosition != AutoPositionOmit {
		fmt.Fprintf(&b, ", %s_AUTO_POSITION = %d", kw, src.AutoPosition)
	}
	if src.GetPublicKey == GetPublicKeyOn {
		fmt.Fprintf(&b, ", GET_%s_PUBLIC_KEY = 1", kw)
	}
	return b.String()
}

// ChangeReplicationTo executes a change-master statement on db, retrying once with the
// other naming on a naming-related 1064 (a compat layer may pass SHOW/STOP/START through
// yet parse CHANGE with only one naming). It returns the executed statement with the
// secret masked, intended for logging.
func (db *GormDB) ChangeReplicationTo(ctx context.Context, src ReplSource) (string, error) {
	version, err := db.Version(ctx)
	if err != nil {
		return "", err
	}
	useReplica := UseReplicaNamingByVersion(version)

	autoKey := false
	if src.GetPublicKey == GetPublicKeyAuto && useReplica {
		src.GetPublicKey = GetPublicKeyOn
		autoKey = true
	}

	// GORM echoes the full SQL on error, bypassing maskSecret; silence it for these execs.
	tx := db.DBWithContext(ctx).Session(&gorm.Session{Logger: gormlogger.Discard})

	changeSQL := ChangeReplicationSQL(useReplica, src)
	execErr := tx.Exec(changeSQL).Error

	var firstSQL string
	var firstErr error
	if execErr != nil && isReplicationNamingError(execErr) {
		firstSQL, firstErr = changeSQL, execErr
		if autoKey {
			// the 1064 falsified the version evidence; drop the auto-added clause on retry
			src.GetPublicKey = GetPublicKeyAuto
		}
		changeSQL = ChangeReplicationSQL(!useReplica, src)
		logger.Warn("got a syntax error on db(%s:%d), retry with '%s', errmsg: %s",
			db.opts.ip, db.opts.port, maskSecret(changeSQL, src.Password),
			maskSecret(firstErr.Error(), src.Password))
		execErr = tx.Exec(changeSQL).Error
	}

	maskedSQL := maskSecret(changeSQL, src.Password)
	if execErr == nil {
		return maskedSQL, nil
	}
	if firstErr == nil {
		return maskedSQL, gerrors.Newf(gerrors.MysqlFailure,
			"failed to execute '%s' on db(%s:%d), errmsg: %s",
			maskedSQL, db.opts.ip, db.opts.port, maskSecret(execErr.Error(), src.Password))
	}
	return maskedSQL, gerrors.Newf(gerrors.MysqlFailure,
		"failed to execute '%s' on db(%s:%d), errmsg: %s; retried with '%s', errmsg: %s",
		maskSecret(firstSQL, src.Password), db.opts.ip, db.opts.port,
		maskSecret(firstErr.Error(), src.Password),
		maskedSQL, maskSecret(execErr.Error(), src.Password))
}

// isMySQLSyntaxError reports whether err is a MySQL 1064 syntax error. It matches the
// error text instead of errors.As to avoid promoting go-sql-driver to a direct dependency.
func isMySQLSyntaxError(err error) bool {
	return err != nil && strings.Contains(err.Error(), "Error 1064")
}

// isReplicationNamingError reports whether err is a 1064 caused by the wrong statement
// naming; the server echoes MASTER_HOST/SOURCE_HOST in the error text for that case,
// which distinguishes it from other syntax errors (e.g. a malformed literal).
func isReplicationNamingError(err error) bool {
	if !isMySQLSyntaxError(err) {
		return false
	}
	return strings.Contains(err.Error(), "MASTER_HOST") || strings.Contains(err.Error(), "SOURCE_HOST")
}

// maskSecret replaces a non-empty secret in s with <secret> for safe logging; both the raw
// and the MySQL-escaped form are masked.
func maskSecret(s, secret string) string {
	if secret == "" {
		return s
	}
	s = strings.ReplaceAll(s, secret, "<secret>")
	return strings.ReplaceAll(s, mysqlStringEscaper.Replace(secret), "<secret>")
}
