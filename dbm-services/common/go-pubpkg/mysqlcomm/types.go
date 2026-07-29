/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlcomm

import "database/sql"

// SlaveStatus slave status 输出
type SlaveStatus struct {
	SlaveIoState             string `gorm:"column:Slave_IO_State" json:"Slave_IO_State" db:"Slave_IO_State"`
	MasterHost               string `gorm:"column:Master_Host" json:"Master_Host" db:"Master_Host"`
	MasterUser               string `gorm:"column:Master_User" json:"Master_User" db:"Master_User"`
	MasterPort               int    `gorm:"column:Master_Port" json:"Master_Port" db:"Master_Port"`
	ConnectRetry             int    `gorm:"column:Connect_Retry" json:"Connect_Retry" db:"Master_Port"`
	MasterLogFile            string `gorm:"column:Master_Log_File" json:"Master_Log_File" db:"Master_Log_File"`
	ReadMasterLogPos         uint64 `gorm:"column:Read_Master_Log_Pos" json:"Read_Master_Log_Pos" db:"Read_Master_Log_Pos"`
	RelayLogFile             string `gorm:"column:Relay_Log_File" json:"Relay_Log_File" db:"Relay_Log_File"`
	RelayLogPos              uint64 `gorm:"column:Relay_Log_Pos" json:"Relay_Log_Pos" db:"Relay_Log_Pos"`
	RelayMasterLogFile       string `gorm:"column:Relay_Master_Log_File" json:"Relay_Master_Log_File" db:"Relay_Master_Log_File"`
	SlaveIoRunning           string `gorm:"column:Slave_IO_Running" json:"Slave_IO_Running" db:"Slave_IO_Running"`
	SlaveSqlRunning          string `gorm:"column:Slave_SQL_Running" json:"Slave_SQL_Running" db:"Slave_SQL_Running"`
	ReplicateDoDb            string `gorm:"column:Replicate_Do_DB" json:"Replicate_Do_DB" db:"Replicate_Do_DB"`
	ReplicateIgnoreDb        string `gorm:"column:Replicate_Ignore_DB" json:"Replicate_Ignore_DB" db:"Replicate_Ignore_DB"`
	ReplicateDoTable         string `gorm:"column:Replicate_Do_Table" json:"Replicate_Do_Table" db:"Replicate_Do_Table"`
	ReplicateIgnoreTable     string `gorm:"column:Replicate_Ignore_Table" json:"Replicate_Ignore_Table" db:"Replicate_Ignore_Table"`
	ReplicateWildDoTable     string `gorm:"column:Replicate_Wild_Do_Table" json:"Replicate_Wild_Do_Table" db:"Replicate_Wild_Do_Table"`
	ReplicateWildIgnoreTable string `gorm:"column:Replicate_Wild_Ignore_Table" json:"Replicate_Wild_Ignore_Table" db:"Replicate_Wild_Ignore_Table"`
	LastErrno                int    `gorm:"column:Last_Errno" json:"Last_Errno" db:"Last_Errno"`
	LastError                string `gorm:"column:Last_Error" json:"Last_Error" db:"Last_Error"`
	SkipCounter              int    `gorm:"column:Skip_Counter" json:"Skip_Counter" db:"Skip_Counter"`
	ExecMasterLogPos         uint64 `gorm:"column:Exec_Master_Log_Pos" json:"Exec_Master_Log_Pos" db:"Exec_Master_Log_Pos"`
	RelayLogSpace            uint64 `gorm:"column:Relay_Log_Space" json:"Relay_Log_Space" db:"Relay_Log_Space"`
	UntilCondition           string `gorm:"column:Until_Condition" json:"Until_Condition" db:"Until_Condition"`
	UntilLogFile             string `gorm:"column:Until_Log_File" json:"Until_Log_File" db:"Until_Log_File"`
	UntilLogPos              uint64 `gorm:"column:Until_Log_Pos" json:"Until_Log_Pos" db:"Until_Log_Pos"`
	MasterSslAllowed         string `gorm:"column:Master_SSL_Allowed" json:"Master_SSL_Allowed" db:"Master_SSL_Allowed"`
	MasterSslCaFile          string `gorm:"column:Master_SSL_CA_File" json:"Master_SSL_CA_File" db:"Master_SSL_CA_File"`
	MasterSslCaPath          string `gorm:"column:Master_SSL_CA_Path" json:"Master_SSL_CA_Path" db:"Master_SSL_CA_Path"`
	MasterSslCert            string `gorm:"column:Master_SSL_Cert" json:"Master_SSL_Cert" db:"Master_SSL_Cert"`
	MasterSslCipher          string `gorm:"column:Master_SSL_Cipher" json:"Master_SSL_Cipher" db:"Master_SSL_Cipher"`
	MasterSslKey             string `gorm:"column:Master_SSL_Key" json:"Master_SSL_Key" db:"Master_SSL_Key"`
	// SecondsBehindMaster 可能为 NULL
	SecondsBehindMaster       sql.NullInt64 `gorm:"column:Seconds_Behind_Master" json:"Seconds_Behind_Master" db:"Seconds_Behind_Master"`
	MasterSslVerifyServerCert string        `gorm:"column:Master_SSL_Verify_Server_Cert" json:"Master_SSL_Verify_Server_Cert" db:"Master_SSL_Verify_Server_Cert"`
	LastIoErrno               int           `gorm:"column:Last_IO_Errno" json:"Last_IO_Errno" db:"Last_IO_Errno"`
	LastIoError               string        `gorm:"column:Last_IO_Error" json:"Last_IO_Error" db:"Last_IO_Error"`
	LastSqlErrno              int           `gorm:"column:Last_SQL_Errno" json:"Last_SQL_Errno" db:"Last_SQL_Errno"`
	LastSqlError              string        `gorm:"column:Last_SQL_Error" json:"Last_SQL_Error" db:"Last_SQL_Error"`
	ReplicateIgnoreServerIds  string        `gorm:"column:Replicate_Ignore_Server_Ids" json:"Replicate_Ignore_Server_Ids" db:"Replicate_Ignore_Server_Ids"`
	MasterServerId            uint64        `gorm:"column:Master_Server_Id" json:"Master_Server_Id" db:"Master_Server_Id"`
	MasterUuid                string        `gorm:"column:Master_UUID" json:"Master_UUID" db:"Master_UUID"`
	MasterInfoFile            string        `gorm:"column:Master_Info_File" json:"Master_Info_File" db:"Master_Info_File"`
	SqlDelay                  uint64        `gorm:"column:SQL_Delay" json:"SQL_Delay" db:"SQL_Delay"`
	// SqlRemainingDelay 可能为 NULL
	SqlRemainingDelay          sql.NullInt64 `gorm:"column:SQL_Remaining_Delay" json:"SQL_Remaining_Delay" db:"SQL_Remaining_Delay"`
	SlaveSqlRunningState       string        `gorm:"column:Slave_SQL_Running_State" json:"Slave_SQL_Running_State" db:"Slave_SQL_Running_State"`
	MasterRetryCount           int           `gorm:"column:Master_Retry_Count" json:"Master_Retry_Count" db:"Master_Retry_Count"`
	MasterBind                 string        `gorm:"column:Master_Bind" json:"Master_Bind" db:"Master_Bind"`
	LastIoErrorTimestamp       string        `gorm:"column:Last_IO_Error_Timestamp" json:"Last_IO_Error_Timestamp" db:"Last_IO_Error_Timestamp"`
	LastSqlErrorTimestamp      string        `gorm:"column:Last_SQL_Error_Timestamp" json:"Last_SQL_Error_Timestamp" db:"Last_SQL_Error_Timestamp"`
	MasterSslCrl               string        `gorm:"column:Master_SSL_Crl" json:"Master_SSL_Crl" db:"Master_SSL_Crl"`
	MasterSslCrlpath           string        `gorm:"column:Master_SSL_Crlpath" json:"Master_SSL_Crlpath" db:"Master_SSL_Crlpath"`
	RetrievedGtidSet           string        `gorm:"column:Retrieved_Gtid_Set" json:"Retrieved_Gtid_Set" db:"Retrieved_Gtid_Set"`
	ExecutedGtidSet            string        `gorm:"column:Executed_Gtid_Set" json:"Executed_Gtid_Set" db:"Executed_Gtid_Set"`
	AutoPosition               int           `gorm:"column:Auto_Position" json:"Auto_Position" db:"Auto_Position"`
	ReplicateWildParallelTable string        `gorm:"column:Replicate_Wild_Parallel_Table" json:"Replicate_Wild_Parallel_Table" db:"Replicate_Wild_Parallel_Table"`

	SlaveStatusReplica
}

