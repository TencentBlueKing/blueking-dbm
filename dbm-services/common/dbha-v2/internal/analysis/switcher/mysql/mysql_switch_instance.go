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

package mysql

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// TODO: remove those variables and get them dynamically
const (
	DefaultIgnoreCheckSum     bool = false
	DefaultIgnoreSlaveDelay   bool = false
	AllowedMaxChecksumFailCnt int  = 2
	AllowedMaxSlaveDelay      int  = 600
	AllowedMaxTimeDelay       int  = 300
	AllowSlowBytes            int  = 0

	DefaultMySQLProtocol string = "tcp"
)

const (
	// CheckSumSQL checksum number
	CheckSumSQL = "SELECT COUNT(DISTINCT `db`, tbl) AS total_count " +
		"FROM (" +
		"SELECT `db`, tbl " +
		"FROM infodba_schema.checksum " +
		"WHERE ts > DATE_SUB(NOW(), INTERVAL 7 DAY) " +
		"UNION " +
		"SELECT `db`, tbl " +
		"FROM infodba_schema.checksum_history " +
		"WHERE ts > DATE_SUB(NOW(), INTERVAL 7 DAY)" +
		") AS combined_results"

	// CheckSumFailSQL inconsistent checksum number
	CheckSumFailSQL = "SELECT COUNT(DISTINCT `db`, tbl, chunk) AS total_count " +
		"FROM infodba_schema.checksum " +
		"WHERE (this_crc <> master_crc OR this_cnt <> master_cnt) AND ts > DATE_SUB(NOW(), INTERVAL 7 DAY) " +
		"UNION " +
		"SELECT COUNT(DISTINCT `db`, tbl, chunk) AS total_count " +
		"FROM infodba_schema.checksum_history " +
		"WHERE (this_crc <> master_crc OR this_cnt <> master_cnt) AND ts > DATE_SUB(NOW(), INTERVAL 7 DAY)"

	// CheckDelaySQL master and slave's time delay
	CheckDelaySQL = `
		SELECT unix_timestamp(now())-unix_timestamp(master_time) as time_delay, delay_sec as slave_delay 
		FROM infodba_schema.master_slave_heartbeat 
		WHERE master_server_id = ? and slave_server_id != master_server_id
	`
)

// MySQLVariableResult represents MySQL variable result
type MySQLVariableResult struct {
	VariableName string `gorm:"column:Variable_name"`
	Value        string `gorm:"column:Value"`
}

