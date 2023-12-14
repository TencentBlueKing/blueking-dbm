// Package native TODO
/*
 * @Description: database  operation sets
 */
package native

import (
	"database/sql"
	"strings"
)

const (
	// SLAVE_IO_RUNING_OK TODO
	SLAVE_IO_RUNING_OK = "YES"
	// SLAVE_SQL_RUNING_OK TODO
	SLAVE_SQL_RUNING_OK = "YES"
)

// NotRowFound TODO
const NotRowFound = "not row found"
const (
	// INFODBA_SCHEMA TODO
	INFODBA_SCHEMA = "infodba_schema"
	// TEST_DB TODO
	TEST_DB = "test"
	// INFO_SCHEMA TODO
	INFO_SCHEMA = "information_schema"
	// PERF_SCHEMA TODO
	PERF_SCHEMA = "performance_schema"
)

var dbSysUsers = []string{"event_scheduler", "system user"}

// DBSys TODO
var DBSys = []string{"mysql", "sys", INFO_SCHEMA, PERF_SCHEMA, INFODBA_SCHEMA, TEST_DB}

// DBUserAdmin TODO
const DBUserAdmin = "ADMIN"

// ShowTableStatusResp TODO
type ShowTableStatusResp struct {
	Name          string `db:"Name"`
	Engine        string `db:"Engine"`
	Version       int    `db:"Version"`
	RowFormat     string `db:"Row_format"`
	Rows          int    `db:"Rows"`
	AvgRowLength  int    `db:"Avg_row_length"`
	DataLength    int    `db:"Data_length"`
	MaxDataLength int    `db:"Max_data_length"`
	IndexLength   int    `db:"Index_length"`
	DataFree      int    `db:"Data_free"`
	Collation     string `db:"Collation"`
	// Auto_increment
	// more ...
}

// ShowSlaveStatusResp TODO
type ShowSlaveStatusResp struct {
	MasterHost          string        `json:"Master_Host" db:"Master_Host"`
	MasterPort          int           `json:"Master_Port" db:"Master_Port"`
	MasterUser          string        `json:"Master_User" db:"Master_User"`
	MasterLogFile       string        `json:"Master_Log_File" db:"Master_Log_File"`
	ReadMasterLogPos    int           `json:"Read_Master_Log_Pos" db:"Read_Master_Log_Pos"`
	RelayMasterLogFile  string        `json:"Relay_Master_Log_File" db:"Relay_Master_Log_File"`
	ExecMasterLogPos    int           `json:"Exec_Master_Log_Pos" db:"Exec_Master_Log_Pos"`
	SlaveIORunning      string        `json:"Slave_IO_Running" db:"Slave_IO_Running"`
	SlaveSQLRunning     string        `json:"Slave_SQL_Running" db:"Slave_SQL_Running"`
	SecondsBehindMaster sql.NullInt64 `json:"Seconds_Behind_Master" db:"Seconds_Behind_Master"`
}

// ReplSyncIsOk TODO
// 判断主从同步是否 Ok
func (s ShowSlaveStatusResp) ReplSyncIsOk() bool {
	var empty ShowSlaveStatusResp
	if s == empty {
		return false
	}
	ioRunningIsOk := strings.EqualFold(strings.ToUpper(s.SlaveIORunning), strings.ToUpper(SLAVE_IO_RUNING_OK))
	sqlRunningIsOk := strings.EqualFold(strings.ToUpper(s.SlaveSQLRunning), strings.ToUpper(SLAVE_SQL_RUNING_OK))
	return ioRunningIsOk && sqlRunningIsOk
}

// MasterStatusResp TODO
type MasterStatusResp struct {
	File            string `json:"bin_file" db:"File"`
	Position        int    `json:"bin_position" db:"Position"`
	BinlogDoDB      string `json:"binlog_db_db" db:"Binlog_Do_DB"`
	BinlogIgnoreDB  string `json:"binlog_ignore_db" db:"Binlog_Ignore_DB"`
	ExecutedGtidSet string `json:"executed_gtid_set" db:"Executed_Gtid_Set"`
}

// SlaveHostResp TODO
type SlaveHostResp struct {
	ServerID  string `json:"server_id" db:"Server_id"`
	Host      string `json:"host" db:"Host"`
	Port      int    `json:"port" db:"Port"`
	MasterID  string `json:"master_id" db:"Master_id"`
	SlaveUUID string `json:"slave_uuid" db:"Slave_UUID"`
}

// ShowProcesslistResp TODO
type ShowProcesslistResp struct {
	ID   uint64         `json:"id" db:"Id"`
	User string         `json:"user" db:"User"`
	Host sql.NullString `json:"host" db:"Host"`
	DB   sql.NullString `json:"db" db:"db"`
	// Command sql.NullString `json:"command" db:"Command"`
	Time  int            `json:"time" db:"Time"`
	State sql.NullString `json:"state" db:"State"`
	Info  sql.NullString `json:"info" db:"Info"`
}

// SelectProcessListResp TODO
type SelectProcessListResp struct {
	ID           uint64         `json:"ID" db:"ID"`
	User         string         `json:"USER" db:"USER"`
	Host         string         `json:"HOST" db:"HOST"`
	DB           sql.NullString `json:"DB" db:"DB"`
	Command      string         `json:"COMMAND" db:"COMMAND"`
	Time         string         `json:"TIME" db:"TIME"`
	State        sql.NullString `json:"STATE" db:"STATE"`
	Info         sql.NullString `json:"INFO" db:"INFO"`
	TimeMs       int64          `json:"TIME_MS" db:"TIME_MS"`
	RowsSent     uint64         `json:"ROWS_SENT" db:"ROWS_SENT"`
	RowsExamined uint64         `json:"ROWS_EXAMINED" db:"ROWS_EXAMINED"`
	RowsRead     uint64         `json:"ROWS_READ" db:"ROWS_READ"`
	OSThreadID   uint64         `json:"OS_THREAD_ID" db:"OS_THREAD_ID"`
}

// ProxyAdminBackend TODO
// SELECT * FROM backends
type ProxyAdminBackend struct {
	BackendNdx       int    `json:"backend_ndx"`
	Address          string `json:"address"`
	State            string `json:"state"`
	Type             string `json:"type"`
	Uuid             string `json:"uuid"`
	ConnectedClients int    `json:"connected_clients"`
}

// ShowOpenTablesResp TODO
type ShowOpenTablesResp struct {
	Database string `db:"Database"`
	Table    string `db:"Table"`
	In_use   int    `db:"In_use"`
}

// MySQLGlobalVariableItem TODO
type MySQLGlobalVariableItem struct {
	VariableName string `db:"Variable_name"`
	Value        string `db:"Value"`
}

// ShowEnginesResp TODO
type ShowEnginesResp struct {
	Engine  string `db:"Engine"`
	Support string `db:"Support"`
	// ... complete
}

// UserHosts TODO
type UserHosts struct {
	Host string `db:"Host"`
	User string `db:"User"`
}

// Warning show warnings respone
type Warning struct {
	Level   string `db:"Level"`
	Code    int    `db:"Code"`
	Message string `db:"Message"`
}