type SlaveStatusReplica struct {
	ReplicaIoState     string `gorm:"column:Replica_IO_State" json:"Replica_IO_State" db:"Replica_IO_State"`
	SourceHost         string `gorm:"column:Source_Host" json:"Source_Host" db:"Source_Host"`
	SourceUser         string `gorm:"column:Source_User" json:"Source_User" db:"Source_User"`
	SourcePort         int    `gorm:"column:Source_Port" json:"Source_Port" db:"Source_Port"`
	ConnectRetry       int    `gorm:"column:Connect_Retry" json:"Connect_Retry" db:"Source_Port"`
	SourceLogFile      string `gorm:"column:Source_Log_File" json:"Source_Log_File" db:"Source_Log_File"`
	ReadSourceLogPos   uint64 `gorm:"column:Read_Source_Log_Pos" json:"Read_Source_Log_Pos" db:"Read_Source_Log_Pos"`
	RelaySourceLogFile string `gorm:"column:Relay_Source_Log_File" json:"Relay_Source_Log_File" db:"Relay_Source_Log_File"`
	ReplicaIoRunning   string `gorm:"column:Replica_IO_Running" json:"Replica_IO_Running" db:"Replica_IO_Running"`
	ReplicaSqlRunning  string `gorm:"column:Replica_SQL_Running" json:"Replica_SQL_Running" db:"Replica_SQL_Running"`
	ExecSourceLogPos   uint64 `gorm:"column:Exec_Source_Log_Pos" json:"Exec_Source_Log_Pos" db:"Exec_Source_Log_Pos"`
	// SecondsBehindSource 可能为 NULL
	SecondsBehindSource    sql.NullInt64 `gorm:"column:Seconds_Behind_Source" json:"Seconds_Behind_Source" db:"Seconds_Behind_Source"`
	SourceServerId         uint64        `gorm:"column:Source_Server_Id" json:"Source_Server_Id" db:"Source_Server_Id"`
	SourceUuid             string        `gorm:"column:Source_UUID" json:"Source_UUID" db:"Source_UUID"`
	SourceInfoFile         string        `gorm:"column:Source_Info_File" json:"Source_Info_File" db:"Source_Info_File"`
	ReplicaSqlRunningState string        `gorm:"column:Replica_SQL_Running_State" json:"Replica_SQL_Running_State" db:"Replica_SQL_Running_State"`
	SourceRetryCount       int           `gorm:"column:Source_Retry_Count" json:"Source_Retry_Count" db:"Source_Retry_Count"`
	SourceBind             string        `gorm:"column:Source_Bind" json:"Source_Bind" db:"Source_Bind"`

	SourceSslAllowed          string `gorm:"column:Source_SSL_Allowed" json:"Source_SSL_Allowed" db:"Source_SSL_Allowed"`
	SourceSslCaFile           string `gorm:"column:Source_SSL_CA_File" json:"Source_SSL_CA_File" db:"Source_SSL_CA_File"`
	SourceSslCaPath           string `gorm:"column:Source_SSL_CA_Path" json:"Source_SSL_CA_Path" db:"Source_SSL_CA_Path"`
	SourceSslCert             string `gorm:"column:Source_SSL_Cert" json:"Source_SSL_Cert" db:"Source_SSL_Cert"`
	SourceSslCipher           string `gorm:"column:Source_SSL_Cipher" json:"Source_SSL_Cipher" db:"Source_SSL_Cipher"`
	SourceSslKey              string `gorm:"column:Source_SSL_Key" json:"Source_SSL_Key" db:"Source_SSL_Key"`
	SourceSslVerifyServerCert string `gorm:"column:Source_SSL_Verify_Server_Cert" json:"Source_SSL_Verify_Server_Cert" db:"Source_SSL_Verify_Server_Cert"`
	SourceSslCrl              string `gorm:"column:Source_SSL_Crl" json:"Source_SSL_Crl" db:"Source_SSL_Crl"`
	SourceSslCrlpath          string `gorm:"column:Source_SSL_Crlpath" json:"Source_SSL_Crlpath" db:"Source_SSL_Crlpath"`
}