// SlaveStatusInfo represents MySQL slave status information
type SlaveStatusInfo struct {
	SlaveIOState               string `gorm:"column:Slave_IO_State"                json:"Slave_IO_State"`
	MasterHost                 string `gorm:"column:Master_Host"                   json:"Master_Host"`
	MasterUser                 string `gorm:"column:Master_User"                   json:"Master_User"`
	MasterPort                 int    `gorm:"column:Master_Port"                   json:"Master_Port"`
	ConnectRetry               int    `gorm:"column:Connect_Retry"                 json:"Connect_Retry"`
	MasterLogFile              string `gorm:"column:Master_Log_File"               json:"Master_Log_File"`
	ReadMasterLogPos           uint64 `gorm:"column:Read_Master_Log_Pos"           json:"Read_Master_Log_Pos"`
	RelayLogFile               string `gorm:"column:Relay_Log_File"                json:"Relay_Log_File"`
	RelayLogPos                uint64 `gorm:"column:Relay_Log_Pos"                 json:"Relay_Log_Pos"`
	RelayMasterLogFile         string `gorm:"column:Relay_Master_Log_File"         json:"Relay_Master_Log_File"`
	SlaveIORunning             string `gorm:"column:Slave_IO_Running"              json:"Slave_IO_Running"`
	SlaveSQLRunning            string `gorm:"column:Slave_SQL_Running"             json:"Slave_SQL_Running"`
	ReplicateDoDB              string `gorm:"column:Replicate_Do_DB"               json:"Replicate_Do_DB"`
	ReplicateIgnoreDB          string `gorm:"column:Replicate_Ignore_DB"           json:"Replicate_Ignore_DB"`
	ReplicateDoTable           string `gorm:"column:Replicate_Do_Table"            json:"Replicate_Do_Table"`
	ReplicateIgnoreTable       string `gorm:"column:Replicate_Ignore_Table"        json:"Replicate_Ignore_Table"`
	ReplicateWildDoTable       string `gorm:"column:Replicate_Wild_Do_Table"       json:"Replicate_Wild_Do_Table"`
	ReplicateWildIgnoreTable   string `gorm:"column:Replicate_Wild_Ignore_Table"   json:"Replicate_Wild_Ignore_Table"`
	LastErrno                  int    `gorm:"column:Last_Errno"                    json:"Last_Errno"`
	LastError                  string `gorm:"column:Last_Error"                    json:"Last_Error"`
	SkipCounter                int    `gorm:"column:Skip_Counter"                  json:"Skip_Counter"`
	ExecMasterLogPos           uint64 `gorm:"column:Exec_Master_Log_Pos"           json:"Exec_Master_Log_Pos"`
	RelayLogSpace              uint64 `gorm:"column:Relay_Log_Space"               json:"Relay_Log_Space"`
	UntilCondition             string `gorm:"column:Until_Condition"               json:"Until_Condition"`
	UntilLogFile               string `gorm:"column:Until_Log_File"                json:"Until_Log_File"`
	UntilLogPos                uint64 `gorm:"column:Until_Log_Pos"                 json:"Until_Log_Pos"`
	MasterSSLAllowed           string `gorm:"column:Master_SSL_Allowed"            json:"Master_SSL_Allowed"`
	MasterSSLCAFile            string `gorm:"column:Master_SSL_CA_File"            json:"Master_SSL_CA_File"`
	MasterSSLCAPath            string `gorm:"column:Master_SSL_CA_Path"            json:"Master_SSL_CA_Path"`
	MasterSSLCert              string `gorm:"column:Master_SSL_Cert"               json:"Master_SSL_Cert"`
	MasterSSLCipher            string `gorm:"column:Master_SSL_Cipher"             json:"Master_SSL_Cipher"`
	MasterSSLKey               string `gorm:"column:Master_SSL_Key"                json:"Master_SSL_Key"`
	SecondsBehindMaster        int    `gorm:"column:Seconds_Behind_Master"         json:"Seconds_Behind_Master"`
	MasterSSLVerifyServerCert  string `gorm:"column:Master_SSL_Verify_Server_Cert" json:"Master_SSL_Verify_Server_Cert"`
	LastIOErrno                int    `gorm:"column:Last_IO_Errno"                 json:"Last_IO_Errno"`
	LastIOError                string `gorm:"column:Last_IO_Error"                 json:"Last_IO_Error"`
	LastSQLErrno               int    `gorm:"column:Last_SQL_Errno"                json:"Last_SQL_Errno"`
	LastSQLError               string `gorm:"column:Last_SQL_Error"                json:"Last_SQL_Error"`
	ReplicateIgnoreServerIDs   string `gorm:"column:Replicate_Ignore_Server_Ids"   json:"Replicate_Ignore_Server_Ids"`
	MasterServerID             uint64 `gorm:"column:Master_Server_Id"              json:"Master_Server_Id"`
	MasterUUID                 string `gorm:"column:Master_UUID"                   json:"Master_UUID"`
	MasterInfoFile             string `gorm:"column:Master_Info_File"              json:"Master_Info_File"`
	SqlDelay                   uint64 `gorm:"column:SQL_Delay"                     json:"SQL_Delay"`
	SqlRemainingDelay          string `gorm:"column:SQL_Remaining_Delay"           json:"SQL_Remaining_Delay"`
	SlaveSqlRunningState       string `gorm:"column:Slave_SQL_Running_State"       json:"Slave_SQL_Running_State"`
	MasterRetryCount           int    `gorm:"column:Master_Retry_Count"            json:"Master_Retry_Count"`
	MasterBind                 string `gorm:"column:Master_Bind"                   json:"Master_Bind"`
	LastIoErrorTimestamp       string `gorm:"column:Last_IO_Error_Timestamp"       json:"Last_IO_Error_Timestamp"`
	LastSqlErrorTimestamp      string `gorm:"column:Last_SQL_Error_Timestamp"      json:"Last_SQL_Error_Timestamp"`
	MasterSSLCrl               string `gorm:"column:Master_SSL_Crl"                json:"Master_SSL_Crl"`
	MasterSSLCrlpath           string `gorm:"column:Master_SSL_Crlpath"            json:"Master_SSL_Crlpath"`
	RetrievedGtidSet           string `gorm:"column:Retrieved_Gtid_Set"            json:"Retrieved_Gtid_Set"`
	ExecutedGtidSet            string `gorm:"column:Executed_Gtid_Set"             json:"Executed_Gtid_Set"`
	AutoPosition               string `gorm:"column:Auto_Position"                 json:"Auto_Position"`
	ReplicateWildParallelTable string `gorm:"column:Replicate_Wild_Parallel_Table" json:"Replicate_Wild_Parallel_Table"`
}

// SlaveStatusPartialInfo contains partial slave status information for switching
type SlaveStatusPartialInfo struct {
	MasterHost              string
	MasterPort              int
	MasterLogFileIndex      int
	RelayMasterLogFileIndex int
	ReadMasterLogPos        uint64
	ExecMasterLogPos        uint64
}

// CalSlowBytes calculates slow bytes for slave replication
func CalSlowBytes(slaveStatus *SlaveStatusPartialInfo, maxBinlogSize uint64) uint64 {
	return uint64(slaveStatus.MasterLogFileIndex-slaveStatus.RelayMasterLogFileIndex)*(maxBinlogSize/1024) -
		(slaveStatus.ExecMasterLogPos / 1024) + (slaveStatus.ReadMasterLogPos / 1024)
}

// SlaveTimeDelayInfo contains slave replication delay information
type SlaveTimeDelayInfo struct {
	SlaveIODelay        float64 `gorm:"column:slave_delay"`
	SlaveHeartbeatDelay float64 `gorm:"column:time_delay"`
}

// MasterStatusInfo represents MySQL master status information
type MasterStatusInfo struct {
	File            string
	Position        uint64
	BinlogDoDB      string
	BinlogIgnoreDB  string
	ExecutedGtidSet string
}

// ProxyBackendInfo contains proxy backend connection information
type ProxyBackendInfo struct {
	BackendNdx       int    `db:"backend_ndx"`
	Address          string `db:"address"`
	State            string `db:"state"`
	Type             string `db:"type"`
	UUID             string `db:"uuid"`
	ConnectedClients int    `db:"connected_clients"`
	RefreshTime      int    `db:"refresh_time"`
}

// NewMySQLSwitchInstance creates a new MySQL switch instance based on metadata
func NewMySQLSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	mysqlBaseInstance := MySQLBaseSwitchInstance{
		BaseSwitchInstance: switchcore.BaseSwitchInstance{
			IP:           metadata.IP,
			Port:         metadata.Port,
			Status:       metadata.Status,
			BkCloudID:    metadata.BkCloudID,
			BkIdcCityID:  metadata.BkIdcCityID,
			BkBizID:      metadata.BkBizID,
			Cluster:      metadata.Cluster,
			ClusterID:    metadata.ClusterID,
			ClusterType:  metadata.ClusterType,
			MachineType:  metadata.MachineType,
			InstanceRole: metadata.InstanceRole,
			DbmClient:    &dbm.Client{},
		},
		IsStandBy:        metadata.IsStandBy,
		AdminPort:        metadata.AdminPort,
		BindEntry:        metadata.BindEntry,
		ProxyInstanceSet: metadata.ProxyInstanceSet,
		BinlogDumperSet:  metadata.BinlogDumpers,
	}

	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypeBackend:
		res := &MySQLStorageSwitchInstance{
			MySQLBaseSwitchInstance: mysqlBaseInstance,
		}
		if metadata.InstanceRole == dbm.MySQLStorageMaster {
			res.SetStandbySlave(metadata.Receiver)
		}
		return res, nil

	case haprobe.DbmMetadataMachineTypeProxy:
		res := &MySQLProxySwitchInstance{
			MySQLBaseSwitchInstance: mysqlBaseInstance,
		}
		return res, nil

	default:
		logger.Error("unknown machine type(%s) for MySQL switch instance constructor", metadata.MachineType)
		return nil, gerrors.New(gerrors.InvalidParameter, "Invalid machine type")
	}
}

// MySQLBaseSwitchInstance provides base functionality for MySQL switch operations
type MySQLBaseSwitchInstance struct {
	switchcore.BaseSwitchInstance

	// The following are instance metadata information from DBM

	StandBySlave     *dbm.DbmMetadataSlaveInfo
	IsStandBy        bool
	AdminPort        int
	BindEntry        dbm.DbmMetadataBindEntry
	ProxyInstanceSet []dbm.DbmMetadataProxyInstance
	BinlogDumperSet  []dbm.DbmMetadataBinlogDumper
}

// GetBinlogDumperInfo returns binlog dumper information as string
func (sw *MySQLBaseSwitchInstance) GetBinlogDumperInfo() string {
	dumperInfo := "nil"
	if len(sw.BinlogDumperSet) > 0 {
		var dumperInfos []string
		for _, dumper := range sw.BinlogDumperSet {
			dumperInfos = append(dumperInfos, fmt.Sprintf("%s:%d", dumper.Ip, dumper.Port))
		}
		dumperInfo = fmt.Sprintf("(%s)", strings.Join(dumperInfos, ","))
	}
	return dumperInfo
}

// SetStandbySlave sets the standby slave for master instance
// Only master instances can call this method.
// If no standby slave is found, it uses the first slave in the list.
func (sw *MySQLBaseSwitchInstance) SetStandbySlave(slaves []dbm.DbmMetadataSlaveInfo) {
	if len(slaves) == 0 {
		logger.Warn("no standby slave found from provided slaves for mysql master(%s:%d)", sw.IP, sw.Port)
		sw.StandBySlave = nil
		return
	}

	findIndex := 0
	for i, slave := range slaves {
		if slave.IsStandBy {
			findIndex = i
			break
		}
	}
	sw.StandBySlave = &dbm.DbmMetadataSlaveInfo{}
	*(sw.StandBySlave) = slaves[findIndex]
	logger.Debug("successfully set standby slave for mysql master(%s:%d): %s",
		sw.IP, sw.Port, converter.ToStrIgnoreErr(*(sw.StandBySlave)))
}

// parseMasterLogFileIndex safely parses the numeric index from MasterLogFile format like "binlog.000002"
func parseMasterLogFileIndex(masterLogFile string) (int, error) {
	if !strings.Contains(masterLogFile, ".") {
		return 0, gerrors.Newf(gerrors.Failure, "MasterLogFile does not contain dot separator: %s", masterLogFile)
	}

	parts := strings.Split(masterLogFile, ".")
	if len(parts) < 2 {
		return 0, gerrors.Newf(gerrors.Failure, "MasterLogFile has insufficient parts after splitting: %s", masterLogFile)
	}

	indexStr := parts[1]
	if indexStr == "" {
		return 0, gerrors.Newf(gerrors.Failure, "MasterLogFile index part is empty: %s", masterLogFile)
	}

	index, err := strconv.Atoi(indexStr)
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, "failed to parse MasterLogFile index as integer: %s", indexStr)
	}

	return index, nil
}