func (s *SlaveStatus) ReplicaToSlave() {
	if s.MasterHost == "" && s.SourceHost != "" {
		s.SlaveIoState = s.ReplicaIoState
		s.MasterHost = s.SourceHost
		s.MasterUser = s.SourceUser
		s.MasterPort = s.SourcePort
		s.MasterLogFile = s.SourceLogFile
		s.ReadMasterLogPos = s.ReadSourceLogPos
		s.RelayMasterLogFile = s.RelaySourceLogFile
		s.SlaveIoRunning = s.ReplicaIoRunning
		s.SlaveSqlRunning = s.ReplicaSqlRunning
		s.ExecMasterLogPos = s.ExecSourceLogPos
		s.SecondsBehindMaster = s.SecondsBehindSource
		s.MasterSslVerifyServerCert = s.SourceSslVerifyServerCert
		s.MasterServerId = s.SourceServerId
		s.MasterUuid = s.SourceUuid
		s.MasterInfoFile = s.SourceInfoFile
		s.SlaveSqlRunningState = s.ReplicaSqlRunningState
		s.MasterRetryCount = s.SourceRetryCount
		s.MasterBind = s.SourceBind
		/*
			s.MasterSslAllowed = s.SourceSslAllowed
			s.MasterSslCaFile = s.SourceSslCaFile
			s.MasterSslCaPath = s.SourceSslCaPath
			s.MasterSslCert = s.SourceSslCert
			s.MasterSslCipher = s.SourceSslCipher
			s.MasterSslKey = s.SourceSslKey
			s.MasterSslCrl = s.SourceSslCrl
			s.MasterSslCrlpath = s.SourceSslCrlpath
		*/
	}
}