// GetSlaveStatusPartialInfo retrieves partial slave status information
func (sw *MySQLBaseSwitchInstance) GetSlaveStatusPartialInfo(slaveDB *hamysql.GormDB) (*SlaveStatusPartialInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave status")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	slaveStatus, err := sw.ShowSlaveStatus(slaveDB)
	if err != nil {
		return nil, err
	}

	ret := &SlaveStatusPartialInfo{}

	if !strings.EqualFold(slaveStatus.SlaveSQLRunning, "Yes") {
		errMsg := fmt.Sprintf("slave node(%s:%d) is abnormal(Slave_SQL_Running:'%s')",
			ip, port, slaveStatus.SlaveSQLRunning)
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	ret.MasterLogFileIndex, err = parseMasterLogFileIndex(slaveStatus.MasterLogFile)
	if err != nil {
		errMsg := fmt.Sprintf("failed to parse the master log file of slave node(%s:%d) (Master_Log_File:'%s'): %s",
			ip, port, slaveStatus.MasterLogFile, err.Error())
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	ret.RelayMasterLogFileIndex, err = parseMasterLogFileIndex(slaveStatus.RelayMasterLogFile)
	if err != nil {
		errMsg := fmt.Sprintf("failed to parse the relay master log file of slave node(%s:%d) "+
			"(Relay_Master_Log_File:'%s'): %s", ip, port, slaveStatus.RelayMasterLogFile, err.Error())
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	ret.MasterHost = slaveStatus.MasterHost
	ret.MasterPort = slaveStatus.MasterPort
	ret.ReadMasterLogPos = slaveStatus.ReadMasterLogPos
	ret.ExecMasterLogPos = slaveStatus.ExecMasterLogPos
	return ret, nil
}

// CheckSqlReplicationDelay checks if slave replication is delayed
func (sw *MySQLBaseSwitchInstance) CheckSqlReplicationDelay(slaveDB *hamysql.GormDB, ignoreDelay bool) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when checking sql replication delay")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	allowSlowKBytes := AllowSlowBytes

	var varQueryRes MySQLVariableResult
	err := slaveDB.DB().Raw("show variables like 'max_binlog_size'").Scan(&varQueryRes).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to query max_binlog_size from (%s:%d): %s", ip, port, err.Error())
	}

	maxBinlogSize, parseErr := strconv.ParseUint(varQueryRes.Value, 10, 64)
	if parseErr != nil {
		return gerrors.Newf(gerrors.Failure, "failed to parse max_binlog_size('%s') from (%s:%d): %s",
			varQueryRes.Value, ip, port, parseErr.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "the max_binlog_size of slave node(%s:%d) is %dMB", ip, port, maxBinlogSize/1024/1024)

	slaveStatus, err := sw.GetSlaveStatusPartialInfo(slaveDB)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to get slave status of slave node(%s:%d): %s", ip, port, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully get slave status of slave node(%s:%d), Relay_Master_Log_File_Index: %d, "+
		"Exec_Master_Log_Pos: %d", ip, port, slaveStatus.RelayMasterLogFileIndex, slaveStatus.ReadMasterLogPos)

	if slaveStatus.MasterHost != sw.IP || slaveStatus.MasterPort != sw.Port {
		errMsg := fmt.Sprintf("the slave's master info(%s:%d) and the broken-down instance(%s:%d) are not equal",
			slaveStatus.MasterHost, slaveStatus.MasterPort, sw.IP, sw.Port)
		return gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	if ignoreDelay {
		sw.ReportLogf(switchlogger.SwitchInfo, "replication delay check was specified to skip for slave node(%s:%d)", ip, port)
		return nil
	}

	realSlowKBytes := CalSlowBytes(slaveStatus, maxBinlogSize)
	if realSlowKBytes <= uint64(allowSlowKBytes) {
		sw.ReportLogf(switchlogger.SwitchInfo, "the slave(%s:%d) was delayed for %dKB, which is less than allowed(%dKB)",
			ip, port, realSlowKBytes, allowSlowKBytes)
		return nil
	}

	loop := 10
	sw.ReportLogf(switchlogger.SwitchInfo, "the slave(%s:%d) was delayed for %dKB, which is larger than allowed(%dKB), "+
		"try to wait in a loop", ip, port, realSlowKBytes, allowSlowKBytes)
	var i int
	for i = 0; i < loop; i++ {
		time.Sleep(3 * time.Second)
		tmpSlaveStatus, err := sw.GetSlaveStatusPartialInfo(slaveDB)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to query slave status from slave(%s:%d): %s",
				ip, port, err.Error())
		}
		realSlowKBytes = CalSlowBytes(tmpSlaveStatus, maxBinlogSize)
		if realSlowKBytes <= uint64(allowSlowKBytes) {
			// TODO: for GTID
			break
		}
		sw.ReportLogf(switchlogger.SwitchInfo, "Loop (%d): the slave(%s:%d) was delayed for %dKB, which is larger than allowed(%dKB)",
			i, ip, port, realSlowKBytes, allowSlowKBytes)
	}
	if i == loop {
		return gerrors.Newf(gerrors.NodeAbnormal, "after waiting for %d loops, the slave(%s:%d) was still delayed too much",
			loop, ip, port)
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "sql replication delay check was passed for slave node(%s:%d)", ip, port)
	return nil
}

// GetSlaveCheckSum returns checksum count and failure count
func (sw *MySQLBaseSwitchInstance) GetSlaveCheckSum(db *hamysql.GormDB) (int, int, error) {
	if db == nil {
		return 0, 0, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave checksum")
	}
	ip := db.Host()
	port := db.Port()

	var (
		checksumCnt, checksumFailCnt int
	)

	err := db.DB().Raw(CheckSumSQL).Scan(&checksumCnt).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to get checksumCnt from node(%s:%d): %s",
			ip, port, err.Error())
	}

	err = db.DB().Raw(CheckSumFailSQL).Scan(&checksumFailCnt).Error
	if err != nil {
		return checksumCnt, 0, gerrors.Newf(gerrors.Failure, "failed to get checksumFailCnt from node(%s:%d): %s",
			ip, port, err.Error())
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully get checksumCnt(%d) and checksumFailCnt(%d) of slave node(%s:%d)",
		checksumCnt, checksumFailCnt, ip, port)
	return checksumCnt, checksumFailCnt, nil
}

// GetSlaveTimeDelay retrieves slave replication delay information
func (sw *MySQLBaseSwitchInstance) GetSlaveTimeDelay(slaveDB *hamysql.GormDB) (int, int, error) {
	if slaveDB == nil {
		return 0, 0, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave time delay")
	}
	ip := slaveDB.Host()
	port := slaveDB.Port()

	slaveStatus := SlaveStatusInfo{}
	err := slaveDB.DB().Raw("show slave status").Scan(&slaveStatus).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to query slave status from node(%s:%d): %s",
			ip, port, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully get Master_Server_Id of slave node(%s:%d): %d",
		ip, port, slaveStatus.MasterServerID)

	delayInfo := SlaveTimeDelayInfo{}
	err = slaveDB.DB().Raw(CheckDelaySQL, slaveStatus.MasterServerID).Scan(&delayInfo).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to query slave time delay info from node(%s:%d): %s",
			ip, port, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully get slave time delay of slave node(%s:%d), SlaveIODelay: %f, "+
		"SlaveHeartbeatDelay: %f", ip, port, delayInfo.SlaveIODelay, delayInfo.SlaveHeartbeatDelay)

	return int(delayInfo.SlaveIODelay), int(delayInfo.SlaveHeartbeatDelay), nil
}

// HasUserCreatedDatabase checks if user-created databases exist
func (sw *MySQLBaseSwitchInstance) HasUserCreatedDatabase(db *hamysql.GormDB) (bool, error) {
	if db == nil {
		return false, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting user-created database")
	}
	ip := db.Host()
	port := db.Port()

	var systemDbs = map[string]bool{
		"mysql":              true,
		"information_schema": true,
		"performance_schema": true,
		"test":               true,
		"infodba_schema":     true,
		"sys":                true,
	}

	var databases []string
	err := db.DB().Raw("show databases").Scan(&databases).Error
	if err != nil {
		return false, gerrors.Newf(gerrors.Failure, "failed to query databases from node(%s:%d): %s",
			ip, port, err.Error())
	}

	for _, database := range databases {
		if _, exists := systemDbs[database]; !exists {
			sw.ReportLogf(switchlogger.SwitchInfo, "found user-created database on node(%s:%d): %s", ip, port, database)
			return true, nil
		}
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "no user-created database found on node(%s:%d)", ip, port)
	return false, nil
}

// CheckSlaveCheckSum checks the slave checksum status
func (sw *MySQLBaseSwitchInstance) CheckSlaveCheckSum(ip string, port int, checksumCnt int, checksumFailCnt int) error {
	if checksumCnt < 1 {
		return gerrors.Newf(gerrors.NodeAbnormal, "no checksum was done on db(%s:%d)", ip, port)
	}

	if checksumFailCnt > AllowedMaxChecksumFailCnt {
		return gerrors.Newf(gerrors.NodeAbnormal, "checksum failure count (%d) of db(%s:%d) "+
			"is larger than allowed (%d)", checksumFailCnt, ip, port, AllowedMaxChecksumFailCnt)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "checksum failure count (%d) of db(%s:%d) is in "+
		"allowed range(%d)", checksumFailCnt, ip, port, AllowedMaxChecksumFailCnt)

	return nil
}

// CheckSlaveTimeDelay checks the slave time delay
func (sw *MySQLBaseSwitchInstance) CheckSlaveTimeDelay(ip string, port int, slaveDelay int, timeDelay int) error {
	if slaveDelay >= AllowedMaxSlaveDelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "IO_Thread delay (%d) on slave(%s:%d) is larger than allowed (%d)",
			slaveDelay, ip, port, AllowedMaxSlaveDelay)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "IO_Thread delay (%d) on slave(%s:%d) is in allowed range(%d)",
		slaveDelay, ip, port, AllowedMaxSlaveDelay)

	if timeDelay >= AllowedMaxTimeDelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "heartbeat delay (%d) on slave(%s:%d) is larger than allowed (%d)",
			timeDelay, ip, port, AllowedMaxTimeDelay)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "heartbeat delay (%d) on slave(%s:%d) is in allowed range(%d)",
		timeDelay, ip, port, AllowedMaxTimeDelay)

	return nil
}

// CheckSlaveStatus verifies if slave node satisfies switching conditions
func (sw *MySQLBaseSwitchInstance) CheckSlaveStatus() error {
	sw.ReportLogf(switchlogger.SwitchInfo, "Start to check slave(%s:%d) status for current mysql master",
		sw.StandBySlave.Ip, sw.StandBySlave.Port)

	// TODO: get the following values dynamically
	ignoreCheckSum := DefaultIgnoreCheckSum
	ignoreSlaveDelay := DefaultIgnoreSlaveDelay
	ip := sw.StandBySlave.Ip
	port := sw.StandBySlave.Port

	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to connect to mysql slave(%s:%d) when checking slave status: %s", ip, port, err.Error())
	}

	defer func() {
		con, _ := slaveDB.DB().DB()
		if err = con.Close(); err != nil {
			sw.ReportLogf(switchlogger.SwitchWarn,
				"failed to close connection of slave DB(%s:%d) after checking slave status: %s", ip, port, err.Error())
		}
	}()

	if err := sw.CheckSqlReplicationDelay(slaveDB, ignoreSlaveDelay); err != nil {
		return err
	}

	var slaveDelay, timeDelay int
	if !ignoreSlaveDelay {
		if slaveDelay, timeDelay, err = sw.GetSlaveTimeDelay(slaveDB); err != nil {
			return err
		}
	}

	var needCheck bool
	if needCheck, err = sw.HasUserCreatedDatabase(slaveDB); err != nil {
		return err
	}

	checksumCnt := 1
	checksumFailCnt := 0
	if !ignoreCheckSum {
		if checksumCnt, checksumFailCnt, err = sw.GetSlaveCheckSum(slaveDB); err != nil {
			return err
		}
	}

	if !needCheck {
		sw.ReportLogf(switchlogger.SwitchInfo, "no user-created database found on slave db(%s:%d), skip checksum check", ip, port)
		return nil
	}

	if sw.Status == dbm.Available { // Is this necessary? Actually the delay check is not skipped
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay = 1, 0, 0, 0
		sw.ReportLogf(switchlogger.SwitchInfo, "slave node(%s:%d) is available, skip the check of delay and checksum", ip, port)
	}

	if err = sw.CheckSlaveCheckSum(ip, port, checksumCnt, checksumFailCnt); err != nil {
		return err
	}

	if err = sw.CheckSlaveTimeDelay(ip, port, slaveDelay, timeDelay); err != nil {
		return err
	}

	return nil
}

// StopSlave stops slave replication
func (sw *MySQLBaseSwitchInstance) StopSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to stop slave")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	stopSlaveSQL := "STOP SLAVE"

	err := slaveDB.DB().Exec(stopSlaveSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on slave(%s:%d), errmsg: %s", stopSlaveSQL, slaveIp, slavePort, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on slave(%s:%d)", stopSlaveSQL, slaveIp, slavePort)
	return nil
}

// StartSlave starts slave replication
func (sw *MySQLBaseSwitchInstance) StartSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to start slave")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	startSlaveSQL := "START SLAVE"

	err := slaveDB.DB().Exec(startSlaveSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on slave(%s:%d), errmsg: %s", startSlaveSQL, slaveIp, slavePort, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on slave(%s:%d)", startSlaveSQL, slaveIp, slavePort)
	return nil
}

// ShowMasterStatus retrieves master status information
func (sw *MySQLBaseSwitchInstance) ShowMasterStatus(db *hamysql.GormDB) (*MasterStatusInfo, error) {
	if db == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to show master status")
	}
	slaveIp := db.Host()
	slavePort := db.Port()
	showMasterSQL := "SHOW MASTER STATUS"

	masterStatus := &MasterStatusInfo{}
	err := db.DB().Raw(showMasterSQL).Scan(masterStatus).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on mysql(%s:%d), errmsg: %s", showMasterSQL, slaveIp, slavePort, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on mysql(%s:%d)", showMasterSQL, slaveIp, slavePort)

	return masterStatus, nil
}

// ShowSlaveStatus retrieves slave status information
func (sw *MySQLBaseSwitchInstance) ShowSlaveStatus(slaveDB *hamysql.GormDB) (*SlaveStatusInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to show slave status")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	showSlaveSQL := "SHOW SLAVE STATUS"

	slaveStatus := &SlaveStatusInfo{}
	err := slaveDB.DB().Raw(showSlaveSQL).Scan(slaveStatus).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on slave(%s:%d), errmsg: %s", showSlaveSQL, slaveIp, slavePort, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on slave(%s:%d)", showSlaveSQL, slaveIp, slavePort)

	return slaveStatus, nil
}

// ResetSlave resets slave replication settings
func (sw *MySQLBaseSwitchInstance) ResetSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to reset slave")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	resetSlaveSQL := "RESET SLAVE /*!50516 ALL */"

	err := slaveDB.DB().Exec(resetSlaveSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on mysql(%s:%d), errmsg: %s", resetSlaveSQL, slaveIp, slavePort, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on mysql(%s:%d)", resetSlaveSQL, slaveIp, slavePort)

	return nil
}

// ResetSlaveWithBinlogPos resets slave and gets consistent binlog position
func (sw *MySQLBaseSwitchInstance) ResetSlaveWithBinlogPos(slaveIp string, slavePort int) (string, uint64, error) {
	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
	)
	if err != nil {
		return "", 0, gerrors.Newf(gerrors.Failure,
			"failed to connect mysql slave(%s:%d) when resetting slave: %s", slaveIp, slavePort, err.Error())
	}

	defer func() {
		con, _ := slaveDB.DB().DB()
		if err = con.Close(); err != nil {
			sw.ReportLogf(switchlogger.SwitchWarn,
				"failed to close slave DB connect(%s:%d) after resetting slave: %s", slaveIp, slavePort, err.Error())
		}
	}()

	err = sw.StopSlave(slaveDB)
	if err != nil {
		return "", 0, err
	}

	masterStatus := &MasterStatusInfo{}
	masterStatus, err = sw.ShowMasterStatus(slaveDB)
	if err != nil {
		return "", 0, err
	}

	err = sw.ResetSlave(slaveDB)
	if err != nil {
		return masterStatus.File, masterStatus.Position, err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully reset slave status for the slave node(%s:%d), "+
		"binlog info: [binlog_file:%s, binlog_pos:%d]",
		slaveIp, slavePort, masterStatus.File, masterStatus.Position)

	return masterStatus.File, masterStatus.Position, nil
}

// ChangeMasterAuto automatically changes master configuration
func (sw *MySQLBaseSwitchInstance) ChangeMasterAuto(slaveIp string, slavePort int, changeMasterSQL string) error {
	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to connect mysql slave(%s:%d) when changing master: %s", slaveIp, slavePort, err.Error())
	}

	defer func() {
		con, _ := slaveDB.DB().DB()
		if err = con.Close(); err != nil {
			sw.ReportLogf(switchlogger.SwitchWarn,
				"failed to close slave DB connect(%s:%d) after changing master: %s", slaveIp, slavePort, err.Error())
		}
	}()

	err = sw.StopSlave(slaveDB)
	if err != nil {
		return err
	}

	slaveStatus, err := sw.ShowSlaveStatus(slaveDB)
	if err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "before switching to the new master node, "+
		"the actual synchronization position of the slave node(%s:%d) is: [binlog_file:%s, binlog_pos:%d]",
		slaveIp, slavePort, slaveStatus.RelayMasterLogFile, slaveStatus.ExecMasterLogPos)

	err = slaveDB.DB().Exec(changeMasterSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute '%s' on node(%s:%d), errmsg: %s",
			changeMasterSQL, slaveIp, slavePort, err.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on node(%s:%d)", changeMasterSQL, slaveIp, slavePort)

	err = sw.StartSlave(slaveDB)
	if err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully changed master for the slave node(%s:%d)", slaveIp, slavePort)
	return nil
}

// MySQLStorageSwitchInstance handles MySQL storage node switching
type MySQLStorageSwitchInstance struct {
	MySQLBaseSwitchInstance

	// Information obtained during switch

	NewMasterBinlogFile string
	NewMasterBinlogPos  uint64
}

// GetInstanceInfo returns instance information as string
func (sw *MySQLStorageSwitchInstance) GetInstanceInfo() string {
	standBySlave := "nil"
	if sw.StandBySlave != nil {
		standBySlave = fmt.Sprintf("%s:%d", sw.StandBySlave.Ip, sw.StandBySlave.Port)
	}
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, bk_idc_city_id:%d, bk_biz_id:%d, status:%s, "+
		"cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s, standby_slave:%s, is_stand_by:%t}",
		sw.BkCloudID, sw.IP, sw.Port, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole, standBySlave, sw.IsStandBy)
	return infoStr
}

// CheckMySQLStorageMaster performs pre-switch validation checks for "backend_master" node
func (sw *MySQLStorageSwitchInstance) CheckMySQLStorageMaster() (switchcore.SwitchCheckCode, error) {
	if sw.StandBySlave == nil {
		err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
	if sw.StandBySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(gerrors.Failure, "the standby slave(%s:%d) is unavailable",
			sw.StandBySlave.Ip, sw.StandBySlave.Port)
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	if err := sw.CheckSlaveStatus(); err != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "slave status check unpass: %s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	if len(sw.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure, "no proxy instances were found for this storage node")
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	return switchcore.SwitchRequired, nil
}

// CheckBeforeSwitch performs pre-switch validation checks
func (sw *MySQLStorageSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	switch sw.InstanceRole {
	case dbm.MySQLStorageSlave:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a slave node, no need to check")
		return switchcore.SwitchRequired, nil
	case dbm.MySQLStorageRepeater:
		sw.ReportLogf(switchlogger.SwitchWarn, "this is a repeater, dbha don't support")
		return switchcore.SwitchNotNeeded, nil
	case dbm.MySQLStorageMaster:
		return sw.CheckMySQLStorageMaster()
	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", sw.InstanceRole)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// SwitchProxyBackendAddress switches proxy backend to new address
func (sw *MySQLStorageSwitchInstance) SwitchProxyBackendAddress(proxyIp string, proxyAdminPort int,
	proxyUser string, proxyPasswd string, slaveIp string, slavePort int) error {
	proxyDB, err := hamysql.NewSqlxDB(
		hamysql.OptionIP(proxyIp),
		hamysql.OptionPort(proxyAdminPort),
		hamysql.OptionUser(proxyUser),
		hamysql.OptionPassword(proxyPasswd),
		hamysql.OptionCharset(""),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect proxy(%s:%d): %s", proxyIp, proxyAdminPort, err.Error())
	}

	defer func() {
		con := proxyDB.DB()
		if err = con.Close(); err != nil {
			sw.ReportLogf(switchlogger.SwitchWarn, "failed to close connection of proxy(%s:%d): %s", proxyIp, proxyAdminPort, err.Error())
		}
	}()

	switchSql := fmt.Sprintf("refresh_backends('%s:%d',1)", slaveIp, slavePort)
	querySql := "select * from backends"

	_, err = proxyDB.DB().Exec(switchSql)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on proxy(%s:%d), errmsg: %s",
			switchSql, proxyIp, proxyAdminPort, err.Error())
	}

	var backendList []ProxyBackendInfo
	err = proxyDB.DB().Select(&backendList, querySql)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on proxy(%s:%d), errmsg: %s",
			querySql, proxyIp, proxyAdminPort, err.Error())
	}

	slaveAddress := fmt.Sprintf("%s:%d", slaveIp, slavePort)
	for _, oneBackend := range backendList {
		if oneBackend.Address == slaveAddress {
			sw.ReportLogf(switchlogger.SwitchInfo, "successfully refresh proxy(%s:%d) backends to %s", proxyIp, proxyAdminPort, slaveAddress)
			// TODO: There are some redundant processing logics in dbha-v1 here, will modify after understanding it better
			return nil
		}
	}
	return gerrors.Newf(gerrors.Failure, "failed to refresh proxy(%s:%d) backends to %s",
		proxyIp, proxyAdminPort, slaveAddress)
}

// DoMasterSwitch performs the actual MySQL storage master switch
//  1. refresh all proxies' backends to 1.1.1.1
//  2. reset slave status for the standby slave and get its
//     consistent synchronization position(binlog file and binlog position)
//  3. refresh all proxies' backends to the alive mysql(standby slave)
func (sw *MySQLStorageSwitchInstance) DoMasterSwitch() error {
	proxyUser := config.Cfg.Database.Mysql.ProxyUser
	proxyPasswd := config.Cfg.Database.Mysql.ProxyPassword

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 1: update all proxies' backends to 1.1.1.1 first")
	for _, proxyIns := range sw.ProxyInstanceSet {
		err := sw.SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, proxyUser, proxyPasswd,
			"1.1.1.1", 3306)
		if err != nil {
			err = gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to 1.1.1.1 for the proxy(%s:%d), errmsg: %s",
				proxyIns.Ip, proxyIns.Port, err.Error())
			sw.ReportLog(switchlogger.SwitchWarn, err.Error())
			return err
		}
	}
	sw.ReportLog(switchlogger.SwitchInfo, "successfully update all proxies' backends to 1.1.1.1")

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 2: reset slave status for the standby slave")
	binlogFile, binlogPosition, err := sw.ResetSlaveWithBinlogPos(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		err = gerrors.Newf(gerrors.Failure, "failed to reset slave status for the standby slave(%s:%d), errmsg: %s",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return err
	}

	sw.NewMasterBinlogFile = binlogFile
	sw.NewMasterBinlogPos = binlogPosition

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 3: update all proxies' backends to the new master")
	for _, proxyIns := range sw.ProxyInstanceSet {
		err = sw.SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, proxyUser,
			proxyPasswd, sw.StandBySlave.Ip, sw.StandBySlave.Port)
		if err != nil {
			err = gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to (%s:%d) for the proxy(%s:%d), errmsg: %s",
				sw.StandBySlave.Ip, sw.StandBySlave.Port, proxyIns.Ip, proxyIns.Port, err.Error())
			sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		}
	}
	sw.ReportLog(switchlogger.SwitchInfo, "successfully update all proxies' backends to the new master")

	return nil
}

// DoSlaveSwitch performs the actual MySQL storage slave switch
func (sw *MySQLStorageSwitchInstance) DoSlaveSwitch() error {
	if sw.IsStandBy {
		sw.ReportLogf(switchlogger.SwitchInfo, "nothing to do for the standby slave")
		return nil
	}

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 1: delete this slave storage instance from all bound entries")
	return sw.DeleteNameService(sw.BindEntry)
}

// DoSwitch performs the actual switch for MySQL backend nodes
func (sw *MySQLStorageSwitchInstance) DoSwitch() error {
	switch sw.InstanceRole {
	case dbm.MySQLStorageSlave:
		return sw.DoSlaveSwitch()

	case dbm.MySQLStorageMaster:
		return sw.DoMasterSwitch()

	default:
		return gerrors.Newf(gerrors.Failure, "the instance role(%s) is not supported when doing switch",
			sw.InstanceRole)
	}
}

// UpdateMetaInfo swaps roles of backend master and slave
func (sw *MySQLStorageSwitchInstance) UpdateMetaInfo() error {
	if sw.InstanceRole != dbm.MySQLStorageMaster {
		sw.ReportLogf(switchlogger.SwitchInfo, "nothing to do for the instance role(%s) when updating meta info",
			sw.InstanceRole)
		return nil
	}

	err := sw.DbmClient.SwapMySQLRole(sw.BkCloudID, sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		errMsg := fmt.Sprintf("failed to swap roles of backend nodes(master:%s:%d, slave:%s:%d), errmsg:%s",
			sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, errMsg)
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully swap roles of backend nodes(master:%s:%d, slave:%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	return nil
}

// DoFinal performs final operations after switch completion
func (sw *MySQLStorageSwitchInstance) DoFinal() error {
	sw.ReportLogf(switchlogger.SwitchInfo, "tbinlogdumpers info of current mysql: %s", sw.GetBinlogDumperInfo())

	if (sw.InstanceRole != dbm.MySQLStorageMaster) || len(sw.BinlogDumperSet) == 0 {
		sw.ReportLogf(switchlogger.SwitchInfo, "no need to switch tbinlogdumper for current mysql")
		return nil
	}

	switchInstances := []dbm.DumperSwitchInstance{}
	for _, dumper := range sw.BinlogDumperSet {
		switchInstances = append(switchInstances, dbm.DumperSwitchInstance{
			Ip:             dumper.Ip,
			Port:           dumper.Port,
			BinlogFile:     sw.NewMasterBinlogFile,
			BinlogPosition: sw.NewMasterBinlogPos,
		})
	}

	SwitchInfos := []dbm.DumperSwitchInfo{
		{
			ClusterDomain:   sw.Cluster,
			SwitchInstances: switchInstances,
		},
	}

	err := sw.DbmClient.SwitchBinlogDumper(sw.BkCloudID, sw.GetApp(), SwitchInfos)
	if err != nil {
		errMsg := fmt.Sprintf("failed to switch all tbinlogdumpers for current mysql, errmsg: %s",
			err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully switch all tbinlogdumpers for current mysql")

	return nil
}

// MySQLProxySwitchInstance handles MySQL proxy node switching
type MySQLProxySwitchInstance struct {
	MySQLBaseSwitchInstance
}

// DoSwitch deletes proxy instance from bound entries
func (sw *MySQLProxySwitchInstance) DoSwitch() error {
	sw.ReportLog(switchlogger.SwitchInfo, "switch step 1: delete this proxy instance from all bound entries")
	return sw.DeleteNameService(sw.BindEntry)
}

// GetInstanceInfo returns instance information as string
func (sw *MySQLProxySwitchInstance) GetInstanceInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, admin_port:%d, bk_idc_city_id:%d, "+
		"bk_biz_id:%d, status:%s, cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.AdminPort, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType)
	return infoStr
}
